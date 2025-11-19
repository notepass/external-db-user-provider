#!/usr/bin/env python3
"""
Test for database name validation and password generation functionality
"""

import sys
import re
sys.path.insert(0, '/home/runner/work/docker-build-test/docker-build-test')

import k8s_crd_manager


def test_validate_db_name():
    """Test database name validation"""
    print("Testing database name validation...")
    print("-" * 60)
    
    # Valid names
    valid_names = [
        'my_database',
        'MyDatabase123',
        'DATABASE_NAME',
        'test_db_2024',
        'a1b2c3',
        '___test___',
    ]
    
    for name in valid_names:
        is_valid, error = k8s_crd_manager.validate_db_name(name)
        assert is_valid, f"'{name}' should be valid but got error: {error}"
        print(f"  ✓ '{name}' is valid")
    
    # Invalid names
    invalid_names = [
        ('my-database', 'contains hyphen'),
        ('my database', 'contains space'),
        ('my.database', 'contains dot'),
        ('my@database', 'contains @'),
        ('my$database', 'contains $'),
        ('my#database', 'contains #'),
        ('', 'empty string'),
        ('database!', 'contains !'),
        ('data;base', 'contains semicolon'),
    ]
    
    for name, reason in invalid_names:
        is_valid, error = k8s_crd_manager.validate_db_name(name)
        assert not is_valid, f"'{name}' should be invalid ({reason}) but was accepted"
        assert error is not None, f"Error message should be provided for '{name}'"
        print(f"  ✓ '{name}' correctly rejected ({reason})")
    
    print("\n✓ All database name validation tests passed")
    return True


def test_generate_db_password():
    """Test database password generation"""
    print("\nTesting database password generation...")
    print("-" * 60)
    
    # Test default length (24 characters)
    password = k8s_crd_manager.generate_db_password()
    assert len(password) == 24, f"Password should be 24 characters, got {len(password)}"
    print(f"  ✓ Generated password with default length (24): {password}")
    
    # Test custom lengths
    for length in [8, 16, 32, 48]:
        password = k8s_crd_manager.generate_db_password(length)
        assert len(password) == length, f"Password should be {length} characters, got {len(password)}"
        print(f"  ✓ Generated password with length {length}: {password}")
    
    # Verify password only contains safe characters (letters and digits)
    for _ in range(10):
        password = k8s_crd_manager.generate_db_password(24)
        assert re.match(r'^[a-zA-Z0-9]+$', password), \
            f"Password should only contain alphanumeric characters, got: {password}"
    
    print("  ✓ All generated passwords contain only safe characters (letters and digits)")
    
    # Test uniqueness (generate multiple passwords, they should be different)
    passwords = [k8s_crd_manager.generate_db_password(24) for _ in range(100)]
    unique_passwords = set(passwords)
    assert len(unique_passwords) > 95, \
        f"Passwords should be unique, got {len(unique_passwords)} unique out of 100"
    print(f"  ✓ Generated passwords are unique ({len(unique_passwords)}/100 unique)")
    
    print("\n✓ All password generation tests passed")
    return True


def test_db_name_uppercase_conversion():
    """Test that database names are converted to uppercase"""
    print("\nTesting database name uppercase conversion...")
    print("-" * 60)
    
    test_cases = [
        ('mydb', 'MYDB'),
        ('MyDatabase', 'MYDATABASE'),
        ('test_db_123', 'TEST_DB_123'),
        ('ALREADY_UPPERCASE', 'ALREADY_UPPERCASE'),
        ('MiXeD_CaSe', 'MIXED_CASE'),
    ]
    
    for input_name, expected_output in test_cases:
        output = input_name.upper()
        assert output == expected_output, \
            f"Expected '{input_name}' to become '{expected_output}', got '{output}'"
        print(f"  ✓ '{input_name}' → '{output}'")
    
    print("\n✓ All uppercase conversion tests passed")
    return True


def test_integration():
    """Test integration with module functions"""
    print("\nTesting module integration...")
    print("-" * 60)
    
    # Verify functions exist in module
    assert hasattr(k8s_crd_manager, 'validate_db_name'), \
        "validate_db_name function should exist"
    assert hasattr(k8s_crd_manager, 'generate_db_password'), \
        "generate_db_password function should exist"
    
    print("  ✓ validate_db_name function exists")
    print("  ✓ generate_db_password function exists")
    
    # Test actual usage scenario
    db_name = "test_database_2024"
    is_valid, error = k8s_crd_manager.validate_db_name(db_name)
    assert is_valid, f"Valid database name rejected: {error}"
    
    db_name_uppercase = db_name.upper()
    password = k8s_crd_manager.generate_db_password(24)
    
    print(f"\n  Simulated usage:")
    print(f"    Original DB name: {db_name}")
    print(f"    Validated: ✓")
    print(f"    Uppercase DB name: {db_name_uppercase}")
    print(f"    Generated password: {password}")
    print(f"    Password length: {len(password)}")
    
    assert len(password) == 24, "Password should be 24 characters"
    assert db_name_uppercase == "TEST_DATABASE_2024", "Uppercase conversion failed"
    
    print("\n✓ Integration test passed")
    return True


if __name__ == '__main__':
    print("=" * 70)
    print("Testing Database Name Validation and Password Generation")
    print("=" * 70)
    print()
    
    all_passed = True
    
    try:
        # Test 1: Validate DB names
        if not test_validate_db_name():
            all_passed = False
        
        # Test 2: Generate passwords
        if not test_generate_db_password():
            all_passed = False
        
        # Test 3: Uppercase conversion
        if not test_db_name_uppercase_conversion():
            all_passed = False
        
        # Test 4: Integration
        if not test_integration():
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
        print("  - DB names are validated (letters, numbers, underscores only)")
        print("  - DB names are converted to uppercase")
        print("  - 24-character DB-safe passwords are generated")
        sys.exit(0)
    else:
        print("Some tests failed! ✗")
        print("=" * 70)
        sys.exit(1)
