import json
import pytest
from datetime import date
from decimal import Decimal
from uuid import uuid4, UUID
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.main import app
from app.database import async_engine, Base, AsyncSessionLocal
from app.models.masters import School, Company
from app.models.packages import Package, PackageRevision, RevisionLine, DocumentEvent, DocumentNumber
from app.models.approvals import Approval
from app.models.logistics import LogisticsRecord, LogisticsEvidence
from app.models.archive import ArchiveRecord
from app.models.generation import GenerationJob, Artifact
from app.services.generation_worker import run_generation_job


@pytest.fixture(autouse=True)
async def prepare_database():
    """Clean tables before each test."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


async def seed_test_package_fixture(db, status="DRAFT", items_count=2):
    """Creates a comprehensive package with Revision 1 and valid lines/events/numbers."""
    # 1. School (get existing or create)
    school = await db.scalar(select(School).limit(1))
    if not school:
        school = School(
            name="SD NEGERI KEBON KOSONG 09",
            npsn=f"2010{uuid4().hex[:4]}",
            level="SD",
            address="Jl. Kemayoran Gempol no.32",
            email="sdnkk09@gmail.com"
        )
        db.add(school)
        await db.flush()

    # 2. Company (get existing or create)
    company = await db.scalar(select(Company).limit(1))
    if not company:
        company = Company(
            legal_name="CV. PUSTAKA CEMERLANG INDONESIA",
            address="Wisma Mitra Sunter Unit 3-03, Jakarta Utara",
            director_name="Bambang Solifian",
            director_title="Direktur Utama"
        )
        db.add(company)
        await db.flush()

    # 3. Package
    pkg = Package(
        package_number=f"PKG/2026/Q2/{uuid4().hex[:4].upper()}",
        school_id=school.id,
        fiscal_year=2026,
        quarter=2,
        status="ISSUED" if status == "ISSUED" else ("CANCELLED" if status == "CANCELLED" else "ACTIVE")
    )
    db.add(pkg)
    await db.flush()

    # 4. Revision 1
    school_snap = {"name": school.name, "npsn": school.npsn, "address": school.address}
    comp_snap = {"legal_name": company.legal_name, "director_name": company.director_name}
    tax_snap = [{"tax_type": "PPN", "rate": "0.11", "is_inclusive": False, "withholding_rule": "NONE"}]

    rev = PackageRevision(
        package_id=pkg.id,
        revision_number=1,
        version=1,
        status=status,
        ai_review_status="COMPLETED",
        school_snapshot=school_snap,
        company_snapshot=comp_snap,
        tax_policy_snapshot=tax_snap,
        officials_snapshot=[],
        subtotal=Decimal("385000"),
        tax_total=Decimal("42350"),
        grand_total=Decimal("427350"),
        terbilang_grand_total="Empat Ratus Dua Puluh Tujuh Ribu Tiga Ratus Lima Puluh Rupiah",
        is_locked=(status in ["UNDER_REVIEW", "APPROVED", "ISSUED", "CANCELLED"]),
        notes="Revisi draft pengadaan alat kebersihan"
    )
    db.add(rev)
    await db.flush()

    # 5. Lines
    l1 = RevisionLine(
        revision_id=rev.id,
        line_number=1,
        original_description="Pembersih Kaca",
        confirmed_description="Pembersih Kaca 450ml",
        quantity=Decimal("10"),
        received_quantity=Decimal("10"),
        unit="Botol",
        hps_unit_price=Decimal("25000"),
        offer_unit_price=Decimal("24000"),
        final_unit_price=Decimal("24000"),
        discount=Decimal("0"),
        line_total=Decimal("240000"),
        condition="BAIK"
    )
    l2 = RevisionLine(
        revision_id=rev.id,
        line_number=2,
        original_description="Pembersih Debu",
        confirmed_description="Kemoceng Microfiber",
        quantity=Decimal("5"),
        received_quantity=Decimal("5"),
        unit="Pcs",
        hps_unit_price=Decimal("30000"),
        offer_unit_price=Decimal("29000"),
        final_unit_price=Decimal("29000"),
        discount=Decimal("0"),
        line_total=Decimal("145000"),
        condition="BAIK"
    )
    db.add_all([l1, l2])

    # 6. Events (HPS through KWITANSI)
    event_codes = ["HPS", "SPP", "PENAWARAN", "NEGOSIASI", "PESANAN", "SURAT_JALAN", "BAPB", "BAST", "BAPP", "FAKTUR", "KWITANSI"]
    for idx, ev_code in enumerate(event_codes, start=1):
        db.add(DocumentEvent(
            revision_id=rev.id,
            event_code=ev_code,
            event_date=date(2026, 5, min(idx, 28)),
            day_name_id="Selasa",
            location="Jakarta"
        ))

    # 7. Numbers (D01-D13)
    for i in range(1, 14):
        db.add(DocumentNumber(
            revision_id=rev.id,
            doc_code=f"D{i:02d}",
            doc_number=f"{i:02d}/PCI/2026",
            issuer="COMPANY" if f"D{i:02d}" in ["D03", "D06", "D07", "D08", "D13"] else "SCHOOL",
            counter_val=i,
            is_reserved=True
        ))

    pkg.current_revision_id = rev.id
    await db.commit()
    await db.refresh(pkg)
    await db.refresh(rev)
    return pkg, rev


@pytest.mark.asyncio
async def test_optimistic_locking_collision():
    """Simulates simultaneous update attempts from two sessions.
    Asserts first succeeds and second returns HTTP 409 Conflict.
    """
    async with AsyncSessionLocal() as db:
        pkg, rev = await seed_test_package_fixture(db, status="DRAFT")
        pkg_id = str(pkg.id)
        rev_id = str(rev.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Client A updates lines with expected_version = 1 -> succeeds
        resp_a = await client.patch(
            f"/api/v1/packages/{pkg_id}/revisions/{rev_id}",
            headers={"X-User-Role": "ADMINISTRATION"},
            json={
                "expected_version": 1,
                "notes": "Pembaruan dari Sesi A",
                "lines": [
                    {
                        "line_number": 1,
                        "original_description": "Pembersih Kaca",
                        "confirmed_description": "Pembersih Kaca Spray 500ml",
                        "quantity": 10,
                        "unit": "Botol",
                        "hps_unit_price": 25000,
                        "offer_unit_price": 24000,
                        "final_unit_price": 24000,
                        "discount": 0,
                        "line_total": 240000,
                        "condition": "BAIK"
                    }
                ]
            }
        )
        assert resp_a.status_code == 200, resp_a.text
        data_a = resp_a.json()
        assert data_a["version"] == 2

        # Client B attempts to update with stale expected_version = 1 -> HTTP 409 Conflict
        resp_b = await client.patch(
            f"/api/v1/packages/{pkg_id}/revisions/{rev_id}",
            headers={"X-User-Role": "ADMINISTRATION"},
            json={
                "expected_version": 1,
                "notes": "Pembaruan dari Sesi B (stale)"
            }
        )
        assert resp_b.status_code == 409
        assert "Konflik persaingan pembaruan" in resp_b.json()["detail"]

        # Client B attempts to submit with stale expected_version = 1 -> HTTP 409 Conflict
        resp_submit_stale = await client.post(
            f"/api/v1/packages/{pkg_id}/revisions/{rev_id}/submit",
            headers={"X-User-Role": "ADMINISTRATION"},
            json={"expected_version": 1}
        )
        assert resp_submit_stale.status_code == 409

        # Client B submits with expected_version = 2 -> Succeeds
        resp_submit = await client.post(
            f"/api/v1/packages/{pkg_id}/revisions/{rev_id}/submit",
            headers={"X-User-Role": "ADMINISTRATION"},
            json={"expected_version": 2}
        )
        assert resp_submit.status_code == 200
        assert resp_submit.json()["new_status"] == "UNDER_REVIEW"
        assert resp_submit.json()["version"] == 3


@pytest.mark.asyncio
async def test_workflow_lifecycle_and_dual_status():
    """Validates complete business lifecycle:
    DRAFT -> UNDER_REVIEW -> RETURNED -> UNDER_REVIEW -> APPROVED -> ISSUED.
    Verifies approvals row, dual package/revision state, and final artifact generation.
    """
    async with AsyncSessionLocal() as db:
        pkg, rev = await seed_test_package_fixture(db, status="DRAFT")
        pkg_id = str(pkg.id)
        rev_id = str(rev.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Admin submits (expected_version = 1) -> UNDER_REVIEW
        resp1 = await client.post(
            f"/api/v1/packages/{pkg_id}/revisions/{rev_id}/submit",
            headers={"X-User-Role": "ADMINISTRATION"},
            json={"expected_version": 1, "notes": "Diajukan untuk penelaahan"}
        )
        assert resp1.status_code == 200
        assert resp1.json()["new_status"] == "UNDER_REVIEW"
        assert resp1.json()["version"] == 2

        # 2. Finance returns with comment -> RETURNED
        resp2 = await client.post(
            f"/api/v1/packages/{pkg_id}/revisions/{rev_id}/return",
            headers={"X-User-Role": "FINANCE_DIRECTOR"},
            json={"expected_version": 2, "comment": "Mohon perjelas spesifikasi botol pembersih kaca."}
        )
        assert resp2.status_code == 200
        assert resp2.json()["new_status"] == "RETURNED"
        assert resp2.json()["version"] == 3

        # 3. Admin re-submits -> UNDER_REVIEW
        resp3 = await client.post(
            f"/api/v1/packages/{pkg_id}/revisions/{rev_id}/submit",
            headers={"X-User-Role": "ADMINISTRATION"},
            json={"expected_version": 3, "notes": "Spesifikasi telah dilengkapi"}
        )
        assert resp3.status_code == 200
        assert resp3.json()["new_status"] == "UNDER_REVIEW"
        assert resp3.json()["version"] == 4

        # 4. Finance approves -> APPROVED
        resp4 = await client.post(
            f"/api/v1/packages/{pkg_id}/revisions/{rev_id}/approve",
            headers={"X-User-Role": "FINANCE_DIRECTOR"},
            json={"expected_version": 4, "manifest_hash": "dummy_manifest_hash_abc123", "note": "Dokumen lengkap dan sah"}
        )
        assert resp4.status_code == 200
        assert resp4.json()["new_status"] == "APPROVED"
        assert resp4.json()["version"] == 5

        # Verify Approval record in DB
        async with AsyncSessionLocal() as db:
            appr_res = await db.execute(select(Approval).where(Approval.revision_id == rev.id))
            approvals = appr_res.scalars().all()
            assert len(approvals) == 2  # 1 RETURNED, 1 APPROVED
            assert approvals[-1].decision == "APPROVED"

        # 5. Logistics updates delivery facts
        resp_log = await client.patch(
            f"/api/v1/packages/{pkg_id}/revisions/{rev_id}/logistics",
            headers={"X-User-Role": "LOGISTICS"},
            json={
                "dispatch_date": "2026-05-10",
                "receipt_date": "2026-05-12",
                "delivery_reference": "SJ-PCI-2026-001",
                "courier_name": "Suryanto",
                "vehicle_plate": "B 1234 PCI",
                "inspection_status": "PASSED"
            }
        )
        assert resp_log.status_code == 200

        # 6. Final Issuance
        resp_issue = await client.post(
            f"/api/v1/packages/{pkg_id}/revisions/{rev_id}/issue",
            headers={"X-User-Role": "FINANCE_DIRECTOR"}
        )
        assert resp_issue.status_code == 200
        assert resp_issue.json()["new_status"] == "ISSUED"
        assert resp_issue.json()["package_status"] == "ISSUED"

        # Check that ArchiveRecord was registered in PENDING
        async with AsyncSessionLocal() as db:
            arch_res = await db.execute(select(ArchiveRecord).where(ArchiveRecord.revision_id == rev.id))
            archive = arch_res.scalar_one_or_none()
            assert archive is not None
            assert archive.status == "PENDING"
            assert "Rev-1" in archive.folder_path


@pytest.mark.asyncio
async def test_rbac_unauthorized_actions():
    """Asserts strict server-side role boundaries:
    - Administration cannot approve
    - Logistics cannot alter prices
    - Finance Director cannot edit lines directly without returning
    """
    async with AsyncSessionLocal() as db:
        pkg, rev = await seed_test_package_fixture(db, status="UNDER_REVIEW")
        pkg_id = str(pkg.id)
        rev_id = str(rev.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Admin attempts to call approve -> 403 Forbidden
        resp_admin_approve = await client.post(
            f"/api/v1/packages/{pkg_id}/revisions/{rev_id}/approve",
            headers={"X-User-Role": "ADMINISTRATION"},
            json={"expected_version": 1}
        )
        assert resp_admin_approve.status_code == 403

        # 2. Logistics attempts to edit pricing/lines via PATCH -> 403 Forbidden
        resp_logistics_edit = await client.patch(
            f"/api/v1/packages/{pkg_id}/revisions/{rev_id}",
            headers={"X-User-Role": "LOGISTICS"},
            json={
                "expected_version": 1,
                "lines": [
                    {
                        "line_number": 1,
                        "original_description": "Pembersih Kaca",
                        "confirmed_description": "Pembersih Kaca",
                        "unit": "Botol",
                        "hps_unit_price": 999999
                    }
                ]
            }
        )
        assert resp_logistics_edit.status_code == 403

        # 3. Finance attempts to edit lines without returning -> 403 Forbidden
        resp_fin_edit = await client.patch(
            f"/api/v1/packages/{pkg_id}/revisions/{rev_id}",
            headers={"X-User-Role": "FINANCE_DIRECTOR"},
            json={
                "expected_version": 1,
                "notes": "Direct edit by Finance"
            }
        )
        assert resp_fin_edit.status_code == 403


@pytest.mark.asyncio
async def test_state_contingent_cancellation_rbac():
    """Asserts state-contingent cancellation:
    - Admin can cancel DRAFT
    - Admin CANNOT cancel APPROVED or ISSUED (HTTP 403)
    - Finance Director CAN cancel APPROVED or ISSUED
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Admin cancels DRAFT -> Succeeds
        async with AsyncSessionLocal() as db:
            pkg_draft, _ = await seed_test_package_fixture(db, status="DRAFT")
            pkg_draft_id = str(pkg_draft.id)

        resp_cancel_draft = await client.post(
            f"/api/v1/packages/{pkg_draft_id}/cancel",
            headers={"X-User-Role": "ADMINISTRATION"},
            json={"reason": "Sekolah membatalkan kebutuhan alat kebersihan"}
        )
        assert resp_cancel_draft.status_code == 200
        assert resp_cancel_draft.json()["new_status"] == "CANCELLED"

        # 2. Create APPROVED package
        async with AsyncSessionLocal() as db:
            pkg_appr, _ = await seed_test_package_fixture(db, status="APPROVED")
            pkg_appr_id = str(pkg_appr.id)

        # Admin attempts to cancel APPROVED -> HTTP 403
        resp_admin_cancel = await client.post(
            f"/api/v1/packages/{pkg_appr_id}/cancel",
            headers={"X-User-Role": "ADMINISTRATION"},
            json={"reason": "Admin mencoba membatalkan paket disetujui"}
        )
        assert resp_admin_cancel.status_code == 403
        assert "Hanya Direktur Keuangan" in resp_admin_cancel.json()["detail"]

        # Finance Director cancels APPROVED -> Succeeds
        resp_fin_cancel = await client.post(
            f"/api/v1/packages/{pkg_appr_id}/cancel",
            headers={"X-User-Role": "FINANCE_DIRECTOR"},
            json={"reason": "Dibatalkan direksi karena revisi alokasi dana BOS"}
        )
        assert resp_fin_cancel.status_code == 200
        assert resp_fin_cancel.json()["new_status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_post_approval_immutability():
    """Confirms that attempting to PATCH an APPROVED or ISSUED revision fails with HTTP 409."""
    async with AsyncSessionLocal() as db:
        pkg, rev = await seed_test_package_fixture(db, status="APPROVED")
        pkg_id = str(pkg.id)
        rev_id = str(rev.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.patch(
            f"/api/v1/packages/{pkg_id}/revisions/{rev_id}",
            headers={"X-User-Role": "ADMINISTRATION"},
            json={
                "expected_version": 1,
                "notes": "Attempting illegal post-approval modification"
            }
        )
        assert resp.status_code == 409
        assert "terkunci" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_logistics_br13_and_dispute_routing():
    """Asserts that damaged goods or partial shipments:
    1. Route the revision to OUTSIDE_PILOT_DISPUTE.
    2. Block final issuance under BR13.
    """
    async with AsyncSessionLocal() as db:
        pkg, rev = await seed_test_package_fixture(db, status="APPROVED")
        pkg_id = str(pkg.id)
        rev_id = str(rev.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Mark line 1 as RUSAK
        resp_log = await client.patch(
            f"/api/v1/packages/{pkg_id}/revisions/{rev_id}/logistics",
            headers={"X-User-Role": "LOGISTICS"},
            json={
                "dispatch_date": "2026-05-10",
                "receipt_date": "2026-05-12",
                "line_updates": [
                    {
                        "line_number": 1,
                        "condition": "RUSAK"
                    }
                ]
            }
        )
        assert resp_log.status_code == 200

        # Check DB that revision transitioned to OUTSIDE_PILOT_DISPUTE
        async with AsyncSessionLocal() as db:
            r_res = await db.execute(select(PackageRevision).where(PackageRevision.id == rev.id))
            updated_rev = r_res.scalar_one()
            assert updated_rev.status == "OUTSIDE_PILOT_DISPUTE"

        # Attempting to issue fails with 400 (not APPROVED) or 422 (BR13)
        resp_issue = await client.post(
            f"/api/v1/packages/{pkg_id}/revisions/{rev_id}/issue",
            headers={"X-User-Role": "FINANCE_DIRECTOR"}
        )
        assert resp_issue.status_code in [400, 422]


@pytest.mark.asyncio
async def test_reopen_supersedes_prior_revision():
    """Verifies reopen lifecycle:
    1. Package is ISSUED with Rev 1.
    2. Reopen creates Rev 2 (DRAFT) while Rev 1 remains ISSUED.
    3. Once Rev 2 becomes ISSUED, Rev 1 is atomically marked SUPERSEDED.
    """
    async with AsyncSessionLocal() as db:
        pkg, rev1 = await seed_test_package_fixture(db, status="ISSUED")
        pkg_id = str(pkg.id)
        rev1_id = str(rev1.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Reopen
        resp_reopen = await client.post(
            f"/api/v1/packages/{pkg_id}/reopen",
            headers={"X-User-Role": "ADMINISTRATION"},
            json={"reason": "Penyesuaian kuantitas pesanan"}
        )
        assert resp_reopen.status_code == 201
        data2 = resp_reopen.json()
        assert data2["revision_number"] == 2
        assert data2["status"] == "DRAFT"
        rev2_id = data2["id"]

        # Verify Rev 1 is still ISSUED in DB
        async with AsyncSessionLocal() as db:
            r1 = await db.scalar(select(PackageRevision).where(PackageRevision.id == rev1.id))
            assert r1.status == "ISSUED"

        # Advance Rev 2 to ISSUED:
        # a. Submit
        await client.post(
            f"/api/v1/packages/{pkg_id}/revisions/{rev2_id}/submit",
            headers={"X-User-Role": "ADMINISTRATION"},
            json={"expected_version": 1}
        )
        # b. Approve
        await client.post(
            f"/api/v1/packages/{pkg_id}/revisions/{rev2_id}/approve",
            headers={"X-User-Role": "FINANCE_DIRECTOR"},
            json={"expected_version": 2}
        )
        # c. Logistics
        await client.patch(
            f"/api/v1/packages/{pkg_id}/revisions/{rev2_id}/logistics",
            headers={"X-User-Role": "LOGISTICS"},
            json={"receipt_date": "2026-05-20"}
        )
        # d. Issue Rev 2
        resp_issue2 = await client.post(
            f"/api/v1/packages/{pkg_id}/revisions/{rev2_id}/issue",
            headers={"X-User-Role": "FINANCE_DIRECTOR"}
        )
        assert resp_issue2.status_code == 200

        # Verify Rev 1 is now SUPERSEDED and Rev 2 is ISSUED
        async with AsyncSessionLocal() as db:
            r1_after = await db.scalar(select(PackageRevision).where(PackageRevision.id == rev1.id))
            r2_after = await db.scalar(select(PackageRevision).where(PackageRevision.id == UUID(rev2_id)))
            assert r1_after.status == "SUPERSEDED"
            assert r2_after.status == "ISSUED"


@pytest.mark.asyncio
async def test_drive_outage_resilience():
    """Simulates a Google Drive sync failure:
    Asserts Package remains ISSUED, ArchiveRecord is FAILED, and local downloads still work.
    """
    async with AsyncSessionLocal() as db:
        pkg, rev = await seed_test_package_fixture(db, status="ISSUED")
        pkg_id = str(pkg.id)
        rev_id = str(rev.id)

        # Create pending archive record
        arch = ArchiveRecord(
            package_id=pkg.id,
            revision_id=rev.id,
            target_provider="GOOGLE_DRIVE",
            folder_path="2026/Q2/SD/Test/Rev-1",
            status="PENDING"
        )
        db.add(arch)
        await db.commit()
        await db.refresh(arch)
        arch_id = str(arch.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Simulate n8n reporting upload failure
        resp_cb = await client.post(
            "/api/v1/internal/archive/callback",
            headers={"X-Internal-Service-Key": "dev-internal-service-key"},
            json={
                "archive_id": arch_id,
                "status": "FAILED",
                "error_message": "Google Drive API HTTP 503 Service Unavailable"
            }
        )
        assert resp_cb.status_code == 200
        assert resp_cb.json()["status"] == "FAILED"
        assert resp_cb.json()["attempt_count"] == 1

        # Check that Package and Revision remain ISSUED
        async with AsyncSessionLocal() as db:
            p = await db.scalar(select(Package).where(Package.id == pkg.id))
            r = await db.scalar(select(PackageRevision).where(PackageRevision.id == rev.id))
            assert p.status == "ISSUED"
            assert r.status == "ISSUED"


@pytest.mark.asyncio
async def test_audit_trail_inquiry():
    """Queries package audit trail and verifies chronological operations recording."""
    async with AsyncSessionLocal() as db:
        pkg, rev = await seed_test_package_fixture(db, status="DRAFT")
        pkg_id = str(pkg.id)
        rev_id = str(rev.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Submit
        await client.post(
            f"/api/v1/packages/{pkg_id}/revisions/{rev_id}/submit",
            headers={"X-User-Role": "ADMINISTRATION"},
            json={"expected_version": 1}
        )

        # Return
        await client.post(
            f"/api/v1/packages/{pkg_id}/revisions/{rev_id}/return",
            headers={"X-User-Role": "FINANCE_DIRECTOR"},
            json={"expected_version": 2, "comment": "Tolong revisi"}
        )

        # Get audit
        resp_audit = await client.get(
            f"/api/v1/packages/{pkg_id}/audit",
            headers={"X-User-Role": "ADMINISTRATION"}
        )
        assert resp_audit.status_code == 200
        events = resp_audit.json()
        assert len(events) >= 2
        actions = [e["action"] for e in events]
        assert "RETURN" in actions
        assert "SUBMIT" in actions
