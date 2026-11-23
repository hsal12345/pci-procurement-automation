import io
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import openpyxl
import pytest
from docx import Document
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import hash_password
from app.database import AsyncSessionLocal, Base, async_engine
from app.main import app
from app.models.generation import Artifact, GenerationJob
from app.models.imports import ImportRecord
from app.models.masters import (
    BudgetClassification,
    Company,
    FundingSource,
    Item,
    OfficialAppointment,
    PackageProfile,
    School,
    TaxPolicyVersion,
    TemplateRegistry,
    Unit,
)
from app.models.packages import DocumentEvent, DocumentNumber, Package, PackageRevision, RevisionLine
from app.models.users import User
from app.models.validation import Finding, ValidationRun


@pytest.fixture(autouse=True)
async def prepare_database():
    """Clean tables before each test."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await async_engine.dispose()


async def _seed_users_and_tokens(client: AsyncClient):
    """Creates all 4 RBAC users per Table 4.2 and logs them in to get JWT Bearer headers."""
    creds = [
        ("admin", "administrasi@pci.co.id", "Staf Administrasi Pengadaan", "ADMINISTRATION"),
        ("direktur", "direktur@pci.co.id", "Bambang Solifian", "FINANCE_DIRECTOR"),
        ("logistik", "logistik@pci.co.id", "Petugas Logistik", "LOGISTICS"),
        ("sysadmin", "sysadmin@pci.co.id", "Administrator Sistem", "SYSTEM_ADMINISTRATOR"),
    ]
    async with AsyncSessionLocal() as db:
        for username, email, full_name, role in creds:
            db.add(
                User(
                    username=username,
                    email=email,
                    full_name=full_name,
                    password_hash=hash_password("Admin123!"),
                    role=role,
                    is_active=True,
                )
            )
        await db.commit()

    tokens = {}
    for username, _, _, role in creds:
        res = await client.post(
            "/api/v1/auth/login",
            json={"username_or_email": username, "password": "Admin123!"},
        )
        assert res.status_code == 200, res.text
        tokens[role] = res.json()["access_token"]
    return tokens


async def _seed_full_domain(tmp_path: Path):
    """Seeds master records, a package + revision, validation finding, import, template, and artifact."""
    async with AsyncSessionLocal() as db:
        school = School(
            name="SD NEGERI RAWAMANGUN 01",
            npsn=f"2010{uuid4().hex[:4]}",
            level="SD",
            address="Jl. Pemuda No. 1",
            email="sdn01@example.com",
        )
        company = Company(
            legal_name="CV. PUSTAKA CEMERLANG INDONESIA",
            address="Wisma Mitra Sunter Unit 3-03",
            director_name="Bambang Solifian",
            director_title="Direktur Utama",
            is_active=True,
        )
        unit = Unit(code="Eks", display_label="Eksemplar", allowed_fractional=False)
        fs = FundingSource(code="BOS_REGULER", name="BOS Reguler", is_active=True)
        budget = BudgetClassification(
            fiscal_year=2026,
            activity_code="05.02.01",
            activity_name="Pengembangan Perpustakaan",
            account_code="5.1.02.01.01.0012",
            account_name="Belanja Bahan Cetak",
            funding_source_code="BOS",
            funding_scheme="BOS_REGULER",
            is_active=True,
        )
        item = Item(
            sku="PCI-BK-001",
            canonical_description="Buku Pelajaran SD",
            default_unit="Eks",
            reference_price=Decimal("45000"),
            is_active=True,
        )
        profile = PackageProfile(
            code="BOS_REGULER",
            name="BOS Reguler",
            required_doc_codes=["D01", "D02", "D03"],
        )
        tmpl = TemplateRegistry(
            doc_code="D01",
            doc_name="HPS",
            funding_scheme="ALL",
            is_mandatory=True,
            version=1,
            filename="D01_HPS.docx",
            required_tokens=["school.name"],
            detected_tokens=["school.name"],
            is_active=True,
        )
        tax = TaxPolicyVersion(
            policy_id="DEFAULT_2026",
            version=1,
            tax_type="PPN",
            rate=Decimal("0.11"),
            is_inclusive=False,
            withholding_rule="NONE",
            rounding_rule="ROUND_HALF_UP",
            is_active=True,
        )
        db.add_all([school, company, unit, fs, budget, item, profile, tmpl, tax])
        await db.flush()

        official = OfficialAppointment(
            school_id=school.id,
            person_name="Drs. Mulyadi",
            nip="196501011990031005",
            role="KEPALA_SEKOLAH",
            valid_from=date(2026, 1, 1),
        )
        db.add(official)

        pkg = Package(
            package_number=f"PKG/2026/Q2/{uuid4().hex[:4].upper()}",
            school_id=school.id,
            fiscal_year=2026,
            quarter=2,
            status="ACTIVE",
        )
        db.add(pkg)
        await db.flush()

        rev = PackageRevision(
            package_id=pkg.id,
            revision_number=1,
            version=1,
            status="DRAFT",
            ai_review_status="COMPLETED",
            school_snapshot={"name": school.name, "npsn": school.npsn, "address": school.address},
            company_snapshot={"legal_name": company.legal_name, "director_name": company.director_name},
            tax_policy_snapshot=[{"tax_type": "PPN", "rate": "0.11", "is_inclusive": False, "withholding_rule": "NONE"}],
            officials_snapshot=[{"role": "KEPALA_SEKOLAH", "name": "Drs. Mulyadi", "nip": "196501011990031005"}],
            subtotal=Decimal("100000"),
            tax_total=Decimal("11000"),
            grand_total=Decimal("111000"),
            terbilang_grand_total="Seratus Sebelas Ribu Rupiah",
            is_locked=False,
        )
        db.add(rev)
        await db.flush()
        pkg.current_revision_id = rev.id

        line = RevisionLine(
            revision_id=rev.id,
            line_number=1,
            original_description="Buku Tulis",
            confirmed_description="Buku Tulis 58 Lembar",
            quantity=Decimal("10"),
            unit="Eks",
            hps_unit_price=Decimal("10000"),
            offer_unit_price=Decimal("10000"),
            final_unit_price=Decimal("10000"),
            line_total=Decimal("100000"),
            condition="BAIK",
        )
        ev = DocumentEvent(
            revision_id=rev.id,
            event_code="HPS",
            event_date=date(2026, 5, 4),
            day_name_id="Senin",
            location="Jakarta",
        )
        num = DocumentNumber(
            revision_id=rev.id,
            doc_code="D01",
            doc_number="01/PCI/2026",
            issuer="SCHOOL",
            counter_val=1,
            is_reserved=True,
        )
        v_run = ValidationRun(revision_id=rev.id, triggered_by="ADMINISTRATION", passed=True, error_count=0, warning_count=1, info_count=0)
        db.add_all([line, ev, num, v_run])
        await db.flush()

        finding = Finding(
            run_id=v_run.id,
            rule_code="BR12",
            severity="WARNING",
            message="Contoh peringatan validasi",
            disposition="PENDING",
        )
        job = GenerationJob(revision_id=rev.id, status="SUCCEEDED", progress_percent=100)
        art_file = tmp_path / "D01_HPS.docx"
        art_file.write_bytes(b"PK\x03\x04dummy")
        art = Artifact(
            revision_id=rev.id,
            doc_code="D01",
            format="DOCX",
            filename="D01_HPS.docx",
            file_path=str(art_file),
            file_size=art_file.stat().st_size,
            sha256_hash="deadbeef",
            is_draft=True,
        )
        db.add_all([finding, job, art])

        # Also create an import workbook file + ImportRecord
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "HPS"
        ws.append(["No", "Nama Barang", "Spesifikasi", "Qty", "Satuan", "Harga Satuan", "Total"])
        ws.append([1, "Buku Tulis", "58 lbr", 10, "Eks", 10000, 100000])
        imp_path = tmp_path / "sample_import.xlsx"
        wb.save(imp_path)
        wb.close()

        # Copy to upload dir so _resolve_workbook_path finds it
        from app.config import settings
        stored_name = f"{uuid4()}_sample_import.xlsx"
        dest_imp = settings.get_upload_dir() / stored_name
        dest_imp.write_bytes(imp_path.read_bytes())

        imp = ImportRecord(
            original_filename="sample_import.xlsx",
            file_hash="abc123",
            file_size=dest_imp.stat().st_size,
            uploader="Staf Administrasi",
            status="PARSED",
            candidate_payload={
                "source_format": "XLSX",
                "sheet_names": ["HPS"],
                "active_sheet": "HPS",
                "raw_preview_rows": [],
                "candidate_lines": [
                    {
                        "line_number": 1,
                        "original_description": "Buku Tulis",
                        "confirmed_description": "Buku Tulis",
                        "quantity": 10,
                        "unit": "Eks",
                        "hps_unit_price": 10000,
                    }
                ],
                "detected_discrepancies": [],
                "can_proceed_to_confirm": True,
            },
            sheet_metadata={"stored_filename": stored_name, "source_format": "XLSX", "active_sheet": "HPS"},
            detected_discrepancies=[],
        )
        db.add(imp)
        await db.commit()

        return {
            "school_id": str(school.id),
            "company_id": str(company.id),
            "official_id": str(official.id),
            "item_id": str(item.id),
            "unit_id": str(unit.id),
            "budget_id": str(budget.id),
            "funding_source_id": str(fs.id),
            "profile_id": str(profile.id),
            "package_id": str(pkg.id),
            "revision_id": str(rev.id),
            "finding_id": str(finding.id),
            "job_id": str(job.id),
            "artifact_id": str(art.id),
            "import_id": str(imp.id),
        }


def _make_valid_docx_bytes() -> bytes:
    doc = Document()
    doc.add_paragraph("Sekolah: {{school.name}}")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_xlsx_bytes() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "HPS"
    ws.append(["No", "Nama Barang", "Spesifikasi", "Qty", "Satuan", "Harga Satuan", "Total"])
    ws.append([1, "Spidol Whiteboard", "Hitam", 5, "Pcs", 12000, 60000])
    buf = io.BytesIO()
    wb.save(buf)
    wb.close()
    return buf.getvalue()


@pytest.mark.asyncio
async def test_jwt_and_header_auth_precedence_and_users_rbac():
    """Verifies JWT Bearer auth, inactive user 403, invalid Authorization 401,
    JWT role precedence over spoofed X-User-Role, and strict SYSTEM_ADMINISTRATOR on /users.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tokens = await _seed_users_and_tokens(client)

        # 1. Invalid Authorization scheme must return 401 (never fall back to X-User-Role)
        res_bad_auth = await client.get(
            "/api/v1/packages",
            headers={"Authorization": "Basic abc123", "X-User-Role": "ADMINISTRATION"},
        )
        assert res_bad_auth.status_code == 401

        # 2. Invalid X-User-Role returns 403
        res_bad_role = await client.get("/api/v1/packages", headers={"X-User-Role": "HACKER"})
        assert res_bad_role.status_code == 403

        # 3. Spoofed X-User-Role cannot escalate a LOGISTICS JWT to ADMINISTRATION
        res_spoof = await client.post(
            "/api/v1/masters/units",
            headers={
                "Authorization": f"Bearer {tokens['LOGISTICS']}",
                "X-User-Role": "SYSTEM_ADMINISTRATOR",
            },
            json={"code": "Dus", "display_label": "Dus", "allowed_fractional": False},
        )
        assert res_spoof.status_code == 403

        # 4. /users requires real JWT Bearer token (X-User-Role alone -> 401)
        res_users_no_jwt = await client.get(
            "/api/v1/users",
            headers={"X-User-Role": "SYSTEM_ADMINISTRATOR"},
        )
        assert res_users_no_jwt.status_code == 401

        # 5. /users strictly allows SYSTEM_ADMINISTRATOR JWT; blocks other 3 roles with 403
        for forbidden_role in ("ADMINISTRATION", "FINANCE_DIRECTOR", "LOGISTICS"):
            res_u_forb = await client.get(
                "/api/v1/users",
                headers={"Authorization": f"Bearer {tokens[forbidden_role]}"},
            )
            assert res_u_forb.status_code == 403
            res_u_post = await client.post(
                "/api/v1/users",
                headers={"Authorization": f"Bearer {tokens[forbidden_role]}"},
                json={
                    "username": "x",
                    "email": "x@pci.co.id",
                    "full_name": "X",
                    "password": "Password123!",
                    "role": "ADMINISTRATION",
                },
            )
            assert res_u_post.status_code == 403

        res_u_ok = await client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {tokens['SYSTEM_ADMINISTRATOR']}"},
        )
        assert res_u_ok.status_code == 200
        assert len(res_u_ok.json()) == 4


