import urllib.request
import urllib.error

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/revisions/b79f5b1a-bdd6-41e7-b50a-a169b764ccbb/logistics",
    headers={"X-User-Role": "ADMINISTRATION"}
)

try:
    with urllib.request.urlopen(req) as resp:
        print("Status:", resp.status)
        print("Body:", resp.read().decode())
except urllib.error.HTTPError as e:
    print("HTTPError Status:", e.code)
    print("Body:", e.read().decode())
except Exception as e:
    print("Exception:", e)
