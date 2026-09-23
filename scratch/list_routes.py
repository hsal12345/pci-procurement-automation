import urllib.request
import json

try:
    with urllib.request.urlopen("http://127.0.0.1:8000/openapi.json") as resp:
        data = json.loads(resp.read().decode())
        print(f"Total endpoints: {len(data['paths'])}")
        for path in sorted(data['paths'].keys()):
            methods = list(data['paths'][path].keys())
            print(f"{methods} {path}")
except Exception as e:
    print(f"Error: {e}")
