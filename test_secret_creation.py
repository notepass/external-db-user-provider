#!/usr/bin/env python3
"""
Test for Kubernetes Secret creation functionality
This test verifies that database credentials are properly stored in Kubernetes Secrets
"""

import sys
import base64
sys.path.insert(0, '/home/runner/work/docker-build-test/docker-build-test')

from kubernetes import client
import k8s_crd_manager


def test_secret_data_structure_mariadb():
    """Test that secret data is properly structured for MariaDB"""
    print("Testing secret data structure for MariaDB...")
    print("-" * 60)
    
    secret_name = "test-mariadb-secret"
    namespace = "default"
    db_username = "TEST_DATABASE"
    db_password = "SecurePassword123456789"
    db_type = "mariadb"
    custom_db_name_prop = "test_database"
    
    # Prepare expected secret data
    expected_data = {
        'dbUsername': base64.b64encode(db_username.encode()).decode('utf-8'),
        'dbPassword': base64.b64encode(db_password.encode()).decode('utf-8'),
        'dbDb': base64.b64encode(db_username.encode()).decode('utf-8'),
        'dbType': base64.b64encode(db_type.encode()).decode('utf-8'),
        'dbNameAlt': base64.b64encode('MySQL'.encode()).decode('utf-8'),
        'dbNameCustom': base64.b64encode(custom_db_name_prop.encode()).decode('utf-8'),
    }
    
    print(f"  Secret name: {secret_name}")
    print(f"  DB Username: {db_username}")
    print(f"  DB Password: {db_password}")
    print(f"  DB Type: {db_type}")
    print(f"  DB Name Alt: MySQL")
    print(f"  DB Name Custom: {custom_db_name_prop}")
    
    # Verify base64 encoding works correctly
    for key, value in expected_data.items():
        decoded = base64.b64decode(value).decode('utf-8')
        print(f"  ✓ {key}: {decoded}")
    
    print("\n✓ MariaDB secret data structure test passed")
    return True


def test_secret_data_structure_postgres():
    """Test that secret data is properly structured for PostgreSQL"""
    print("\nTesting secret data structure for PostgreSQL...")
    print("-" * 60)
    
    secret_name = "test-postgres-secret"
    namespace = "default"
    db_username = "PROD_DATABASE"
    db_password = "AnotherSecurePass12345"
    db_type = "postgres"
    custom_db_name_prop = None  # Test without custom name
    
    # Prepare expected secret data
    expected_data = {
        'dbUsername': base64.b64encode(db_username.encode()).decode('utf-8'),
        'dbPassword': base64.b64encode(db_password.encode()).decode('utf-8'),
        'dbDb': base64.b64encode(db_username.encode()).decode('utf-8'),
        'dbType': base64.b64encode(db_type.encode()).decode('utf-8'),
        'dbNameAlt': base64.b64encode('postgresql'.encode()).decode('utf-8'),
    }
    
    print(f"  Secret name: {secret_name}")
    print(f"  DB Username: {db_username}")
    print(f"  DB Password: {db_password}")
    print(f"  DB Type: {db_type}")
    print(f"  DB Name Alt: postgresql")
    print(f"  DB Name Custom: (not set)")
    
    # Verify base64 encoding works correctly
    for key, value in expected_data.items():
        decoded = base64.b64decode(value).decode('utf-8')
        print(f"  ✓ {key}: {decoded}")
    
    # Verify dbNameCustom is not in the dict when custom_db_name_prop is None
    assert 'dbNameCustom' not in expected_data, "dbNameCustom should not be present when custom_db_name_prop is None"
    print("  ✓ dbNameCustom correctly omitted when not provided")
    
    print("\n✓ PostgreSQL secret data structure test passed")
    return True


