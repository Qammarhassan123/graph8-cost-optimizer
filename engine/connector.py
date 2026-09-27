"""
Graph8Connector
Handles authentication, API key storage, live connection testing,
and interfacing with Graph8 REST API endpoints.
"""

import urllib.request
import urllib.error
import json
import ssl
from typing import Dict, Any, Tuple, Optional

class Graph8Connector:
    def __init__(self, api_key: str = "", base_url: str = "https://be.graph8.com/api/v1"):
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.is_connected = False
        self.connection_info: Dict[str, Any] = {}
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    def set_credentials(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key.strip()
        if base_url:
            self.base_url = base_url.rstrip("/")
        self.is_connected = False
        self.connection_info = {}

    def test_connection(self) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Tests the connection to Graph8 API using the provided API Key.
        Does not fake success.
        """
        if not self.api_key:
            self.is_connected = False
            return False, "API Key is required.", {"mode": "DISCONNECTED"}

        # Attempt API health / user verification endpoint
        test_endpoints = [
            f"{self.base_url}/health",
            f"{self.base_url}/me",
            f"{self.base_url}/user",
            f"{self.base_url}/providers"
        ]

        last_error = ""
        for url in test_endpoints:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "X-API-Key": self.api_key,
                "User-Agent": "Graph8-Cost-Optimizer/1.0",
                "Accept": "application/json"
            }
            try:
                req = urllib.request.Request(url, headers=headers, method="GET")
                with urllib.request.urlopen(req, timeout=4, context=self.ssl_context) as resp:
                    if resp.status in (200, 201, 204):
                        data = json.loads(resp.read().decode("utf-8") or "{}")
                        self.is_connected = True
                        self.connection_info = {
                            "status": "connected",
                            "endpoint": url,
                            "mode": "LIVE",
                            "data": data
                        }
                        return True, "Successfully connected to Graph8 Live API.", self.connection_info
            except urllib.error.HTTPError as e:
                err_text = e.read().decode("utf-8", errors="ignore")
                if e.code == 401 or e.code == 403:
                    last_error = f"Authentication failed (HTTP {e.code}): Invalid API Key."
                    break
                else:
                    last_error = f"HTTP {e.code} error from {url}: {err_text[:100]}"
            except Exception as e:
                last_error = f"Connection failed to {url}: {str(e)}"

        self.is_connected = False
        self.connection_info = {
            "status": "disconnected",
            "error": last_error,
            "mode": "DEMO_FALLBACK"
        }
        return False, f"Could not connect to live Graph8 API. {last_error}", self.connection_info

    def get_providers_from_api(self) -> Optional[list]:
        """
        Retrieves provider list from live Graph8 API if available.
        Returns None if endpoint is unreachable or unsupported.
        """
        if not self.is_connected:
            return None

        url = f"{self.base_url}/providers"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-API-Key": self.api_key,
            "User-Agent": "Graph8-Cost-Optimizer/1.0"
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=4, context=self.ssl_context) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict) and "providers" in data:
                        return data["providers"]
        except Exception:
            pass
        return None
