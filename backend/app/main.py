from contextlib import asynccontextmanager
from decimal import Decimal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, select, text
from app.config import settings
from app.api.v1 import api_v1_router
from app.database import async_engine, AsyncSessionLocal, Base
import app.models  # noqa: F401
from app.models.masters import (
    TaxPolicyVersion,
    Unit,
    Item,
    FundingSource,
    BudgetClassification,
    PackageProfile,
    TemplateRegistry,
)
from app.services.export.template_builder import TEMPLATES_DIR, build_all_templates
from app.services.template_registry_service import extract_and_validate_docx_bytes


def _sync_ensure_schema_columns(sync_conn):
    inspector = inspect(sync_conn)
    existing_tables = set(inspector.get_table_names())
    migrations = [
        ("items", "kbli", "ALTER TABLE items ADD COLUMN kbli VARCHAR(32)"),
        ("items", "reference_price", "ALTER TABLE items ADD COLUMN reference_price NUMERIC(18, 2) DEFAULT 0 NOT NULL"),
        ("items", "is_active", "ALTER TABLE items ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL"),
        ("budget_classifications", "funding_scheme", "ALTER TABLE budget_classifications ADD COLUMN funding_scheme VARCHAR(32) DEFAULT 'BOS_REGULER' NOT NULL"),
        ("budget_classifications", "is_active", "ALTER TABLE budget_classifications ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL"),
        ("funding_sources", "is_active", "ALTER TABLE funding_sources ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL"),
        ("archive_records", "drive_folder_url", "ALTER TABLE archive_records ADD COLUMN drive_folder_url VARCHAR(512)"),
        ("archive_records", "progress_percent", "ALTER TABLE archive_records ADD COLUMN progress_percent INTEGER DEFAULT 0 NOT NULL"),
        ("archive_records", "current_step", "ALTER TABLE archive_records ADD COLUMN current_step VARCHAR(255)"),
        ("archive_records", "uploaded_files", "ALTER TABLE archive_records ADD COLUMN uploaded_files INTEGER DEFAULT 0 NOT NULL"),
        ("archive_records", "total_files", "ALTER TABLE archive_records ADD COLUMN total_files INTEGER DEFAULT 0 NOT NULL"),
        ("archive_records", "total_bytes", "ALTER TABLE archive_records ADD COLUMN total_bytes INTEGER DEFAULT 0 NOT NULL"),
        ("artifacts", "drive_file_id", "ALTER TABLE artifacts ADD COLUMN drive_file_id VARCHAR(128)"),
        ("artifacts", "drive_web_view_link", "ALTER TABLE artifacts ADD COLUMN drive_web_view_link VARCHAR(512)"),
        ("artifacts", "drive_synced_at", "ALTER TABLE artifacts ADD COLUMN drive_synced_at TIMESTAMP WITH TIME ZONE"),
    ]
    for table_name, col_name, stmt in migrations:
        if table_name in existing_tables:
            cols = {c["name"] for c in inspector.get_columns(table_name)}
            if col_name not in cols:
                sync_conn.execute(text(stmt))


async def _ensure_schema_columns(conn):
    """Idempotently adds columns introduced during C3 specification alignment."""
    await conn.run_sync(_sync_ensure_schema_columns)


