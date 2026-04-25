"""
Test full query response - verify drivers and all fields work correctly.
"""
import requests
import json

API = "http://127.0.0.1:8000"

payload = {"query": "Why did operating profit change for Castrol India Ltd in Q2 2024 compared to Q2 2021?"}
r = requests.post(f"{API}/api/query", json=payload, timeout=15)
print(f"Status: {r.status_code}")
print(json.dumps(r.json(), indent=2))
