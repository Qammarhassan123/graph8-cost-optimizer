"""
Database Manager for Graph8 Cost Optimizer.
Uses SQLite for zero-dependency persistence of jobs history, provider inventory, and app settings.
"""

import sqlite3
import json
import time
import os
from typing import Dict, List, Any, Optional

if os.environ.get("VERCEL"):
    DB_FILE = "/tmp/cost_optimizer.db"
else:
    DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cost_optimizer.db")

class DatabaseManager:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self._init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Providers table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS providers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                action TEXT NOT NULL,
                credit_cost REAL NOT NULL,
                available INTEGER NOT NULL DEFAULT 1,
                is_byok INTEGER NOT NULL DEFAULT 0,
                success_rate REAL NOT NULL,
                avg_response_time REAL NOT NULL,
                sample_size INTEGER NOT NULL DEFAULT 0,
                last_updated REAL NOT NULL,
                supported_actions TEXT
            )
            """)

            # Jobs history table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                created_at REAL NOT NULL,
                batch_name TEXT NOT NULL,
                contacts_count INTEGER NOT NULL,
                enrichment_type TEXT NOT NULL,
                original_strategy_json TEXT NOT NULL,
                optimized_strategy_json TEXT NOT NULL,
                baseline_cost REAL NOT NULL,
                estimated_cost REAL NOT NULL,
                actual_cost REAL NOT NULL DEFAULT 0.0,
                estimated_savings REAL NOT NULL,
                actual_savings REAL NOT NULL DEFAULT 0.0,
                success_rate REAL NOT NULL DEFAULT 0.0,
                actual_successes INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                calculation_details_json TEXT
            )
            """)

            # App settings table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """)

            conn.commit()

    def get_settings(self) -> Dict[str, str]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            return {row["key"]: row["value"] for row in cursor.fetchall()}

    def set_setting(self, key: str, value: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
            conn.commit()

    def save_job(self, job_data: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO jobs (
                id, created_at, batch_name, contacts_count, enrichment_type,
                original_strategy_json, optimized_strategy_json, baseline_cost,
                estimated_cost, actual_cost, estimated_savings, actual_savings,
                success_rate, actual_successes, status, calculation_details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_data["id"],
                job_data.get("created_at", time.time()),
                job_data.get("batch_name", "Enrichment Batch"),
                job_data.get("contacts_count", 0),
                job_data.get("enrichment_type", "email_enrichment"),
                json.dumps(job_data.get("original_strategy", {})),
                json.dumps(job_data.get("optimized_strategy", {})),
                job_data.get("baseline_cost", 0.0),
                job_data.get("estimated_cost", 0.0),
                job_data.get("actual_cost", 0.0),
                job_data.get("estimated_savings", 0.0),
                job_data.get("actual_savings", 0.0),
                job_data.get("success_rate", 0.0),
                job_data.get("actual_successes", 0),
                job_data.get("status", "SIMULATED"),
                json.dumps(job_data.get("calculation_details", {}))
            ))
            conn.commit()

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC")
            rows = cursor.fetchall()
            jobs = []
            for r in rows:
                j = dict(r)
                j["original_strategy"] = json.loads(j.pop("original_strategy_json", "{}"))
                j["optimized_strategy"] = json.loads(j.pop("optimized_strategy_json", "{}"))
                j["calculation_details"] = json.loads(j.pop("calculation_details_json", "{}"))
                jobs.append(j)
            return jobs

    def populate_seed_jobs_if_empty(self):
        """
        Seeds realistic historical jobs if database is fresh.
        """
        existing = self.get_all_jobs()
        if existing:
            return

        now = time.time()
        seed_jobs = [
            {
                "id": "job_1001",
                "created_at": now - 86400 * 2,
                "batch_name": "US Enterprise Tech Lead List",
                "contacts_count": 10000,
                "enrichment_type": "email_enrichment",
                "original_strategy": {"chain": ["Apollo", "Clearbit", "Hunter"]},
                "optimized_strategy": {"chain": ["Prospeo", "Hunter"]},
                "baseline_cost": 32000.0,
                "estimated_cost": 23500.0,
                "actual_cost": 23210.0,
                "estimated_savings": 8500.0,
                "actual_savings": 8790.0,
                "success_rate": 84.5,
                "actual_successes": 8450,
                "status": "COMPLETED",
                "calculation_details": {"estimated_cost_per_success": 2.74, "is_demo": True}
            },
            {
                "id": "job_1002",
                "created_at": now - 86400 * 5,
                "batch_name": "EMEA Mid-Market Financial Leads",
                "contacts_count": 5000,
                "enrichment_type": "email_enrichment",
                "original_strategy": {"chain": ["Clearbit", "Lusha"]},
                "optimized_strategy": {"chain": ["Hunter", "Dropcontact"]},
                "baseline_cost": 17500.0,
                "estimated_cost": 12200.0,
                "actual_cost": 12150.0,
                "estimated_savings": 5300.0,
                "actual_savings": 5350.0,
                "success_rate": 81.2,
                "actual_successes": 4060,
                "status": "COMPLETED",
                "calculation_details": {"estimated_cost_per_success": 2.99, "is_demo": True}
            },
            {
                "id": "job_1003",
                "created_at": now - 86400 * 9,
                "batch_name": "APAC Startup Founders Campaign",
                "contacts_count": 2500,
                "enrichment_type": "email_enrichment",
                "original_strategy": {"chain": ["Apollo", "RocketReach"]},
                "optimized_strategy": {"chain": ["Prospeo", "Icypeas"]},
                "baseline_cost": 7500.0,
                "estimated_cost": 4800.0,
                "actual_cost": 4720.0,
                "estimated_savings": 2700.0,
                "actual_savings": 2780.0,
                "success_rate": 78.4,
                "actual_successes": 1960,
                "status": "COMPLETED",
                "calculation_details": {"estimated_cost_per_success": 2.40, "is_demo": True}
            }
        ]
        for j in seed_jobs:
            self.save_job(j)
