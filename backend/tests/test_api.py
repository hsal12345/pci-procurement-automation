import pytest
from httpx import AsyncClient, ASGITransport
from pathlib import Path
from decimal import Decimal
from app.main import app
from app.database import async_engine, Base, AsyncSessionLocal
from app.models.masters import TaxPolicyVersion


@pytest.fixture(autouse=True)
async def prepare_database():
    """Ensures database tables are fresh and clean before running tests."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        p_ppn = TaxPolicyVersion(
            policy_id="DEFAULT_2026",
            version=1,
            tax_type="PPN",
            rate=Decimal("0.11"),
            is_inclusive=False,
            withholding_rule="NONE",
            rounding_rule="ROUND_HALF_UP",
            is_active=True,
        )
        p_pph = TaxPolicyVersion(
            policy_id="DEFAULT_2026",
            version=1,
            tax_type="PPH22",
            rate=Decimal("0.015"),
            is_inclusive=False,
            withholding_rule="WITHHOLD_FROM_PAYABLE",
            rounding_rule="ROUND_HALF_UP",
            is_active=True,
        )
        session.add_all([p_ppn, p_pph])
        await session.commit()
    yield


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_masters_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create company
        comp_payload = {
            "legal_name": "CV. PUSTAKA CEMERLANG INDONESIA",
            "npwp": "01.234.567.8-012.000",
            "address": "Wisma Mitra Sunter Unit 3-03, Jl. Yos Sudarso Kav. 89",
            "city": "Jakarta",
            "director_name": "Bambang Solifian",
            "director_title": "Direktur Utama"
        }
        res_comp = await client.post("/api/v1/masters/companies", json=comp_payload)
        assert res_comp.status_code == 201
        comp_data = res_comp.json()
        assert comp_data["legal_name"] == comp_payload["legal_name"]

        # 2. Create school
        school_payload = {
            "name": "SEKOLAH DASAR NEGERI KEBON KOSONG 09",
            "npsn": "20100123",
            "level": "SD",
            "address": "Jl. Kemayoran Gempol no.32 RT 015.05",
            "email": "sdnkk05pg@gmail.com"
        }
        res_school = await client.post("/api/v1/masters/schools", json=school_payload)
        assert res_school.status_code == 201
        school_data = res_school.json()
        assert school_data["name"] == school_payload["name"]
        school_id = school_data["id"]

        # 3. Create appointment
        official_payload = {
            "school_id": school_id,
            "person_name": "Sulistiawati",
            "nip": "197909092022212008",
            "role": "PENGURUS_BARANG",
            "valid_from": "2020-01-01"
        }
        res_off = await client.post(f"/api/v1/masters/schools/{school_id}/officials", json=official_payload)
        assert res_off.status_code == 201
        off_data = res_off.json()
        assert off_data["person_name"] == "Sulistiawati"


@pytest.mark.asyncio
async def test_import_and_validation_workflow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Find 4 PCI KK09.xlsx
        file_path = Path("4 PCI KK09.xlsx").resolve()
        if not file_path.exists():
            file_path = Path("..") / "4 PCI KK09.xlsx"
        assert file_path.exists()

        # 1. Upload workbook
        with open(file_path, "rb") as f:
            res_upload = await client.post(
                "/api/v1/imports/upload",
                files={"file": ("4 PCI KK09.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            )
        assert res_upload.status_code == 202
        upload_data = res_upload.json()
        import_id = upload_data["import_id"]
        assert import_id is not None

        # 2. Preview import
        res_prev = await client.get(f"/api/v1/imports/{import_id}/preview")
        assert res_prev.status_code == 200
        prev_data = res_prev.json()
        assert len(prev_data["candidate_lines"]) == 8
        assert len(prev_data["detected_discrepancies"]) > 0

        # 3. Confirm import to create package & Revision 1
        res_conf = await client.post(f"/api/v1/imports/{import_id}/confirm", json={})
        assert res_conf.status_code == 201
        conf_data = res_conf.json()
        package_id = conf_data["package_id"]
        revision_id = conf_data["revision_id"]
        assert conf_data["subtotal"] == 2285000.0
        assert conf_data["grand_total"] == 2536350.0  # subtotal + 11% PPN

        # 4. Trigger validation endpoint
        res_val = await client.post(f"/api/v1/revisions/{revision_id}/validate")
        assert res_val.status_code == 200
        val_data = res_val.json()
        assert val_data["revision_id"] == revision_id
        # Findings list returned
        assert isinstance(val_data["findings"], list)

        # 5. Test Optimistic Concurrency Locking on Revision Update
        # Expect conflict if expected_version is wrong
        bad_update = {
            "expected_version": 999,
            "notes": "Testing conflict"
        }
        res_bad = await client.patch(f"/api/v1/packages/{package_id}/revisions/{revision_id}", json=bad_update)
        assert res_bad.status_code == 409
        assert "Optimistic Lock Error" in res_bad.json()["detail"]

        # Successful update with correct expected_version
        good_update = {
            "expected_version": 1,
            "notes": "Catatan revisi yang sah"
        }
        res_good = await client.patch(f"/api/v1/packages/{package_id}/revisions/{revision_id}", json=good_update)
        assert res_good.status_code == 200
        good_data = res_good.json()
        assert good_data["version"] == 2  # Version incremented!
        assert good_data["notes"] == "Catatan revisi yang sah"
