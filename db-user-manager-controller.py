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
import signal

from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
from datetime import datetime, timezone

log_level = logging.INFO

if os.environ.get('LOG_LEVEL'):
    match os.environ.get('LOG_LEVEL'):
        case "DEBUG":
            log_level = logging.DEBUG
        case "INFO":
            log_level = logging.INFO
        case "WARNING":
            log_level = logging.WARNING
        case "ERROR":
            log_level = logging.ERROR
        case "CRITICAL":
            log_level = logging.CRITICAL

log = logging.getLogger(__name__)
logging.getLogger().setLevel(log_level)

handler = logging.StreamHandler(sys.stderr)
handler.setLevel(log_level)
# [%(asctime)s] [%(name)s]
formatter = logging.Formatter('[%(levelname)s] %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)

def update_request_status(request, phase, message=None):
    """
    Patch the status subresource of a DbUserRequest.
    Use this instead of deleting the request so ArgoCD self-heal is preserved.
    """
    api = client.CustomObjectsApi()
    metadata_obj = request.get('metadata', {})
    name = metadata_obj.get('name')
    namespace = metadata_obj.get('namespace')
    status_body = {
        "status": {
            "phase": phase,
            "message": message or "",
            "lastUpdated": datetime.now(timezone.utc).isoformat()
        }
    }
    try:
        api.patch_namespaced_custom_object_status(
            group="notepass.de",
            version="v1",
            namespace=namespace,
            plural="dbuserrequests",
            name=name,
            body=status_body
        )
        log.info(f"Updated status of DbUserRequest '{name}' in '{namespace}' to '{phase}'")
    except ApiException as e:
        log.error(f"Failed to patch status for {name}/{namespace}: {e}")
        raise

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

def call_create_script(request, password):
    spec = request.get('spec')
    db_type = spec.get('db_type').lower()
    db_name = spec.get('db_name').lower()

    extensions = []
    if db_type == 'mariadb':
        script_path = './create-mariadb-user.sh'
    elif db_type == 'postgres':
        script_path = './create-pg-user.sh'
        pg_options = spec.get('postgres', {})
        pg_extensions = pg_options.get('extensions')
        extensions = spec.get('extensions')
        if pg_extensions and isinstance(pg_extensions, list):
            extensions = pg_extensions
    else:
        raise Exception(f"Unknown database type '{db_type}'.")

        # Call the script with parameters (pass lowercase db name and generated password)
    cmd = [script_path, db_name, password]
    if extensions and isinstance(extensions, list):
        cmd.extend(str(ext) for ext in extensions)
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        log.info(f"Successfully called {script_path} to create DB {db_name}. Output:\n====[STDOUT]====\n {result.stdout}\n====[STDERR]====\n{result.stderr}\n====[END]====")
        return db_name
    else:
        raise Exception(f"Script {script_path} returned with exit code {result.returncode}.\n====[STDOUT]====\n {result.stdout}\n====[STDERR]====\n{result.stderr}\n====[END]====")

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

def find_existing_secret(name, namespace):
    """
    Find an existing Kubernetes Secret by name in the given namespace.

    Args:
        name: Name of the Secret resource to look up
        namespace: Namespace where the Secret resource should reside

    Returns:
        The V1Secret object if found, otherwise None.
    """
    v1 = client.CoreV1Api()
    try:
        secret = v1.read_namespaced_secret(name=name, namespace=namespace)
        return secret
    except ApiException as e:
        if hasattr(e, 'status') and e.status == 404:
            return None
        raise Exception(f"Exception when retrieving Secret '{name}' in namespace '{namespace}': {e}")

def create_secret_for_request(request, password):
    metadata_obj = request.get('metadata')
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

    create_secret(values, spec.get('secret_name'), metadata_obj.get('namespace'))

def create_secret(values, name, namespace):
    log.info(f"Creating DB user secret '{name}' in '{namespace}'")

    encoded_values = {}
    for key, value in values.items():
        encoded_values[key] = base64.b64encode(value.encode("utf-8")).decode('utf-8')

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
                # TODO: Move isInstance logic to validation
                # TODO: Parse reqeust as object an pass that to make life easier
                if not isinstance(event, dict):
                    log.warning(f"Received non-dict event: {event}. Skipping.")
                    continue
                event_type = event.get('type')
                if event_type == 'ADDED':
                    db_user_request = event.get('object', {})
                    if db_user_request.get('status', {}).get('phase', 'UNSET') != "Pending":
                        log.debug(f"Not processing DBUR '{db_user_request.get('metadata', {}).get('namespace')}:{db_user_request.get('metadata', {}).get('name')}', as state is '{db_user_request.get('status', {}).get('phase', 'UNSET')}' and not 'Pending'")
                        continue
                    if not isinstance(db_user_request, dict):
                        log.warning(f"Received non-dict db_user_request: {db_user_request}. Skipping.")
                        continue
                    source_name = db_user_request.get('metadata', {}).get('name')
                    source_namespace = db_user_request.get('metadata', {}).get('namespace')
                    log.info(f"New DbUserRequest created with name '{source_name}' in '{source_namespace}'. Trying to process")
                    try:
                        validate_user_request(db_user_request)
                    except Exception as exc:
                        log.error(f"Validation failed for request with name '{source_name}' in '{source_namespace}': {exc}. Will ignore request.")
                        continue

                    # TODO: Also checkk if the secret already exists. Creation order is secret -> dbuser -> delete request!
                    if find_existing_secret(db_user_request.get('spec', {}).get('secret_name'), db_user_request.get('metadata', {}).get('namespace')):
                        msg = f"Secret with name '{db_user_request.get('spec', {}).get('secret_name')}' already exists, skipping creating of new DB/User. Will skip request. Note: Will create DbUser for entry"
                        log.info(msg)
                        update_request_status(db_user_request, "Fulfilled", msg)
                    else:
                        password = generate_simple_password()
                        db_name_and_username = call_create_script(db_user_request, password)
                        create_secret_for_request(db_user_request, password)
                        msg = f"DbUser for DB {db_name_and_username} with username {db_name_and_username} successfully created. Credentials stored in secret {db_user_request.get('spec', {}).get('secret_name')}."
                        log.info(msg)
                        update_request_status(db_user_request, "Fulfilled", msg)

            except Exception as ex:
                log.error(f"Error while in event processing loop: {ex}. Trying to continue.")
                log.debug(f"Trace:\n{traceback.format_exc()}")
                update_request_status(event.get('object', {}), "Failed", f"Error while trying to process: {ex}")
    except Exception as e:
        raise Exception(f"Error while trying to loop over events: {e}")

def validate_db_name(db_name):
    if not db_name:
        raise Exception("DB name may not be empty")

    if not regex.match(r'^[a-z0-9_]+$', db_name):
        raise Exception("DB name is not valid. Allowed a-z0-9_")

def validate_k8s_resource_name(resource_name):
    if not regex.match(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$', resource_name):
        raise Exception(f"Invalid name for a resource: \"{resource_name}\": a lowercase RFC 1123 subdomain must consist of lower case alphanumeric characters, '-' or '.', and must start and end with an alphanumeric character (e.g. 'example.com', regex used for validation is '[a-z0-9[]([-a-z0-9[]*[a-z0-9[])?(\\\\.[a-z0-9[]([-a-z0-9[]*[a-z0-9[])?)*')")

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

    try:
        validate_k8s_resource_name(secret_name)
    except Exception as e:
        raise Exception(f"Validation error: The secret_name value '{user_and_db_name}' is invalid: {e}")

shutdown_flag = False

def handle_sigterm(signum, frame):
    global shutdown_flag
    log.info("Received SIGTERM, shutting down...")
    shutdown_flag = True

signal.signal(signal.SIGTERM, handle_sigterm)

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

        try:
            db_user_request_thread.start()
        except Exception as e:
            log.fatal(f"Failed to start thread. Exiting. Cause: {e}")
            sys.exit(2)

        log.info("Watcher started successfully")

        # Keep the main thread alive, exit immediately on shutdown_flag
        while not shutdown_flag:
            time.sleep(1)

        log.info("Main loop exiting due to shutdown flag.")
        sys.exit(0)

    except KeyboardInterrupt:
        log.info("Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        log.fatal(f"Fatal error in execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()