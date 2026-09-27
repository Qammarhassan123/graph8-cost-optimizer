"""
Vercel Serverless Function Entrypoint for Graph8 Cost Optimizer.
Routes API requests to the optimization engine and returns JSON responses.
"""

import http.server
import json
import os
import sys
import urllib.parse
import time

# Add root directory to python module search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import DatabaseManager
from engine.connector import Graph8Connector
from engine.providers import ProviderRegistry
from engine.analyzer import ContactAnalyzer
from engine.segmentation import SegmentationEngine
from engine.optimizer import OptimizationEngine
from engine.execution import ExecutionEngine
from engine.savings import SavingsCalculator

# Initialize Vercel serverless database & singletons
db = DatabaseManager()
db.populate_seed_jobs_if_empty()

connector = Graph8Connector()
provider_registry = ProviderRegistry(db)
execution_engine = ExecutionEngine(db, provider_registry)

# In-memory batch store for serverless execution
CURRENT_BATCH = {
    "contacts": [],
    "stats": {},
    "last_simulation": None
}

class handler(http.server.BaseHTTPRequestHandler):
    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200, "text/plain")

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        if path == "/api/v1/health":
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "ok", "app": "Graph8 Cost Optimizer", "platform": "Vercel Serverless", "version": "1.0.0"}).encode("utf-8"))

        elif path == "/api/v1/connection/status":
            saved_key = db.get_settings().get("graph8_api_key", "")
            if saved_key and not connector.api_key:
                connector.set_credentials(saved_key)
            self._set_headers(200)
            self.wfile.write(json.dumps({
                "is_connected": connector.is_connected,
                "api_key_masked": (saved_key[:8] + "..." + saved_key[-4:]) if len(saved_key) > 12 else ("****" if saved_key else "None"),
                "connection_info": connector.connection_info,
                "is_demo_mode": db.get_settings().get("demo_mode", "true") == "true"
            }).encode("utf-8"))

        elif path == "/api/v1/providers":
            action_filter = query.get("action", [None])[0]
            providers = provider_registry.get_all_providers(action_filter)
            self._set_headers(200)
            self.wfile.write(json.dumps({"providers": providers}).encode("utf-8"))

        elif path == "/api/v1/dashboard":
            jobs = db.get_all_jobs()
            savings_data = SavingsCalculator.calculate_summary(jobs)
            recent_jobs = jobs[:5]

            top_expensive_segments = [
                {"segment": "US (Enterprise)", "avg_cost_per_success": "3.33 credits", "recommendation": "Use Prospeo -> Hunter waterfall"},
                {"segment": "UK (Mid-Market)", "avg_cost_per_success": "3.10 credits", "recommendation": "Use Hunter -> Prospeo waterfall"},
                {"segment": "APAC (SMB)", "avg_cost_per_success": "2.85 credits", "recommendation": "Use Icypeas -> Dropcontact waterfall"}
            ]

            self._set_headers(200)
            self.wfile.write(json.dumps({
                "metrics": savings_data,
                "recent_jobs": recent_jobs,
                "current_opportunity": {"batch_size": 10000, "estimated_savings_credits": 8500, "estimated_savings_percent": 26.6, "status": "RECOMMENDED"},
                "top_expensive_segments": top_expensive_segments,
                "is_demo": True
            }).encode("utf-8"))

        elif path == "/api/v1/savings":
            jobs = db.get_all_jobs()
            summary = SavingsCalculator.calculate_summary(jobs)
            self._set_headers(200)
            self.wfile.write(json.dumps(summary).encode("utf-8"))

        elif path == "/api/v1/jobs":
            jobs = db.get_all_jobs()
            self._set_headers(200)
            self.wfile.write(json.dumps({"jobs": jobs}).encode("utf-8"))

        elif path == "/api/v1/demo/generate":
            count = int(query.get("count", [10000])[0])
            csv_data = ContactAnalyzer.generate_demo_dataset(count)
            contacts, stats, warnings = ContactAnalyzer.parse_csv(csv_data)
            CURRENT_BATCH["contacts"] = contacts
            CURRENT_BATCH["stats"] = stats
            CURRENT_BATCH["last_simulation"] = None
            self._set_headers(200)
            self.wfile.write(json.dumps({
                "message": f"Generated demo dataset with {count:,} contacts.",
                "stats": stats,
                "sample_contacts": contacts[:5],
                "is_demo": True
            }).encode("utf-8"))

        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Route not found"}).encode("utf-8"))

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_data_bytes = self.rfile.read(content_length)

        if path == "/api/v1/connection/test":
            data = json.loads(post_data_bytes.decode("utf-8") or "{}")
            key = data.get("api_key", "").strip()
            connector.set_credentials(key)
            success, msg, info = connector.test_connection()
            db.set_setting("graph8_api_key", key)
            db.set_setting("demo_mode", "false" if success else "true")
            self._set_headers(200)
            self.wfile.write(json.dumps({
                "success": success,
                "message": msg,
                "connection_info": info,
                "is_demo_mode": not success
            }).encode("utf-8"))

        elif path == "/api/v1/contacts/upload":
            try:
                raw_text = post_data_bytes.decode("utf-8")
                if raw_text.startswith("{") and "csv_content" in raw_text:
                    payload = json.loads(raw_text)
                    csv_text = payload["csv_content"]
                else:
                    csv_text = raw_text

                contacts, stats, warnings = ContactAnalyzer.parse_csv(csv_text)
                if not contacts:
                    self._set_headers(400)
                    self.wfile.write(json.dumps({"error": "No valid contacts parsed from CSV.", "warnings": warnings}).encode("utf-8"))
                    return

                CURRENT_BATCH["contacts"] = contacts
                CURRENT_BATCH["stats"] = stats
                CURRENT_BATCH["last_simulation"] = None

                self._set_headers(200)
                self.wfile.write(json.dumps({
                    "message": f"Successfully parsed {len(contacts):,} contacts.",
                    "stats": stats,
                    "warnings": warnings,
                    "sample_contacts": contacts[:5]
                }).encode("utf-8"))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": f"Upload failed: {str(e)}"}).encode("utf-8"))

        elif path == "/api/v1/optimizer/simulate":
            data = json.loads(post_data_bytes.decode("utf-8") or "{}")
            constraints = data.get("constraints", {
                "max_success_drop_percent": 2.0,
                "min_savings_percent": 10.0,
                "max_latency_sec": 30.0
            })

            contacts = data.get("contacts") or CURRENT_BATCH["contacts"]
            if not contacts:
                csv_data = ContactAnalyzer.generate_demo_dataset(10000)
                contacts, stats, _ = ContactAnalyzer.parse_csv(csv_data)
                CURRENT_BATCH["contacts"] = contacts
                CURRENT_BATCH["stats"] = stats

            providers = provider_registry.get_all_providers("email_enrichment")
            simulation_result = OptimizationEngine.optimize_enrichment(
                contacts=contacts,
                available_providers=providers,
                constraints=constraints
            )

            CURRENT_BATCH["last_simulation"] = simulation_result

            self._set_headers(200)
            self.wfile.write(json.dumps(simulation_result).encode("utf-8"))

        elif path == "/api/v1/optimizer/execute":
            data = json.loads(post_data_bytes.decode("utf-8") or "{}")
            simulation_plan = data.get("simulation_plan") or CURRENT_BATCH["last_simulation"]

            if not simulation_plan:
                # Generate default simulation plan if none passed
                csv_data = ContactAnalyzer.generate_demo_dataset(1000)
                contacts, stats, _ = ContactAnalyzer.parse_csv(csv_data)
                providers = provider_registry.get_all_providers("email_enrichment")
                simulation_plan = OptimizationEngine.optimize_enrichment(contacts, providers)

            contacts = CURRENT_BATCH["contacts"] or ContactAnalyzer.parse_csv(ContactAnalyzer.generate_demo_dataset(1000))[0]
            job_id = f"job_{int(time.time())}"

            execution_result = execution_engine.execute_job(
                job_id=job_id,
                contacts=contacts,
                optimization_plan=simulation_plan
            )

            db.save_job({
                "id": job_id,
                "created_at": time.time(),
                "batch_name": f"Batch Optimization ({len(contacts):,} contacts)",
                "contacts_count": len(contacts),
                "enrichment_type": "email_enrichment",
                "original_strategy": simulation_plan.get("current_strategy", {}),
                "optimized_strategy": simulation_plan.get("optimized_strategy", {}),
                "baseline_cost": execution_result["baseline_estimated_credits"],
                "estimated_cost": simulation_plan.get("optimized_strategy", {}).get("expected_credits", 0),
                "actual_cost": execution_result["actual_credits_spent"],
                "estimated_savings": simulation_plan.get("comparison", {}).get("estimated_credits_saved", 0),
                "actual_savings": execution_result["actual_savings_credits"],
                "success_rate": execution_result["actual_success_rate"],
                "actual_successes": execution_result["actual_successful_emails"],
                "status": "COMPLETED",
                "calculation_details": execution_result
            })

            self._set_headers(200)
            self.wfile.write(json.dumps(execution_result).encode("utf-8"))

        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Route not found"}).encode("utf-8"))

    def do_PUT(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        content_length = int(self.headers.get("Content-Length", 0))
        post_data_bytes = self.rfile.read(content_length)

        if path.startswith("/api/v1/providers/"):
            provider_id = path.replace("/api/v1/providers/", "")
            payload = json.loads(post_data_bytes.decode("utf-8") or "{}")
            updated = provider_registry.update_provider(provider_id, payload)
            if updated:
                self._set_headers(200)
                self.wfile.write(json.dumps({"success": True, "provider": updated}).encode("utf-8"))
            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "Provider not found"}).encode("utf-8"))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Route not found"}).encode("utf-8"))
