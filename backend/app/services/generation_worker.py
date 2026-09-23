"""Background document generation worker service.
Executes multi-format document rendering (XLSX, DOCX, PDF, ZIP) asynchronously,
tracks job progress, updates GenerationJob records, and registers artifacts idempotently.
"""
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Set
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.generation import GenerationJob, Artifact
from app.models.packages import PackageRevision
from app.services.export.context_builder import build_generation_context
from app.services.export.excel_generator import ExcelPackageGenerator
from app.services.export.docx_generator import DocxPackageGenerator
from app.services.export.pdf_service import PdfService
from app.services.export.zip_packager import ZipPackager, compute_sha256

logger = logging.getLogger("app.services.generation_worker")


async def run_generation_job(
    job_id: UUID,
    formats: Optional[List[str]] = None,
    is_draft_override: Optional[bool] = None
) -> None:
    """Executes asynchronous multi-format generation job for a package revision."""
    logger.info(f"Starting generation job {job_id}")

    async with AsyncSessionLocal() as db:
        try:
            # 1. Load Job
            job_res = await db.execute(select(GenerationJob).where(GenerationJob.id == job_id))
            job = job_res.scalar_one_or_none()
            if not job:
                logger.error(f"Generation job {job_id} not found.")
                return

            job.status = "RUNNING"
            job.started_at = datetime.now(timezone.utc)
            job.progress_percent = 5
            await db.commit()

            # 2. Load PackageRevision with all required relationships
            rev_res = await db.execute(
                select(PackageRevision)
                .options(
                    selectinload(PackageRevision.package),
                    selectinload(PackageRevision.lines),
                    selectinload(PackageRevision.events),
                    selectinload(PackageRevision.numbers),
                )
                .where(PackageRevision.id == job.revision_id)
            )
            revision = rev_res.scalar_one_or_none()
            if not revision:
                raise ValueError(f"Revision {job.revision_id} associated with job {job_id} not found.")

            # Determine draft status: Draft if not locked or package not approved
            if is_draft_override is not None:
                is_draft = is_draft_override
            else:
                pkg_status = revision.package.status if revision.package else "DRAFT"
                is_draft = not (revision.is_locked and pkg_status in ["APPROVED", "ISSUED"])

            # Normalize requested formats
            if not formats:
                target_formats: Set[str] = {"XLSX", "DOCX", "PDF", "ZIP"}
            else:
                target_formats = {f.strip().upper() for f in formats}
                if "ALL" in target_formats:
                    target_formats = {"XLSX", "DOCX", "PDF", "ZIP"}

            # Base output directory from configurable .env path
            base_dir = Path(settings.ARTIFACT_STORAGE_PATH)
            rev_dir = base_dir / str(revision.package_id) / f"rev_{revision.revision_number}"
            rev_dir.mkdir(parents=True, exist_ok=True)

            # Build generation context
            context = build_generation_context(revision, package=revision.package, is_draft=is_draft)

            collected_artifacts = []
            docx_rendered_files = {}

            # 3. XLSX Generation
            if "XLSX" in target_formats:
                logger.info(f"Generating consolidated Excel workbook for job {job_id}")
                xlsx_dir = rev_dir / "excel"
                xlsx_dir.mkdir(parents=True, exist_ok=True)
                xlsx_path = xlsx_dir / "00_PAKET_PENGADAAN.xlsx"

                excel_gen = ExcelPackageGenerator(context, is_draft=is_draft)
                excel_gen.generate_workbook(output_path=xlsx_path)

                collected_artifacts.append({
                    "doc_code": "ALL",
                    "format": "XLSX",
                    "filename": xlsx_path.name,
                    "path": xlsx_path,
                    "file_path": str(xlsx_path),
                    "size_bytes": xlsx_path.stat().st_size,
                    "sha256": compute_sha256(xlsx_path),
                })
                job.progress_percent = 30
                await db.commit()

            # 4. DOCX Generation
            # If PDF is requested, DOCX must also be generated first as source
            need_docx = ("DOCX" in target_formats) or ("PDF" in target_formats)
            if need_docx:
                logger.info(f"Generating 13 DOCX documents for job {job_id}")
                docx_dir = rev_dir / "docx"
                docx_dir.mkdir(parents=True, exist_ok=True)

                docx_gen = DocxPackageGenerator(context)
                docx_rendered_files = docx_gen.generate_all(docx_dir)

                if "DOCX" in target_formats:
                    for doc_code, docx_path in docx_rendered_files.items():
                        collected_artifacts.append({
                            "doc_code": doc_code,
                            "format": "DOCX",
                            "filename": docx_path.name,
                            "path": docx_path,
                            "file_path": str(docx_path),
                            "size_bytes": docx_path.stat().st_size,
                            "sha256": compute_sha256(docx_path),
                        })

                job.progress_percent = 55
                await db.commit()

            # 5. PDF Generation & Merging
            if "PDF" in target_formats:
                logger.info(f"Converting DOCX to PDF for job {job_id}")
                pdf_dir = rev_dir / "pdf"
                pdf_dir.mkdir(parents=True, exist_ok=True)

                pdf_service = PdfService()
                pdf_rendered_files = pdf_service.convert_batch_docx(
                    docx_rendered_files,
                    pdf_dir,
                    is_draft=is_draft
                )

                for doc_code, pdf_path in pdf_rendered_files.items():
                    collected_artifacts.append({
                        "doc_code": doc_code,
                        "format": "PDF",
                        "filename": pdf_path.name,
                        "path": pdf_path,
                        "file_path": str(pdf_path),
                        "size_bytes": pdf_path.stat().st_size,
                        "sha256": compute_sha256(pdf_path),
                    })

                job.progress_percent = 85
                await db.commit()

            # 6. ZIP Packaging & Manifests
            if "ZIP" in target_formats:
                logger.info(f"Assembling ZIP archive and SHA-256 manifests for job {job_id}")
                zip_dir = rev_dir / "zip"
                zip_dir.mkdir(parents=True, exist_ok=True)

                packager = ZipPackager(context)
                pkg_result = packager.create_package_zip(collected_artifacts, zip_dir)

                zip_info = pkg_result["zip_file"]
                collected_artifacts.append({
                    "doc_code": "ZIP",
                    "format": "ZIP",
                    "filename": zip_info["filename"],
                    "path": Path(zip_info["file_path"]),
                    "file_path": zip_info["file_path"],
                    "size_bytes": zip_info["size_bytes"],
                    "sha256": zip_info["sha256"],
                })

            # 7. Idempotent Artifact Database Registration
            # Delete any existing artifacts for this revision matching the generated formats
            formats_to_clean = list(target_formats)
            await db.execute(
                delete(Artifact)
                .where(
                    Artifact.revision_id == revision.id,
                    Artifact.format.in_(formats_to_clean)
                )
            )

            # Insert freshly generated artifacts
            for art in collected_artifacts:
                # Avoid inserting helper manifest files as separate DB rows unless format is tracked
                if art.get("format") in ["XLSX", "DOCX", "PDF", "ZIP"]:
                    db_art = Artifact(
                        job_id=job.id,
                        revision_id=revision.id,
                        doc_code=art["doc_code"],
                        format=art["format"],
                        filename=art["filename"],
                        file_path=art["file_path"],
                        file_size=art["size_bytes"],
                        sha256_hash=art["sha256"],
                        is_draft=is_draft,
                        archive_status="SYNCED",
                    )
                    db.add(db_art)

            # 8. Complete Job
            job.status = "SUCCEEDED"
            job.progress_percent = 100
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info(f"Generation job {job_id} succeeded with {len(collected_artifacts)} artifacts.")

        except Exception as exc:
            logger.exception(f"Generation job {job_id} failed: {exc}")
            await db.rollback()

            # Refresh job and set failed status
            fail_job_res = await db.execute(select(GenerationJob).where(GenerationJob.id == job_id))
            fail_job = fail_job_res.scalar_one_or_none()
            if fail_job:
                fail_job.status = "FAILED"
                fail_job.error_message = str(exc)
                fail_job.completed_at = datetime.now(timezone.utc)
                await db.commit()
