"""Tests for multi-format (.docx, .pdf, .doc) deterministic extraction, pre-LLM context enrichment,
and real-time AI progress tracking (JSON snapshot + SSE + async mapping endpoint).
"""
from decimal import Decimal
import asyncio
import json
from pathlib import Path
import docx
import pytest
from httpx import ASGITransport, AsyncClient
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from sqlalchemy import select

from app.database import AsyncSessionLocal, Base, async_engine
from app.main import app
from app.models.ai import AIUsageLog
from app.models.imports import ImportRecord
from app.models.masters import School, TaxPolicyVersion
from app.models.packages import DocumentEvent, DocumentNumber, Package
from app.services.ai.runtime_manager import runtime_manager
from app.services.extractors.doc_extractor import DocExtractor


@pytest.fixture(autouse=True)
async def prepare_database():
    prev_cfg = runtime_manager.get_config().model_dump()
    runtime_manager.update_config({"runtime_mode": "local", "provider": "mock", "ai_enabled": True})
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
        session.add(p_ppn)
        await session.commit()
    try:
        yield
    finally:
        runtime_manager.update_config(prev_cfg)
        await async_engine.dispose()


def _create_sample_docx(path: Path) -> None:
    document = docx.Document()
    document.add_paragraph("PEMERINTAH PROVINSI DKI JAKARTA")
    document.add_paragraph("SDN KEBON KOSONG 09 PAGI")
    document.add_paragraph("Jl. Kemayoran Gempol No. 32 Email: sdnkk09@example.sch.id")
    document.add_paragraph("Kegiatan: Pemeliharaan Alat Kebersihan Sekolah")
    document.add_paragraph("Rincian Kegiatan: Belanja Bahan Kebersihan TW II")
    document.add_paragraph("Tahun Anggaran: 2026")
    document.add_paragraph("Daftar Kebutuhan Barang:")

    tbl = document.add_table(rows=4, cols=6)
    headers = ["No", "Nama Barang", "Spesifikasi", "Volume", "Satuan", "Harga Satuan"]
    for idx, h in enumerate(headers):
        tbl.rows[0].cells[idx].text = h

    rows_data = [
        ("1", "Cairan Pembersih Lantai", "Botol 800ml", "12", "botol", "22.000"),
        ("2", "Sapu Ijuk", "Gagang kayu kuat", "6", "buah", "28.000"),
        ("JUMLAH", "", "", "", "", ""),
    ]
    for r_i, row in enumerate(rows_data, start=1):
        for c_i, val in enumerate(row):
            tbl.rows[r_i].cells[c_i].text = val

    document.save(str(path))


def _create_sample_pdf(path: Path, blank: bool = False) -> None:
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    if blank:
        story.append(Spacer(1, 20))
    else:
        story.append(Paragraph("SDN SUNTER AGUNG 05", styles["Title"]))
        story.append(Paragraph("Jl. Danau Sunter Selatan No. 10 | Email: sdnsunter05@example.sch.id", styles["Normal"]))
        story.append(Paragraph("Kegiatan: Pengadaan Perlengkapan Kelas", styles["Normal"]))
        story.append(Paragraph("Tahun Anggaran: 2026", styles["Normal"]))
        story.append(Spacer(1, 12))

        table_data = [
            ["No", "Nama Barang", "Spesifikasi", "Volume", "Satuan", "Harga Satuan"],
            ["1", "Kertas HVS A4", "80 gsm putih", "10", "rim", "55.000"],
            ["2", "Spidol Whiteboard", "Hitam refillable", "24", "buah", "9.500"],
        ]
        table = Table(table_data)
        table.setStyle(
            TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ])
        )
        story.append(table)
    doc.build(story)


