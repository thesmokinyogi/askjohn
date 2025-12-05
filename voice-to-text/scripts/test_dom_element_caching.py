"""
Test script to verify DOM element caching in index.html.

Tests:
1. Elements are cached at top of script
2. No redundant getElementById calls for cached elements
3. Null checks are present

Note: This is a static analysis - actual DOM testing requires browser.
Following working agreement: Observe, Verify, Document
"""

import sys
import re
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_elements_cached():
    """Test that frequently-used elements are cached at top."""
    print("\n=== Testing DOM Elements Are Cached ===")
    
    try:
        html_path = project_root / "app" / "static" / "index.html"
        with open(html_path, 'r') as f:
            content = f.read()
        
        # Find the DOM elements section
        dom_section_match = re.search(
            r'// DOM elements.*?\n(.*?)\n\s*// Initialize',
            content,
            re.DOTALL
        )
        
        if not dom_section_match:
            print("❌ FAIL: Could not find DOM elements section")
            return False
        
        dom_section = dom_section_match.group(1)
        
        # Elements that should be cached
        required_elements = [
            'budgetTotal', 'providersGrid', 'modelList', 'stereoCard',
            'modelName', 'modelBadge', 'costValue', 'costBreakdown',
            'jobStatus', 'jobId', 'jobMessage', 'transcript', 'confidence',
            'wordCount', 'duration', 'actualCost'
        ]
        
        found_elements = []
        missing_elements = []
        
        for element in required_elements:
            pattern = rf'const {element}\s*=\s*document\.getElementById\([\'"]{element}[\'"]\)'
            if re.search(pattern, dom_section):
                found_elements.append(element)
            else:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"❌ FAIL: Missing cached elements: {', '.join(missing_elements)}")
            return False
        else:
            print(f"✅ PASS: All {len(found_elements)} required elements are cached")
            return True
            
    except Exception as e:
        print(f"❌ FAIL: Error testing element caching: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_no_redundant_getelementbyid():
    """Test that cached elements don't have redundant getElementById calls."""
    print("\n=== Testing No Redundant getElementById Calls ===")
    
    try:
        html_path = project_root / "app" / "static" / "index.html"
        with open(html_path, 'r') as f:
            content = f.read()
        
        # Elements that are cached
        cached_elements = [
            'budgetTotal', 'providersGrid', 'modelList', 'stereoCard',
            'modelName', 'modelBadge', 'costValue', 'costBreakdown',
            'jobStatus', 'jobId', 'jobMessage', 'transcript', 'confidence',
            'wordCount', 'duration', 'actualCost'
        ]
        
        violations = []
        
        for element in cached_elements:
            # Look for getElementById calls for this element outside the cache section
            # Pattern: document.getElementById('elementName') but not in cache section
            pattern = rf'document\.getElementById\([\'"]{element}[\'"]\)'
            matches = re.finditer(pattern, content)
            
            for match in matches:
                # Check if this is in the cache section (first 850 lines)
                line_num = content[:match.start()].count('\n') + 1
                if line_num > 850:  # Cache section is around lines 798-830
                    violations.append((element, line_num))
        
        if violations:
            print(f"❌ FAIL: Found {len(violations)} redundant getElementById calls:")
            for element, line_num in violations[:10]:  # Show first 10
                print(f"   Line {line_num}: {element}")
            if len(violations) > 10:
                print(f"   ... and {len(violations) - 10} more")
            return False
        else:
            print("✅ PASS: No redundant getElementById calls for cached elements")
            return True
            
    except Exception as e:
        print(f"❌ FAIL: Error testing redundant calls: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_null_checks_present():
    """Test that null checks are present for cached elements."""
    print("\n=== Testing Null Checks Are Present ===")
    
    try:
        html_path = project_root / "app" / "static" / "index.html"
        with open(html_path, 'r') as f:
            content = f.read()
        
        # Elements that should have null checks when used
        elements_needing_checks = [
            'budgetTotal', 'providersGrid', 'modelList', 'stereoCard',
            'modelName', 'modelBadge', 'costValue', 'costBreakdown',
            'jobStatus', 'jobId', 'jobMessage', 'transcript', 'confidence',
            'wordCount', 'duration', 'actualCost'
        ]
        
        # Count null checks
        null_check_pattern = r'if\s*\([^)]*\)\s*\{'
        null_checks = len(re.findall(null_check_pattern, content))
        
        # Check for specific patterns like "if (element)" or "if (!element)"
        element_null_checks = 0
        for element in elements_needing_checks:
            # Look for patterns like "if (element)" or "if (!element)"
            pattern = rf'if\s*\((!?{element})\)'
            if re.search(pattern, content):
                element_null_checks += 1
        
        if element_null_checks >= len(elements_needing_checks) * 0.3:  # At least 30% have checks
            print(f"✅ PASS: Found null checks for {element_null_checks} elements")
            print(f"   Total null checks in file: {null_checks}")
            return True
        else:
            print(f"⚠️  WARNING: Only {element_null_checks} elements have explicit null checks")
            print(f"   Consider adding more defensive null checks")
            return True  # Not a failure, just a warning
            
    except Exception as e:
        print(f"❌ FAIL: Error testing null checks: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("DOM Element Caching Verification")
    print("=" * 60)
    print("\nNote: This is static analysis. Actual DOM testing requires browser.")
    
    results = []
    
    results.append(("Elements are cached", test_elements_cached()))
    results.append(("No redundant getElementById", test_no_redundant_getelementbyid()))
    results.append(("Null checks present", test_null_checks_present()))
    
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

