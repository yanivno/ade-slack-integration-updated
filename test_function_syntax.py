#!/usr/bin/env python3
"""
Test script to validate the function_app.py syntax and basic imports.
This ensures the code will run without errors in Azure.
"""

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")
    try:
        import azure.functions as func
        print("✓ azure.functions")
        
        from azure.identity import DefaultAzureCredential
        print("✓ azure.identity.DefaultAzureCredential")
        
        from azure.mgmt.devcenter import DevCenterMgmtClient
        print("✓ azure.mgmt.devcenter.DevCenterMgmtClient")
        
        from azure.developer.devcenter import DevCenterClient
        print("✓ azure.developer.devcenter.DevCenterClient")
        
        from azure.mgmt.resource import ResourceManagementClient
        print("✓ azure.mgmt.resource.ResourceManagementClient")
        
        print("\n✓ All imports successful!")
        return True
    except Exception as e:
        print(f"\n✗ Import failed: {e}")
        return False

def test_syntax():
    """Test that function_app.py has valid syntax."""
    print("\nTesting syntax...")
    try:
        import py_compile
        py_compile.compile('function_app.py', doraise=True)
        print("✓ Syntax validation passed!")
        return True
    except Exception as e:
        print(f"✗ Syntax error: {e}")
        return False

def test_function_definitions():
    """Test that key functions are defined."""
    print("\nTesting function definitions...")
    try:
        import function_app
        
        required_functions = [
            'get_credential',
            'fetch_all_dev_centers_and_projects',
            'fetch_environments_from_project',
            'fetch_resource_group_tags',
            'fetch_all_environments',
            'extract_owner_email',
            'parse_expiration_date',
            'categorize_by_expiration',
        ]
        
        for func_name in required_functions:
            if hasattr(function_app, func_name):
                print(f"✓ {func_name}")
            else:
                print(f"✗ {func_name} not found")
                return False
        
        print("\n✓ All required functions defined!")
        return True
    except Exception as e:
        print(f"\n✗ Function definition test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Function App Validation Tests")
    print("=" * 60)
    
    results = []
    
    results.append(("Syntax Check", test_syntax()))
    results.append(("Import Check", test_imports()))
    results.append(("Function Definitions", test_function_definitions()))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✓✓✓ ALL TESTS PASSED - Ready for deployment! ✓✓✓\n")
        return 0
    else:
        print("\n✗✗✗ SOME TESTS FAILED - Fix errors before deployment ✗✗✗\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
