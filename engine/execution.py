"""
ExecutionEngine
Executes or simulates the optimized enrichment job batch step-by-step,
tracking real-time progress, credit consumption, provider attempt logs, and actual outcomes.
"""

import time
import random
from typing import Dict, List, Any, Callable, Optional
from engine.learning import LearningSystem

class ExecutionEngine:
    def __init__(self, db_conn=None, provider_registry=None):
        self.db_conn = db_conn
        self.provider_registry = provider_registry

    def execute_job(
        self,
        job_id: str,
        contacts: List[Dict[str, Any]],
        optimization_plan: Dict[str, Any],
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes an enrichment job according to the approved optimization plan.
        """
        total_contacts = len(contacts)
        if total_contacts <= 0:
            return {"error": "No contacts to process."}

        opt_strat = optimization_plan.get("optimized_strategy", {})
        curr_strat = optimization_plan.get("current_strategy", {})

        baseline_estimated_credits = curr_strat.get("expected_credits", total_contacts * 3.2)

        # Batch execution configuration
        batch_size = max(1, min(500, total_contacts // 20 or 1))
        processed = 0
        actual_credits_spent = 0.0
        actual_successes = 0
        actual_failures = 0

        provider_attempt_counts: Dict[str, Dict[str, Any]] = {}

        segment_routing = opt_strat.get("segment_routing", {})

        start_time = time.time()

        # Iterate over contacts in batches
        for i in range(0, total_contacts, batch_size):
            batch = contacts[i:i + batch_size]
            
            for c in batch:
                seg_name = c.get("segment", "US (Mid-Market)")
                routing = segment_routing.get(seg_name)
                
                # Chain of providers for this contact
                if routing and "recommended_chain" in routing:
                    chain_names = routing["recommended_chain"]
                else:
                    chain_names = ["Prospeo", "Hunter"]

                found = False
                for p_name in chain_names:
                    p_id = p_name.lower().replace(" ", "")
                    if p_id not in provider_attempt_counts:
                        provider_attempt_counts[p_id] = {
                            "provider_id": p_id,
                            "provider_name": p_name,
                            "attempts": 0,
                            "successes": 0,
                            "credits": 0.0,
                            "latencies": []
                        }

                    # Determine provider cost and success probability
                    cost = 1.5 if "prospeo" in p_id else (2.0 if "hunter" in p_id else 3.0)
                    base_prob = 0.82 if "prospeo" in p_id else (0.88 if "hunter" in p_id else 0.90)

                    provider_attempt_counts[p_id]["attempts"] += 1
                    provider_attempt_counts[p_id]["credits"] += cost
                    actual_credits_spent += cost

                    # Simulate attempt outcome based on realistic probability
                    sim_success = random.random() < base_prob
                    lat = random.uniform(0.4, 1.8)
                    provider_attempt_counts[p_id]["latencies"].append(lat)

                    if sim_success:
                        provider_attempt_counts[p_id]["successes"] += 1
                        actual_successes += 1
                        found = True
                        c["email"] = c.get("email") or f"{c['first_name'].lower()}.{c['last_name'].lower()}@{c.get('domain', 'company.com')}"
                        c["enrichment_status"] = "SUCCESS"
                        c["enriched_by"] = p_name
                        break

                if not found:
                    actual_failures += 1
                    c["enrichment_status"] = "FAILED"

            processed += len(batch)
            progress_pct = round((processed / total_contacts) * 100, 1)

            if progress_callback:
                progress_callback({
                    "job_id": job_id,
                    "processed": processed,
                    "total": total_contacts,
                    "progress_percent": progress_pct,
                    "credits_spent": round(actual_credits_spent, 1),
                    "successful": actual_successes,
                    "status": "RUNNING"
                })

        elapsed_time = round(time.time() - start_time, 2)
        actual_success_rate = round((actual_successes / max(total_contacts, 1)) * 100, 2)
        actual_cost_per_success = round(actual_credits_spent / max(actual_successes, 1), 2)
        actual_savings_credits = round(baseline_estimated_credits - actual_credits_spent, 1)
        actual_savings_percent = round((actual_savings_credits / max(baseline_estimated_credits, 0.1)) * 100, 1)

        # Prepare summary of provider attempts
        provider_stats_summary = []
        for pid, pdata in provider_attempt_counts.items():
            avg_lat = sum(pdata["latencies"]) / max(len(pdata["latencies"]), 1)
            provider_stats_summary.append({
                "provider_id": pid,
                "provider_name": pdata["provider_name"],
                "attempts": pdata["attempts"],
                "successes": pdata["successes"],
                "credits": round(pdata["credits"], 1),
                "avg_latency": round(avg_lat, 2)
            })

        # Update Learning System if provider registry is available
        learning_result = {}
        if self.provider_registry:
            learning_result = LearningSystem.update_provider_metrics(provider_stats_summary, self.provider_registry)

        return {
            "job_id": job_id,
            "status": "COMPLETED",
            "total_contacts": total_contacts,
            "actual_credits_spent": round(actual_credits_spent, 1),
            "baseline_estimated_credits": round(baseline_estimated_credits, 1),
            "actual_savings_credits": actual_savings_credits,
            "actual_savings_percent": actual_savings_percent,
            "actual_successful_emails": actual_successes,
            "actual_failed_emails": actual_failures,
            "actual_success_rate": actual_success_rate,
            "actual_cost_per_success": actual_cost_per_success,
            "elapsed_seconds": elapsed_time,
            "provider_attempts": provider_stats_summary,
            "learning_updates": learning_result,
            "is_demo": True
        }
