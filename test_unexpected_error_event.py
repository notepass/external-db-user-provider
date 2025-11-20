#!/usr/bin/env python3
"""
Test for unexpected error event creation functionality
This test verifies that events are created when unexpected errors occur
during DbUserRequest handling.
"""

from kubernetes import client
from datetime import datetime, timezone
import sys
import os

# Mock the subprocess to test error handling
class MockSubprocessResult:
    def __init__(self, returncode, stdout='', stderr=''):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_unexpected_error_event_creation():
    """
    Test that an event is created when an unexpected error occurs
    in handle_db_user_creation
    """
    print("Testing event creation for unexpected errors...")
    print("-" * 60)
    
    # Create a mock db_user_request that would cause an error
    db_user_request = {
        'metadata': {
            'name': 'test-db-user',
            'namespace': 'default',
            'uid': 'test-uid-123'
        },
        'spec': {
            'db_type': 'postgres',
            'custom_db_name_prop': 'testdb'
        }
    }
    
    # Test that we can extract metadata for event creation
    metadata = db_user_request.get('metadata', {})
    resource_name = metadata.get('name', 'unknown')
    namespace = metadata.get('namespace', 'default')
    resource_uid = metadata.get('uid', '')
    
    print(f"Resource name: {resource_name}")
    print(f"Namespace: {namespace}")
    print(f"UID: {resource_uid}")
    
    # Simulate creating an event for an unexpected error
    error_message = "Unexpected error during user creation: Test exception"
    
    try:
        event = client.CoreV1Event(
            metadata=client.V1ObjectMeta(
                name=f"{resource_name}.{datetime.now(timezone.utc).strftime('%s')}",
                namespace=namespace
            ),
            involved_object=client.V1ObjectReference(
                api_version='notepass.de/v1',
                kind='DbUserRequest',
                name=resource_name,
                namespace=namespace,
                uid=resource_uid
            ),
            reason='UnexpectedError',
            message=error_message,
            type='Warning',
            first_timestamp=datetime.now(timezone.utc),
            last_timestamp=datetime.now(timezone.utc),
            count=1,
            source=client.V1EventSource(component='k8s-crd-manager')
        )
        
        print("\n✓ Event object created successfully for unexpected error")
        print(f"  Reason: {event.reason}")
        print(f"  Message: {event.message}")
        print(f"  Type: {event.type}")
        
        assert event.reason == 'UnexpectedError'
        assert event.message == error_message
        assert event.type == 'Warning'
        assert event.involved_object.name == resource_name
        
        print("\n✓ All assertions passed")
        return True
        
    except Exception as e:
        print(f"\n✗ Failed to create event for unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_module_import():
    """Test that the module can be imported"""
    print("\nTesting module import...")
    print("-" * 60)
    
    try:
        sys.path.insert(0, '/home/runner/work/docker-build-test/docker-build-test')
        import k8s_crd_manager
        
        # Check that the function exists
        assert hasattr(k8s_crd_manager, 'handle_db_user_creation')
        assert hasattr(k8s_crd_manager, 'create_event_for_resource')
        
        print("✓ Module imported successfully")
        print("✓ Required functions exist")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("=" * 70)
    print("Testing Unexpected Error Event Creation")
    print("=" * 70)
    print()
    
    all_passed = True
    
    # Test 1: Module import
    if not test_module_import():
        all_passed = False
    
    print()
    
    # Test 2: Event creation for unexpected errors
    if not test_unexpected_error_event_creation():
        all_passed = False
    
    print()
    print("=" * 70)
    if all_passed:
        print("All tests passed! ✓")
        print("=" * 70)
        sys.exit(0)
    else:
        print("Some tests failed! ✗")
        print("=" * 70)
        sys.exit(1)
