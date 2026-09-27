"""
CostEstimator & SuccessRateEstimator
Implements the exact waterfall mathematics for credit consumption,
success probability, expected successful enrichments, expected failed enrichments,
and expected cost per successful result.
"""

from typing import List, Dict, Any

class StrategyEstimator:
    @staticmethod
    def evaluate_waterfall(
        contact_count: int,
        provider_chain: List[Dict[str, Any]],
        segment_success_rates: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """
        Evaluates a sequence/chain of providers in a waterfall execution.
        """
        if contact_count <= 0 or not provider_chain:
            return {
                "expected_credits": 0,
                "expected_successes": 0,
                "expected_failures": contact_count,
                "cumulative_success_rate": 0.0,
                "expected_cost_per_success": 0.0,
                "provider_step_breakdown": []
            }

        remaining_contacts = float(contact_count)
        total_credits = 0.0
        total_successes = 0.0
        step_breakdown = []

        cumulative_fail_prob = 1.0

        for idx, provider in enumerate(provider_chain):
            p_id = provider["id"]
            p_name = provider.get("name", p_id)
            cost_per_attempt = float(provider.get("credit_cost", 1.0))
            
            # Use segment-specific success rate if provided, else historical default
            if segment_success_rates and p_id in segment_success_rates:
                p_success = float(segment_success_rates[p_id])
            else:
                p_success = float(provider.get("success_rate", 0.70))

            # Clamp success rate between 0.01 and 0.99 for calculation safety
            p_success = max(0.01, min(0.99, p_success))

            attempts_at_step = remaining_contacts
            credits_spent_step = attempts_at_step * cost_per_attempt
            successes_step = attempts_at_step * p_success
            fails_step = attempts_at_step * (1.0 - p_success)

            total_credits += credits_spent_step
            total_successes += successes_step
            remaining_contacts = fails_step

            cumulative_fail_prob *= (1.0 - p_success)

            step_breakdown.append({
                "step": idx + 1,
                "provider_id": p_id,
                "provider_name": p_name,
                "attempts": round(attempts_at_step, 1),
                "credit_cost_per_attempt": cost_per_attempt,
                "credits_spent": round(credits_spent_step, 1),
                "success_rate": round(p_success * 100, 1),
                "successes": round(successes_step, 1),
                "expected_cost_per_step_success": round(cost_per_attempt / p_success, 2)
            })

        cumulative_success_rate = 1.0 - cumulative_fail_prob
        expected_failures = contact_count - total_successes
        cost_per_success = round(total_credits / max(total_successes, 0.01), 2)

        return {
            "contact_count": contact_count,
            "expected_credits": round(total_credits, 1),
            "expected_successes": round(total_successes, 1),
            "expected_failures": round(expected_failures, 1),
            "cumulative_success_rate": round(cumulative_success_rate * 100, 2),
            "expected_cost_per_success": cost_per_success,
            "provider_step_breakdown": step_breakdown
        }
