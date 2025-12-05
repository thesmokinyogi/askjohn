#!/usr/bin/env python3
"""
Test script to verify budget display logic in the UI.

This simulates the JavaScript budget display logic to identify issues.
"""

import json
import sys
from pathlib import Path

# Simulate the budget API response
def get_budget_api_response():
    """Simulate what /api/budget returns."""
    budget_file = Path(__file__).parent.parent / "data" / "budget_tracking.json"
    
    if not budget_file.exists():
        return {
            "month": "2025-11",
            "monthly_budget": 250.0,
            "total_spent": 0.0,
            "remaining": 250.0,
            "percent_used": 0.0,
            "providers": {}
        }
    
    with open(budget_file, 'r') as f:
        data = json.load(f)
    
    # Calculate total spent (same logic as BudgetService._calculate_total_spent)
    total_spent = 0.0
    for provider_data in data.get("providers", {}).values():
        total_spent += provider_data.get("total_cost", 0.0)
    
    monthly_budget = data.get("monthly_budget", 250.0)
    remaining = monthly_budget - total_spent
    
    return {
        "month": data.get("month", "2025-11"),
        "monthly_budget": monthly_budget,
        "total_spent": round(total_spent, 2),
        "remaining": round(remaining, 2),
        "percent_used": round((total_spent / monthly_budget * 100), 1) if monthly_budget > 0 else 0,
        "providers": data.get("providers", {})
    }


# Simulate JavaScript updateBudgetDisplay function
def simulate_update_budget_display(budget_data, budget_total_element_exists=True):
    """
    Simulate the JavaScript updateBudgetDisplay function.
    
    Args:
        budget_data: The budget data object (or None)
        budget_total_element_exists: Whether the budgetTotal DOM element exists
    
    Returns:
        Tuple of (success, display_text, error_message)
    """
    # Simulate: if (!budgetData) return;
    if not budget_data:
        return (False, None, "budgetData is null/undefined")
    
    # Simulate: if (budgetTotal) { ... }
    if not budget_total_element_exists:
        return (False, None, "budgetTotal element not found")
    
    # Simulate: const spent = budgetData.total_spent || 0;
    spent = budget_data.get("total_spent") if budget_data.get("total_spent") is not None else 0
    
    # Simulate: const budget = budgetData.monthly_budget || 250;
    budget = budget_data.get("monthly_budget") if budget_data.get("monthly_budget") is not None else 250
    
    # Simulate: budgetTotal.textContent = `$${spent.toFixed(2)} / $${budget.toFixed(0)}`;
    try:
        display_text = f"${spent:.2f} / ${budget:.0f}"
        return (True, display_text, None)
    except Exception as e:
        return (False, None, f"Error formatting display: {e}")


def test_budget_display():
    """Run tests on budget display logic."""
    print("=" * 60)
    print("Budget Display Logic Test")
    print("=" * 60)
    
    # Test 1: Get actual API response
    print("\n1. Testing API Response:")
    print("-" * 60)
    api_response = get_budget_api_response()
    print(f"   API Response: {json.dumps(api_response, indent=2)}")
    print(f"   ✓ total_spent: ${api_response['total_spent']:.2f}")
    print(f"   ✓ monthly_budget: ${api_response['monthly_budget']:.0f}")
    
    # Test 2: Simulate updateBudgetDisplay with valid data
    print("\n2. Testing updateBudgetDisplay with valid data:")
    print("-" * 60)
    success, display_text, error = simulate_update_budget_display(api_response, budget_total_element_exists=True)
    if success:
        print(f"   ✓ Display text: {display_text}")
    else:
        print(f"   ✗ Error: {error}")
    
    # Test 3: Test with null budgetData
    print("\n3. Testing updateBudgetDisplay with null budgetData:")
    print("-" * 60)
    success, display_text, error = simulate_update_budget_display(None, budget_total_element_exists=True)
    if not success:
        print(f"   ✓ Correctly handles null: {error}")
    else:
        print(f"   ✗ Should have failed but didn't!")
    
    # Test 4: Test with missing total_spent
    print("\n4. Testing updateBudgetDisplay with missing total_spent:")
    print("-" * 60)
    incomplete_data = {"monthly_budget": 250.0}
    success, display_text, error = simulate_update_budget_display(incomplete_data, budget_total_element_exists=True)
    if success:
        print(f"   ✓ Display text (with default): {display_text}")
    else:
        print(f"   ✗ Error: {error}")
    
    # Test 5: Test with missing monthly_budget
    print("\n5. Testing updateBudgetDisplay with missing monthly_budget:")
    print("-" * 60)
    incomplete_data = {"total_spent": 1.8}
    success, display_text, error = simulate_update_budget_display(incomplete_data, budget_total_element_exists=True)
    if success:
        print(f"   ✓ Display text (with default): {display_text}")
    else:
        print(f"   ✗ Error: {error}")
    
    # Test 6: Test with zero values
    print("\n6. Testing updateBudgetDisplay with zero values:")
    print("-" * 60)
    zero_data = {"total_spent": 0.0, "monthly_budget": 250.0}
    success, display_text, error = simulate_update_budget_display(zero_data, budget_total_element_exists=True)
    if success:
        print(f"   ✓ Display text: {display_text}")
        if display_text == "$0.00 / $250":
            print("   ✓ Correctly displays zero")
        else:
            print(f"   ✗ Expected '$0.00 / $250' but got '{display_text}'")
    else:
        print(f"   ✗ Error: {error}")
    
    # Test 7: Test actual current data
    print("\n7. Testing with actual current budget data:")
    print("-" * 60)
    success, display_text, error = simulate_update_budget_display(api_response, budget_total_element_exists=True)
    if success:
        print(f"   ✓ Display text: {display_text}")
        expected = f"${api_response['total_spent']:.2f} / ${api_response['monthly_budget']:.0f}"
        if display_text == expected:
            print(f"   ✓ Matches expected: {expected}")
        else:
            print(f"   ✗ Expected '{expected}' but got '{display_text}'")
    else:
        print(f"   ✗ Error: {error}")
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"API total_spent: ${api_response['total_spent']:.2f}")
    print(f"Expected display: ${api_response['total_spent']:.2f} / ${api_response['monthly_budget']:.0f}")
    
    if api_response['total_spent'] > 0:
        print("\n⚠️  If UI shows $0.00, possible causes:")
        print("   1. budgetData is null when updateBudgetDisplay() is called")
        print("   2. budgetTotal element is null (DOM not ready)")
        print("   3. loadBudget() is failing silently")
        print("   4. updateBudgetDisplay() is called before loadBudget() completes")
        print("   5. JavaScript error preventing execution")
    else:
        print("\n✓ Budget data shows $0.00 because no costs recorded yet")


if __name__ == "__main__":
    test_budget_display()

