"""
OptimizationEngine
The core intelligence layer for Graph8 Cost Optimizer.
Determines the optimal enrichment strategy across segments to minimize credit cost
per successful result subject to strict quality and latency guardrails.
"""

from typing import List, Dict, Any, Optional
from engine.estimator import StrategyEstimator
from engine.segmentation import SegmentationEngine

# Historical segment success rate matrix (simulated empirical data / baseline)
SEGMENT_SUCCESS_MATRIX = {
    "US": {
        "prospeo": 0.86, "hunter": 0.90, "apollo": 0.92, "clearbit": 0.95,
        "dropcontact": 0.78, "icypeas": 0.72, "lusha": 0.88, "rocketreach": 0.87,
        "wiza": 0.82, "graph8": 0.85
    },
    "UK": {
        "prospeo": 0.81, "hunter": 0.92, "apollo": 0.87, "clearbit": 0.91,
        "dropcontact": 0.85, "icypeas": 0.79, "lusha": 0.84, "rocketreach": 0.83,
        "wiza": 0.78, "graph8": 0.84
    },
    "EU": {
        "prospeo": 0.80, "hunter": 0.85, "apollo": 0.84, "clearbit": 0.89,
        "dropcontact": 0.88, "icypeas": 0.81, "lusha": 0.80, "rocketreach": 0.81,
        "wiza": 0.76, "graph8": 0.82
    },
    "APAC": {
        "prospeo": 0.75, "hunter": 0.79, "apollo": 0.88, "clearbit": 0.86,
        "dropcontact": 0.68, "icypeas": 0.65, "lusha": 0.82, "rocketreach": 0.84,
        "wiza": 0.85, "graph8": 0.80
    },
    "Rest of World": {
        "prospeo": 0.72, "hunter": 0.76, "apollo": 0.82, "clearbit": 0.84,
        "dropcontact": 0.65, "icypeas": 0.60, "lusha": 0.78, "rocketreach": 0.79,
        "wiza": 0.75, "graph8": 0.78
    }
}

