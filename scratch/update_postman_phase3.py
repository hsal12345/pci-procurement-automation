import json
from pathlib import Path

base_collection_path = Path(r"c:\Coding\AKPSI PROJECT\backend\pci_procurement_postman_collection.json")
with open(base_collection_path, "r", encoding="utf-8") as f:
    collection = json.load(f)

# Ensure variable keys exist
existing_vars = {v["key"] for v in collection.get("variable", [])}
new_vars = [
    {"key": "internalServiceKey", "value": "dev-internal-service-key", "type": "string", "description": "X-Internal-Service-Key for internal archive API"},
    {"key": "archiveId", "value": "", "type": "string"}
]
for nv in new_vars:
    if nv["key"] not in existing_vars:
        collection["variable"].append(nv)

# Phase 3 items:
workflow_item = {
    "name": "6. Workflow & Approval Transitions",
    "description": "Enterprise state machine coordinating review, approval, withdrawal, return, final issuance, reopening, and cancellation under strict RBAC.",
    "item": [
        {
            "name": "Submit Revision (DRAFT -> UNDER_REVIEW)",
            "request": {
                "method": "POST",
                "header": [
                    {"key": "Content-Type", "value": "application/json"},
                    {"key": "X-User-Role", "value": "ADMINISTRATION"}
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "expected_version": 1,
                        "notes": "Diajukan untuk penelaahan Direktur Keuangan"
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/v1/packages/{{packageId}}/revisions/{{revisionId}}/submit",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "packages", "{{packageId}}", "revisions", "{{revisionId}}", "submit"]
                },
                "description": "Submits a DRAFT revision for review. Requires validation to pass (BR01-BR15)."
            },
            "response": []
        },
        {
            "name": "Withdraw Revision (UNDER_REVIEW -> DRAFT)",
            "request": {
                "method": "POST",
                "header": [
                    {"key": "Content-Type", "value": "application/json"},
                    {"key": "X-User-Role", "value": "ADMINISTRATION"}
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "expected_version": 2,
                        "reason": "Perlu perbaikan data penawaran harga"
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/v1/packages/{{packageId}}/revisions/{{revisionId}}/withdraw",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "packages", "{{packageId}}", "revisions", "{{revisionId}}", "withdraw"]
                },
                "description": "Withdraws revision back to DRAFT before review decision is rendered."
            },
            "response": []
        },
        {
            "name": "Return Revision (UNDER_REVIEW -> RETURNED)",
            "request": {
                "method": "POST",
                "header": [
                    {"key": "Content-Type", "value": "application/json"},
                    {"key": "X-User-Role", "value": "FINANCE_DIRECTOR"}
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "expected_version": 2,
                        "comment": "Mohon perjelas spesifikasi barang baris ke-2 dan cek pagu anggaran."
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/v1/packages/{{packageId}}/revisions/{{revisionId}}/return",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "packages", "{{packageId}}", "revisions", "{{revisionId}}", "return"]
                },
                "description": "Reviewer returns revision with detailed comments for administrative revision."
            },
            "response": []
        },
        {
            "name": "Approve Revision (UNDER_REVIEW -> APPROVED)",
            "request": {
                "method": "POST",
                "header": [
                    {"key": "Content-Type", "value": "application/json"},
                    {"key": "X-User-Role", "value": "FINANCE_DIRECTOR"}
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "expected_version": 4,
                        "manifest_hash": "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890",
                        "note": "Dokumen dan kalkulasi telah diverifikasi sesuai ketentuan BOS."
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/v1/packages/{{packageId}}/revisions/{{revisionId}}/approve",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "packages", "{{packageId}}", "revisions", "{{revisionId}}", "approve"]
                },
                "description": "Finance Director formal approval. Locks commercial pricing and unlocks logistics recording."
            },
            "response": []
        },
        {
            "name": "Final Issuance (APPROVED -> ISSUED)",
            "request": {
                "method": "POST",
                "header": [
                    {"key": "X-User-Role", "value": "FINANCE_DIRECTOR"}
                ],
                "url": {
                    "raw": "{{baseUrl}}/api/v1/packages/{{packageId}}/revisions/{{revisionId}}/issue",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "packages", "{{packageId}}", "revisions", "{{revisionId}}", "issue"]
                },
                "description": "Performs final issuance: enforces BR13 logistics compliance, generates clean official documents without draft watermark, verifies BR14 export equivalence, updates package to ISSUED, marks predecessors SUPERSEDED, and registers Google Drive archive sync."
            },
            "response": []
        },
        {
            "name": "Reopen Package (ISSUED -> Clones new DRAFT)",
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "exec": [
                            "var jsonData = pm.response.json();",
                            "if (jsonData && jsonData.id) {",
                            "    pm.collectionVariables.set('revisionId', jsonData.id);",
                            "    console.log('Saved new revisionId:', jsonData.id);",
                            "}"
                        ],
                        "type": "text/javascript"
                    }
                }
            ],
            "request": {
                "method": "POST",
                "header": [
                    {"key": "Content-Type", "value": "application/json"},
                    {"key": "X-User-Role", "value": "ADMINISTRATION"}
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "reason": "Revisi pesanan penyesuaian anggaran semester 2"
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/v1/packages/{{packageId}}/reopen",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "packages", "{{packageId}}", "reopen"]
                },
                "description": "Reopens an ISSUED package by creating Revision N+1 in DRAFT while Rev N remains ISSUED until Rev N+1 is issued."
            },
            "response": []
        },
        {
            "name": "Cancel Package (State-Contingent RBAC)",
            "request": {
                "method": "POST",
                "header": [
                    {"key": "Content-Type", "value": "application/json"},
                    {"key": "X-User-Role", "value": "FINANCE_DIRECTOR"}
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "reason": "Sekolah membatalkan pengadaan barang secara sepihak."
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/v1/packages/{{packageId}}/cancel",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "packages", "{{packageId}}", "cancel"]
                },
                "description": "Cancels entire package. If DRAFT/RETURNED: Admin or Finance can cancel. If APPROVED/ISSUED: ONLY Finance Director can cancel."
            },
            "response": []
        }
    ]
}

