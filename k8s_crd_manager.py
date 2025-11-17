#!/usr/bin/env python3
"""
Kubernetes CRD Manager
A script to create and manage Kubernetes resources from Custom Resource Definitions (CRDs)
"""

import os
import sys
from kubernetes import client, config
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


def list_crd_resources(group, version, namespace, plural):
    """
    List all custom resources from a CRD in a namespace
    
    Args:
        group: API group of the CRD
        version: API version of the CRD
        namespace: Kubernetes namespace
        plural: Plural name of the CRD
    """
    api_instance = client.CustomObjectsApi()
    
    try:
        response = api_instance.list_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural
        )
        print(f"Listed {len(response['items'])} custom resources")
        return response
    except ApiException as e:
        print(f"Exception when listing custom resources: {e}")
        raise


def main():
    """Main function to demonstrate CRD management"""
    print("Kubernetes CRD Manager")
    print("=" * 50)
    
    # Load Kubernetes configuration
    load_k8s_config()
    
    # Example usage - this would be customized based on specific CRDs
    # For demonstration, we'll just verify the connection works
    try:
        v1 = client.CoreV1Api()
        namespaces = v1.list_namespace()
        print(f"\nSuccessfully connected to Kubernetes cluster")
        print(f"Found {len(namespaces.items)} namespaces")
        
        # List the first 5 namespaces as a verification
        print("\nAvailable namespaces:")
        for ns in namespaces.items[:5]:
            print(f"  - {ns.metadata.name}")
            
    except ApiException as e:
        print(f"Error connecting to Kubernetes: {e}")
        sys.exit(1)
    
    print("\nCRD Manager is ready to manage custom resources")
    print("Use the provided functions to create, get, delete, or list CRD resources")


if __name__ == "__main__":
    main()