@pytest.mark.asyncio
async def test_docx_extraction_async_ai_progress_and_confirm(tmp_path: Path):
    docx_path = tmp_path / "rincian_hps.docx"
    _create_sample_docx(docx_path)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-User-Role": "ADMINISTRATION", "X-Actor-Name": "Staf MultiFormat"}

        # 1. Upload .docx
        with open(docx_path, "rb") as f:
            up_res = await client.post(
                "/api/v1/imports/upload",
                headers=headers,
                files={
                    "file": (
                        "rincian_hps.docx",
                        f,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
                data={"fiscal_year": "2026", "quarter": "2", "fund_source": "BOS_REGULER"},
            )
        assert up_res.status_code == 202, up_res.text
        up_data = up_res.json()
        import_id = up_data["import_id"]
        assert up_data["source_format"] == "DOCX"
        assert up_data["extraction_stats"]["tables_count"] >= 1

        # 2. Check preview contains extracted lines & pre-LLM document context
        prev_res = await client.get(f"/api/v1/imports/{import_id}/preview")
        assert prev_res.status_code == 200
        prev = prev_res.json()
        assert prev["source_format"] == "DOCX"
        assert "SDN KEBON KOSONG 09" in prev["school_candidate"]["name"]
        assert len(prev["candidate_lines"]) == 2
        assert len(prev["document_context"]["snippets"]) >= 3

        # 3. Trigger async AI mapping + inspect real-time progress snapshot & SSE stream
        async_res = await client.post(f"/api/v1/ai/imports/{import_id}/suggest-mapping-async", headers=headers)
        assert async_res.status_code == 202, async_res.text
        async_data = async_res.json()
        assert async_data["import_id"] == import_id

        # Poll briefly until background task finishes (MockAIAdapter completes in ~15ms)
        final_prog = None
        for _ in range(30):
            prog_res = await client.get(f"/api/v1/imports/{import_id}/progress")
            assert prog_res.status_code == 200
            final_prog = prog_res.json()
            if final_prog["status"] in ("COMPLETED", "AMBIGUOUS", "FALLBACK", "FAILED"):
                break
            await asyncio.sleep(0.05)

        assert final_prog is not None
        assert final_prog["status"] in ("COMPLETED", "AMBIGUOUS")
        assert final_prog["percent"] == 100
        assert final_prog["stage"] == "FINALIZE"
        assert len(final_prog["events"]) >= 3

        # Verify SSE stream replays terminal event cleanly
        sse_res = await client.get(f"/api/v1/imports/{import_id}/progress/stream")
        assert sse_res.status_code == 200
        assert "text/event-stream" in sse_res.headers.get("content-type", "")
        assert "event: progress" in sse_res.text
        data_lines = [line[5:].strip() for line in sse_res.text.splitlines() if line.startswith("data:")]
        assert data_lines
        streamed_state = json.loads(data_lines[-1])
        assert streamed_state["percent"] == 100

        # 4. Confirm into Draft Package
        conf_res = await client.post(
            f"/api/v1/imports/{import_id}/confirm",
            headers=headers,
            json={
                "fiscal_year": 2026,
                "quarter": 2,
                "funding_source_code": "BOS_REGULER",
                "confirmed_lines": prev["candidate_lines"],
            },
        )
        assert conf_res.status_code == 201, conf_res.text
        conf_data = conf_res.json()
        assert conf_data["grand_total"] > 0


@pytest.mark.asyncio
async def test_pdf_extraction_and_blank_pdf_rejection(tmp_path: Path):
    valid_pdf = tmp_path / "penawaran_sekolah.pdf"
    blank_pdf = tmp_path / "scan_kosong.pdf"
    _create_sample_pdf(valid_pdf, blank=False)
    _create_sample_pdf(blank_pdf, blank=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-User-Role": "ADMINISTRATION"}

        # 1. Blank/non-text PDF rejected deterministically BEFORE touching AI
        with open(blank_pdf, "rb") as f:
            res_blank = await client.post(
                "/api/v1/imports/upload",
                headers=headers,
                files={"file": ("scan_kosong.pdf", f, "application/pdf")},
            )
        assert res_blank.status_code == 422

        async with AsyncSessionLocal() as db:
            logs_before = (await db.execute(select(AIUsageLog))).scalars().all()
            assert len(logs_before) == 0

        # 2. Valid text+table PDF extracted cleanly & mapped via AI
        with open(valid_pdf, "rb") as f:
            res_ok = await client.post(
                "/api/v1/imports/upload",
                headers=headers,
                files={"file": ("penawaran_sekolah.pdf", f, "application/pdf")},
            )
        assert res_ok.status_code == 202, res_ok.text
        up_data = res_ok.json()
        import_id = up_data["import_id"]
        assert up_data["source_format"] == "PDF"

        prev_res = await client.get(f"/api/v1/imports/{import_id}/preview")
        assert prev_res.status_code == 200
        prev = prev_res.json()
        assert len(prev["candidate_lines"]) == 2
        assert any("Kertas HVS A4" in l["original_description"] for l in prev["candidate_lines"])
        assert "SDN SUNTER AGUNG 05" in prev["school_candidate"]["name"]

        ai_res = await client.post(f"/api/v1/ai/imports/{import_id}/suggest-mapping", headers=headers)
        assert ai_res.status_code == 200


@pytest.mark.asyncio
async def test_doc_magic_validation_and_libreoffice_if_installed(tmp_path: Path):
    fake_doc = tmp_path / "invalid.doc"
    fake_doc.write_bytes(b"NOT_AN_OLE2_WORD_DOC")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-User-Role": "ADMINISTRATION"}
        with open(fake_doc, "rb") as f:
            res_fake = await client.post(
                "/api/v1/imports/upload",
                headers=headers,
                files={"file": ("invalid.doc", f, "application/msword")},
            )
        assert res_fake.status_code == 422

        # Only run live .doc conversion test inside container / machine where LibreOffice is installed
        if DocExtractor._find_soffice():
            import subprocess
            src_docx = tmp_path / "sample_source.docx"
            _create_sample_docx(src_docx)
            subprocess.run(
                [DocExtractor._find_soffice(), "--headless", "--convert-to", "doc", "--outdir", str(tmp_path), str(src_docx)],
                check=True,
                capture_output=True,
                timeout=35,
            )
            sample_doc = tmp_path / "sample_source.doc"
            assert sample_doc.exists()
            with open(sample_doc, "rb") as f:
                res_doc = await client.post(
                    "/api/v1/imports/upload",
                    headers=headers,
                    files={"file": ("sample_source.doc", f, "application/msword")},
                )
            assert res_doc.status_code == 202, res_doc.text
            assert res_doc.json()["source_format"] == "DOC"


@pytest.mark.asyncio
async def test_school_year_quarter_assignment_matching_and_override(tmp_path: Path):
    """Verifies Sekolah (normalized master match without duplicate creation), Tahun (fiscal_year),
    and Triwulan (quarter) are extracted, exposed in preview/AI proposal, assigned on Package,
    reflected in DocumentNumber/DocumentEvent dates, and respect manual overrides.
    """
    async with AsyncSessionLocal() as db:
        seeded_school_kk09 = School(
            name="SD NEGERI KEBON KOSONG 09",
            npsn="20101234",
            level="SD",
            address="Jl. Kemayoran Gempol No. 32",
            email="sdnkk09@example.sch.id",
        )
        seeded_school_other = School(
            name="SDN CEMPAKA PUTIH BARAT 01",
            npsn="20104321",
            level="SD",
            address="Jl. Cempaka Putih Barat",
            email="sdncpb01@example.sch.id",
        )
        db.add_all([seeded_school_kk09, seeded_school_other])
        await db.commit()
        await db.refresh(seeded_school_kk09)
        await db.refresh(seeded_school_other)
        kk09_id = seeded_school_kk09.id
        other_id = seeded_school_other.id

    # Document with variant school name ("SDN KEBON KOSONG 09 PAGI"), TA 2025, Triwulan III
    docx_2025_q3 = tmp_path / "bos_2025_tw3.docx"
    document = docx.Document()
    document.add_paragraph("PEMERINTAH PROVINSI DKI JAKARTA")
    document.add_paragraph("SDN KEBON KOSONG 09 PAGI")
    document.add_paragraph("Jl. Kemayoran Gempol No. 32")
    document.add_paragraph("Kegiatan: Pemeliharaan Sarana Sekolah")
    document.add_paragraph("Tahun Anggaran: 2025")
    document.add_paragraph("Periode: Triwulan III")
    tbl = document.add_table(rows=3, cols=6)
    for idx, h in enumerate(["No", "Nama Barang", "Spesifikasi", "Volume", "Satuan", "Harga Satuan"]):
        tbl.rows[0].cells[idx].text = h
    for idx, val in enumerate(["1", "Pembersih Lantai", "Botol 800ml", "10", "botol", "25000"]):
        tbl.rows[1].cells[idx].text = val
    for idx, val in enumerate(["2", "Kain Pel", "Katun", "5", "buah", "30000"]):
        tbl.rows[2].cells[idx].text = val
    document.save(str(docx_2025_q3))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-User-Role": "ADMINISTRATION", "X-Actor-Name": "Verifikator Impor"}

        # 1. Upload WITHOUT hardcoded Step 1 school/fiscal_year/quarter overrides (auto-detect mode)
        with open(docx_2025_q3, "rb") as f:
            up_res = await client.post(
                "/api/v1/imports/upload",
                headers=headers,
                files={
                    "file": (
                        "bos_2025_tw3.docx",
                        f,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
                data={"fund_source": "BOS_REGULER"},
            )
        assert up_res.status_code == 202, up_res.text
        import_id = up_res.json()["import_id"]

        # 2. Preview matches Master School SD NEGERI KEBON KOSONG 09 + extracts 2025 + TW 3
        prev_res = await client.get(f"/api/v1/imports/{import_id}/preview")
        assert prev_res.status_code == 200
        prev = prev_res.json()
        assert prev["school_candidate"]["matched_school_id"] == str(kk09_id)
        assert prev["transaction_metadata"]["tahun_anggaran"] == 2025
        assert prev["transaction_metadata"]["tahun_anggaran_detected"] is True
        assert prev["transaction_metadata"]["triwulan"] == 3
        assert prev["transaction_metadata"]["triwulan_detected"] is True
        assert all(ev["event_date"].startswith("2025-09-") for ev in prev["events_candidate"])

        # 3. AI mapping carries detected context
        ai_res = await client.post(f"/api/v1/ai/imports/{import_id}/suggest-mapping", headers=headers)
        assert ai_res.status_code == 200
        ai_data = ai_res.json()
        assert ai_data["detected_fiscal_year"] == 2025
        assert ai_data["detected_quarter"] == 3
        assert "KEBON KOSONG 09" in (ai_data["detected_school_name"] or "").upper()

        # 4. Confirm WITHOUT passing overrides -> inherits detected Master School, Tahun 2025, Triwulan 3
        conf_res = await client.post(
            f"/api/v1/imports/{import_id}/confirm",
            headers=headers,
            json={
                "funding_source_code": "BOS_REGULER",
                "confirmed_lines": prev["candidate_lines"],
            },
        )
        assert conf_res.status_code == 201, conf_res.text
        conf_data = conf_res.json()
        assert conf_data["school_id"] == str(kk09_id)
        assert conf_data["school_name"] == "SD NEGERI KEBON KOSONG 09"
        assert conf_data["fiscal_year"] == 2025
        assert conf_data["quarter"] == 3
        assert conf_data["package_number"].startswith("PKG/2025/Q3/")

        async with AsyncSessionLocal() as db:
            all_schools = (await db.execute(select(School))).scalars().all()
            assert len(all_schools) == 2  # No duplicate school created!
            pkg = (await db.execute(select(Package).where(Package.id == conf_data["package_id"]))).scalar_one()
            assert pkg.school_id == kk09_id
            assert pkg.fiscal_year == 2025
            assert pkg.quarter == 3
            doc_nums = (
                await db.execute(select(DocumentNumber).where(DocumentNumber.revision_id == pkg.current_revision_id))
            ).scalars().all()
            assert len(doc_nums) == 13
            assert all(dn.doc_number.endswith("/PCI/2025") for dn in doc_nums)
            doc_events = (
                await db.execute(select(DocumentEvent).where(DocumentEvent.revision_id == pkg.current_revision_id))
            ).scalars().all()
            assert len(doc_events) > 0
            assert all(ev.event_date.year == 2025 and ev.event_date.month == 9 for ev in doc_events)

        # 5. Re-upload and confirm WITH explicit user override -> assigns overridden school, 2024, TW IV
        with open(docx_2025_q3, "rb") as f:
            up_res_2 = await client.post(
                "/api/v1/imports/upload",
                headers=headers,
                files={
                    "file": (
                        "bos_override.docx",
                        f,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
                data={"fund_source": "BOP"},
            )
        assert up_res_2.status_code == 202
        import_id_2 = up_res_2.json()["import_id"]
        prev_2 = (await client.get(f"/api/v1/imports/{import_id_2}/preview")).json()
        conf_res_2 = await client.post(
            f"/api/v1/imports/{import_id_2}/confirm",
            headers=headers,
            json={
                "school_id": str(other_id),
                "fiscal_year": 2024,
                "quarter": 4,
                "funding_source_code": "BOP",
                "confirmed_lines": prev_2["candidate_lines"],
            },
        )
        assert conf_res_2.status_code == 201, conf_res_2.text
        conf_data_2 = conf_res_2.json()
        assert conf_data_2["school_id"] == str(other_id)
        assert conf_data_2["school_name"] == "SDN CEMPAKA PUTIH BARAT 01"
        assert conf_data_2["fiscal_year"] == 2024
        assert conf_data_2["quarter"] == 4
        assert conf_data_2["package_number"].startswith("PKG/2024/Q4/")

        async with AsyncSessionLocal() as db:
            pkg_2 = (await db.execute(select(Package).where(Package.id == conf_data_2["package_id"]))).scalar_one()
            events_2 = (
                await db.execute(select(DocumentEvent).where(DocumentEvent.revision_id == pkg_2.current_revision_id))
            ).scalars().all()
            assert all(ev.event_date.year == 2024 and ev.event_date.month == 11 for ev in events_2)
