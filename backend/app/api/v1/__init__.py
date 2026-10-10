from fastapi import APIRouter
from app.api.v1.masters import router as masters_router
from app.api.v1.imports import router as imports_router
from app.api.v1.packages import router as packages_router, revisions_router
from app.api.v1.validation import router as validation_router
from app.api.v1.generation import router as generation_router
from app.api.v1.artifacts import router as artifacts_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.logistics import router as logistics_router
from app.api.v1.audit import router as audit_router
from app.api.v1.internal.archive import router as internal_archive_router
from app.api.v1.ai import router as ai_router
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(masters_router)
api_v1_router.include_router(imports_router)
api_v1_router.include_router(packages_router)
api_v1_router.include_router(revisions_router)
api_v1_router.include_router(validation_router)
api_v1_router.include_router(generation_router)
api_v1_router.include_router(artifacts_router)
api_v1_router.include_router(reviews_router)
api_v1_router.include_router(logistics_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(internal_archive_router)
api_v1_router.include_router(ai_router)


