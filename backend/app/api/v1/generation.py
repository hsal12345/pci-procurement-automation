from typing import Optional
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.generation import GenerationJob
from app.models.packages import PackageRevision
from app.schemas.generation import GenerateRequest, GenerationJobResponse
from app.services.generation_worker import run_generation_job

router = APIRouter(tags=["Document Generation"])


@router.post(
    "/revisions/{id}/generate",
    response_model=GenerationJobResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def trigger_generation(
    id: UUID,
    payload: Optional[GenerateRequest] = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db)
):
    """Enqueues an asynchronous document generation job for the specified revision.
    Accepts selective format requests (e.g. ['XLSX', 'DOCX', 'PDF', 'ZIP']).
    """
    # Verify revision exists
    rev_res = await db.execute(select(PackageRevision).where(PackageRevision.id == id))
    revision = rev_res.scalar_one_or_none()
    if not revision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Revisi paket dengan ID {id} tidak ditemukan."
        )

    formats = payload.formats if payload else None
    is_draft = payload.is_draft if payload else None

    # Create job in QUEUED state
    job = GenerationJob(
        revision_id=revision.id,
        status="QUEUED",
        progress_percent=0
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Dispatch to background task runner
    if background_tasks is not None:
        background_tasks.add_task(
            run_generation_job,
            job.id,
            formats=formats,
            is_draft_override=is_draft
        )

    return job


@router.get("/jobs/{job_id}", response_model=GenerationJobResponse)
async def get_generation_job_status(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """Polls the status and progress percentage of a document generation job."""
    res = await db.execute(select(GenerationJob).where(GenerationJob.id == job_id))
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job generasi dengan ID {job_id} tidak ditemukan."
        )
    return job