@pytest.mark.asyncio
async def test_uc01_masters_rbac_both_jwt_and_header(tmp_path: Path):
    """UC-01 Masters: ADMINISTRATION & SYSTEM_ADMINISTRATOR allowed; FINANCE_DIRECTOR & LOGISTICS -> 403."""
    ids = await _seed_full_domain(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tokens = await _seed_users_and_tokens(client)

        def _hdrs(role: str, use_jwt: bool):
            return {"Authorization": f"Bearer {tokens[role]}"} if use_jwt else {"X-User-Role": role}

        for use_jwt in (True, False):
            # Forbidden roles must receive 403 on every master mutation
            for role in ("FINANCE_DIRECTOR", "LOGISTICS"):
                h = _hdrs(role, use_jwt)
                assert (await client.post("/api/v1/masters/companies", headers=h, json={"legal_name": "PT X", "address": "Jkt"})).status_code == 403
                assert (await client.put(f"/api/v1/masters/companies/{ids['company_id']}", headers=h, json={"city": "Bandung"})).status_code == 403
                assert (await client.post("/api/v1/masters/schools", headers=h, json={"name": "SD X", "npsn": "99999999", "level": "SD", "address": "Jkt"})).status_code == 403
                assert (await client.put(f"/api/v1/masters/schools/{ids['school_id']}", headers=h, json={"address": "Baru"})).status_code == 403
                assert (await client.delete(f"/api/v1/masters/schools/{ids['school_id']}", headers=h)).status_code == 403
                assert (await client.post(f"/api/v1/masters/schools/{ids['school_id']}/officials", headers=h, json={"person_name": "X", "role": "BENDAHARA"})).status_code == 403
                assert (await client.put(f"/api/v1/masters/schools/{ids['school_id']}/officials/{ids['official_id']}", headers=h, json={"person_name": "Y"})).status_code == 403
                assert (await client.delete(f"/api/v1/masters/schools/{ids['school_id']}/officials/{ids['official_id']}", headers=h)).status_code == 403
                assert (await client.post("/api/v1/masters/items", headers=h, json={"canonical_description": "Pulpen", "default_unit": "Pcs"})).status_code == 403
                assert (await client.patch(f"/api/v1/masters/items/{ids['item_id']}/price", headers=h, json={"reference_price": 50000})).status_code == 403
                assert (await client.delete(f"/api/v1/masters/items/{ids['item_id']}", headers=h)).status_code == 403
                assert (await client.post("/api/v1/masters/units", headers=h, json={"code": "Pack", "display_label": "Pack"})).status_code == 403
                assert (await client.post("/api/v1/masters/budgets", headers=h, json={"fiscal_year": 2026, "activity_code": "01", "activity_name": "A", "account_code": "5.1", "account_name": "B"})).status_code == 403
                assert (await client.post("/api/v1/masters/funding-sources", headers=h, json={"code": "DAK", "name": "DAK"})).status_code == 403
                assert (await client.post("/api/v1/masters/tax-policies", headers=h, json={"policy_id": "P2", "version": 1, "tax_type": "PPN", "rate": "0.11"})).status_code == 403

            # Read-only master GETs remain accessible for all 4 valid roles
            for role in ("ADMINISTRATION", "FINANCE_DIRECTOR", "LOGISTICS", "SYSTEM_ADMINISTRATOR"):
                h = _hdrs(role, use_jwt)
                assert (await client.get("/api/v1/masters/schools", headers=h)).status_code == 200
                assert (await client.get("/api/v1/masters/companies", headers=h)).status_code == 200
                assert (await client.get("/api/v1/masters/items", headers=h)).status_code == 200

        # Positive checks with ADMINISTRATION JWT and SYSTEM_ADMINISTRATOR X-User-Role
        res_item = await client.patch(
            f"/api/v1/masters/items/{ids['item_id']}/price",
            headers={"Authorization": f"Bearer {tokens['ADMINISTRATION']}"},
            json={"reference_price": 47000},
        )
        assert res_item.status_code == 200
        res_unit = await client.post(
            "/api/v1/masters/units",
            headers={"X-User-Role": "SYSTEM_ADMINISTRATOR"},
            json={"code": "Lusin", "display_label": "Lusin"},
        )
        assert res_unit.status_code == 201


@pytest.mark.asyncio
async def test_uc03_templates_and_profiles_rbac(tmp_path: Path):
    """UC-03:
    - GET /package-profiles, GET /templates, POST validate/simulate -> ADMINISTRATION & SYSTEM_ADMINISTRATOR (403 for DIR, LOG)
    - PUT /package-profiles/{id}, PATCH /templates/{doc_code}/config, POST /templates/{doc_code}/upload -> SYSTEM_ADMINISTRATOR ONLY (403 for ADM, DIR, LOG)
    """
    ids = await _seed_full_domain(tmp_path)
    docx_bytes = _make_valid_docx_bytes()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tokens = await _seed_users_and_tokens(client)

        # 1. FINANCE_DIRECTOR & LOGISTICS blocked from all UC-03 endpoints
        for role in ("FINANCE_DIRECTOR", "LOGISTICS"):
            h = {"Authorization": f"Bearer {tokens[role]}"}
            assert (await client.get("/api/v1/masters/package-profiles", headers=h)).status_code == 403
            assert (await client.get("/api/v1/masters/templates", headers=h)).status_code == 403
            assert (await client.post("/api/v1/masters/templates/D01/validate", headers=h, files={"file": ("D01.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})).status_code == 403
            assert (await client.post("/api/v1/masters/templates/D01/simulate", headers=h, files={"file": ("D01.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})).status_code == 403

        # 2. ADMINISTRATION can read/validate/simulate, but CANNOT mutate profiles/templates (403)
        h_adm = {"Authorization": f"Bearer {tokens['ADMINISTRATION']}"}
        assert (await client.get("/api/v1/masters/package-profiles", headers=h_adm)).status_code == 200
        assert (await client.get("/api/v1/masters/templates", headers=h_adm)).status_code == 200
        assert (await client.post("/api/v1/masters/templates/D01/validate", headers=h_adm, files={"file": ("D01.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})).status_code == 200
        assert (await client.post("/api/v1/masters/templates/D01/simulate", headers=h_adm, files={"file": ("D01.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})).status_code == 200

        assert (await client.put(f"/api/v1/masters/package-profiles/{ids['profile_id']}", headers=h_adm, json={"required_doc_codes": ["D01"]})).status_code == 403
        assert (await client.patch("/api/v1/masters/templates/D01/config", headers=h_adm, json={"is_mandatory": False})).status_code == 403
        assert (await client.post("/api/v1/masters/templates/D01/upload", headers=h_adm, files={"file": ("D01.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})).status_code == 403

        # 3. SYSTEM_ADMINISTRATOR can mutate profiles/templates
        h_sys = {"Authorization": f"Bearer {tokens['SYSTEM_ADMINISTRATOR']}"}
        assert (await client.put(f"/api/v1/masters/package-profiles/{ids['profile_id']}", headers=h_sys, json={"required_doc_codes": ["D01", "D02"]})).status_code == 200
        assert (await client.patch("/api/v1/masters/templates/D01/config", headers=h_sys, json={"is_mandatory": True})).status_code == 200
        assert (await client.post("/api/v1/masters/templates/D01/upload", headers=h_sys, files={"file": ("D01_v2.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})).status_code == 200


@pytest.mark.asyncio
async def test_uc02_imports_and_ai_mapping_rbac(tmp_path: Path):
    """UC-02 Imports: Only ADMINISTRATION & SYSTEM_ADMINISTRATOR; FINANCE_DIRECTOR & LOGISTICS -> 403."""
    ids = await _seed_full_domain(tmp_path)
    xlsx_bytes = _make_xlsx_bytes()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tokens = await _seed_users_and_tokens(client)

        for role in ("FINANCE_DIRECTOR", "LOGISTICS"):
            h = {"Authorization": f"Bearer {tokens[role]}"}
            assert (await client.get("/api/v1/imports/template", headers=h)).status_code == 403
            assert (await client.post("/api/v1/imports/upload", headers=h, files={"file": ("test.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})).status_code == 403
            assert (await client.get(f"/api/v1/imports/{ids['import_id']}/progress", headers=h)).status_code == 403
            assert (await client.get(f"/api/v1/imports/{ids['import_id']}/preview", headers=h)).status_code == 403
            assert (await client.post(f"/api/v1/imports/{ids['import_id']}/reparse", headers=h, json={"sheet_name": "HPS"})).status_code == 403
            assert (await client.post(f"/api/v1/imports/{ids['import_id']}/confirm", headers=h, json={})).status_code == 403
            assert (await client.post(f"/api/v1/ai/imports/{ids['import_id']}/suggest-mapping", headers=h)).status_code == 403
            assert (await client.post(f"/api/v1/ai/imports/{ids['import_id']}/suggest-mapping-async", headers=h)).status_code == 403

        h_adm = {"Authorization": f"Bearer {tokens['ADMINISTRATION']}"}
        assert (await client.get("/api/v1/imports/template", headers=h_adm)).status_code == 200
        assert (await client.get(f"/api/v1/imports/{ids['import_id']}/progress", headers=h_adm)).status_code == 200
        assert (await client.get(f"/api/v1/imports/{ids['import_id']}/preview", headers=h_adm)).status_code == 200


@pytest.mark.asyncio
async def test_uc04_05_06_07_packages_validation_generation_ai_rbac(tmp_path: Path):
    """Verifies strict RBAC across packages, calculate, validation, generation, artifacts, archive, and AI endpoints."""
    ids = await _seed_full_domain(tmp_path)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tokens = await _seed_users_and_tokens(client)

        # 1. Package creation & calculate: only ADM & SYS (DIR & LOG -> 403)
        for role in ("FINANCE_DIRECTOR", "LOGISTICS"):
            h = {"Authorization": f"Bearer {tokens[role]}"}
            assert (await client.post("/api/v1/packages", headers=h, json={"school_id": ids["school_id"], "fiscal_year": 2026, "quarter": 2})).status_code == 403
            assert (await client.delete(f"/api/v1/packages/{ids['package_id']}", headers=h)).status_code == 403
            assert (await client.post(f"/api/v1/revisions/{ids['revision_id']}/calculate", headers=h, json={"lines": []})).status_code == 403

        # ADM can create & calculate
        h_adm = {"Authorization": f"Bearer {tokens['ADMINISTRATION']}"}
        res_pkg = await client.post("/api/v1/packages", headers=h_adm, json={"school_id": ids["school_id"], "fiscal_year": 2026, "quarter": 2})
        assert res_pkg.status_code == 201
        assert (await client.post(f"/api/v1/revisions/{ids['revision_id']}/calculate", headers=h_adm, json={"lines": []})).status_code == 200

        # 2. Validation, Generation, Artifacts list, Archive read: LOGISTICS -> 403; ADM/DIR/SYS -> allowed
        h_log = {"Authorization": f"Bearer {tokens['LOGISTICS']}"}
        assert (await client.post(f"/api/v1/revisions/{ids['revision_id']}/validate", headers=h_log)).status_code == 403
        assert (await client.get(f"/api/v1/revisions/{ids['revision_id']}/findings", headers=h_log)).status_code == 403
        assert (await client.post(f"/api/v1/findings/{ids['finding_id']}/disposition", headers=h_log, json={"disposition": "ACKNOWLEDGED", "disposition_reason": "OK"})).status_code == 403
        assert (await client.post(f"/api/v1/revisions/{ids['revision_id']}/generate", headers=h_log, json={"formats": ["XLSX"]})).status_code == 403
        assert (await client.get(f"/api/v1/jobs/{ids['job_id']}", headers=h_log)).status_code == 403
        assert (await client.get(f"/api/v1/revisions/{ids['revision_id']}/jobs/latest", headers=h_log)).status_code == 403
        assert (await client.get(f"/api/v1/revisions/{ids['revision_id']}/artifacts", headers=h_log)).status_code == 403
        assert (await client.get(f"/api/v1/revisions/{ids['revision_id']}/archive", headers=h_log)).status_code == 403
        assert (await client.get("/api/v1/archive/health", headers=h_log)).status_code == 403

        h_dir = {"Authorization": f"Bearer {tokens['FINANCE_DIRECTOR']}"}
        assert (await client.post(f"/api/v1/revisions/{ids['revision_id']}/validate", headers=h_dir)).status_code == 200
        assert (await client.get(f"/api/v1/revisions/{ids['revision_id']}/findings", headers=h_dir)).status_code == 200
        assert (await client.post(f"/api/v1/findings/{ids['finding_id']}/disposition", headers=h_dir, json={"disposition": "ACKNOWLEDGED", "disposition_reason": "Sesuai"})).status_code == 200
        assert (await client.get(f"/api/v1/jobs/{ids['job_id']}", headers=h_dir)).status_code == 200
        assert (await client.get(f"/api/v1/revisions/{ids['revision_id']}/artifacts", headers=h_dir)).status_code == 200

        # Direct artifact download remains accessible for browser <a href> / <iframe>
        assert (await client.get(f"/api/v1/artifacts/{ids['artifact_id']}/download")).status_code == 200

        # 3. AI endpoints:
        # - LOGISTICS blocked on ALL /ai/* endpoints
        assert (await client.get("/api/v1/ai/usage", headers=h_log)).status_code == 403
        assert (await client.get("/api/v1/ai/logs", headers=h_log)).status_code == 403
        assert (await client.get("/api/v1/ai/config", headers=h_log)).status_code == 403
        assert (await client.put("/api/v1/ai/config", headers=h_log, json={"runtime_mode": "local"})).status_code == 403
        assert (await client.post("/api/v1/ai/test-connection", headers=h_log)).status_code == 403
        assert (await client.post("/api/v1/ai/playground/test", headers=h_log, json={"test_type": "DISCREPANCY"})).status_code == 403
        assert (await client.post(f"/api/v1/ai/revisions/{ids['revision_id']}/audit", headers=h_log)).status_code == 403
        assert (await client.get(f"/api/v1/ai/revisions/{ids['revision_id']}/audit/latest", headers=h_log)).status_code == 403
        assert (await client.patch(f"/api/v1/ai/revisions/{ids['revision_id']}/audit/passing-grade", headers=h_log, json={"passing_grade": 90})).status_code == 403
        assert (await client.post(f"/api/v1/ai/revisions/{ids['revision_id']}/fix-recommendations", headers=h_log)).status_code == 403
        assert (await client.post(f"/api/v1/ai/revisions/{ids['revision_id']}/apply-fixes", headers=h_log, json={"expected_version": 1, "changes": []})).status_code == 403
        assert (await client.post(f"/api/v1/ai/revisions/{ids['revision_id']}/record-manual-review", headers=h_log, json={"reason": "Test"})).status_code == 403
        assert (await client.get("/api/v1/ai/knowledge", headers=h_log)).status_code == 403
        assert (await client.post("/api/v1/ai/knowledge/chat", headers=h_log, json={"message": "Halo"})).status_code == 403

        # - FINANCE_DIRECTOR blocked from fix-recommendations, apply-fixes, PUT /ai/config
        assert (await client.post(f"/api/v1/ai/revisions/{ids['revision_id']}/fix-recommendations", headers=h_dir)).status_code == 403
        assert (await client.post(f"/api/v1/ai/revisions/{ids['revision_id']}/apply-fixes", headers=h_dir, json={"expected_version": 1, "changes": []})).status_code == 403
        assert (await client.put("/api/v1/ai/config", headers=h_dir, json={"runtime_mode": "local"})).status_code == 403
        assert (await client.get("/api/v1/ai/usage", headers=h_dir)).status_code == 200
        assert (await client.get("/api/v1/ai/logs", headers=h_dir)).status_code == 200
        assert (await client.get(f"/api/v1/ai/revisions/{ids['revision_id']}/audit/latest", headers=h_dir)).status_code == 200

        # - ADMINISTRATION blocked from /ai/usage, /ai/logs, /ai/config (GET & PUT), /ai/test-connection, /ai/playground/test
        assert (await client.get("/api/v1/ai/usage", headers=h_adm)).status_code == 403
        assert (await client.get("/api/v1/ai/logs", headers=h_adm)).status_code == 403
        assert (await client.get("/api/v1/ai/config", headers=h_adm)).status_code == 403
        assert (await client.put("/api/v1/ai/config", headers=h_adm, json={"runtime_mode": "local"})).status_code == 403
        assert (await client.post("/api/v1/ai/test-connection", headers=h_adm)).status_code == 403
        assert (await client.post("/api/v1/ai/playground/test", headers=h_adm, json={"test_type": "DISCREPANCY"})).status_code == 403
        assert (await client.get("/api/v1/ai/knowledge", headers=h_adm)).status_code == 200


@pytest.mark.asyncio
async def test_uc08_09_10_workflow_audit_logistics_strict_rbac(tmp_path: Path):
    """Verifies UC-08 exclusive FINANCE_DIRECTOR approve/return/cancel-approved,
    unconditional LOGISTICS block on cancel/workflow, UC-09 global /audit restriction,
    and UC-10 logistics restriction (FINANCE_DIRECTOR -> 403).
    """
    ids = await _seed_full_domain(tmp_path)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tokens = await _seed_users_and_tokens(client)
        h_adm = {"Authorization": f"Bearer {tokens['ADMINISTRATION']}"}
        h_dir = {"Authorization": f"Bearer {tokens['FINANCE_DIRECTOR']}"}
        h_log = {"Authorization": f"Bearer {tokens['LOGISTICS']}"}
        h_sys = {"Authorization": f"Bearer {tokens['SYSTEM_ADMINISTRATOR']}"}

        # 1. UC-09 Global Audit Portal (/audit & /audit/events): strictly FINANCE_DIRECTOR & SYSTEM_ADMINISTRATOR
        assert (await client.get("/api/v1/audit", headers=h_adm)).status_code == 403
        assert (await client.get("/api/v1/audit/events", headers=h_adm)).status_code == 403
        assert (await client.get("/api/v1/audit", headers=h_log)).status_code == 403
        assert (await client.get("/api/v1/audit/events", headers=h_log)).status_code == 403
        assert (await client.get("/api/v1/audit", headers=h_dir)).status_code == 200
        assert (await client.get("/api/v1/audit/events", headers=h_sys)).status_code == 200

        # Package-level Tab 7 audit remains readable by all 4 roles
        for h in (h_adm, h_dir, h_log, h_sys):
            assert (await client.get(f"/api/v1/packages/{ids['package_id']}/audit", headers=h)).status_code == 200

        # 2. UC-10 Logistics: FINANCE_DIRECTOR cannot mutate logistics or upload evidence (403)
        assert (await client.patch(f"/api/v1/revisions/{ids['revision_id']}/logistics", headers=h_dir, json={"courier_name": "JNE"})).status_code == 403
        assert (await client.post(f"/api/v1/revisions/{ids['revision_id']}/logistics/evidence", headers=h_dir, files={"file": ("bukti.pdf", b"%PDF-1.4\n", "application/pdf")})).status_code == 403
        assert (await client.patch(f"/api/v1/revisions/{ids['revision_id']}/logistics", headers=h_log, json={"courier_name": "Armada PCI"})).status_code == 200

        # 3. UC-08 Submit -> UNDER_REVIEW: DIR & LOG -> 403; ADM -> 200
        assert (await client.post(f"/api/v1/revisions/{ids['revision_id']}/submit", headers=h_dir, json={"expected_version": 1})).status_code == 403
        assert (await client.post(f"/api/v1/revisions/{ids['revision_id']}/submit", headers=h_log, json={"expected_version": 1})).status_code == 403
        res_sub = await client.post(f"/api/v1/revisions/{ids['revision_id']}/submit", headers=h_adm, json={"expected_version": 1})
        assert res_sub.status_code == 200

        # 4. UC-08 Approve & Return: EXCLUSIVELY FINANCE_DIRECTOR (ADM, LOG, SYS -> 403!)
        for h_forbidden in (h_adm, h_log, h_sys):
            assert (await client.post(f"/api/v1/revisions/{ids['revision_id']}/return", headers=h_forbidden, json={"expected_version": 2, "comment": "Tolak"})).status_code == 403
            assert (await client.post(f"/api/v1/revisions/{ids['revision_id']}/approve", headers=h_forbidden, json={"expected_version": 2})).status_code == 403

        # Withdraw: DIR & LOG -> 403
        assert (await client.post(f"/api/v1/revisions/{ids['revision_id']}/withdraw", headers=h_dir, json={"expected_version": 2, "reason": "Test"})).status_code == 403
        assert (await client.post(f"/api/v1/revisions/{ids['revision_id']}/withdraw", headers=h_log, json={"expected_version": 2, "reason": "Test"})).status_code == 403

        # Approve as FINANCE_DIRECTOR -> 200
        res_appr = await client.post(f"/api/v1/revisions/{ids['revision_id']}/approve", headers=h_dir, json={"expected_version": 2})
        assert res_appr.status_code == 200

        # Reopen & Issue: LOGISTICS -> 403
        assert (await client.post(f"/api/v1/packages/{ids['package_id']}/reopen", headers=h_log, json={"reason": "Test"})).status_code == 403
        assert (await client.post(f"/api/v1/revisions/{ids['revision_id']}/issue", headers=h_log)).status_code == 403

        # 5. Cancel on APPROVED: ADM, LOG, SYS -> 403; FINANCE_DIRECTOR -> 200
        for h_forbidden in (h_adm, h_log, h_sys):
            assert (await client.post(f"/api/v1/packages/{ids['package_id']}/cancel", headers=h_forbidden, json={"reason": "Batal ilegal"})).status_code == 403

        # Also test LOGISTICS cannot cancel a DRAFT package!
        res_draft_pkg = await client.post("/api/v1/packages", headers=h_adm, json={"school_id": ids["school_id"], "fiscal_year": 2026, "quarter": 2})
        assert res_draft_pkg.status_code == 201
        draft_pkg_id = res_draft_pkg.json()["id"]
        assert (await client.post(f"/api/v1/packages/{draft_pkg_id}/cancel", headers=h_log, json={"reason": "Logistik coba batal"})).status_code == 403

        # FINANCE_DIRECTOR cancels APPROVED package -> 200
        res_cancel_ok = await client.post(f"/api/v1/packages/{ids['package_id']}/cancel", headers=h_dir, json={"reason": "Pembatalan resmi Direktur Keuangan"})
        assert res_cancel_ok.status_code == 200
