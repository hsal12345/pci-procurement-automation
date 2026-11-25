from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.config import Settings, settings
from app.database import AsyncSessionLocal, Base, async_engine
from app.main import app
from app.models.archive import ArchiveRecord
from app.models.audit import AuditEvent
from app.models.generation import Artifact
from app.models.masters import Company, School
from app.models.packages import Package, PackageRevision
from app.services.drive_sync import execute_revision_drive_upload
from app.services.google_drive_service import GoogleDriveService


@pytest.fixture(autouse=True)
async def prepare_database():
    """Clean tables before each test."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


async def _seed_package_and_artifacts(
    tmp_path: Path,
    rev_status: str = "APPROVED",
    pkg_status: str = "ACTIVE",
    revision_number: int = 1,
    school_name: str = "SD NEGERI KEBON KOSONG 09",
    fiscal_year: int = 2026,
    quarter: int = 2,
    package_id=None,
    package_number: str = None,
):
    async with AsyncSessionLocal() as db:
        school = await db.scalar(select(School).limit(1))
        if not school:
            school = School(
                name=school_name,
                npsn=f"2010{uuid4().hex[:4]}",
                level="SD",
                address="Jl. Kemayoran",
            )
            db.add(school)
            await db.flush()

        company = await db.scalar(select(Company).limit(1))
        if not company:
            company = Company(
                legal_name="CV. PUSTAKA CEMERLANG INDONESIA",
                address="Wisma Mitra Sunter Unit 3-03",
                director_name="Bambang Solifian",
            )
            db.add(company)
            await db.flush()

        if package_id is None:
            pkg = Package(
                package_number=package_number or f"PKG/{fiscal_year}/Q{quarter}/{uuid4().hex[:4].upper()}",
                school_id=school.id,
                fiscal_year=fiscal_year,
                quarter=quarter,
                status=pkg_status,
            )
            db.add(pkg)
            await db.flush()
        else:
            pkg = await db.get(Package, package_id)

        rev = PackageRevision(
            package_id=pkg.id,
            revision_number=revision_number,
            version=1,
            status=rev_status,
            school_snapshot={"name": school_name, "npsn": school.npsn},
            company_snapshot={"legal_name": company.legal_name},
            tax_policy_snapshot=[],
            officials_snapshot=[],
            is_locked=(rev_status in ["UNDER_REVIEW", "APPROVED", "ISSUED"]),
        )
        db.add(rev)
        await db.flush()

        # Create 2 sample artifact files on disk (DOCX + ZIP)
        docx_file = tmp_path / f"D01_HPS_rev{revision_number}.docx"
        docx_file.write_bytes(b"PK\x03\x04dummy-docx-content")
        zip_file = tmp_path / f"PKG_REV{revision_number}_20261114.zip"
        zip_file.write_bytes(b"PK\x03\x04dummy-zip-content")

        art1 = Artifact(
            revision_id=rev.id,
            doc_code="D01",
            format="DOCX",
            filename="D01_HPS.docx",
            file_path=str(docx_file),
            file_size=docx_file.stat().st_size,
            sha256_hash="abc123",
            is_draft=False,
            archive_status="PENDING",
        )
        art2 = Artifact(
            revision_id=rev.id,
            doc_code="ZIP",
            format="ZIP",
            filename=zip_file.name,
            file_path=str(zip_file),
            file_size=zip_file.stat().st_size,
            sha256_hash="def456",
            is_draft=False,
            archive_status="PENDING",
        )
        db.add_all([art1, art2])
        await db.commit()
        return pkg.id, rev.id


@pytest.mark.asyncio
async def test_drive_upload_requires_approved_status_and_admin_role(tmp_path):
    """Asserts DRAFT cannot be uploaded and non-Admin roles receive HTTP 403."""
    _, draft_rev_id = await _seed_package_and_artifacts(tmp_path, rev_status="DRAFT")
    _, approved_rev_id = await _seed_package_and_artifacts(tmp_path, rev_status="APPROVED")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Draft revision rejected (400)
        resp_draft = await client.post(
            f"/api/v1/revisions/{draft_rev_id}/archive/upload",
            headers={"X-User-Role": "ADMINISTRATION"},
        )
        assert resp_draft.status_code == 400
        assert "APPROVED" in resp_draft.json()["detail"]

        # 2. Logistics / Finance Director rejected (403)
        for forbidden_role in ("LOGISTICS", "FINANCE_DIRECTOR"):
            resp_role = await client.post(
                f"/api/v1/revisions/{approved_rev_id}/archive/upload",
                headers={"X-User-Role": forbidden_role},
            )
            assert resp_role.status_code == 403

        # 3. SysAdmin allowed (202) in mock mode
        with patch.object(settings, "DRIVE_SYNC_MODE", "mock"):
            resp_ok = await client.post(
                f"/api/v1/revisions/{approved_rev_id}/archive/upload",
                headers={"X-User-Role": "SYSTEM_ADMINISTRATOR"},
            )
            assert resp_ok.status_code == 202
            body = resp_ok.json()
            assert body["status"] in ("SYNCING", "SYNCED")


@pytest.mark.asyncio
async def test_drive_hierarchy_and_revision_overwrite(tmp_path):
    """Asserts Lv1(School)->Lv2(Year)->Lv3(Triwulan)->Lv4(Kode Pengadaan)->Lv5(Files) and overwrite on revision."""
    pkg_id, rev1_id = await _seed_package_and_artifacts(
        tmp_path,
        rev_status="APPROVED",
        revision_number=1,
        school_name="SD NEGERI KEBON KOSONG 09",
        fiscal_year=2026,
        quarter=2,
        package_number="PKG/2026/Q2/0001",
    )
    _, rev2_id = await _seed_package_and_artifacts(
        tmp_path,
        rev_status="APPROVED",
        revision_number=2,
        school_name="SD NEGERI KEBON KOSONG 09",
        fiscal_year=2026,
        quarter=2,
        package_id=pkg_id,
    )

    mock_hierarchy = {
        "folder_id": "lv4_pkg_0001_id",
        "folder_url": "https://drive.google.com/drive/folders/lv4_pkg_0001_id",
        "display_path": "SD NEGERI KEBON KOSONG 09 / 2026 / Triwulan 2 / PKG-2026-Q2-0001",
        "lv1_folder_id": "lv1_school_id",
        "lv2_folder_id": "lv2_year_id",
        "lv3_folder_id": "lv3_triwulan_2_id",
    }

    async def fake_upload(**kwargs):
        fname = kwargs["target_filename"]
        rev_num = kwargs["revision_number"]
        return {
            "id": f"file_{fname}",
            "name": fname,
            "webViewLink": f"https://drive.google.com/file/d/file_{fname}/view",
            "size": kwargs.get("file_size", 10),
            "overwritten": rev_num > 1,
        }

    with (
        patch.object(Settings, "is_drive_live_configured", return_value=True),
        patch(
            "app.services.drive_sync.google_drive_service.ensure_hierarchy",
            new=AsyncMock(return_value=mock_hierarchy),
        ) as mock_ensure,
        patch(
            "app.services.drive_sync.google_drive_service.upload_or_overwrite_file",
            side_effect=fake_upload,
        ) as mock_upload,
    ):
        await execute_revision_drive_upload(rev1_id, actor_name="Admin PCI")
        mock_ensure.assert_awaited_once_with(
            school_name="SD NEGERI KEBON KOSONG 09",
            fiscal_year=2026,
            quarter=2,
            package_number="PKG/2026/Q2/0001",
        )
        uploaded_names = [call.kwargs["target_filename"] for call in mock_upload.call_args_list]
        assert "D01_HPS.docx" in uploaded_names
        assert "00_PAKET_ARSIP_LENGKAP.zip" in uploaded_names

        # Upload Rev-2 -> should overwrite in same Lv4 folder & mark Rev-1 SUPERSEDED
        await execute_revision_drive_upload(rev2_id, actor_name="SysAdmin PCI")

    async with AsyncSessionLocal() as db:
        arch1 = await db.scalar(select(ArchiveRecord).where(ArchiveRecord.revision_id == rev1_id))
        arch2 = await db.scalar(select(ArchiveRecord).where(ArchiveRecord.revision_id == rev2_id))
        assert arch1.status == "SUPERSEDED"
        assert arch2.status == "SYNCED"
        assert arch2.progress_percent == 100
        assert arch2.uploaded_files == 2
        assert arch2.total_files == 2
        assert arch2.drive_folder_id == mock_hierarchy["folder_id"]
        assert arch2.drive_folder_url == mock_hierarchy["folder_url"]
        assert arch2.folder_path == f"{mock_hierarchy['display_path']} (Rev-2)"
        assert "PKG-2026-Q2-0001" in arch2.current_step

        arts2 = (
            await db.execute(select(Artifact).where(Artifact.revision_id == rev2_id))
        ).scalars().all()
        assert all(a.archive_status == "SYNCED" for a in arts2)
        assert all(a.drive_web_view_link for a in arts2)

        audit = await db.scalar(
            select(AuditEvent).where(
                AuditEvent.entity_id == str(arch2.id),
                AuditEvent.action == "ARCHIVE_SYNCED",
            )
        )
        assert audit is not None
        assert audit.after_state["overwritten_count"] == 2


@pytest.mark.asyncio
async def test_ensure_hierarchy_creates_4_folder_levels():
    """Unit test for GoogleDriveService.ensure_hierarchy verifying 4 nested folder levels."""
    svc = GoogleDriveService()
    created_folders = [
        {"id": "lv1_id", "name": "SD NEGERI 01", "webViewLink": "https://drive.google.com/drive/folders/lv1_id"},
        {"id": "lv2_id", "name": "2026", "webViewLink": "https://drive.google.com/drive/folders/lv2_id"},
        {"id": "lv3_id", "name": "Triwulan 2", "webViewLink": "https://drive.google.com/drive/folders/lv3_id"},
        {"id": "lv4_id", "name": "PKG-2026-Q2-0001", "webViewLink": "https://drive.google.com/drive/folders/lv4_id"},
    ]

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False

    with (
        patch.object(Settings, "get_effective_drive_root_folder_id", return_value="root_folder_id"),
        patch.object(svc, "_auth_headers", new=AsyncMock(return_value={"Authorization": "Bearer tok"})),
        patch.object(svc, "_ensure_folder", new=AsyncMock(side_effect=created_folders)) as mock_ensure_folder,
        patch("app.services.google_drive_service.httpx.AsyncClient", return_value=mock_client),
    ):
        res = await svc.ensure_hierarchy(
            school_name="SD NEGERI 01",
            fiscal_year=2026,
            quarter=2,
            package_number="PKG/2026/Q2/0001",
        )

    assert mock_ensure_folder.await_count == 4
    calls = mock_ensure_folder.await_args_list
    assert calls[0].args == (mock_client, {"Authorization": "Bearer tok"}, "root_folder_id", "SD NEGERI 01")
    assert calls[1].args == (mock_client, {"Authorization": "Bearer tok"}, "lv1_id", "2026")
    assert calls[2].args == (mock_client, {"Authorization": "Bearer tok"}, "lv2_id", "Triwulan 2")
    assert calls[3].args == (mock_client, {"Authorization": "Bearer tok"}, "lv3_id", "PKG-2026-Q2-0001")

    assert res == {
        "folder_id": "lv4_id",
        "folder_url": "https://drive.google.com/drive/folders/lv4_id",
        "display_path": "SD NEGERI 01 / 2026 / Triwulan 2 / PKG-2026-Q2-0001",
        "lv1_folder_id": "lv1_id",
        "lv2_folder_id": "lv2_id",
        "lv3_folder_id": "lv3_id",
    }


@pytest.mark.asyncio
async def test_upload_rejects_storage_quota_exceeded_without_zero_byte_fallback(tmp_path):
    """Ensures 403 storageQuotaExceeded fails fast instead of creating 0-byte Drive placeholders."""
    svc = GoogleDriveService()
    sample = tmp_path / "D01_HPS.pdf"
    sample.write_bytes(b"%PDF-1.4\nhello world\n%%EOF")

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False
    mock_client.post = AsyncMock(
        return_value=httpx.Response(
            403,
            json={
                "error": {
                    "code": 403,
                    "message": "Service Accounts do not have storage quota.",
                    "errors": [{"reason": "storageQuotaExceeded"}],
                }
            },
        )
    )

    with (
        patch.object(svc, "_auth_headers", new=AsyncMock(return_value={"Authorization": "Bearer tok"})),
        patch.object(svc, "_find_existing_files", new=AsyncMock(return_value=[])),
        patch("app.services.google_drive_service.httpx.AsyncClient", return_value=mock_client),
    ):
        with pytest.raises(RuntimeError, match="storageQuotaExceeded"):
            await svc.upload_or_overwrite_file(
                local_path=sample,
                folder_id="fld_root",
                target_filename="D01_HPS.pdf",
                fmt="PDF",
            )

    # Exactly 1 binary upload attempt — never a second 0-byte metadata POST
    assert mock_client.post.await_count == 1


@pytest.mark.asyncio
async def test_upload_replaces_existing_zero_byte_file_with_full_bytes(tmp_path):
    """Ensures stale 0-byte files in Drive are deleted/detached and re-uploaded with full binary size."""
    svc = GoogleDriveService()
    payload = b"PK\x03\x04binary-zip-bytes-1234567890"
    sample = tmp_path / "00_PAKET_ARSIP_LENGKAP.zip"
    sample.write_bytes(payload)

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False
    mock_client.patch = AsyncMock()
    mock_client.post = AsyncMock(
        return_value=httpx.Response(
            200,
            json={
                "id": "new_non_zero_id",
                "name": "00_PAKET_ARSIP_LENGKAP.zip",
                "webViewLink": "https://drive.google.com/file/d/new_non_zero_id/view",
                "size": str(len(payload)),
            },
        )
    )

    with (
        patch.object(svc, "_auth_headers", new=AsyncMock(return_value={"Authorization": "Bearer tok"})),
        patch.object(
            svc,
            "_find_existing_files",
            new=AsyncMock(return_value=[{"id": "stale_zero_id", "name": "00_PAKET_ARSIP_LENGKAP.zip", "size": "0"}]),
        ),
        patch.object(svc, "_delete_or_remove_file", new=AsyncMock()) as mock_delete,
        patch("app.services.google_drive_service.httpx.AsyncClient", return_value=mock_client),
    ):
        res = await svc.upload_or_overwrite_file(
            local_path=sample,
            folder_id="fld_triwulan",
            target_filename="00_PAKET_ARSIP_LENGKAP.zip",
            fmt="ZIP",
        )

    mock_delete.assert_awaited_once_with(mock_client, {"Authorization": "Bearer tok"}, "stale_zero_id", "fld_triwulan")
    assert mock_client.post.await_count == 1
    assert mock_client.patch.await_count == 0
    assert res["id"] == "new_non_zero_id"
    assert res["size"] == len(payload)
    assert res["overwritten"] is True


@pytest.mark.asyncio
async def test_preflight_blocks_upload_when_service_account_zero_quota(tmp_path):
    """Ensures API rejects live upload before backgrounding if Drive reports 0-byte Service Account quota."""
    _, approved_rev_id = await _seed_package_and_artifacts(tmp_path, rev_status="APPROVED")

    with (
        patch.object(Settings, "is_drive_live_configured", return_value=True),
        patch(
            "app.api.v1.archive.google_drive_service.check_health",
            new=AsyncMock(
                return_value={
                    "connected": True,
                    "can_upload_binary": False,
                    "error": "Service Account pada My Drive pribadi memiliki kuota 0 byte.",
                }
            ),
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/revisions/{approved_rev_id}/archive/upload",
                headers={"X-User-Role": "ADMINISTRATION"},
            )
            assert resp.status_code == 400
            assert "0 byte" in resp.json()["detail"]
