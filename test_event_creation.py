#!/usr/bin/env python3
"""
Test for event creation functionality
This test verifies that the CoreV1Event can be properly instantiated
with the required parameters.
"""

from kubernetes import client
from datetime import datetime, timezone


def test_event_object_creation():
    """Test that CoreV1Event can be created with the correct parameters"""
    event_name = "test-event.12345"
    namespace = "default"
    resource_name = "test-resource"
    resource_uid = "test-uid-123"
    reason = "TestReason"
    message = "Test message"
    event_type = "Warning"
    
    # This should not raise an exception
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
    
    assert event.metadata.name == event_name
    assert event.metadata.namespace == namespace
    assert event.involved_object.name == resource_name
    assert event.involved_object.kind == 'DbUserRequest'
    assert event.reason == reason
    assert event.message == message
    assert event.type == event_type
    assert event.count == 1
    
    print("✓ All assertions passed")


def test_v1event_does_not_exist():
    """Verify that V1Event does not exist in the client module"""
    assert not hasattr(client, 'V1Event'), "V1Event should not exist in kubernetes.client"
    print("✓ Confirmed V1Event does not exist")


def test_corev1event_exists():
    """Verify that CoreV1Event exists in the client module"""
    assert hasattr(client, 'CoreV1Event'), "CoreV1Event should exist in kubernetes.client"
    print("✓ Confirmed CoreV1Event exists")


if __name__ == '__main__':
    print("Running event creation tests...")
    print()
    
    test_v1event_does_not_exist()
    test_corev1event_exists()
    test_event_object_creation()
    
    print()
    print("All tests passed! ✓")
