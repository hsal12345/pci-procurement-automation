from contextlib import asynccontextmanager
from decimal import Decimal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from app.config import settings
from app.api.v1 import api_v1_router
from app.database import AsyncSessionLocal
from app.models.masters import TaxPolicyVersion


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(TaxPolicyVersion))
        if not res.scalars().first():
            p_ppn = TaxPolicyVersion(
                policy_id="DEFAULT_2026",
                version=1,
                tax_type="PPN",
                rate=Decimal("0.11"),
                is_inclusive=False,
                withholding_rule="NONE",
                rounding_rule="ROUND_HALF_UP",
                is_active=True,
            )
            p_pph = TaxPolicyVersion(
                policy_id="DEFAULT_2026",
                version=1,
                tax_type="PPH22",
                rate=Decimal("0.015"),
                is_inclusive=False,
                withholding_rule="WITHHOLD_FROM_PAYABLE",
                rounding_rule="ROUND_HALF_UP",
                is_active=True,
            )
            session.add_all([p_ppn, p_pph])
            await session.commit()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="PCI Procurement & SPJ System backend API for Indonesian primary school (SD) procurement automation.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles

# Register API v1 routes
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

# Mount storage directory for static file access (letterheads, artifacts, logos)
storage_dir = settings.BASE_DIR / "storage"
storage_dir.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(storage_dir)), name="storage")


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV
    }