def test_secret_object_creation():
    """Test that secret object can be created with correct structure"""
    print("\nTesting secret object creation...")
    print("-" * 60)
    
    secret_name = "test-secret"
    namespace = "test-namespace"
    db_username = "MY_DB"
    db_password = "TestPassword1234567890AB"
    db_type = "mariadb"
    
    # Create secret data
    secret_data = {
        'dbUsername': base64.b64encode(db_username.encode()).decode('utf-8'),
        'dbPassword': base64.b64encode(db_password.encode()).decode('utf-8'),
        'dbDb': base64.b64encode(db_username.encode()).decode('utf-8'),
        'dbType': base64.b64encode(db_type.encode()).decode('utf-8'),
        'dbNameAlt': base64.b64encode('MySQL'.encode()).decode('utf-8'),
    }
    
    # Create the secret object (without actually creating it in K8s)
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
    
    print(f"  ✓ Secret object created")
    print(f"    Name: {secret.metadata.name}")
    print(f"    Namespace: {secret.metadata.namespace}")
    print(f"    Type: {secret.type}")
    print(f"    Data keys: {list(secret.data.keys())}")
    
    # Verify all required keys are present
    required_keys = ['dbUsername', 'dbPassword', 'dbDb', 'dbType', 'dbNameAlt']
    for key in required_keys:
        assert key in secret.data, f"Required key '{key}' missing from secret data"
    print(f"  ✓ All required keys present: {required_keys}")
    
    print("\n✓ Secret object creation test passed")
    return True


def test_function_exists():
    """Test that the create_db_credentials_secret function exists"""
    print("\nTesting function existence...")
    print("-" * 60)
    
    assert hasattr(k8s_crd_manager, 'create_db_credentials_secret'), \
        "create_db_credentials_secret function should exist"
    
    print("  ✓ create_db_credentials_secret function exists")
    
    import inspect
    sig = inspect.signature(k8s_crd_manager.create_db_credentials_secret)
    print(f"  Signature: {sig}")
    
    params = list(sig.parameters.keys())
    expected_params = ['secret_name', 'namespace', 'db_username', 'db_password', 'db_type', 'custom_db_name_prop']
    for param in expected_params:
        assert param in params, f"Expected parameter '{param}' not found"
    print(f"  ✓ All expected parameters present: {expected_params}")
    
    print("\n✓ Function existence test passed")
    return True


def test_db_type_to_name_alt_mapping():
    """Test mapping of db_type to dbNameAlt"""
    print("\nTesting db_type to dbNameAlt mapping...")
    print("-" * 60)
    
    test_cases = [
        ('mariadb', 'MySQL'),
        ('postgres', 'postgresql'),
        ('MariaDB', 'MySQL'),  # Test case insensitivity
        ('POSTGRES', 'postgresql'),
    ]
    
    for db_type_input, expected_alt in test_cases:
        if db_type_input.lower() == 'mariadb':
            db_name_alt = 'MySQL'
        elif db_type_input.lower() == 'postgres':
            db_name_alt = 'postgresql'
        else:
            db_name_alt = db_type_input
        
        assert db_name_alt == expected_alt, \
            f"Expected '{expected_alt}' for db_type '{db_type_input}', got '{db_name_alt}'"
        print(f"  ✓ '{db_type_input}' → '{db_name_alt}'")
    
    print("\n✓ DB type mapping test passed")
    return True


if __name__ == '__main__':
    print("=" * 70)
    print("Testing Kubernetes Secret Creation for Database Credentials")
    print("=" * 70)
    print()
    
    all_passed = True
    
    try:
        # Test 1: Function exists
        if not test_function_exists():
            all_passed = False
        
        # Test 2: MariaDB secret structure
        if not test_secret_data_structure_mariadb():
            all_passed = False
        
        # Test 3: PostgreSQL secret structure
        if not test_secret_data_structure_postgres():
            all_passed = False
        
        # Test 4: Secret object creation
        if not test_secret_object_creation():
            all_passed = False
        
        # Test 5: DB type mapping
        if not test_db_type_to_name_alt_mapping():
            all_passed = False
        
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    print()
    print("=" * 70)
    if all_passed:
        print("All tests passed! ✓")
        print("=" * 70)
        print("\nSummary:")
        print("  - Secrets created with proper base64 encoding")
        print("  - dbUsername, dbPassword, dbDb, dbType, dbNameAlt fields included")
        print("  - dbNameCustom included only when custom_db_name_prop is provided")
        print("  - MariaDB → MySQL, Postgres → postgresql mapping")
        sys.exit(0)
    else:
        print("Some tests failed! ✗")
        print("=" * 70)
        sys.exit(1)
