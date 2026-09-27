"""
Direct Vercel REST API Deployment Script.
Deploys Graph8 Cost Optimizer directly to Vercel without needing Node.js or npm.
"""

import os
import sys
import json
import urllib.request
import urllib.error

DEPLOY_FILES = [
    "vercel.json",
    "requirements.txt",
    "db.py",
    "server.py",
    "api/index.py",
    "engine/__init__.py",
    "engine/connector.py",
    "engine/providers.py",
    "engine/analyzer.py",
    "engine/segmentation.py",
    "engine/estimator.py",
    "engine/optimizer.py",
    "engine/execution.py",
    "engine/learning.py",
    "engine/savings.py",
    "static/index.html",
    "static/styles.css",
    "static/app.js",
    "static/graph8-logo.svg"
]

def deploy_to_vercel(token: str, project_name: str = "graph8-cost-optimizer"):
    token = token.strip()
    if not token:
        print("ERROR: Vercel Token is required.")
        return None

    base_dir = os.path.dirname(os.path.abspath(__file__))
    files_payload = []

    for rel_path in DEPLOY_FILES:
        full_path = os.path.join(base_dir, rel_path.replace("/", os.sep))
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            files_payload.append({
                "file": rel_path,
                "data": content
            })

    print(f"Bundled {len(files_payload)} files for deployment.")

    url = "https://api.vercel.com/v13/deployments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    body = {
        "name": project_name,
        "files": files_payload,
        "projectSettings": {
            "framework": None
        }
    }

    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")

    try:
        print("Uploading deployment to Vercel...")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            deploy_url = data.get("url")
            print("==================================================")
            print(" SUCCESS! PROJECT DEPLOYED TO VERCEL:")
            print(f" Live URL: https://{deploy_url}")
            print("==================================================")
            return data
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8")
        print(f"Vercel API Error (HTTP {e.code}): {err}")
        return None
    except Exception as e:
        print(f"Deployment failed: {str(e)}")
        return None

if __name__ == "__main__":
    token = os.environ.get("VERCEL_TOKEN") or (sys.argv[1] if len(sys.argv) > 1 else "")
    if token:
        deploy_to_vercel(token)
    else:
        print("Usage: python deploy_vercel.py <VERCEL_TOKEN>")
