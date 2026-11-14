"""Background document generation worker service.
Executes multi-format document rendering (XLSX, DOCX, PDF, ZIP) asynchronously,
tracks job progress, updates GenerationJob records, and registers artifacts idempotently.
"""
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from pypdf import PdfWriter
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.generation import GenerationJob, Artifact
from app.models.packages import PackageRevision
from app.services.export.context_builder import build_generation_context
from app.services.export.excel_generator import ExcelPackageGenerator
from app.services.export.docx_generator import DocxPackageGenerator, DOCUMENT_MAP
from app.services.export.pdf_service import PdfService, CANONICAL_PDF_ORDER
from app.services.export.zip_packager import ZipPackager, compute_sha256

logger = logging.getLogger("app.services.generation_worker")


def _convert_single_pdf(
    pdf_service: PdfService,
    docx_path: Path,
    pdf_dir: Path,
    is_draft: bool,
) -> Path:
    """Converts a single DOCX file to PDF and applies draft watermark if needed."""
    raw_pdf = pdf_service.convert_docx_to_pdf(docx_path, pdf_dir)
    if is_draft:
        watermarked_pdf = pdf_dir / f"{raw_pdf.stem}_wm.pdf"
        pdf_service.apply_draft_watermark(raw_pdf, watermarked_pdf)
        raw_pdf.unlink()
        watermarked_pdf.rename(raw_pdf)
    return raw_pdf


def _merge_pdfs(pdf_map: Dict[str, Path], merged_path: Path) -> Path:
    """Merges individual PDF files into a single consolidated PDF in canonical order."""
    merger = PdfWriter()
    try:
        for doc_code, _expected_name in CANONICAL_PDF_ORDER:
            if doc_code in pdf_map and pdf_map[doc_code].exists():
                merger.append(str(pdf_map[doc_code]))
        with open(merged_path, "wb") as f_merged:
            merger.write(f_merged)
    finally:
        merger.close()
    return merged_path