DEFAULT_DOC_DEFINITIONS = [
    ("D01", "Harga Perkiraan Sendiri (HPS)", "D01_HPS.docx", True, ["school.name", "items", "totals.grand_total_formatted"]),
    ("D02", "Surat Permintaan Penawaran (SPP)", "D02_SPP.docx", True, ["school.name", "company.legal_name", "numbers.D02.doc_number"]),
    ("D03", "Surat Penawaran Harga (SPH)", "D03_S_PENAWARAN.docx", True, ["company.legal_name", "school.name", "totals.grand_total_formatted"]),
    ("D04", "Berita Acara Negosiasi Harga", "D04_S_NEGOSIASI.docx", True, ["school.name", "company.legal_name", "totals.grand_total_formatted"]),
    ("D05", "Surat Pesanan (SP)", "D05_SURAT_PESANAN.docx", True, ["school.name", "company.legal_name", "items"]),
    ("D06", "Faktur Tagihan / Invoice", "D06_FAKTUR.docx", True, ["company.legal_name", "totals.grand_total_formatted"]),
    ("D07", "Kwitansi Pembayaran SPJ", "D07_KWITANSI.docx", True, ["school.name", "totals.grand_total_formatted", "totals.terbilang"]),
    ("D08", "Surat Jalan Pengiriman Barang", "D08_SURAT_JALAN.docx", True, ["company.legal_name", "school.name", "items"]),
    ("D09", "Berita Acara Pemeriksaan Barang (BAPB)", "D09_BAPB.docx", True, ["school.name", "items"]),
    ("D10", "Berita Acara Serah Terima (BAST) Sekolah", "D10_BAST.docx", True, ["school.name", "company.legal_name", "totals.grand_total_formatted"]),
    ("D11", "Berita Acara Penyelesaian Pekerjaan (BAPP)", "D11_BAPP.docx", True, ["school.name", "company.legal_name"]),
    ("D12", "Lampiran Rincian Barang BAPP", "D12_LAMP_BAPP.docx", True, ["items"]),
    ("D13", "Berita Acara Serah Terima (BAST) Rekanan", "D13_BAST_REKANAN.docx", True, ["company.legal_name", "school.name"]),
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_schema_columns(conn)

    async with AsyncSessionLocal() as session:
        # 1. Seed TaxPolicyVersion
        res = await session.execute(select(TaxPolicyVersion))
        if not res.scalars().first():
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

        # 2. Seed Units
        if not (await session.execute(select(Unit))).scalars().first():
            session.add_all([
                Unit(code="Eks", display_label="Eksemplar", allowed_fractional=False),
                Unit(code="Pcs", display_label="Pieces / Buah", allowed_fractional=False),
                Unit(code="Unit", display_label="Unit", allowed_fractional=False),
                Unit(code="Set", display_label="Set", allowed_fractional=False),
                Unit(code="Rim", display_label="Rim (500 Lembar)", allowed_fractional=False),
                Unit(code="Paket", display_label="Paket Kegiatan", allowed_fractional=False),
                Unit(code="Box", display_label="Kotak / Dos", allowed_fractional=False),
            ])

        # 3. Seed FundingSources
        if not (await session.execute(select(FundingSource))).scalars().first():
            session.add_all([
                FundingSource(code="BOS_REGULER", name="BOS Reguler", description="Bantuan Operasional Satuan Pendidikan Reguler", is_active=True),
                FundingSource(code="BOS_KINERJA", name="BOS Kinerja", description="Bantuan Operasional Satuan Pendidikan Kinerja", is_active=True),
                FundingSource(code="BOP", name="BOP Pendidikan", description="Bantuan Operasional Pendidikan Daerah (DKI Jakarta)", is_active=True),
                FundingSource(code="LAINNYA", name="Dana Lainnya / Swakelola", description="Sumber pendanaan sah lainnya", is_active=True),
            ])

        # 4. Seed BudgetClassifications (Kode Rekening & Kegiatan BOS/BOP)
        if not (await session.execute(select(BudgetClassification))).scalars().first():
            session.add_all([
                BudgetClassification(
                    fiscal_year=2026,
                    activity_code="05.02.01",
                    activity_name="Pengembangan Perpustakaan & Pengadaan Buku Teks",
                    sub_activity="Pengadaan Buku Teks Utama dan Buku Pendamping Siswa",
                    account_code="5.1.02.01.01.0012",
                    account_name="Belanja Bahan-Bahan Lainnya / Bahan Cetak & Buku",
                    funding_source_code="BOS",
                    funding_scheme="BOS_REGULER",
                    is_active=True,
                ),
                BudgetClassification(
                    fiscal_year=2026,
                    activity_code="06.05.08",
                    activity_name="Penyediaan Alat Tulis Kantor (ATK) & Bahan Habis Pakai",
                    sub_activity="Belanja ATK Kegiatan Pembelajaran dan Administrasi",
                    account_code="5.1.02.01.01.0024",
                    account_name="Belanja Alat/Bahan untuk Kegiatan Kantor-Alat Tulis Kantor",
                    funding_source_code="BOS",
                    funding_scheme="BOS_REGULER",
                    is_active=True,
                ),
                BudgetClassification(
                    fiscal_year=2026,
                    activity_code="07.12.02",
                    activity_name="Pengembangan Sarana dan Prasarana Sekolah (BOP)",
                    sub_activity="Pengadaan Peralatan TIK & Penunjang Pembelajaran",
                    account_code="5.2.02.10.01.0002",
                    account_name="Belanja Modal Personal Computer / Perangkat TIK Sekolah",
                    funding_source_code="BOP",
                    funding_scheme="BOP",
                    is_active=True,
                ),
            ])

        # 5. Seed KatalogBarang (Items with SKU, KBLI, Satuan, Harga Acuan)
        if not (await session.execute(select(Item))).scalars().first():
            session.add_all([
                Item(
                    sku="PCI-BK-001",
                    kbli="47611",
                    canonical_description="Buku Teks Pendamping Bahasa Indonesia SD Kelas 4 (Kurikulum Merdeka)",
                    default_spec="Kertas HVS 70gr, Cetak Full Color, Jilid Soft Cover AC 210gr",
                    brand="Pustaka Cemerlang",
                    category="Buku Pendidikan",
                    default_unit="Eks",
                    reference_price=Decimal("45000"),
                    is_active=True,
                ),
                Item(
                    sku="PCI-BK-002",
                    kbli="47611",
                    canonical_description="Buku Teks Pendamping Matematika SD Kelas 5 (Kurikulum Merdeka)",
                    default_spec="Kertas HVS 70gr, Isi 180 Halaman, Cetak Full Color",
                    brand="Pustaka Cemerlang",
                    category="Buku Pendidikan",
                    default_unit="Eks",
                    reference_price=Decimal("48500"),
                    is_active=True,
                ),
                Item(
                    sku="PCI-ATK-001",
                    kbli="46421",
                    canonical_description="Kertas HVS A4 80 gram Sinar Dunia",
                    default_spec="Ukuran A4 (210 x 297 mm), 80 gsm, isi 500 lembar per rim",
                    brand="SiDu",
                    category="ATK & Bahan Cetak",
                    default_unit="Rim",
                    reference_price=Decimal("58000"),
                    is_active=True,
                ),
                Item(
                    sku="PCI-TIK-001",
                    kbli="46511",
                    canonical_description="Printer Inkjet Multifungsi EcoTank (Print/Scan/Copy)",
                    default_spec="Resolusi 5760 x 1440 dpi, Koneksi USB & WiFi, Garansi Resmi 2 Tahun",
                    brand="Epson",
                    category="Perangkat TIK",
                    default_unit="Unit",
                    reference_price=Decimal("2850000"),
                    is_active=True,
                ),
            ])

        # 6. Seed PackageProfiles (Mandatory/Optional per BOS & BOP)
        if not (await session.execute(select(PackageProfile))).scalars().first():
            all_13 = [f"D{i:02d}" for i in range(1, 14)]
            bop_docs = [f"D{i:02d}" for i in range(1, 13)]  # D13 optional for BOP
            session.add_all([
                PackageProfile(
                    code="BOS_REGULER",
                    name="Paket Lengkap SPJ BOS Reguler (13 Dokumen)",
                    description="Seluruh 13 dokumen pengadaan & serah terima wajib untuk pelaporan dana BOS Reguler.",
                    required_doc_codes=all_13,
                ),
                PackageProfile(
                    code="BOS_KINERJA",
                    name="Paket Lengkap SPJ BOS Kinerja (13 Dokumen)",
                    description="Kelengkapan 13 dokumen pengadaan barang/jasa dana BOS Kinerja.",
                    required_doc_codes=all_13,
                ),
                PackageProfile(
                    code="BOP",
                    name="Paket SPJ BOP Pendidikan (D01-D12 Wajib, D13 Opsional)",
                    description="Standar dokumen SPJ BOP DKI Jakarta; BAST Rekanan (D13) bersifat opsional.",
                    required_doc_codes=bop_docs,
                ),
            ])

        # 7. Seed TemplateRegistry (D01..D13)
        if not (await session.execute(select(TemplateRegistry))).scalars().first():
            if not TEMPLATES_DIR.exists() or not any(TEMPLATES_DIR.glob("*.docx")):
                build_all_templates()
            for doc_code, doc_name, filename, is_mand, req_tokens in DEFAULT_DOC_DEFINITIONS:
                tmpl_file = TEMPLATES_DIR / filename
                detected = []
                if tmpl_file.is_file():
                    res_val = extract_and_validate_docx_bytes(
                        doc_code, filename, tmpl_file.read_bytes(), req_tokens
                    )
                    detected = res_val.get("detected_tokens", [])
                session.add(
                    TemplateRegistry(
                        doc_code=doc_code,
                        doc_name=doc_name,
                        funding_scheme="ALL",
                        is_mandatory=is_mand,
                        version=1,
                        filename=filename,
                        file_path=str(tmpl_file) if tmpl_file.is_file() else None,
                        required_tokens=req_tokens,
                        detected_tokens=detected,
                        is_active=True,
                        uploaded_by="SYSTEM_DEFAULT",
                    )
                )

        await session.commit()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="PCI Procurement & SPJ System backend API for Indonesian primary school (SD) procurement automation.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles

# Register API v1 routes
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

# Mount storage directory for static file access (letterheads, artifacts, logos)
storage_dir = settings.BASE_DIR / "storage"
storage_dir.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(storage_dir)), name="storage")


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV
    }
