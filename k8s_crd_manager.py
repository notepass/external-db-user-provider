#!/usr/bin/env python3
"""
Kubernetes CRD Manager
A script to create and manage Kubernetes resources from Custom Resource Definitions (CRDs)
"""

import os
import sys
import subprocess
import time
import threading
import re
import secrets
import string
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException


def validate_db_name(db_name):
    """
    Validate database name to ensure it only contains letters, numbers, and underscores
    
    Args:
        db_name: The database name to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not db_name:
        return False, "Database name cannot be empty"
    
    # Check if name only contains letters, numbers, and underscores
    if not re.match(r'^[a-zA-Z0-9_]+$', db_name):
        return False, f"Database name '{db_name}' contains invalid characters. Only letters, numbers, and underscores are allowed."
    
    return True, None


def generate_db_password(length=24):
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


def create_db_credentials_secret(secret_name, namespace, db_username, db_password, db_type, custom_db_name_prop=None):
    """
    Create a Kubernetes Secret with database credentials
    
    Args:
        secret_name: Name of the secret to create
        namespace: Kubernetes namespace
        db_username: Database username (uppercase db name)
        db_password: Generated database password
        db_type: Database type (mariadb or postgres)
        custom_db_name_prop: Optional custom database name property
        
    Returns:
        The created secret object
    """
    import base64
    
    v1 = client.CoreV1Api()
    
    # Prepare secret data (all values must be base64 encoded)
    secret_data = {
        'dbUsername': base64.b64encode(db_username.encode()).decode('utf-8'),
        'dbPassword': base64.b64encode(db_password.encode()).decode('utf-8'),
        'dbDb': base64.b64encode(db_username.encode()).decode('utf-8'),  # Same as username
        'dbType': base64.b64encode(db_type.encode()).decode('utf-8'),
    }
    
    # Add dbNameAlt based on db_type
    if db_type.lower() == 'mariadb':
        db_name_alt = 'MySQL'
    elif db_type.lower() == 'postgres':
        db_name_alt = 'postgresql'
    else:
        db_name_alt = db_type
    
    secret_data['dbNameAlt'] = base64.b64encode(db_name_alt.encode()).decode('utf-8')
    
    # Add dbNameCustom only if custom_db_name_prop is provided
    if custom_db_name_prop:
        secret_data['dbNameCustom'] = base64.b64encode(custom_db_name_prop.encode()).decode('utf-8')
    
    # Create the secret object
    secret = client.V1Secret(
        api_version='v1',
        kind='Secret',
        metadata=client.V1ObjectMeta(
            name=secret_name,
            namespace=namespace
        ),
        type='Opaque',
        data=secret_data
    )
    
    try:
        response = v1.create_namespaced_secret(namespace=namespace, body=secret)
        print(f"Secret '{secret_name}' created successfully in namespace '{namespace}'")
        return response
    except ApiException as e:
        print(f"Exception when creating secret: {e}")
        raise


def load_k8s_config():
    """Load Kubernetes configuration from cluster or local kubeconfig"""
    try:
        # Try to load in-cluster config first (when running in a pod)
        config.load_incluster_config()
        print("Loaded in-cluster Kubernetes configuration")
    except config.ConfigException:
        try:
            # Fallback to local kubeconfig file
            config.load_kube_config()
            print("Loaded local kubeconfig")
        except config.ConfigException as e:
            print(f"Error loading Kubernetes configuration: {e}")
            sys.exit(1)


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
        print(f"Created custom resource: {response['metadata']['name']}")
        return response
    except ApiException as e:
        print(f"Exception when creating custom resource: {e}")
        raise


def get_crd_resource(group, version, namespace, plural, name):
    """
    Get a custom resource from a CRD
    
    Args:
        group: API group of the CRD
        version: API version of the CRD
        namespace: Kubernetes namespace
        plural: Plural name of the CRD
        name: Name of the resource
    """
    api_instance = client.CustomObjectsApi()
    
    try:
        response = api_instance.get_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
            name=name
        )
        print(f"Retrieved custom resource: {name}")
        return response
    except ApiException as e:
        print(f"Exception when retrieving custom resource: {e}")
        raise


def delete_crd_resource(group, version, namespace, plural, name):
    """
    Delete a custom resource from a CRD
    
    Args:
        group: API group of the CRD
        version: API version of the CRD
        namespace: Kubernetes namespace
        plural: Plural name of the CRD
        name: Name of the resource
    """
    api_instance = client.CustomObjectsApi()
    
    try:
        response = api_instance.delete_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
            name=name
        )
        print(f"Deleted custom resource: {name}")
        return response
    except ApiException as e:
        print(f"Exception when deleting custom resource: {e}")
        raise


def find_existing_dbuser_by_db_name(db_name, namespace):
    """
    Find an existing DbUser by db_name in the specified namespace
    
    Args:
        db_name: The database name to search for (uppercase)
        namespace: Kubernetes namespace to search in
        
    Returns:
        DbUser object if found, None otherwise
    """
    api_instance = client.CustomObjectsApi()
    group = 'notepass.de'
    version = 'v1'
    plural = 'dbuser'
    
    try:
        # List all DbUser objects in the namespace
        response = api_instance.list_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural
        )
        
        # Check if any DbUser has a matching db_name
        for item in response.get('items', []):
            spec = item.get('spec', {})
            existing_db_name = spec.get('db_name', '')
            if existing_db_name == db_name:
                print(f"Found existing DbUser with db_name '{db_name}': {item['metadata']['name']}")
                return item
        
        return None
    except ApiException as e:
        print(f"Exception when listing DbUser objects: {e}")
        return None


def create_event_for_resource(resource_name, namespace, resource_uid, reason, message, event_type='Warning'):
    """
    Create a Kubernetes event for a custom resource
    
    Args:
        resource_name: Name of the resource the event is about
        namespace: Kubernetes namespace
        resource_uid: UID of the resource
        reason: Short, machine-understandable string for the reason
        message: Human-readable description of the event
        event_type: Type of event (Normal or Warning)
    """
    v1 = client.CoreV1Api()
    
    try:
        from datetime import datetime, timezone
        
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
            source=client.V1EventSource(component='k8s-crd-manager')
        )
        
        v1.create_namespaced_event(namespace=namespace, body=event)
        print(f"Event created for {resource_name}: {reason}")
        return event
    except ApiException as e:
        print(f"Exception when creating event: {e}")
    except Exception as e:
        print(f"Error creating event: {e}")


def handle_db_user_creation(db_user_request):
    """
    Handle creation of a DbUserRequest custom resource
    Calls the appropriate database user creation script based on db_name
    
    Args:
        db_user_request: The DbUserRequest custom resource object
    """
    try:
        spec = db_user_request.get('spec', {})
        db_type = spec.get('db_type', '')
        custom_db_name_prop = spec.get('custom_db_name_prop', '')
        secret_name = spec.get('secret_name', '')
        metadata = db_user_request.get('metadata', {})
        resource_name = metadata.get('name', 'unknown')
        namespace = metadata.get('namespace', 'default')
        resource_uid = metadata.get('uid', '')
        
        print(f"Handling creation of DbUserRequest: {resource_name}")
        print(f"  db_type: {db_type}")
        print(f"  custom_db_name_prop: {custom_db_name_prop}")
        print(f"  secret_name: {secret_name}")
        
        # Validate the database name
        is_valid, error_message = validate_db_name(custom_db_name_prop)
        if not is_valid:
            print(f"Validation error: {error_message}")
            # Create an event for the validation failure
            create_event_for_resource(
                resource_name=resource_name,
                namespace=namespace,
                resource_uid=resource_uid,
                reason='ValidationFailed',
                message=error_message,
                event_type='Warning'
            )
            return
        
        # Convert database name to uppercase
        db_name_uppercase = custom_db_name_prop.upper()
        print(f"  db_name_uppercase: {db_name_uppercase}")
        
        # Check if a DbUser with this db_name already exists
        existing_dbuser = find_existing_dbuser_by_db_name(db_name_uppercase, namespace)
        if existing_dbuser:
            print(f"DbUser with db_name '{db_name_uppercase}' already exists. Skipping creation.")
            # Create an event to indicate the request was already fulfilled
            create_event_for_resource(
                resource_name=resource_name,
                namespace=namespace,
                resource_uid=resource_uid,
                reason='AlreadyExists',
                message=f"DbUser with db_name '{db_name_uppercase}' already exists. Request considered fulfilled.",
                event_type='Normal'
            )
            
            # Delete the DbUserRequest as it's considered fulfilled
            try:
                group = 'notepass.de'
                version = 'v1'
                delete_crd_resource(group, version, namespace, 'dbuserrequests', resource_name)
                print(f"DbUserRequest '{resource_name}' deleted as it was already fulfilled.")
            except Exception as e:
                print(f"Failed to delete DbUserRequest '{resource_name}': {e}")
            return
        
        # Generate a secure database password
        db_password = generate_db_password(24)
        print(f"  Generated password (length: {len(db_password)})")
        
        # Determine which script to call based on db_name
        if db_type.lower() == 'mariadb':
            script_path = './create-mariadb-user.sh'
        elif db_type.lower() == 'postgres':
            script_path = './create-pg-user.sh'
        else:
            print(f"Warning: Unknown db_name '{db_type}'. No action taken.")
            return
        
        # Call the script with parameters (pass uppercase db name and generated password)
        cmd = [script_path, resource_name, db_type, db_name_uppercase, db_password]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print(f"Script output: {result.stdout}")
        if result.stderr:
            print(f"Script errors: {result.stderr}")
        print(f"Script exit code: {result.returncode}")

        # If user creation was successful, create a DbUser object and delete the DbUserRequest
        if result.returncode == 0:
            group = 'notepass.de'
            version = 'v1'
            namespace = metadata.get('namespace', 'default')
            
            # Create Kubernetes Secret with database credentials if secret_name is provided
            if secret_name:
                try:
                    create_db_credentials_secret(
                        secret_name=secret_name,
                        namespace=namespace,
                        db_username=db_name_uppercase,
                        db_password=db_password,
                        db_type=db_type,
                        custom_db_name_prop=custom_db_name_prop if custom_db_name_prop else None
                    )
                except Exception as e:
                    print(f"Failed to create secret '{secret_name}': {e}")
                    # Create an event for the secret creation failure
                    create_event_for_resource(
                        resource_name=resource_name,
                        namespace=namespace,
                        resource_uid=resource_uid,
                        reason='SecretCreationFailed',
                        message=f"Failed to create secret '{secret_name}': {str(e)}",
                        event_type='Warning'
                    )
            else:
                print("No secret_name provided, skipping secret creation")
            
            # Create DbUser object with the request data from DbUserRequest spec
            try:
                from datetime import datetime, timezone
                db_user_body = {
                    'apiVersion': f'{group}/{version}',
                    'kind': 'DbUser',
                    'metadata': {
                        'name': resource_name,
                        'namespace': namespace
                    },
                    'spec': {
                        'db_name': db_name_uppercase,  # Store the uppercase db_name
                        'request': spec,  # Store the entire spec from DbUserRequest
                        'created': datetime.now(timezone.utc).isoformat()
                    }
                }
                create_crd_resource(group, version, namespace, 'dbuser', db_user_body)
                print(f"DbUser '{resource_name}' created successfully with db_name '{db_name_uppercase}'.")
            except Exception as e:
                print(f"Failed to create DbUser '{resource_name}': {e}")
            
            # Delete the DbUserRequest CRD after creating DbUser
            try:
                delete_crd_resource(group, version, namespace, 'dbuserrequests', resource_name)
                print(f"DbUserRequest '{resource_name}' deleted after successful creation.")
            except Exception as e:
                print(f"Failed to delete DbUserRequest '{resource_name}': {e}")
        else:
            # Script failed - create an event for the DbUserRequest
            print(f"DbUserRequest '{resource_name}' not deleted due to script error.")
            namespace = metadata.get('namespace', 'default')
            resource_uid = metadata.get('uid', '')
            
            error_message = f"User creation script failed with exit code {result.returncode}."
            if result.stderr:
                error_message += f" Error: {result.stderr.strip()}"
            elif result.stdout:
                error_message += f" Output: {result.stdout.strip()}"
            
            create_event_for_resource(
                resource_name=resource_name,
                namespace=namespace,
                resource_uid=resource_uid,
                reason='CreationFailed',
                message=error_message,
                event_type='Warning'
            )

    except Exception as e:
        print(f"Error handling DbUserRequest creation: {e}")
        # Create an event for the unexpected error
        try:
            metadata = db_user_request.get('metadata', {})
            resource_name = metadata.get('name', 'unknown')
            namespace = metadata.get('namespace', 'default')
            resource_uid = metadata.get('uid', '')
            
            error_message = f"Unexpected error during user creation: {str(e)}"
            create_event_for_resource(
                resource_name=resource_name,
                namespace=namespace,
                resource_uid=resource_uid,
                reason='UnexpectedError',
                message=error_message,
                event_type='Warning'
            )
        except Exception as event_error:
            print(f"Failed to create event for unexpected error: {event_error}")


def handle_db_user_deletion(db_user_request):
    """
    Handle deletion of a DbUserRequest custom resource
    Calls the appropriate database user disable script based on db_name
    
    Args:
        db_user_request: The DbUserRequest custom resource object
    """
    try:
        spec = db_user_request.get('spec', {})
        db_type = spec.get('db_type', '')
        custom_db_name_prop = spec.get('custom_db_name_prop', '')
        metadata = db_user_request.get('metadata', {})
        resource_name = metadata.get('name', 'unknown')

        print(f"Handling creation of DbUserRequest: {resource_name}")
        print(f"  db_type: {db_type}")
        print(f"  custom_db_name_prop: {custom_db_name_prop}")

        # Determine which script to call based on db_name
        if db_type.lower() == 'mariadb':
            script_path = './create-mariadb-user.sh'
        elif db_type.lower() == 'postgres':
            script_path = './create-pg-user.sh'
        else:
            print(f"Warning: Unknown db_name '{db_type}'. No action taken.")
            return
        
        # Call the script with parameters
        cmd = [script_path, resource_name, db_type, custom_db_name_prop]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print(f"Script output: {result.stdout}")
        if result.stderr:
            print(f"Script errors: {result.stderr}")
        print(f"Script exit code: {result.returncode}")
        
    except Exception as e:
        print(f"Error handling DbUserRequest deletion: {e}")


def handle_db_user_object_deletion(db_user):
    """
    Handle deletion of a DbUser custom resource
    Calls delete-pg-user.sh script with db_name from the request object
    
    Args:
        db_user: The DbUser custom resource object
    """
    try:
        spec = db_user.get('spec', {})
        request = spec.get('request', {})
        db_name = request.get('db_name', '')
        metadata = db_user.get('metadata', {})
        resource_name = metadata.get('name', 'unknown')
        
        print(f"Handling deletion of DbUser: {resource_name}")
        print(f"  db_name from request: {db_name}")
        
        if not db_name:
            print(f"Warning: No db_name found in request object. No action taken.")
            return
        
        # Call the delete-pg-user.sh script with db_name parameter
        script_path = './delete-pg-user.sh'
        cmd = [script_path, db_name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print(f"Script output: {result.stdout}")
        if result.stderr:
            print(f"Script errors: {result.stderr}")
        print(f"Script exit code: {result.returncode}")
        
    except Exception as e:
        print(f"Error handling DbUser deletion: {e}")


def watch_db_user_requests():
    """
    Watch for DbUserRequest custom resources and handle create/delete events
    across all namespaces
    """
    api_instance = client.CustomObjectsApi()
    group = 'notepass.de'
    version = 'v1'
    plural = 'dbuserrequests'
    
    print(f"Starting to watch DbUserRequest resources in all namespaces")
    print("=" * 60)
    
    w = watch.Watch()
    
    try:
        for event in w.stream(
            api_instance.list_custom_object_for_all_namespaces,
            group,
            version,
            plural
        ):
            event_type = event['type']
            db_user_request = event['object']
            resource_name = db_user_request.get('metadata', {}).get('name', 'unknown')
            resource_namespace = db_user_request.get('metadata', {}).get('namespace', 'unknown')
            
            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Event: {event_type} - {resource_namespace}/{resource_name}")
            
            if event_type == 'ADDED':
                handle_db_user_creation(db_user_request)
            #elif event_type == 'DELETED':
            #    handle_db_user_deletion(db_user_request)
            elif event_type == 'MODIFIED':
                print(f"DbUserRequest {resource_name} was modified (no action taken)")
            
    except KeyboardInterrupt:
        print("\nStopping watch...")
        w.stop()
    except ApiException as e:
        print(f"API Exception while watching: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error while watching: {e}")
        raise


def watch_db_users():
    """
    Watch for DbUser custom resources and handle deletion events
    across all namespaces
    """
    api_instance = client.CustomObjectsApi()
    group = 'notepass.de'
    version = 'v1'
    plural = 'dbuser'
    
    print(f"Starting to watch DbUser resources in all namespaces")
    print("=" * 60)
    
    w = watch.Watch()
    
    try:
        for event in w.stream(
            api_instance.list_custom_object_for_all_namespaces,
            group,
            version,
            plural
        ):
            event_type = event['type']
            db_user = event['object']
            resource_name = db_user.get('metadata', {}).get('name', 'unknown')
            resource_namespace = db_user.get('metadata', {}).get('namespace', 'unknown')
            
            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Event: {event_type} - {resource_namespace}/{resource_name}")
            
            if event_type == 'DELETED':
                handle_db_user_object_deletion(db_user)
            elif event_type == 'ADDED':
                print(f"DbUser {resource_name} was added (no action taken)")
            elif event_type == 'MODIFIED':
                print(f"DbUser {resource_name} was modified (no action taken)")
            
    except KeyboardInterrupt:
        print("\nStopping watch...")
        w.stop()
    except ApiException as e:
        print(f"API Exception while watching: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error while watching: {e}")
        raise


def main():
    """Main function to watch and manage DbUserRequest and DbUser CRDs"""
    print("Kubernetes CRD Manager")
    print("=" * 60)
    
    # Load Kubernetes configuration
    load_k8s_config()
    
    # Verify connection to Kubernetes cluster
    try:
        v1 = client.CoreV1Api()
        #namespaces = v1.list_namespace()
        print(f"\nSuccessfully connected to Kubernetes cluster")
        #print(f"Found {len(namespaces.items)} namespaces")
        
    except ApiException as e:
        print(f"Error connecting to Kubernetes: {e}")
        sys.exit(1)
    
    print(f"\nStarting to watch for DbUserRequest and DbUser resources...")
    print(f"Watching all namespaces")
    print(f"Press Ctrl+C to stop\n")
    
    # Start watching for both DbUserRequest and DbUser resources in separate threads
    try:
        # Create threads for both watchers
        db_user_request_thread = threading.Thread(
            target=watch_db_user_requests,
            daemon=True,
            name="DbUserRequestWatcher"
        )
        
        db_user_thread = threading.Thread(
            target=watch_db_users,
            daemon=True,
            name="DbUserWatcher"
        )
        
        # Start both threads
        db_user_request_thread.start()
        db_user_thread.start()
        
        print("Both watchers started successfully\n")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