async def _register_artifact(
    db,
    job_id: UUID,
    revision_id: UUID,
    doc_code: str,
    fmt: str,
    file_path: Path,
    is_draft: bool,
    collected_artifacts: List[Dict[str, Any]],
) -> None:
    """Computes file metadata and registers an artifact both in memory and DB."""
    size_bytes = file_path.stat().st_size
    sha256_hex = await asyncio.to_thread(compute_sha256, file_path)
    collected_artifacts.append({
        "doc_code": doc_code,
        "format": fmt,
        "filename": file_path.name,
        "path": file_path,
        "file_path": str(file_path),
        "size_bytes": size_bytes,
        "sha256": sha256_hex,
    })
    db.add(
        Artifact(
            job_id=job_id,
            revision_id=revision_id,
            doc_code=doc_code,
            format=fmt,
            filename=file_path.name,
            file_path=str(file_path),
            file_size=size_bytes,
            sha256_hash=sha256_hex,
            is_draft=is_draft,
            archive_status="SYNCED",
        )
    )


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

            # Build generation context & clean previous artifacts for requested formats
            context = build_generation_context(revision, package=revision.package, is_draft=is_draft)
            formats_to_clean = list(target_formats)
            await db.execute(
                delete(Artifact)
                .where(
                    Artifact.revision_id == revision.id,
                    Artifact.format.in_(formats_to_clean),
                )
            )
            job.progress_percent = 12
            await db.commit()

            collected_artifacts: List[Dict[str, Any]] = []
            docx_rendered_files: Dict[str, Path] = {}

            # 3. XLSX Generation
            if "XLSX" in target_formats:
                logger.info(f"Generating consolidated Excel workbook for job {job_id}")
                xlsx_dir = rev_dir / "excel"
                xlsx_dir.mkdir(parents=True, exist_ok=True)
                xlsx_path = xlsx_dir / "00_PAKET_PENGADAAN.xlsx"

                excel_gen = ExcelPackageGenerator(context, is_draft=is_draft)
                await asyncio.to_thread(excel_gen.generate_workbook, xlsx_path)

                await _register_artifact(
                    db=db,
                    job_id=job.id,
                    revision_id=revision.id,
                    doc_code="ALL",
                    fmt="XLSX",
                    file_path=xlsx_path,
                    is_draft=is_draft,
                    collected_artifacts=collected_artifacts,
                )
                job.progress_percent = 25
                await db.commit()

            # 4. DOCX Generation
            # If PDF is requested, DOCX must also be generated first as source
            need_docx = ("DOCX" in target_formats) or ("PDF" in target_formats)
            if need_docx:
                logger.info(f"Generating 13 DOCX documents for job {job_id}")
                docx_dir = rev_dir / "docx"
                docx_dir.mkdir(parents=True, exist_ok=True)

                docx_gen = await asyncio.to_thread(DocxPackageGenerator, context)
                total_docx = len(DOCUMENT_MAP)
                for idx, (doc_code, (_tmpl_filename, out_filename)) in enumerate(DOCUMENT_MAP.items()):
                    out_path = docx_dir / out_filename
                    await asyncio.to_thread(docx_gen.generate_single, doc_code, out_path)
                    docx_rendered_files[doc_code] = out_path

                    if "DOCX" in target_formats:
                        await _register_artifact(
                            db=db,
                            job_id=job.id,
                            revision_id=revision.id,
                            doc_code=doc_code,
                            fmt="DOCX",
                            file_path=out_path,
                            is_draft=is_draft,
                            collected_artifacts=collected_artifacts,
                        )

                    job.progress_percent = 25 + int(((idx + 1) / total_docx) * 25)
                    await db.commit()

            # 5. PDF Generation & Merging
            if "PDF" in target_formats:
                logger.info(f"Converting DOCX to PDF for job {job_id}")
                pdf_dir = rev_dir / "pdf"
                pdf_dir.mkdir(parents=True, exist_ok=True)

                pdf_service = await asyncio.to_thread(PdfService)
                pdf_rendered_files: Dict[str, Path] = {}
                total_pdfs = max(len(docx_rendered_files), 1)
                for idx, (doc_code, docx_path) in enumerate(docx_rendered_files.items()):
                    pdf_path = await asyncio.to_thread(
                        _convert_single_pdf, pdf_service, docx_path, pdf_dir, is_draft
                    )
                    pdf_rendered_files[doc_code] = pdf_path

                    await _register_artifact(
                        db=db,
                        job_id=job.id,
                        revision_id=revision.id,
                        doc_code=doc_code,
                        fmt="PDF",
                        file_path=pdf_path,
                        is_draft=is_draft,
                        collected_artifacts=collected_artifacts,
                    )
                    job.progress_percent = 50 + int(((idx + 1) / total_pdfs) * 35)
                    await db.commit()

                merged_path = pdf_dir / "00_PAKET_LENGKAP.pdf"
                await asyncio.to_thread(_merge_pdfs, pdf_rendered_files, merged_path)
                await _register_artifact(
                    db=db,
                    job_id=job.id,
                    revision_id=revision.id,
                    doc_code="ALL",
                    fmt="PDF",
                    file_path=merged_path,
                    is_draft=is_draft,
                    collected_artifacts=collected_artifacts,
                )
                job.progress_percent = 90
                await db.commit()

            # 6. ZIP Packaging & Manifests
            if "ZIP" in target_formats:
                logger.info(f"Assembling ZIP archive and SHA-256 manifests for job {job_id}")
                zip_dir = rev_dir / "zip"
                zip_dir.mkdir(parents=True, exist_ok=True)

                packager = ZipPackager(context)
                pkg_result = await asyncio.to_thread(
                    packager.create_package_zip, collected_artifacts, zip_dir
                )
                zip_path = Path(pkg_result["zip_file"]["file_path"])
                await _register_artifact(
                    db=db,
                    job_id=job.id,
                    revision_id=revision.id,
                    doc_code="ZIP",
                    fmt="ZIP",
                    file_path=zip_path,
                    is_draft=is_draft,
                    collected_artifacts=collected_artifacts,
                )

            # 7. Complete Job
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