logistics_item = {
    "name": "7. Logistics & Inspection Operations",
    "description": "Logistics recording, physical delivery tracking, inspection outcomes (BAIK / RUSAK / KURANG), and photo/PDF evidence capture.",
    "item": [
        {
            "name": "Update Logistics Facts & Inspection",
            "request": {
                "method": "PATCH",
                "header": [
                    {"key": "Content-Type", "value": "application/json"},
                    {"key": "X-User-Role", "value": "LOGISTICS"}
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "dispatch_date": "2026-05-15",
                        "receipt_date": "2026-05-18",
                        "delivery_reference": "SJ-PCI-2026-0089",
                        "courier_name": "Budi Santoso",
                        "vehicle_plate": "B 9876 PCI",
                        "inspection_status": "PASSED",
                        "inspection_notes": "Seluruh barang diterima dalam keadaan baik dan lengkap",
                        "inspected_by": "Drs. H. Mulyono"
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/v1/packages/{{packageId}}/revisions/{{revisionId}}/logistics",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "packages", "{{packageId}}", "revisions", "{{revisionId}}", "logistics"]
                },
                "description": "Updates dispatch/receipt dates, courier details, and overall inspection status."
            },
            "response": []
        },
        {
            "name": "Batch Update Line Inspection Conditions",
            "request": {
                "method": "PATCH",
                "header": [
                    {"key": "Content-Type", "value": "application/json"},
                    {"key": "X-User-Role", "value": "LOGISTICS"}
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "lines": [
                            {
                                "line_number": 1,
                                "condition": "BAIK",
                                "received_quantity": 10,
                                "notes": "Kondisi botol sempurna"
                            },
                            {
                                "line_number": 2,
                                "condition": "BAIK",
                                "received_quantity": 5,
                                "notes": "Kemasan utuh dan segel aman"
                            }
                        ]
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/v1/packages/{{packageId}}/revisions/{{revisionId}}/logistics/lines",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "packages", "{{packageId}}", "revisions", "{{revisionId}}", "logistics", "lines"]
                },
                "description": "Updates physical condition and received quantity per line. Any RUSAK or KURANG routes revision to OUTSIDE_PILOT_DISPUTE."
            },
            "response": []
        },
        {
            "name": "Upload Logistics Evidence File",
            "request": {
                "method": "POST",
                "header": [
                    {"key": "X-User-Role", "value": "LOGISTICS"}
                ],
                "body": {
                    "mode": "formdata",
                    "formdata": [
                        {"key": "file", "type": "file", "src": "", "description": "Evidence image or scan (JPEG, PNG, PDF up to 10MB)"},
                        {"key": "evidence_type", "value": "SURAT_JALAN_FISIK", "type": "text", "description": "SURAT_JALAN_FISIK | FOTO_SERAH_TERIMA | DOKUMENTASI_BARANG | BERITA_ACARA_FISIK | LAINNYA"},
                        {"key": "caption", "value": "Scan Surat Jalan Asli bertandatangan Kepala Sekolah", "type": "text"}
                    ]
                },
                "url": {
                    "raw": "{{baseUrl}}/api/v1/packages/{{packageId}}/revisions/{{revisionId}}/logistics/evidence",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "packages", "{{packageId}}", "revisions", "{{revisionId}}", "logistics", "evidence"]
                },
                "description": "Uploads binary inspection proof with SHA-256 integrity verification."
            },
            "response": []
        },
        {
            "name": "List Logistics Evidences",
            "request": {
                "method": "GET",
                "header": [
                    {"key": "X-User-Role", "value": "{{userRole}}"}
                ],
                "url": {
                    "raw": "{{baseUrl}}/api/v1/packages/{{packageId}}/revisions/{{revisionId}}/logistics/evidence",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "packages", "{{packageId}}", "revisions", "{{revisionId}}", "logistics", "evidence"]
                },
                "description": "Lists all uploaded delivery and inspection evidence records."
            },
            "response": []
        }
    ]
}

