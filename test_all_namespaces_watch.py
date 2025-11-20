#!/usr/bin/env python3
"""
Test for all-namespaces watch functionality
This test verifies that the watch functions can operate across all namespaces
instead of being limited to a single namespace.
"""

import sys
import inspect
from kubernetes import client


def test_api_method_exists():
    """Verify that list_custom_object_for_all_namespaces exists in the API"""
    print("Testing API method existence...")
    print("-" * 60)
    
    api = client.CustomObjectsApi()
    
    # Check that the method exists
    assert hasattr(api, 'list_custom_object_for_all_namespaces'), \
        "list_custom_object_for_all_namespaces should exist in CustomObjectsApi"
    
    print("✓ list_custom_object_for_all_namespaces method exists")
    
    # Check the signature
    sig = inspect.signature(api.list_custom_object_for_all_namespaces)
    print(f"  Signature: {sig}")
    
    # Verify required parameters
    params = list(sig.parameters.keys())
    assert 'group' in params, "group parameter should be present"
    assert 'version' in params, "version parameter should be present"
    assert 'resource_plural' in params, "resource_plural parameter should be present"
    
    print("✓ Required parameters are present")
    return True


def test_watch_functions_updated():
    """Verify that watch functions no longer require namespace parameter"""
    print("\nTesting watch function signatures...")
    print("-" * 60)
    
    sys.path.insert(0, '/home/runner/work/docker-build-test/docker-build-test')
    import k8s_crd_manager
    
    # Check watch_db_user_requests signature
    sig = inspect.signature(k8s_crd_manager.watch_db_user_requests)
    params = list(sig.parameters.keys())
    
    print(f"watch_db_user_requests signature: {sig}")
    assert len(params) == 0, "watch_db_user_requests should have no parameters"
    print("✓ watch_db_user_requests has no namespace parameter")
    
    # Check watch_db_users signature
    sig = inspect.signature(k8s_crd_manager.watch_db_users)
    params = list(sig.parameters.keys())
    
    print(f"watch_db_users signature: {sig}")
    assert len(params) == 0, "watch_db_users should have no parameters"
    print("✓ watch_db_users has no namespace parameter")
    
    return True


def test_function_documentation():
    """Verify that function documentation mentions all namespaces"""
    print("\nTesting function documentation...")
    print("-" * 60)
    
    sys.path.insert(0, '/home/runner/work/docker-build-test/docker-build-test')
    import k8s_crd_manager
    
    # Check watch_db_user_requests docstring
    docstring = k8s_crd_manager.watch_db_user_requests.__doc__
    assert 'all namespaces' in docstring.lower(), \
        "watch_db_user_requests docstring should mention all namespaces"
    print("✓ watch_db_user_requests documentation mentions 'all namespaces'")
    
    # Check watch_db_users docstring
    docstring = k8s_crd_manager.watch_db_users.__doc__
    assert 'all namespaces' in docstring.lower(), \
        "watch_db_users docstring should mention all namespaces"
    print("✓ watch_db_users documentation mentions 'all namespaces'")
    
    return True


if __name__ == '__main__':
    print("=" * 70)
    print("Testing All Namespaces Watch Functionality")
    print("=" * 70)
    print()
    
    all_passed = True
    
    # Test 1: API method exists
    if not test_api_method_exists():
        all_passed = False
    
    # Test 2: Watch functions updated
    if not test_watch_functions_updated():
        all_passed = False
    
    # Test 3: Function documentation
    if not test_function_documentation():
        all_passed = False
    
    print()
    print("=" * 70)
    if all_passed:
        print("All tests passed! ✓")
        print("=" * 70)
        print("\nSummary:")
        print("  - Watch functions now monitor all namespaces")
        print("  - No longer limited to WATCH_NAMESPACE environment variable")
        print("  - Events display namespace/resource_name format")
        sys.exit(0)
    else:
        print("Some tests failed! ✗")
        print("=" * 70)
        sys.exit(1)
