#!/usr/bin/env python3
"""
Test CostCalculationService independently.

Tests cost calculation boundary and free tier transition logic.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.cost_calculation import CostCalculationService
from app.services.pricing import PricingService
from app.services.budget import BudgetService
from unittest.mock import patch


def test_all_free():
    """Test scenario: All free (duration < free_remaining)."""
    print("\n=== Testing: All Free ===")
    
    # Create real services with mocked dependencies
    from app.services.pricing import PricingService
    from app.services.budget import BudgetService
    
    # Use real services but they'll use actual config
    # For testing, we'll patch the methods we need
    pricing_service = PricingService()
    budget_service = BudgetService()
    
    # Patch get_cost_per_minute to return our test value
    with patch.object(pricing_service, 'get_cost_per_minute', return_value=0.004):
        with patch.object(budget_service, 'get_free_tier_remaining', return_value=10.0):
            cost_service = CostCalculationService(pricing_service, budget_service)
    
            result = cost_service.calculate_actual_cost(
                provider="google",
                model="chirp_batch",
                billed_duration_minutes=2.0,
                estimated_duration_minutes=2.0,
                estimated_cost=0.008
            )
            
            expected_cost = 0.0
            expected_free_used = 2.0
            
            if result["actual_cost"] == expected_cost and result["actual_free_minutes_used"] == expected_free_used:
                print(f"  ✓ Duration: 2.0 min, Free remaining: 10.0 min")
                print(f"  ✓ Cost: ${result['actual_cost']:.4f} (expected ${expected_cost:.4f})")
                print(f"  ✓ Free used: {result['actual_free_minutes_used']:.2f} min (expected {expected_free_used:.2f} min)")
                return True
            else:
                print(f"  ❌ Expected cost=${expected_cost}, free_used={expected_free_used}")
                print(f"  ❌ Got cost=${result['actual_cost']}, free_used={result['actual_free_minutes_used']}")
                return False


def test_transition():
    """Test scenario: Transition (part free, part paid)."""
    print("\n=== Testing: Transition (Part Free, Part Paid) ===")
    
    from app.services.pricing import PricingService
    from app.services.budget import BudgetService
    
    pricing_service = PricingService()
    budget_service = BudgetService()
    
    with patch.object(pricing_service, 'get_cost_per_minute', return_value=0.004):
        with patch.object(budget_service, 'get_free_tier_remaining', return_value=3.82):
            cost_service = CostCalculationService(pricing_service, budget_service)
            
            result = cost_service.calculate_actual_cost(
                provider="google",
                model="chirp_batch",
                billed_duration_minutes=5.285,
                estimated_duration_minutes=5.285,
                estimated_cost=0.021
            )
    
            expected_free_used = 3.82
            expected_billable = 5.285 - 3.82
            expected_cost = expected_billable * 0.004
            
            if abs(result["actual_cost"] - expected_cost) < 0.0001:
                print(f"  ✓ Duration: 5.285 min, Free remaining: 3.82 min")
                print(f"  ✓ Free used: {result['actual_free_minutes_used']:.2f} min (expected {expected_free_used:.2f} min)")
                print(f"  ✓ Billable: {result.get('actual_billable_minutes', 0):.3f} min (expected {expected_billable:.3f} min)")
                print(f"  ✓ Cost: ${result['actual_cost']:.6f} (expected ${expected_cost:.6f})")
                return True
            else:
                print(f"  ❌ Expected cost=${expected_cost:.6f}, got ${result['actual_cost']:.6f}")
                return False


def test_all_paid():
    """Test scenario: All paid (free exhausted)."""
    print("\n=== Testing: All Paid (Free Exhausted) ===")
    
    from app.services.pricing import PricingService
    from app.services.budget import BudgetService
    
    pricing_service = PricingService()
    budget_service = BudgetService()
    
    with patch.object(pricing_service, 'get_cost_per_minute', return_value=0.004):
        with patch.object(budget_service, 'get_free_tier_remaining', return_value=0.0):
            cost_service = CostCalculationService(pricing_service, budget_service)
            
            result = cost_service.calculate_actual_cost(
                provider="google",
                model="chirp_batch",
                billed_duration_minutes=5.0,
                estimated_duration_minutes=5.0,
                estimated_cost=0.02
            )
            
            expected_cost = 5.0 * 0.004
            expected_free_used = 0.0
            
            if result["actual_cost"] == expected_cost and result["actual_free_minutes_used"] == expected_free_used:
                print(f"  ✓ Duration: 5.0 min, Free remaining: 0.0 min")
                print(f"  ✓ Cost: ${result['actual_cost']:.4f} (expected ${expected_cost:.4f})")
                print(f"  ✓ Free used: {result['actual_free_minutes_used']:.2f} min (expected {expected_free_used:.2f} min)")
                return True
            else:
                print(f"  ❌ Expected cost=${expected_cost}, free_used={expected_free_used}")
                print(f"  ❌ Got cost=${result['actual_cost']}, free_used={result['actual_free_minutes_used']}")
                return False


def test_missing_billed_duration():
    """Test scenario: Missing billed_duration (falls back to estimated)."""
    print("\n=== Testing: Missing Billed Duration (Fallback) ===")
    
    from app.services.pricing import PricingService
    from app.services.budget import BudgetService
    
    pricing_service = PricingService()
    budget_service = BudgetService()
    
    with patch.object(pricing_service, 'get_cost_per_minute', return_value=0.004):
        with patch.object(budget_service, 'get_free_tier_remaining', return_value=10.0):
            cost_service = CostCalculationService(pricing_service, budget_service)
            
            result = cost_service.calculate_actual_cost(
                provider="google",
                model="chirp_batch",
                billed_duration_minutes=None,  # Missing
                estimated_duration_minutes=5.0,
                estimated_cost=0.02
            )
            
            # Should use estimated duration
            if result.get("billed_duration_minutes") == 5.0:
                print(f"  ✓ Used estimated duration: {result.get('billed_duration_minutes')} min")
                return True
            else:
                print(f"  ❌ Expected billed_duration=5.0, got {result.get('billed_duration_minutes')}")
                return False


def main():
    """Run all cost calculation tests."""
    print("=" * 60)
    print("Testing CostCalculationService")
    print("=" * 60)
    
    results = {
        "all_free": test_all_free(),
        "transition": test_transition(),
        "all_paid": test_all_paid(),
        "missing_billed_duration": test_missing_billed_duration()
    }
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:30} {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL COST CALCULATION TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

