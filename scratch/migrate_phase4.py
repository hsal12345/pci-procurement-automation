import sqlite3
from pathlib import Path

db_path = Path(r"c:\Coding\AKPSI PROJECT\backend\pci_spjed.db")
if not db_path.exists():
    print(f"Database at {db_path} does not exist yet.")
    exit(0)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 1. Create ai_usage_logs table if not exists
cur.execute("""
CREATE TABLE IF NOT EXISTS ai_usage_logs (
    id VARCHAR(36) PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    task_type VARCHAR(50) NOT NULL,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    estimated_cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0.0,
    status VARCHAR(32) NOT NULL DEFAULT 'SUCCESS',
    error_message TEXT,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
""")
print("Ensured ai_usage_logs table exists.")

# 2. Add ai_review_status to package_revisions if not exists
cur.execute("PRAGMA table_info(package_revisions);")
columns = [col[1] for col in cur.fetchall()]
if "ai_review_status" not in columns:
    cur.execute("ALTER TABLE package_revisions ADD COLUMN ai_review_status VARCHAR(32) NOT NULL DEFAULT 'NOT_RUN';")
    print("Added ai_review_status column to package_revisions.")
else:
    print("Column ai_review_status already exists on package_revisions.")

conn.commit()
conn.close()
print("Phase 4 migration completed successfully.")
