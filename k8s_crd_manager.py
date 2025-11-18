#!/usr/bin/env python3
"""
Kubernetes CRD Manager
A script to create and manage Kubernetes resources from Custom Resource Definitions (CRDs)
"""

import os
import sys
import subprocess
import time
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException


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


def handle_db_user_creation(db_user_request):
    """
    Handle creation of a DbUserRequest custom resource
    Calls the appropriate database user creation script based on db_name
    
    Args:
        db_user_request: The DbUserRequest custom resource object
    """
    try:
        spec = db_user_request.get('spec', {})
        db_name = spec.get('db_name', '')
        custom_db_name_prop = spec.get('custom_db_name_prop', '')
        metadata = db_user_request.get('metadata', {})
        resource_name = metadata.get('name', 'unknown')
        
        print(f"Handling creation of DbUserRequest: {resource_name}")
        print(f"  db_name: {db_name}")
        print(f"  custom_db_name_prop: {custom_db_name_prop}")
        
        # Determine which script to call based on db_name
        if db_name.lower() == 'mariadb':
            script_path = './create-mariadb-user.sh'
        elif db_name.lower() == 'postgres':
            script_path = './create-pg-user.sh'
        else:
            print(f"Warning: Unknown db_name '{db_name}'. No action taken.")
            return
        
        # Call the script with parameters
        cmd = [script_path, resource_name, db_name, custom_db_name_prop]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print(f"Script output: {result.stdout}")
        if result.stderr:
            print(f"Script errors: {result.stderr}")
        print(f"Script exit code: {result.returncode}")
        
    except Exception as e:
        print(f"Error handling DbUserRequest creation: {e}")


def handle_db_user_deletion(db_user_request):
    """
    Handle deletion of a DbUserRequest custom resource
    Calls the appropriate database user disable script based on db_name
    
    Args:
        db_user_request: The DbUserRequest custom resource object
    """
    try:
        spec = db_user_request.get('spec', {})
        db_name = spec.get('db_name', '')
        custom_db_name_prop = spec.get('custom_db_name_prop', '')
        metadata = db_user_request.get('metadata', {})
        resource_name = metadata.get('name', 'unknown')
        
        print(f"Handling deletion of DbUserRequest: {resource_name}")
        print(f"  db_name: {db_name}")
        print(f"  custom_db_name_prop: {custom_db_name_prop}")
        
        # Determine which script to call based on db_name
        if db_name.lower() == 'mariadb':
            script_path = './disable-mariadb-user.sh'
        elif db_name.lower() == 'postgres':
            script_path = './disable-pg-user.sh'
        else:
            print(f"Warning: Unknown db_name '{db_name}'. No action taken.")
            return
        
        # Call the script with parameters
        cmd = [script_path, resource_name, db_name, custom_db_name_prop]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print(f"Script output: {result.stdout}")
        if result.stderr:
            print(f"Script errors: {result.stderr}")
        print(f"Script exit code: {result.returncode}")
        
    except Exception as e:
        print(f"Error handling DbUserRequest deletion: {e}")


def watch_db_user_requests(namespace='default'):
    """
    Watch for DbUserRequest custom resources and handle create/delete events
    
    Args:
        namespace: Kubernetes namespace to watch (default: 'default')
    """
    api_instance = client.CustomObjectsApi()
    group = 'notepass.de'
    version = 'v1'
    plural = 'dbuserrequests'
    
    print(f"Starting to watch DbUserRequest resources in namespace: {namespace}")
    print("=" * 60)
    
    w = watch.Watch()
    
    try:
        for event in w.stream(
            api_instance.list_namespaced_custom_object,
            group=group,
            version=version,
            namespace=namespace,
            plural=plural
        ):
            event_type = event['type']
            db_user_request = event['object']
            resource_name = db_user_request.get('metadata', {}).get('name', 'unknown')
            
            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Event: {event_type} - {resource_name}")
            
            if event_type == 'ADDED':
                handle_db_user_creation(db_user_request)
            elif event_type == 'DELETED':
                handle_db_user_deletion(db_user_request)
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


def main():
    """Main function to watch and manage DbUserRequest CRDs"""
    print("Kubernetes DbUserRequest CRD Manager")
    print("=" * 60)
    
    # Load Kubernetes configuration
    load_k8s_config()
    
    # Get namespace from environment variable or use default
    namespace = os.environ.get('WATCH_NAMESPACE', 'default')
    
    # Verify connection to Kubernetes cluster
    try:
        v1 = client.CoreV1Api()
        namespaces = v1.list_namespace()
        print(f"\nSuccessfully connected to Kubernetes cluster")
        print(f"Found {len(namespaces.items)} namespaces")
        
    except ApiException as e:
        print(f"Error connecting to Kubernetes: {e}")
        sys.exit(1)
    
    print(f"\nStarting to watch for DbUserRequest resources...")
    print(f"Namespace: {namespace}")
    print(f"Press Ctrl+C to stop\n")
    
    # Start watching for DbUserRequest resources
    try:
        watch_db_user_requests(namespace=namespace)
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
