from pathlib import Path
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.generation import Artifact
from app.schemas.generation import ArtifactResponse

router = APIRouter(tags=["Document Artifacts"])

MIME_TYPES = {
    "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "PDF": "application/pdf",
    "ZIP": "application/zip",
}


@router.get("/revisions/{revision_id}/artifacts", response_model=List[ArtifactResponse])
async def list_revision_artifacts(revision_id: UUID, db: AsyncSession = Depends(get_db)):
    """Lists all generated document artifacts for a specific package revision."""
    res = await db.execute(
        select(Artifact)
        .where(Artifact.revision_id == revision_id)
        .order_by(Artifact.format, Artifact.filename)
    )
    artifacts = res.scalars().all()

    output = []
    for art in artifacts:
        resp = ArtifactResponse.model_validate(art)
        resp.download_url = f"/api/v1/artifacts/{art.id}/download"
        output.append(resp)

    return output


@router.get("/artifacts/{id}/download")
async def download_artifact(id: UUID, db: AsyncSession = Depends(get_db)):
    """Streams and downloads a generated document file by artifact ID."""
    res = await db.execute(select(Artifact).where(Artifact.id == id))
    art = res.scalar_one_or_none()
    if not art:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arsip dokumen dengan ID {id} tidak ditemukan."
        )

    file_path = Path(art.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Berkas fisik '{art.filename}' tidak ditemukan pada storage host."
        )

    media_type = MIME_TYPES.get(art.format.upper(), "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        filename=art.filename,
        media_type=media_type,
    )
