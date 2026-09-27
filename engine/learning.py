"""
LearningSystem
Implements transparent statistical Bayesian updating for provider performance per segment.
Updates provider historical success rates, avg response times, and sample sizes after job execution.
"""

from typing import Dict, Any, List

class LearningSystem:
    @staticmethod
    def update_provider_metrics(
        provider_stats: List[Dict[str, Any]],
        provider_registry: Any
    ) -> Dict[str, Any]:
        """
        Takes post-execution stats per provider step and updates provider registry metrics
        using Laplace/Bayesian frequency smoothing:
        new_rate = (prior_hits + new_hits) / (prior_attempts + new_attempts)
        """
        updated_providers = []
        for stat in provider_stats:
            p_id = stat.get("provider_id")
            new_attempts = int(stat.get("attempts", 0))
            new_successes = int(stat.get("successes", 0))
            new_latency = float(stat.get("avg_latency", 1.0))

            if not p_id or new_attempts <= 0:
                continue

            provider = provider_registry.get_provider(p_id)
            if not provider:
                continue

            prior_sample = int(provider.get("sample_size", 100))
            prior_rate = float(provider.get("success_rate", 0.75))
            prior_successes = prior_sample * prior_rate

            total_sample = prior_sample + new_attempts
            total_successes = prior_successes + new_successes
            updated_rate = round(total_successes / max(total_sample, 1), 4)

            prior_latency = float(provider.get("avg_response_time", 1.2))
            updated_latency = round((prior_latency * prior_sample + new_latency * new_attempts) / total_sample, 2)

            updates = {
                "success_rate": updated_rate,
                "avg_response_time": updated_latency,
                "sample_size": total_sample
            }

            provider_registry.update_provider(p_id, updates)
            updated_providers.append({
                "provider_id": p_id,
                "provider_name": provider["name"],
                "previous_success_rate": round(prior_rate * 100, 1),
                "new_success_rate": round(updated_rate * 100, 1),
                "previous_sample_size": prior_sample,
                "new_sample_size": total_sample
            })

        return {
            "status": "success",
            "model_type": "Transparent Bayesian Statistical Smoothing",
            "updated_providers": updated_providers
        }
