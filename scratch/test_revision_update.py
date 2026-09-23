import urllib.request
import urllib.error
import json

rev_id = "b79f5b1a-bdd6-41e7-b50a-a169b764ccbb"

# Test 1: PUT /api/v1/revisions/{rev_id}/lines
req1 = urllib.request.Request(
    f"http://127.0.0.1:8000/api/v1/revisions/{rev_id}/lines",
    headers={"Content-Type": "application/json", "X-User-Role": "ADMINISTRATION"},
    data=json.dumps({"lines": [], "expected_version": 1}).encode(),
    method="PUT"
)
try:
    with urllib.request.urlopen(req1) as resp:
        print("Req 1 (revisions/lines) Status:", resp.status)
except urllib.error.HTTPError as e:
    print("Req 1 (revisions/lines) HTTPError:", e.code)

# Test 2: PUT /api/v1/revisions/{rev_id}
req2 = urllib.request.Request(
    f"http://127.0.0.1:8000/api/v1/revisions/{rev_id}",
    headers={"Content-Type": "application/json", "X-User-Role": "ADMINISTRATION"},
    data=json.dumps({"expected_version": 1}).encode(),
    method="PUT"
)
try:
    with urllib.request.urlopen(req2) as resp:
        print("Req 2 (revisions) Status:", resp.status)
except urllib.error.HTTPError as e:
    print("Req 2 (revisions) HTTPError:", e.code)

# Test 3: GET /api/v1/revisions/{rev_id}
req3 = urllib.request.Request(
    f"http://127.0.0.1:8000/api/v1/revisions/{rev_id}",
    headers={"X-User-Role": "ADMINISTRATION"}
)
try:
    with urllib.request.urlopen(req3) as resp:
        print("Req 3 (GET revisions) Status:", resp.status)
except urllib.error.HTTPError as e:
    print("Req 3 (GET revisions) HTTPError:", e.code)