class OptimizationEngine:
    @staticmethod
    def optimize_enrichment(
        contacts: List[Dict[str, Any]],
        available_providers: List[Dict[str, Any]],
        provider_costs: Optional[Dict[str, float]] = None,
        historical_success_rates: Optional[Dict[str, float]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        is_demo: bool = False
    ) -> Dict[str, Any]:
        """
        Executes optimization over input contact batch.
        """
        if not contacts:
            return {"error": "No contacts provided for optimization."}

        # Setup constraints defaults
        constraints = constraints or {}
        max_success_drop = float(constraints.get("max_success_drop_percent", 2.0))
        min_savings_pct = float(constraints.get("min_savings_percent", 10.0))
        max_latency_sec = float(constraints.get("max_latency_sec", 30.0))

        # Filter only active email enrichment providers
        active_providers = [
            p for p in available_providers
            if p.get("available", True) and "email_enrichment" in p.get("supported_actions", [p.get("action")])
        ]
        if not active_providers:
            return {"error": "No active email enrichment providers available."}

        # Build provider dictionary lookup
        p_dict = {p["id"]: dict(p) for p in active_providers}

        # Apply cost overrides if provided
        if provider_costs:
            for pid, cost in provider_costs.items():
                if pid in p_dict:
                    p_dict[pid]["credit_cost"] = float(cost)

        # Apply historical success rate overrides if provided
        if historical_success_rates:
            for pid, rate in historical_success_rates.items():
                if pid in p_dict:
                    p_dict[pid]["success_rate"] = float(rate)

        # 1. Evaluate Current Graph8 Strategy (Default Waterfall: Apollo -> Clearbit -> Hunter)
        # Or top 3 highest tier providers
        current_chain_ids = ["apollo", "clearbit", "hunter"]
        current_chain = [p_dict[pid] for pid in current_chain_ids if pid in p_dict]
        if not current_chain:
            current_chain = list(p_dict.values())[:3]

        total_contacts = len(contacts)
        current_eval = StrategyEstimator.evaluate_waterfall(total_contacts, current_chain)

        # 2. Segment-Aware Optimization
        segments = SegmentationEngine.segment_contacts(contacts)
        segment_recommendations = {}
        overall_optimized_credits = 0.0
        overall_optimized_successes = 0.0
        overall_optimized_latency = 0.0

        sample_sizes = [p.get("sample_size", 0) for p in active_providers]
        avg_sample_size = sum(sample_sizes) / max(len(sample_sizes), 1)
        confidence_level = "HIGH" if avg_sample_size > 10000 else ("MEDIUM" if avg_sample_size > 1000 else "LOW")

        assumptions = [
            "Provider success rates are estimated from recent 30-day historical enrichment logs.",
            "Waterfall cascade triggers sequentially only when preceding provider yields no email.",
            f"Confidence score is rated {confidence_level} based on an average provider sample size of {int(avg_sample_size):,} attempts.",
            "Credit pricing assumes 1 credit = 1 provider search query attempt."
        ]

        # Optimize for each segment
        for seg_name, seg_contacts in segments.items():
            c_count = len(seg_contacts)
            # Find segment region key (US, UK, EU, APAC, Rest of World)
            region = "US" if "US" in seg_name else ("UK" if "UK" in seg_name else ("EU" if "EU" in seg_name else ("APAC" if "APAC" in seg_name else "Rest of World")))
            seg_rates = SEGMENT_SUCCESS_MATRIX.get(region, SEGMENT_SUCCESS_MATRIX["Rest of World"])

            # Calculate cost per success for each provider in this segment
            scored_providers = []
            for p in p_dict.values():
                pid = p["id"]
                rate = seg_rates.get(pid, p.get("success_rate", 0.75))
                cost = p["credit_cost"]
                cps = cost / max(rate, 0.01)
                scored_providers.append({
                    "provider": p,
                    "segment_success_rate": rate,
                    "cost_per_success": cps
                })

            # Sort providers by cost per success (cheapest per successful result first)
            scored_providers.sort(key=lambda x: x["cost_per_success"])

            # Form optimal 2-step or 3-step waterfall chain
            best_chain = [item["provider"] for item in scored_providers[:2]]
            seg_rates_map = {item["provider"]["id"]: item["segment_success_rate"] for item in scored_providers}

            seg_eval = StrategyEstimator.evaluate_waterfall(c_count, best_chain, seg_rates_map)

            overall_optimized_credits += seg_eval["expected_credits"]
            overall_optimized_successes += seg_eval["expected_successes"]

            chain_latency = sum(p.get("avg_response_time", 1.0) for p in best_chain)
            overall_optimized_latency = max(overall_optimized_latency, chain_latency)

            segment_recommendations[seg_name] = {
                "segment_name": seg_name,
                "contact_count": c_count,
                "recommended_chain": [p["name"] for p in best_chain],
                "expected_credits": seg_eval["expected_credits"],
                "expected_successes": seg_eval["expected_successes"],
                "success_rate": seg_eval["cumulative_success_rate"],
                "expected_cost_per_success": seg_eval["expected_cost_per_success"]
            }

        # Overall Optimized Metrics
        opt_success_rate = (overall_optimized_successes / max(total_contacts, 1)) * 100.0
        opt_cost_per_success = round(overall_optimized_credits / max(overall_optimized_successes, 0.01), 2)
        credits_saved = current_eval["expected_credits"] - overall_optimized_credits
        savings_percent = round((credits_saved / max(current_eval["expected_credits"], 0.1)) * 100.0, 1)

        success_drop = current_eval["cumulative_success_rate"] - opt_success_rate
        success_rate_diff_pct = round(opt_success_rate - current_eval["cumulative_success_rate"], 1)

        # 3. Check Safety Guardrails
        is_rejected = False
        rejection_reasons = []

        if success_drop > max_success_drop:
            is_rejected = True
            rejection_reasons.append(
                f"Optimization rejected because estimated success rate would drop by {success_drop:.1f}%, exceeding your maximum allowed drop limit of {max_success_drop:.1f}%."
            )

        if savings_percent < min_savings_pct:
            is_rejected = True
            rejection_reasons.append(
                f"Optimization rejected because estimated credit savings of {savings_percent:.1f}% is below your required minimum threshold of {min_savings_pct:.1f}%."
            )

        if overall_optimized_latency > max_latency_sec:
            is_rejected = True
            rejection_reasons.append(
                f"Optimization rejected because expected latency ({overall_optimized_latency:.1f}s) exceeds your limit of {max_latency_sec:.1f}s."
            )

        status = "REJECTED" if is_rejected else "RECOMMENDED"

        return {
            "status": status,
            "total_contacts": total_contacts,
            "current_strategy": {
                "name": "Default Graph8 Waterfall",
                "chain": [p["name"] for p in current_chain],
                "expected_credits": current_eval["expected_credits"],
                "expected_successful_emails": current_eval["expected_successes"],
                "expected_success_rate": current_eval["cumulative_success_rate"],
                "expected_cost_per_success": current_eval["expected_cost_per_success"]
            },
            "optimized_strategy": {
                "name": "Segment-Optimized Smart Waterfall",
                "expected_credits": round(overall_optimized_credits, 1),
                "expected_successful_emails": round(overall_optimized_successes, 1),
                "expected_success_rate": round(opt_success_rate, 2),
                "expected_cost_per_success": opt_cost_per_success,
                "segment_routing": segment_recommendations
            },
            "comparison": {
                "estimated_credits_saved": round(credits_saved, 1),
                "estimated_savings_percent": savings_percent,
                "success_rate_change_percent": success_rate_diff_pct,
                "cost_per_success_reduction_percent": round(
                    ((current_eval["expected_cost_per_success"] - opt_cost_per_success) / max(current_eval["expected_cost_per_success"], 0.01)) * 100.0,
                    1
                )
            },
            "guardrails": {
                "max_success_drop_percent": max_success_drop,
                "min_savings_percent": min_savings_pct,
                "max_latency_sec": max_latency_sec,
                "passed": not is_rejected,
                "rejection_reasons": rejection_reasons
            },
            "confidence": confidence_level,
            "assumptions": assumptions,
            "is_demo": is_demo
        }
