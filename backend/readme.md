# PCI Procurement & SPJ Automation — Backend (FastAPI)

## Local Setup & Run

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Optional for local development without PostgreSQL:
$env:USE_SQLITE_FALLBACK = "true"

# Seed default schools, companies, and 4 RBAC user accounts:
python seed_master_data.py

# Start API server (Swagger docs at http://localhost:8000/docs):
uvicorn app.main:app --reload --port 8000
```

## Running Tests

```powershell
cd backend
$env:USE_SQLITE_FALLBACK = "true"
pytest -v
```
