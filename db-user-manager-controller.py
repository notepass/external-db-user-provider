import os
import sys
import subprocess
import time
import threading
import re as regex
import secrets
import string
import logging
import traceback
import base64
from importlib.metadata import metadata

from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
from datetime import datetime, timezone

log = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stderr)
handler.setLevel(logging.INFO)
# [%(asctime)s] [%(name)s]
formatter = logging.Formatter('[%(levelname)s] %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)

def generate_simple_password(length=24):
    """
    Generate a database-safe password

    Args:
        length: Length of the password (default: 24)

    Returns:
        str: A randomly generated password safe for database use
    """
    # Use alphanumeric characters (uppercase, lowercase, digits)
    # Avoid special characters that might cause issues in SQL contexts
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def create_event_for_request(request, reason, message, event_type='Warning'):
    """
    Create a Kubernetes event for a custom resource

    Args:
        request: DbUserRequest object
        reason: Short, machine-understandable string for the reason
        message: Human-readable description of the event
        event_type: Type of event (Normal or Warning)
    """
    metadata = request.get('metadata', {})
    resource_name = metadata.get('name')
    namespace = metadata.get('namespace')
    resource_uid = metadata.get('uid')

    log.info(f"metadata={metadata} / resource_name={resource_name} / namespace={namespace} / resource_uid={resource_uid}")

    v1 = client.CoreV1Api()

    event_name = f"{resource_name}.{datetime.now(timezone.utc).strftime('%s')}"

    event = client.CoreV1Event(
        metadata=client.V1ObjectMeta(
            name=event_name,
            namespace=namespace
        ),
        involved_object=client.V1ObjectReference(
            api_version='notepass.de/v1',
            kind='DbUserRequest',
            name=resource_name,
            namespace=namespace,
            uid=resource_uid
        ),
        reason=reason,
        message=message,
        type=event_type,
        first_timestamp=datetime.now(timezone.utc),
        last_timestamp=datetime.now(timezone.utc),
        count=1,
        source=client.V1EventSource(component='db-user-manager-controller')
    )

    v1.create_namespaced_event(namespace=namespace, body=event)
    return event

def delete_request(request):
    metadata = request.get('metadata')
    client.CustomObjectsApi().delete_namespaced_custom_object(
        group='notepass.de',
        version='v1',
        namespace=metadata.get('namespace'),
        plural='dbuserrequests',
        name=metadata.get('name')
    )

def call_create_script(request, password):
    spec = request.get('spec')
    db_type = spec.get('db_type').lower()
    db_name = spec.get('db_name').lower()

    if db_type == 'mariadb':
        script_path = './create-mariadb-user.sh'
    elif db_type == 'postgres':
        script_path = './create-pg-user.sh'
    else:
        raise Exception(f"Unknown database type '{db_type}'.")

        # Call the script with parameters (pass lowercase db name and generated password)
    cmd = [script_path, db_name, password]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        log.info(f"Successfully called {script_path} to create DB {db_name}.")
        return db_name
    else:
        raise Exception(f"Script {script_path} returned with exit code {result.returncode}.\n========\nSTDOUT: {result.stdout}\n========\nSTDERR:{result.stderr}")

def create_db_user(request):
    spec = request.get('spec')
    metadata = request.get('metadata')

    log.info(f"Creating according DbUser '{metadata.get('name')}' for DbUserRequest '{metadata.get('name')}'")
    db_user_body = {
        'apiVersion': f'notepass.de/v1',
        'kind': 'DbUser',
        'metadata': {
            'name': metadata.get('name'),
            'namespace': metadata.get('namespace')
        },
        'spec': {
            'db_name': spec.get('db_name').lower(),  # Store the lowercase db_name
            'request': spec,  # Store the entire spec from DbUserRequest
            'created': datetime.now(timezone.utc).isoformat()
        }
    }
    create_crd_resource('notepass.de', 'v1', metadata.get('namespace'), 'dbuser', db_user_body)
    log.info("DbUser created")

def create_crd_resource(group, version, namespace, plural, body):
    """
    Create a custom resource from a CRD

    Args:
        group: API group of the CRD
        version: API version of the CRD
        namespace: Kubernetes namespace
        plural: Plural name of the CRD
        body: Resource definition as a dictionary
    """
    api_instance = client.CustomObjectsApi()

    try:
        response = api_instance.create_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
            body=body
        )
        return response
    except ApiException as e:
        raise Exception(f"Exception when creating custom resource: {e}")

def create_custom_object_watch(plural):
    try:
        api_instance = client.CustomObjectsApi()
        return watch.Watch().stream(
            api_instance.list_custom_object_for_all_namespaces,
            "notepass.de",
            "v1",
            plural
        )
    except Exception as e:
        raise Exception(f"Could not create a watch for notepass.de:{plural}:v1. Reason: {e}")

