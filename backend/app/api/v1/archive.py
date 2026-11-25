from datetime import datetime
from html import escape
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    get_current_actor_name,
    get_current_user_role,
    require_admin_finance_or_sysadmin,
)
from app.config import settings
from app.database import get_db
from app.models.archive import ArchiveRecord
from app.models.generation import Artifact
from app.models.packages import PackageRevision
from app.schemas.archive import ArchiveRecordResponse
from app.services.drive_sync import execute_revision_drive_upload
from app.services.google_drive_service import google_drive_service, sanitize_drive_name

router = APIRouter(tags=["Google Drive Archive"])

ALLOWED_UPLOAD_ROLES = {"ADMINISTRATION", "SYSTEM_ADMINISTRATOR"}
ELIGIBLE_ARCHIVE_STATUSES = {"APPROVED", "ISSUED"}


def _to_archive_response(
    archive: ArchiveRecord,
    revision_number: Optional[int] = None,
) -> ArchiveRecordResponse:
    resp = ArchiveRecordResponse.model_validate(archive)
    if revision_number is not None:
        resp.revision_number = revision_number
    return resp


@router.get(
    "/revisions/{revision_id}/archive",
    response_model=Optional[ArchiveRecordResponse],
)
async def get_revision_archive_status(
    revision_id: UUID,
    db: AsyncSession = Depends(get_db),
    role: str = Depends(require_admin_finance_or_sysadmin),
):
    """Returns the Google Drive archive status and real-time upload progress for a revision."""
    rev_res = await db.execute(
        select(PackageRevision).where(PackageRevision.id == revision_id)
    )
    revision = rev_res.scalar_one_or_none()
    if not revision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Revisi paket dengan ID {revision_id} tidak ditemukan.",
        )

    arch_res = await db.execute(
        select(ArchiveRecord).where(ArchiveRecord.revision_id == revision_id)
    )
    archive = arch_res.scalar_one_or_none()
    if not archive:
        return None
    return _to_archive_response(archive, revision_number=revision.revision_number)


@router.post(
    "/revisions/{revision_id}/archive/upload",
    response_model=ArchiveRecordResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_revision_to_google_drive(
    revision_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    role: str = Depends(get_current_user_role),
    actor_name: str = Depends(get_current_actor_name),
):
    """Triggers Google Drive upload (with overwrite on revision) for an APPROVED or ISSUED revision.
    Restricted strictly to ADMINISTRATION and SYSTEM_ADMINISTRATOR roles.
    """
    if role.upper() not in ALLOWED_UPLOAD_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya Admin atau Administrator Sistem yang diizinkan mengunggah paket ke Google Drive.",
        )

    rev_res = await db.execute(
        select(PackageRevision)
        .options(selectinload(PackageRevision.package))
        .where(PackageRevision.id == revision_id)
    )
    revision = rev_res.scalar_one_or_none()
    if not revision or not revision.package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Revisi paket dengan ID {revision_id} tidak ditemukan.",
        )

    if (revision.status or "").upper() not in ELIGIBLE_ARCHIVE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Paket pengadaan harus berstatus Disetujui (APPROVED) sebelum dapat disimpan ke Google Drive. "
                f"Status saat ini: {revision.status}."
            ),
        )

    art_count_res = await db.execute(
        select(func.count(Artifact.id)).where(Artifact.revision_id == revision.id)
    )
    total_artifacts = int(art_count_res.scalar_one() or 0)
    if total_artifacts == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Berkas dokumen belum dibuat. Silakan klik 'Hasilkan Seluruh Dokumen (Generate)' terlebih dahulu.",
        )

    if settings.is_drive_live_configured():
        health = await google_drive_service.check_health()
        if not health.get("connected") or not health.get("can_upload_binary"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=health.get("error")
                or (
                    "Google Drive belum siap untuk mengunggah isi berkas. "
                    "Hubungkan akun Google Anda via OAuth 2.0 atau gunakan Shared Drive."
                ),
            )

    pkg = revision.package
    school_name = (revision.school_snapshot or {}).get("name", "Sekolah")
    pkg_folder_name = sanitize_drive_name(pkg.package_number, fallback="Paket")
    folder_path = (
        f"{school_name} / {pkg.fiscal_year} / Triwulan {pkg.quarter} / {pkg_folder_name} "
        f"(Rev-{revision.revision_number})"
    )

    arch_res = await db.execute(
        select(ArchiveRecord).where(ArchiveRecord.revision_id == revision.id)
    )
    archive = arch_res.scalar_one_or_none()

    # Avoid starting duplicate concurrent worker if already actively SYNCING within last 60s
    if archive and archive.status == "SYNCING" and archive.last_attempt_at:
        elapsed = (datetime.utcnow() - archive.last_attempt_at.replace(tzinfo=None)).total_seconds()
        if elapsed < 60:
            return _to_archive_response(archive, revision_number=revision.revision_number)

    if not archive:
        archive = ArchiveRecord(
            package_id=pkg.id,
            revision_id=revision.id,
            target_provider="GOOGLE_DRIVE",
            folder_path=folder_path,
            status="SYNCING",
            progress_percent=5,
            current_step="Memulai antrean unggah ke Google Drive...",
            uploaded_files=0,
            total_files=total_artifacts,
            total_bytes=0,
            attempt_count=0,
            last_attempt_at=datetime.utcnow(),
        )
        db.add(archive)
    else:
        archive.folder_path = folder_path
        archive.status = "SYNCING"
        archive.progress_percent = 5
        archive.current_step = "Memulai antrean unggah ke Google Drive..."
        archive.uploaded_files = 0
        archive.total_files = total_artifacts
        archive.total_bytes = 0
        archive.last_error = None
        archive.last_attempt_at = datetime.utcnow()

    await db.commit()
    await db.refresh(archive)

    background_tasks.add_task(execute_revision_drive_upload, revision.id, actor_name)
    return _to_archive_response(archive, revision_number=revision.revision_number)


