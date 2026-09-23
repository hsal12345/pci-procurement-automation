import json
from pathlib import Path

base_collection_path = Path(r"c:\Coding\AKPSI PROJECT\backend\pci_procurement_postman_collection.json")
with open(base_collection_path, "r", encoding="utf-8") as f:
    collection = json.load(f)

ai_item = {
    "name": "10. AI Assistance & Semantic Verification",
    "description": "Advisory AI engine for intelligent header mapping, cross-document semantic discrepancy auditing, PII sanitization, prompt injection defense, and budget guardrails with manual review fallback (PRD Milestone 5, FR02, FR05, AT16).",
    "item": [
        {
            "name": "AI Suggest Header Mapping",
            "request": {
                "method": "POST",
                "header": [
                    {"key": "X-User-Role", "value": "ADMINISTRATION"}
                ],
                "url": {
                    "raw": "{{baseUrl}}/api/v1/ai/imports/{{importId}}/suggest-mapping",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "ai", "imports", "{{importId}}", "suggest-mapping"]
                },
                "description": "Examines non-standard uploaded spreadsheet, safely sanitizes PII, and returns candidate column mapping and header row index with confidence score."
            },
            "response": []
        },
        {
            "name": "Trigger Semantic Discrepancy Audit",
            "request": {
                "method": "POST",
                "header": [
                    {"key": "X-User-Role", "value": "ADMINISTRATION"},
                    {"key": "X-Actor-Name", "value": "Petugas Administrasi"}
                ],
                "url": {
                    "raw": "{{baseUrl}}/api/v1/ai/revisions/{{revisionId}}/audit",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "ai", "revisions", "{{revisionId}}", "audit"]
                },
                "description": "Applies hybrid deterministic pre-filtering across revision items, passes suspect non-matching items to LLM, and ingests findings (WARNING/INFO) into the findings table."
            },
            "response": []
        },
        {
            "name": "Record Manual Review Fallback",
            "request": {
                "method": "POST",
                "header": [
                    {"key": "Content-Type", "value": "application/json"},
                    {"key": "X-User-Role", "value": "ADMINISTRATION"}
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "reviewer_name": "Petugas Administrasi",
                        "reason": "AI offline karena jaringan sekolah, verifikasi fisik manual telah dilakukan.",
                        "notes": "Seluruh baris rincian barang telah dicocokkan dengan katalog belanja sekolah."
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/v1/ai/revisions/{{revisionId}}/record-manual-review",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "ai", "revisions", "{{revisionId}}", "record-manual-review"]
                },
                "description": "Records manual review verification when AI is unavailable or budget cap is reached, permitting package submission to Under Review (PRD FR05 and AT16)."
            },
            "response": []
        },
        {
            "name": "Get AI Usage & Budget Dashboard",
            "request": {
                "method": "GET",
                "header": [
                    {"key": "X-User-Role", "value": "ADMINISTRATION"}
                ],
                "url": {
                    "raw": "{{baseUrl}}/api/v1/ai/usage",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "ai", "usage"]
                },
                "description": "Returns current month token counts, estimated cumulative costs, remaining budget, and AI service status."
            },
            "response": []
        }
    ]
}

# Remove existing folder if present
collection["item"] = [it for it in collection.get("item", []) if it.get("name") != "10. AI Assistance & Semantic Verification"]
collection["item"].append(ai_item)

# Save to backend
backend_target = Path(r"c:\Coding\AKPSI PROJECT\backend\pci_procurement_postman_collection.json")
with open(backend_target, "w", encoding="utf-8") as f:
    json.dump(collection, f, indent=2, ensure_ascii=False)

# Save to root
root_target = Path(r"c:\Coding\AKPSI PROJECT\pci_procurement_postman_collection.json")
with open(root_target, "w", encoding="utf-8") as f:
    json.dump(collection, f, indent=2, ensure_ascii=False)

print(f"Updated Postman collections with Phase 4 AI module at {backend_target} and {root_target}")
