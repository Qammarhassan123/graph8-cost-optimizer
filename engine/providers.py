"""
ProviderRegistry
Manages the inventory of Graph8 enrichment providers, credit costs, BYOK settings,
historical success rates, average response times, sample sizes, and action capabilities.
"""

import time
from typing import Dict, List, Any, Optional

DEFAULT_PROVIDERS = [
    {
        "id": "prospeo",
        "name": "Prospeo",
        "action": "email_enrichment",
        "credit_cost": 1.0,
        "available": True,
        "is_byok": False,
        "success_rate": 0.82,
        "avg_response_time": 1.2,
        "sample_size": 14500,
        "last_updated": time.time() - 3600 * 2,
        "supported_actions": ["email_enrichment", "phone_enrichment"]
    },
    {
        "id": "hunter",
        "name": "Hunter",
        "action": "email_enrichment",
        "credit_cost": 2.0,
        "available": True,
        "is_byok": True,
        "success_rate": 0.88,
        "avg_response_time": 0.8,
        "sample_size": 22000,
        "last_updated": time.time() - 3600 * 4,
        "supported_actions": ["email_enrichment", "email_verification"]
    },
    {
        "id": "apollo",
        "name": "Apollo",
        "action": "email_enrichment",
        "credit_cost": 3.0,
        "available": True,
        "is_byok": True,
        "success_rate": 0.91,
        "avg_response_time": 1.5,
        "sample_size": 35000,
        "last_updated": time.time() - 3600 * 1,
        "supported_actions": ["email_enrichment", "phone_enrichment", "company_enrichment"]
    },
    {
        "id": "clearbit",
        "name": "Clearbit",
        "action": "email_enrichment",
        "credit_cost": 4.0,
        "available": True,
        "is_byok": False,
        "success_rate": 0.93,
        "avg_response_time": 0.5,
        "sample_size": 18200,
        "last_updated": time.time() - 3600 * 12,
        "supported_actions": ["email_enrichment", "company_enrichment"]
    },
    {
        "id": "dropcontact",
        "name": "Dropcontact",
        "action": "email_enrichment",
        "credit_cost": 1.5,
        "available": True,
        "is_byok": True,
        "success_rate": 0.79,
        "avg_response_time": 2.1,
        "sample_size": 9400,
        "last_updated": time.time() - 3600 * 6,
        "supported_actions": ["email_enrichment"]
    },
    {
        "id": "icypeas",
        "name": "Icypeas",
        "action": "email_enrichment",
        "credit_cost": 1.0,
        "available": True,
        "is_byok": True,
        "success_rate": 0.74,
        "avg_response_time": 2.8,
        "sample_size": 6100,
        "last_updated": time.time() - 3600 * 8,
        "supported_actions": ["email_enrichment"]
    },
    {
        "id": "lusha",
        "name": "Lusha",
        "action": "email_enrichment",
        "credit_cost": 3.5,
        "available": True,
        "is_byok": True,
        "success_rate": 0.86,
        "avg_response_time": 1.1,
        "sample_size": 12800,
        "last_updated": time.time() - 3600 * 3,
        "supported_actions": ["email_enrichment", "phone_enrichment"]
    },
    {
        "id": "rocketreach",
        "name": "RocketReach",
        "action": "email_enrichment",
        "credit_cost": 3.0,
        "available": True,
        "is_byok": False,
        "success_rate": 0.85,
        "avg_response_time": 1.4,
        "sample_size": 8900,
        "last_updated": time.time() - 3600 * 5,
        "supported_actions": ["email_enrichment", "phone_enrichment"]
    },
    {
        "id": "wiza",
        "name": "Wiza",
        "action": "email_enrichment",
        "credit_cost": 2.5,
        "available": True,
        "is_byok": True,
        "success_rate": 0.81,
        "avg_response_time": 1.8,
        "sample_size": 4300,
        "last_updated": time.time() - 3600 * 10,
        "supported_actions": ["email_enrichment"]
    },
    {
        "id": "leadmagic",
        "name": "LeadMagic",
        "action": "email_enrichment",
        "credit_cost": 1.2,
        "available": True,
        "is_byok": False,
        "success_rate": 0.72,
        "avg_response_time": 1.6,
        "sample_size": 3100,
        "last_updated": time.time() - 3600 * 15,
        "supported_actions": ["email_enrichment"]
    },
    {
        "id": "graph8",
        "name": "Graph8 Native",
        "action": "email_enrichment",
        "credit_cost": 2.0,
        "available": True,
        "is_byok": False,
        "success_rate": 0.84,
        "avg_response_time": 0.6,
        "sample_size": 45000,
        "last_updated": time.time() - 3600 * 1,
        "supported_actions": ["email_enrichment", "phone_enrichment", "company_enrichment"]
    },
    {
        "id": "emaillistverify",
        "name": "EmailListVerify",
        "action": "email_verification",
        "credit_cost": 0.5,
        "available": True,
        "is_byok": False,
        "success_rate": 0.96,
        "avg_response_time": 0.4,
        "sample_size": 15000,
        "last_updated": time.time() - 3600 * 20,
        "supported_actions": ["email_verification"]
    },
    {
        "id": "zerobounce",
        "name": "ZeroBounce",
        "action": "email_verification",
        "credit_cost": 0.8,
        "available": True,
        "is_byok": True,
        "success_rate": 0.98,
        "avg_response_time": 0.3,
        "sample_size": 28000,
        "last_updated": time.time() - 3600 * 2,
        "supported_actions": ["email_verification"]
    },
    {
        "id": "builtwith",
        "name": "BuiltWith",
        "action": "tech_enrichment",
        "credit_cost": 2.0,
        "available": True,
        "is_byok": True,
        "success_rate": 0.92,
        "avg_response_time": 0.9,
        "sample_size": 5200,
        "last_updated": time.time() - 3600 * 24,
        "supported_actions": ["tech_enrichment"]
    },
    {
        "id": "semrush",
        "name": "SEMrush",
        "action": "domain_enrichment",
        "credit_cost": 2.5,
        "available": True,
        "is_byok": True,
        "success_rate": 0.89,
        "avg_response_time": 1.0,
        "sample_size": 4100,
        "last_updated": time.time() - 3600 * 30,
        "supported_actions": ["domain_enrichment"]
    }
]

