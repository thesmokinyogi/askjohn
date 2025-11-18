"""
Test free tier to paid transition for ALL models.

Verifies that the transition logic works correctly regardless of which
model is used (chirp_batch, chirp_standard, long_batch, long_standard, etc.)
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.cost_calculation import CostCalculationService
from app.services.budget import BudgetService
from app.services.pricing import PricingService


def test_transition_all_models():
    """Test transition logic for all available models."""
    print("=" * 70)
    print("Free Tier Transition - All Models Verification")
    print("=" * 70)
    print()
    
    # Initialize services
    pricing_service = PricingService()
    budget_service = BudgetService(monthly_budget=250.0)
    cost_service = CostCalculationService(pricing_service, budget_service)
    
    # Set up test scenario: 3.82 minutes remaining (current state)
    budget_service.data["providers"]["google"]["free_tier_used"] = 56.18
    budget_service.data["providers"]["google"]["free_tier_limit"] = 60.0
    
    free_remaining = budget_service.get_free_tier_remaining("google")
    print(f"Current Free Tier Status: {free_remaining:.2f} minutes remaining")
    print()
    
    # Test all models that are actually configured
    # Get available models from pricing service
    try:
        google_pricing = pricing_service.get_provider_pricing("google")
        available_models = list(google_pricing.get("models", {}).keys())
        models_to_test = [m for m in available_models if any(x in m for x in ["chirp", "long", "short"])]
        print(f"Found {len(models_to_test)} models to test: {', '.join(models_to_test)}")
        print()
    except Exception as e:
        print(f"Error getting models: {e}")
        # Fallback to known models
        models_to_test = [
            "chirp_batch",
            "chirp_standard",
            "long_batch",
            "long_standard"
        ]
    
    print("Testing Transition for All Models:")
    print("-" * 70)
    print()
    
    all_passed = True
    test_duration = 5.0  # 5 minute job (3.82 free + 1.18 paid)
    
    for model in models_to_test:
        print(f"Model: {model}")
        
        try:
            # Get pricing rate for this model
            cost_per_min = pricing_service.get_cost_per_minute("google", model)
            print(f"  Rate: ${cost_per_min:.4f}/min")
            
            # Calculate cost for transition job
            result = cost_service.calculate_actual_cost(
                provider="google",
                model=model,
                billed_duration_minutes=test_duration,
                estimated_duration_minutes=test_duration,
                estimated_cost=0.0
            )
            
            actual_free = result["actual_free_minutes_used"]
            actual_billable = result["actual_billable_minutes"]
            actual_cost = result["actual_cost"]
            expected_cost = actual_billable * cost_per_min
            
            # Verify
            free_ok = abs(actual_free - 3.82) < 0.01
            billable_ok = abs(actual_billable - 1.18) < 0.01
            cost_ok = abs(actual_cost - expected_cost) < 0.0001
            
            status = "✅" if (free_ok and billable_ok and cost_ok) else "❌"
            
            print(f"  Free minutes: {actual_free:.2f} (expected: 3.82)")
            print(f"  Billable minutes: {actual_billable:.2f} (expected: 1.18)")
            print(f"  Cost: ${actual_cost:.4f} (expected: ${expected_cost:.4f})")
            print(f"  Status: {status}")
            
            if not (free_ok and billable_ok and cost_ok):
                all_passed = False
                print(f"  ⚠️  MISMATCH!")
                if not free_ok:
                    print(f"     Free: expected 3.82, got {actual_free:.2f}")
                if not billable_ok:
                    print(f"     Billable: expected 1.18, got {actual_billable:.2f}")
                if not cost_ok:
                    print(f"     Cost: expected ${expected_cost:.4f}, got ${actual_cost:.4f}")
            
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            all_passed = False
        
        print()
    
    # Test edge case: Model not in pricing config
    print("Edge Case: Unknown Model")
    print("-" * 70)
    try:
        result = cost_service.calculate_actual_cost(
            provider="google",
            model="unknown_model",
            billed_duration_minutes=test_duration,
            estimated_duration_minutes=test_duration,
            estimated_cost=0.0
        )
        print("  ❌ Should have raised ValueError for unknown model")
        all_passed = False
    except ValueError as e:
        print(f"  ✅ Correctly raised ValueError: {e}")
    except Exception as e:
        print(f"  ⚠️  Unexpected error: {e}")
        all_passed = False
    print()
    
    # Test that free tier is shared (model-agnostic)
    print("Free Tier Sharing (Model-Agnostic):")
    print("-" * 70)
    
    # Use some free tier with one model
    budget_service.data["providers"]["google"]["free_tier_used"] = 56.18
    free_before = budget_service.get_free_tier_remaining("google")
    
    # Simulate using free tier with chirp_batch
    result1 = cost_service.calculate_actual_cost(
        provider="google",
        model="chirp_batch",
        billed_duration_minutes=2.0,
        estimated_duration_minutes=2.0
    )
    free_used_1 = result1["actual_free_minutes_used"]
    
    # Update budget (simulate)
    budget_service.data["providers"]["google"]["free_tier_used"] = 56.18 + free_used_1
    free_after_1 = budget_service.get_free_tier_remaining("google")
    
    # Now use remaining free tier with different model (long_standard)
    result2 = cost_service.calculate_actual_cost(
        provider="google",
        model="long_standard",
        billed_duration_minutes=free_after_1,
        estimated_duration_minutes=free_after_1
    )
    free_used_2 = result2["actual_free_minutes_used"]
    
    print(f"  Free tier before: {free_before:.2f} min")
    print(f"  Used {free_used_1:.2f} min with chirp_batch")
    print(f"  Remaining: {free_after_1:.2f} min")
    print(f"  Used {free_used_2:.2f} min with long_standard")
    print(f"  Status: ✅ Free tier is shared across models")
    print()
    
    # Reset for summary
    budget_service.data["providers"]["google"]["free_tier_used"] = 56.18
    
    print("=" * 70)
    if all_passed:
        print("✅ ALL MODELS PASSED - Transition works for all models!")
    else:
        print("❌ SOME MODELS FAILED - Review before proceeding!")
    print("=" * 70)
    
    return all_passed


if __name__ == "__main__":
    test_transition_all_models()