audit_item = {
    "name": "8. Audit Trail & Compliance",
    "description": "Append-only immutable audit trail recording all lifecycle actions, actors, state changes, and business rationales.",
    "item": [
        {
            "name": "Get Package Audit Trail",
            "request": {
                "method": "GET",
                "header": [
                    {"key": "X-User-Role", "value": "{{userRole}}"}
                ],
                "url": {
                    "raw": "{{baseUrl}}/api/v1/packages/{{packageId}}/audit",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "packages", "{{packageId}}", "audit"]
                },
                "description": "Returns chronological audit log of all events for this package and its revisions."
            },
            "response": []
        }
    ]
}

archive_item = {
    "name": "9. Internal Archive Service (n8n / Google Drive)",
    "description": "Decoupled asynchronous synchronization with Google Drive via n8n webhook orchestration.",
    "item": [
        {
            "name": "Trigger Manual Archive Sync",
            "request": {
                "method": "POST",
                "header": [
                    {"key": "Content-Type", "value": "application/json"},
                    {"key": "X-Internal-Service-Key", "value": "{{internalServiceKey}}"}
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "revision_id": "{{revisionId}}"
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/v1/internal/archive/trigger",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "internal", "archive", "trigger"]
                },
                "description": "Registers or resets an archive synchronization task."
            },
            "response": []
        },
        {
            "name": "Poll Pending Archive Records",
            "request": {
                "method": "GET",
                "header": [
                    {"key": "X-Internal-Service-Key", "value": "{{internalServiceKey}}"}
                ],
                "url": {
                    "raw": "{{baseUrl}}/api/v1/internal/archive/pending?limit=50",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "internal", "archive", "pending"],
                    "query": [{"key": "limit", "value": "50"}]
                },
                "description": "Used by n8n or background sync workers to fetch pending/failed archives."
            },
            "response": []
        },
        {
            "name": "Report Archive Sync Callback",
            "request": {
                "method": "POST",
                "header": [
                    {"key": "Content-Type", "value": "application/json"},
                    {"key": "X-Internal-Service-Key", "value": "{{internalServiceKey}}"}
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "archive_id": "{{archiveId}}",
                        "status": "SYNCED",
                        "drive_folder_id": "1A2B3C4D5E6F7G8H9I0J_drive_id"
                    }, indent=2)
                },
                "url": {
                    "raw": "{{baseUrl}}/api/v1/internal/archive/callback",
                    "host": ["{{baseUrl}}"],
                    "path": ["api", "v1", "internal", "archive", "callback"]
                },
                "description": "Callback endpoint called by n8n or Google Drive worker upon upload completion or failure."
            },
            "response": []
        }
    ]
}

# Remove any previously added items with same names if re-running
item_names_to_add = {
    "6. Workflow & Approval Transitions",
    "7. Logistics & Inspection Operations",
    "8. Audit Trail & Compliance",
    "9. Internal Archive Service (n8n / Google Drive)"
}
collection["item"] = [it for it in collection.get("item", []) if it.get("name") not in item_names_to_add]

collection["item"].extend([workflow_item, logistics_item, audit_item, archive_item])

# Save to backend/
backend_target = Path(r"c:\Coding\AKPSI PROJECT\backend\pci_procurement_postman_collection.json")
with open(backend_target, "w", encoding="utf-8") as f:
    json.dump(collection, f, indent=2, ensure_ascii=False)

# Save to root
root_target = Path(r"c:\Coding\AKPSI PROJECT\pci_procurement_postman_collection.json")
with open(root_target, "w", encoding="utf-8") as f:
    json.dump(collection, f, indent=2, ensure_ascii=False)

print(f"Updated Postman collections at {backend_target} and {root_target}")
