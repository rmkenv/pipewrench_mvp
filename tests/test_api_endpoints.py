import os
import requests
BASE = os.getenv("TEST_BASE", "http://localhost:8000")

def test_root():
    r = requests.get(f"{BASE}/")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "running"