class ProviderRegistry:
    def __init__(self, db_conn=None):
        self.db_conn = db_conn
        self.providers: Dict[str, Dict[str, Any]] = {}
        self._load_defaults()

    def _load_defaults(self):
        for p in DEFAULT_PROVIDERS:
            # Calculate initial expected cost per success
            p_copy = dict(p)
            p_copy["expected_cost_per_success"] = round(p_copy["credit_cost"] / max(p_copy["success_rate"], 0.01), 2)
            p_copy["sample_size_warning"] = p_copy["sample_size"] < 30
            self.providers[p_copy["id"]] = p_copy

    def get_all_providers(self, action: Optional[str] = None) -> List[Dict[str, Any]]:
        result = []
        for p in self.providers.values():
            if action:
                if action in p.get("supported_actions", [p.get("action")]):
                    result.append(p)
            else:
                result.append(p)
        return result

    def get_provider(self, provider_id: str) -> Optional[Dict[str, Any]]:
        return self.providers.get(provider_id)

    def update_provider(self, provider_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if provider_id in self.providers:
            p = self.providers[provider_id]
            for k, v in updates.items():
                if k in p:
                    p[k] = v
            p["last_updated"] = time.time()
            p["expected_cost_per_success"] = round(p["credit_cost"] / max(p["success_rate"], 0.01), 2)
            p["sample_size_warning"] = p["sample_size"] < 30
            return p
        return None
