import pytest
from datetime import date
from decimal import Decimal
from uuid import uuid4
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.main import app
from app.database import async_engine, Base, AsyncSessionLocal
from app.models.masters import School, Company
from app.models.packages import Package, PackageRevision, RevisionLine, DocumentEvent, DocumentNumber
from app.models.audit import AuditEvent
from app.services.ai.discrepancy_auditor import CANONICAL_13_DOCUMENTS


@pytest.fixture(autouse=True)
async def prepare_database():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await async_engine.dispose()


async def seed_broken_package(db):
    school = School(
        name="SD NEGERI KEBON KOSONG 09",
        npsn="20101234",
        level="SD",
        address="Jl. Dakota V No. 12",
    )
    db.add(school)

    company = Company(
        legal_name="CV. PUSTAKA CEMERLANG INDONESIA",
        address="Wisma Mitra Sunter Unit 3-03",
        director_name="Bambang Solifian",
        director_title="Direktur Utama",
    )
    db.add(company)
    await db.flush()

    pkg = Package(
        package_number=f"PKG/2026/Q2/{uuid4().hex[:4].upper()}",
        school_id=school.id,
        fiscal_year=2026,
        quarter=2,
        status="ACTIVE",
    )
    db.add(pkg)
    await db.flush()

    # Deliberately broken revision across BR01, BR02, BR04, BR05, BR06, BR07, BR08, BR09, BR11, BR12
    rev = PackageRevision(
        package_id=pkg.id,
        revision_number=1,
        version=1,
        status="DRAFT",
        ai_review_status="NOT_RUN",
        school_snapshot={},  # BR01 missing
        company_snapshot={},  # BR01 missing
        tax_policy_snapshot=[],  # BR06 missing
        officials_snapshot=[],  # BR09 missing
        subtotal=Decimal("99999"),  # BR05 mismatch
        tax_total=Decimal("0"),
        grand_total=Decimal("99999"),
        terbilang_grand_total="Salah",
    )
    db.add(rev)
    await db.flush()

    # Line 1: semantic mismatch + final > offer (BR04) + wrong line_total (BR05)
    l1 = RevisionLine(
        revision_id=rev.id,
        line_number=1,
        original_description="Pembersih Porselen",
        confirmed_description="Porstex",
        specification="Botol 1 Liter",
        quantity=Decimal("10"),
        received_quantity=Decimal("10"),
        unit="Botol",
        hps_unit_price=Decimal("24000"),
        offer_unit_price=Decimal("22000"),
        final_unit_price=Decimal("25000"),  # > offer (BR04 WARNING)
        line_total=Decimal("100000"),  # wrong (BR05 BLOCK)
        condition="BAIK",
    )
    db.add(l1)

    # Line 2: clean description
    l2 = RevisionLine(
        revision_id=rev.id,
        line_number=2,
        original_description="Kertas HVS A4 70gr",
        confirmed_description="Kertas HVS A4 70gr",
        specification="70gr",
        quantity=Decimal("5"),
        received_quantity=Decimal("5"),
        unit="Rim",
        hps_unit_price=Decimal("50000"),
        offer_unit_price=Decimal("48000"),
        final_unit_price=Decimal("45000"),
        line_total=Decimal("225000"),
        condition="BAIK",
    )
    db.add(l2)

    # Events: wrong fiscal year + weekend + out-of-order + missing rest (BR07 & BR12)
    db.add(DocumentEvent(revision_id=rev.id, event_code="HPS", event_date=date(2025, 5, 10), location="Jakarta"))  # 2025 & Saturday!
    db.add(DocumentEvent(revision_id=rev.id, event_code="PESANAN", event_date=date(2026, 4, 18), location="Jakarta"))  # Saturday
    db.add(DocumentEvent(revision_id=rev.id, event_code="SURAT_JALAN", event_date=date(2026, 4, 10), location="Jakarta"))  # Before PESANAN!

    # Doc numbers: only D01 & D02 with duplicate number (BR02 & BR08)
    db.add(DocumentNumber(revision_id=rev.id, doc_code="D01", doc_number="DUP/001/2026", issuer="SCHOOL"))
    db.add(DocumentNumber(revision_id=rev.id, doc_code="D02", doc_number="DUP/001/2026", issuer="SCHOOL"))

    await db.commit()
    return pkg, rev