@router.get("/archive/health")
async def check_google_drive_health(
    role: str = Depends(require_admin_finance_or_sysadmin),
) -> Dict[str, Any]:
    """Checks Google Drive OAuth 2.0 / Service Account connectivity, root folder access, and quota status."""
    return await google_drive_service.check_health()


@router.get("/archive/oauth/login")
async def google_drive_oauth_login():
    """Redirects the administrator to Google OAuth 2.0 consent screen to grant Drive upload access."""
    try:
        auth_url = google_drive_service.get_oauth_authorization_url()
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return RedirectResponse(url=auth_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/archive/oauth/callback", response_class=HTMLResponse)
async def google_drive_oauth_callback(
    code: Optional[str] = None,
    error: Optional[str] = None,
):
    """Receives Google OAuth 2.0 authorization code and saves refresh token for Drive binary uploads."""
    if error:
        return HTMLResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8"><title>OAuth Google Drive Dibatalkan</title></head>
<body style="font-family:system-ui,sans-serif;max-width:560px;margin:48px auto;padding:24px;line-height:1.6;">
  <h2 style="color:#dc2626;">Autentikasi Google Drive Dibatalkan</h2>
  <p>Google mengembalikan status: <code>{escape(error)}</code>.</p>
  <p>Anda dapat menutup tab ini dan mencoba menghubungkan ulang dari halaman Dokumen Paket SPJ.</p>
</body></html>""",
        )

    if not code:
        return HTMLResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content="""<!doctype html>
<html lang="id"><head><meta charset="utf-8"><title>Kode OAuth Tidak Ditemukan</title></head>
<body style="font-family:system-ui,sans-serif;max-width:560px;margin:48px auto;padding:24px;line-height:1.6;">
  <h2 style="color:#dc2626;">Kode OAuth Tidak Ditemukan</h2>
  <p>Parameter <code>code</code> tidak dikirim oleh Google. Silakan ulangi proses Login Google Drive.</p>
</body></html>""",
        )

    try:
        res = await google_drive_service.exchange_oauth_code(code)
    except Exception as exc:
        return HTMLResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8"><title>Gagal Menghubungkan Google Drive</title></head>
<body style="font-family:system-ui,sans-serif;max-width:560px;margin:48px auto;padding:24px;line-height:1.6;">
  <h2 style="color:#dc2626;">Gagal Menghubungkan Google Drive</h2>
  <p>{escape(str(exc))}</p>
  <p>Periksa kembali Authorized Redirect URI (<code>{escape(settings.GOOGLE_DRIVE_OAUTH_REDIRECT_URI)}</code>) di Google Cloud Console.</p>
</body></html>""",
        )

    connected_email = escape(res.get("connected_email") or "Akun Google Anda")
    return HTMLResponse(
        status_code=status.HTTP_200_OK,
        content=f"""<!doctype html>
<html lang="id"><head><meta charset="utf-8"><title>Google Drive Terhubung</title></head>
<body style="font-family:system-ui,sans-serif;max-width:560px;margin:48px auto;padding:24px;line-height:1.6;">
  <h2 style="color:#059669;">Google Drive Berhasil Terhubung (OAuth 2.0)</h2>
  <p>Akun <strong>{connected_email}</strong> sekarang aktif digunakan untuk mengunggah berkas SPJ penuh ke Google Drive.</p>
  <p>Tab ini dapat ditutup sekarang—status di halaman aplikasi akan diperbarui otomatis saat Anda kembali ke tab aplikasi.</p>
  <script>
    try {{
      if (window.opener) {{
        window.opener.postMessage({{ type: "gdrive-oauth-connected", email: "{connected_email}" }}, "*");
      }}
    }} catch (e) {{}}
  </script>
</body></html>""",
    )


@router.post("/archive/oauth/disconnect")
async def google_drive_oauth_disconnect(
    role: str = Depends(get_current_user_role),
) -> Dict[str, Any]:
    """Disconnects the stored Google Drive OAuth 2.0 token."""
    if role.upper() not in ALLOWED_UPLOAD_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya Admin atau Administrator Sistem yang dapat memutus koneksi OAuth Google Drive.",
        )
    removed = google_drive_service.disconnect_oauth()
    return {"disconnected": True, "token_removed": removed}
