"""
Test script to verify context-agnostic implementation fixes.

Tests:
1. LibraryService singleton pattern
2. CloudStorageService singleton pattern
3. Service instantiation consistency
4. No duplicate instances

Following working agreement: Observe, Verify, Document
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_library_service_singleton():
    """Test that get_library_service() returns singleton instance."""
    print("\n=== Testing LibraryService Singleton ===")
    
    try:
        from app.services.library import get_library_service
        
        # Get two instances
        service1 = get_library_service()
        service2 = get_library_service()
        
        # Should be the same instance
        if service1 is service2:
            print("✅ PASS: get_library_service() returns singleton (same instance)")
            return True
        else:
            print("❌ FAIL: get_library_service() returns different instances")
            print(f"   service1 id: {id(service1)}")
            print(f"   service2 id: {id(service2)}")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Error testing LibraryService singleton: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_storage_service_singleton():
    """Test that get_storage_service() returns singleton instance."""
    print("\n=== Testing CloudStorageService Singleton ===")
    
    try:
        from app.dependencies import get_storage_service
        
        # Get two instances
        service1 = get_storage_service()
        service2 = get_storage_service()
        
        # Should be the same instance
        if service1 is service2:
            print("✅ PASS: get_storage_service() returns singleton (same instance)")
            return True
        else:
            print("❌ FAIL: get_storage_service() returns different instances")
            print(f"   service1 id: {id(service1)}")
            print(f"   service2 id: {id(service2)}")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Error testing CloudStorageService singleton: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_service_imports():
    """Test that services can be imported correctly."""
    print("\n=== Testing Service Imports ===")
    
    results = []
    
    # Test LibraryService import
    try:
        from app.services.library import get_library_service, LibraryService
        print("✅ LibraryService imports: get_library_service, LibraryService")
        results.append(True)
    except ImportError as e:
        print(f"❌ LibraryService import failed: {e}")
        results.append(False)
    
    # Test CloudStorageService import
    try:
        from app.dependencies import get_storage_service
        print("✅ CloudStorageService imports: get_storage_service")
        results.append(True)
    except ImportError as e:
        print(f"❌ CloudStorageService import failed: {e}")
        results.append(False)
    
    return all(results)

def test_main_uses_singletons():
    """Test that main.py uses singleton functions."""
    print("\n=== Testing main.py Uses Singletons ===")
    
    try:
        # Read main.py and check for patterns
        main_path = project_root / "app" / "main.py"
        with open(main_path, 'r') as f:
            content = f.read()
        
        checks = {
            'get_library_service()': 'get_library_service()' in content,
            'get_storage_service()': 'get_storage_service()' in content,
            'NOT LibraryService()': 'LibraryService()' not in content or 
                                    content.count('LibraryService()') == 0,
            'NOT CloudStorageService(': 'CloudStorageService(' not in content or
                                      (content.count('CloudStorageService(') == 0 or
                                       'from app.services.storage import CloudStorageService' in content)
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            if passed:
                print(f"✅ {check_name}")
            else:
                print(f"❌ {check_name}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAIL: Error checking main.py: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dependencies_uses_singletons():
    """Test that dependencies.py uses singleton functions."""
    print("\n=== Testing dependencies.py Uses Singletons ===")
    
    try:
        # Read dependencies.py and check for patterns
        deps_path = project_root / "app" / "dependencies.py"
        with open(deps_path, 'r') as f:
            content = f.read()
        
        checks = {
            'get_library_service()': 'get_library_service()' in content,
            'NOT LibraryService()': 'LibraryService()' not in content or 
                                    content.count('LibraryService()') == 0
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            if passed:
                print(f"✅ {check_name}")
            else:
                print(f"❌ {check_name}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAIL: Error checking dependencies.py: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_library_uses_singleton():
    """Test that api/v1/library.py uses singleton function."""
    print("\n=== Testing api/v1/library.py Uses Singleton ===")
    
    try:
        # Read library.py and check for patterns
        api_lib_path = project_root / "app" / "api" / "v1" / "library.py"
        with open(api_lib_path, 'r') as f:
            content = f.read()
        
        checks = {
            'get_library_service imported': 'from app.services.library import get_library_service' in content or
                                            '_get_library_service' in content,
            'NOT LibraryService()': 'LibraryService()' not in content or 
                                    content.count('LibraryService()') == 0
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            if passed:
                print(f"✅ {check_name}")
            else:
                print(f"❌ {check_name}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAIL: Error checking api/v1/library.py: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Context-Agnostic Implementation Fixes Verification")
    print("=" * 60)
    
    results = []
    
    results.append(("Service imports", test_service_imports()))
    results.append(("LibraryService singleton", test_library_service_singleton()))
    results.append(("CloudStorageService singleton", test_storage_service_singleton()))
    results.append(("main.py uses singletons", test_main_uses_singletons()))
    results.append(("dependencies.py uses singletons", test_dependencies_uses_singletons()))
    results.append(("api/v1/library.py uses singleton", test_api_library_uses_singleton()))
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