@pytest.mark.asyncio
async def test_semantic_audit_percentage_and_adjustable_passing_grade():
    async with AsyncSessionLocal() as db:
        _, rev = await seed_broken_package(db)
        rev_id = str(rev.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Default passing grade (95%)
        resp = await client.post(
            f"/api/v1/ai/revisions/{rev_id}/audit",
            headers={"X-User-Role": "ADMINISTRATION"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "COMPLETED"
        assert data["passing_grade"] == 95.0
        assert 0.0 <= data["overall_score"] < 95.0
        assert data["passed"] is False
        assert len(data["document_scores"]) == len(CANONICAL_13_DOCUMENTS)
        doc_codes = {d["doc_code"] for d in data["document_scores"]}
        assert doc_codes == {c for c, _ in CANONICAL_13_DOCUMENTS}

        # 2. Retrieve latest persisted report
        latest_resp = await client.get(f"/api/v1/ai/revisions/{rev_id}/audit/latest")
        assert latest_resp.status_code == 200
        latest = latest_resp.json()
        assert latest["overall_score"] == data["overall_score"]
        assert latest["passing_grade"] == 95.0

        # 3. Adjust passing grade down to 50% -> passes!
        patch_resp = await client.patch(
            f"/api/v1/ai/revisions/{rev_id}/audit/passing-grade",
            headers={"X-User-Role": "ADMINISTRATION"},
            json={"passing_grade": 50.0},
        )
        assert patch_resp.status_code == 200
        patched = patch_resp.json()
        assert patched["passing_grade"] == 50.0
        assert patched["passed"] is True

        # 4. Run audit explicitly with custom passing grade 80%
        resp_custom = await client.post(
            f"/api/v1/ai/revisions/{rev_id}/audit",
            headers={"X-User-Role": "ADMINISTRATION"},
            json={"passing_grade": 80.0},
        )
        assert resp_custom.status_code == 200
        assert resp_custom.json()["passing_grade"] == 80.0


@pytest.mark.asyncio
async def test_ai_fix_recommendation_and_apply_resolves_all_issues():
    async with AsyncSessionLocal() as db:
        _, rev = await seed_broken_package(db)
        rev_id = str(rev.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1 & 2: Request AI Fix Recommendations
        rec_resp = await client.post(
            f"/api/v1/ai/revisions/{rev_id}/fix-recommendations",
            headers={"X-User-Role": "ADMINISTRATION"},
        )
        assert rec_resp.status_code == 200
        rec = rec_resp.json()
        assert rec["status"] == "COMPLETED"
        assert len(rec["reasoning_steps"]) >= 4
        assert len(rec["changes"]) > 0

        categories = {c["category"] for c in rec["changes"]}
        assert "IDENTITY" in categories
        assert "OFFICIALS" in categories
        assert "TAX_POLICY" in categories
        assert "DATES" in categories
        assert "DOC_NUMBERS" in categories
        assert "ITEMS_TEXT" in categories
        assert "ITEMS_PRICING" in categories
        assert "TOTALS" in categories

        # RBAC check: LOGISTICS cannot apply fixes
        forbidden_resp = await client.post(
            f"/api/v1/ai/revisions/{rev_id}/apply-fixes",
            headers={"X-User-Role": "LOGISTICS"},
            json={"expected_version": 1, "changes": rec["changes"]},
        )
        assert forbidden_resp.status_code == 403

        # Optimistic lock check: wrong expected_version -> 409
        conflict_resp = await client.post(
            f"/api/v1/ai/revisions/{rev_id}/apply-fixes",
            headers={"X-User-Role": "ADMINISTRATION"},
            json={"expected_version": 99, "changes": rec["changes"]},
        )
        assert conflict_resp.status_code == 409

        # Step 3 & 4: Apply all reviewed changes
        apply_resp = await client.post(
            f"/api/v1/ai/revisions/{rev_id}/apply-fixes",
            headers={"X-User-Role": "ADMINISTRATION"},
            json={"expected_version": 1, "changes": rec["changes"]},
        )
        assert apply_resp.status_code == 200
        applied = apply_resp.json()
        assert applied["new_version"] == 2
        assert applied["applied_count"] == len(rec["changes"])
        assert applied["validation_passed"] is True
        assert applied["remaining_errors"] == 0
        assert applied["remaining_warnings"] == 0

        # Verify subsequent AI Semantic Audit scores 100.0% across all 13 documents & passes 95%!
        audit_after = await client.post(
            f"/api/v1/ai/revisions/{rev_id}/audit",
            headers={"X-User-Role": "ADMINISTRATION"},
        )
        assert audit_after.status_code == 200
        audit_data = audit_after.json()
        assert audit_data["findings_count"] == 0
        assert audit_data["overall_score"] == 100.0
        assert audit_data["passed"] is True
        assert all(d["score_percentage"] == 100.0 and d["passed"] is True for d in audit_data["document_scores"])

        # Verify audit log recorded AI_AUTOFIX_APPLY
        async with AsyncSessionLocal() as db:
            aud = (
                await db.execute(
                    select(AuditEvent).where(
                        AuditEvent.entity_id == rev_id,
                        AuditEvent.action == "AI_AUTOFIX_APPLY",
                    )
                )
            ).scalar_one_or_none()
            assert aud is not None
            reloaded_rev = (
                await db.execute(
                    select(PackageRevision)
                    .options(selectinload(PackageRevision.lines))
                    .where(PackageRevision.id == rev.id)
                )
            ).scalar_one()
            # Subtotal: (10 * 22000) + (5 * 45000) = 220000 + 225000 = 445000
            assert reloaded_rev.subtotal == Decimal("445000")