def create_secret_for_request(request, password):
    metadata = request.get('metadata')
    spec = request.get('spec')
    is_pg = spec.get('db_type').lower() == 'postgres'

    db_type_alt = 'postgresql' if is_pg else 'mysql'
    db_host = os.environ['PGHOST'] if is_pg else os.environ['MYSQL_HOST']

    values = {
        "dbDb": spec.get('db_name').lower(),
        "dbHost": db_host,
        "dbPass": password,
        "dbSchema": "public",
        "dbType": spec.get('db_type').lower(),
        "dbTypeAlt": db_type_alt,
        "dbUser": spec.get('db_name').lower()
    }

    if spec.get('custom_db_name_prop'):
        values["dbTypeCustom"] = spec.get('custom_db_name_prop')

    create_secret(values, metadata.get('name'), metadata.get('namespace'))


def create_secret(values, name, namespace):
    log.info(f"Creating DB user secret '{name}' in '{namespace}'")

    encoded_values = {}
    for key, value in values.items():
        encoded_values[key] = base64.b64encode(value)

    secret = client.V1Secret(
        api_version='v1',
        kind='Secret',
        metadata=client.V1ObjectMeta(
            name=name,
            namespace=namespace
        ),
        type='Opaque',
        data=encoded_values
    )

    client.CoreV1Api().create_namespaced_secret(namespace=namespace, body=secret)
    log.info(f"Secret '{name}' in '{namespace}' created")

def watch_user_requests():
    log.info("Watching DB user requests")
    try:
        for event in create_custom_object_watch("dbuserrequests"):
            try:
                event_type = event['type']
                if event_type == 'ADDED':
                    db_user_request = event['object']
                    source_name = db_user_request.get('metadata', {}).get('name')
                    source_namespace = db_user_request.get('metadata', {}).get('namespace')
                    log.info(f"New DbUserRequest created with name '{source_name}' in '{source_namespace}'. Trying to process")
                    try:
                        validate_user_request(db_user_request)
                    except Exception as exc:
                        log.error(f"Validation failed for request with name '{source_name}' in '{source_namespace}': {exc}. Will ignore request.")
                        #create_event_for_request(db_user_request, 'ValidationFailed', exc)
                        continue
                    password = generate_simple_password()
                    db_name_and_username = call_create_script(db_user_request, password)
                    create_secret_for_request(db_user_request, password)
                    create_db_user(db_user_request)
                    delete_request(db_user_request)


            except Exception as ex:
                log.error(f"Error while in event processing loop: {ex}. Trying to continue. Trace:\n{traceback.format_exc()}")
    except Exception as e:
        raise Exception(f"Error while trying to loop over events: {e}")

def validate_db_name(db_name):
    if not db_name:
        raise Exception("DB name may not be empty")

    if not regex.match(r'^[a-z0-9_]+$', db_name):
        raise Exception("DB name is not valid. Allowed a-z0-9_")

def generate_db_password(length=24):
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def load_k8s_config():
    try:
        log.info("Attempting to load in-cluster-configuration")
        config.load_incluster_config()
        log.info("Loaded in-cluster-configuration")
    except config.ConfigException as e:
        log.warning(f"Failed to load in-cluster-configuration. Attempting to load kube config in case the application is running locally. Cause: {e}")
        try:
            config.load_kube_config()
            log.info("Loaded local kubeconfig")
        except config.ConfigException as ex:
            log.error(f"Error loading local kubeconfig configuration: {e}. Giving up.")
            raise Exception(f"Error loading local kubernetes configuration. Exhausted all sources:\nIn-cluster-source error: {e}\nLocal config error: {ex}")

def validate_user_request(request):
    spec = request.get('spec', {})
    db_type = spec.get('db_type')
    user_and_db_name = spec.get('db_name')
    secret_name = spec.get('secret_name')
    if not (db_type and user_and_db_name and secret_name):
        raise Exception(f"Validation error: db_type, db_name and/or secret_name are missing from the request object")

    if db_type.lower() != 'mariadb' and db_type.lower() != 'postgres':
        raise Exception(f"Validation error: Unknown database type '{db_type}'. Currently supported: 'postgres' and 'mariadb'.")

    try:
        validate_db_name(user_and_db_name)
    except Exception as e:
        raise Exception(f"Validation error: The db_name value '{user_and_db_name}' is invalid: {e}")

def watch_db_users():
    log.info("Watching DB users")

def main():
    log.info("Kubernetes external DB User manager")
    log.info("=" * 60)

    try:
        log.info("Loading configuration")
        load_k8s_config()
    except Exception as e:
        log.fatal(f"Failed to load configuration. Exiting. Cause: {e}")
        sys.exit(1)

    log.info("Starting CRD watcher threads")

    # Start watching for both DbUserRequest and DbUser resources in separate threads
    try:
        # Create threads for both watchers
        db_user_request_thread = threading.Thread(
            target=watch_user_requests,
            daemon=True,
            name="DbUserRequestWatcher"
        )

        db_user_thread = threading.Thread(
            target=watch_db_users,
            daemon=True,
            name="DbUserWatcher"
        )

        try:
            db_user_request_thread.start()
            db_user_thread.start()
        except Exception as e:
            log.fatal(f"Failed to start threads. Exiting. Cause: {e}")
            sys.exit(2)

        log.info("Both watchers started successfully")

        # Keep the main thread alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        log.info("Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        log.fatal(f"Fatal error in execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()