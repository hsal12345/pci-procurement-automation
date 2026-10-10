import shutil
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_current_actor_name, get_current_user_role
from app.config import settings
from app.database import get_db
from app.models.imports import ImportRecord
from app.models.masters import School, Company, TaxPolicyVersion, OfficialAppointment
from app.models.packages import Package, PackageRevision, RevisionLine, DocumentEvent, DocumentNumber
from app.schemas.imports import ImportUploadResponse, ImportPreviewResponse, ImportConfirmRequest
from app.services.import_service import ExcelImportService
from app.core.terbilang import terbilang

router = APIRouter(prefix="/imports", tags=["Imports"])
import_service = ExcelImportService()


@router.post("/upload", response_model=ImportUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_excel_import(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    role: str = Depends(get_current_user_role),
    actor_name: str = Depends(get_current_actor_name),
):
    """Uploads an .xlsx workbook, securely parses structural content,
    and stores candidate JSON with detected discrepancies.
    """
    if role not in ("ADMINISTRATION", "SYSTEM_ADMINISTRATOR"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak: Hanya staf Administrasi atau Administrator Sistem yang dapat mengimpor spreadsheet.",
        )

    if not file.filename.endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hanya file berekstensi .xlsx yang didukung untuk impor berkas pengadaan."
        )

    temp_path = settings.get_upload_dir() / f"{uuid4()}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_hash = import_service.compute_sha256(temp_path)
    file_size = temp_path.stat().st_size

    # Parse structural workbook
    try:
        parsed_result = import_service.parse_workbook(temp_path)
    except Exception as e:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Gagal memproses struktur berkas Excel: {str(e)}"
        )

    # Store import record in database
    import_record = ImportRecord(
        original_filename=file.filename,
        file_hash=file_hash,
        file_size=file_size,
        uploader=actor_name,
        status="PARSED",
        candidate_payload=parsed_result,
        sheet_metadata={"sheet_names": parsed_result["sheet_names"]},
        detected_discrepancies=parsed_result["detected_discrepancies"],
    )
    db.add(import_record)
    await db.commit()
    await db.refresh(import_record)

    return ImportUploadResponse(
        import_id=import_record.id,
        filename=import_record.original_filename,
        file_hash=import_record.file_hash,
        status=import_record.status,
        message="Berkas berhasil diunggah dan diuraikan. Silakan tinjau pratinjau pemetaan sebelum konfirmasi."
    )


@router.get("/{id}/preview", response_model=ImportPreviewResponse)
async def get_import_preview(id: UUID, db: AsyncSession = Depends(get_db)):
    """Retrieves normalized preview of candidate transaction lines, metadata,
    and detected invariant discrepancies for staff confirmation.
    """
    result = await db.execute(select(ImportRecord).where(ImportRecord.id == id))
    rec = result.scalar_one_or_none()
    if not rec or not rec.candidate_payload:
        raise HTTPException(status_code=404, detail="Data impor berkas tidak ditemukan.")

    payload = rec.candidate_payload
    return ImportPreviewResponse(
        import_id=rec.id,
        filename=rec.original_filename,
        status=rec.status,
        school_candidate=payload.get("school_candidate", {}),
        transaction_metadata=payload.get("transaction_metadata", {}),
        candidate_lines=payload.get("candidate_lines", []),
        events_candidate=payload.get("events_candidate", []),
        detected_discrepancies=rec.detected_discrepancies or [],
        can_proceed_to_confirm=payload.get("can_proceed_to_confirm", False)
    )


@router.post("/{id}/confirm", status_code=status.HTTP_201_CREATED)
async def confirm_import_and_create_package(
    id: UUID,
    request: ImportConfirmRequest,
    db: AsyncSession = Depends(get_db),
    role: str = Depends(get_current_user_role),
):
    """Commits confirmed candidate data into a new package and Revision 1.
    Snapshots master data immutably and recalculates exact financial totals.
    """
    if role not in ("ADMINISTRATION", "SYSTEM_ADMINISTRATOR"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak: Hanya staf Administrasi atau Administrator Sistem yang dapat mengonfirmasi impor.",
        )

    result = await db.execute(select(ImportRecord).where(ImportRecord.id == id))
    rec = result.scalar_one_or_none()
    if not rec or not rec.candidate_payload:
        raise HTTPException(status_code=404, detail="Data impor berkas tidak ditemukan.")

    payload = rec.candidate_payload
    meta = payload.get("transaction_metadata", {})
    fiscal_year = meta.get("tahun_anggaran", 2026)

    # 1. Resolve or create School
    school_id = request.school_id
    if not school_id:
        # Check if school candidate matches an existing school or create one
        cand_school = payload.get("school_candidate", {})
        cand_name = cand_school.get("name", "SEKOLAH DASAR NEGERI KEBON KOSONG 09")
        res_school = await db.execute(select(School).where(School.name == cand_name))
        school = res_school.scalars().first()
        if not school:
            school = School(
                name=cand_name,
                address=cand_school.get("address", "Jl. Kemayoran Gempol no.32"),
                email=cand_school.get("email", "sdnkk05pg@gmail.com"),
                level="SD"
            )
            db.add(school)
            await db.flush()
        school_id = school.id
    else:
        res_school = await db.execute(select(School).where(School.id == school_id))
        school = res_school.scalars().first()
        if not school:
            raise HTTPException(status_code=404, detail="Sekolah yang dipilih tidak ditemukan.")

    # 2. Get active Company
    res_company = await db.execute(select(Company).where(Company.is_active == True))
    company = res_company.scalars().first()
    if not company:
        # Seed default company if none exists
        company = Company(
            legal_name="CV. PUSTAKA CEMERLANG INDONESIA",
            address="Wisma Mitra Sunter Unit 3-03, Jl. Yos Sudarso Kav. 89",
            director_name="Bambang Solifian",
            director_title="Direktur Utama"
        )
        db.add(company)
        await db.flush()

    # 3. Get tax policy versions
    res_taxes = await db.execute(select(TaxPolicyVersion).where(TaxPolicyVersion.is_active == True))
    tax_policies = res_taxes.scalars().all()
    if not tax_policies:
        # Seed default PPN 11% and PPh 22 1.5%
        p_ppn = TaxPolicyVersion(
            policy_id="DEFAULT_2026",
            version=1,
            tax_type="PPN",
            rate=Decimal("0.11"),
            is_inclusive=False,
            withholding_rule="NONE",
            rounding_rule="ROUND_HALF_UP"
        )
        p_pph = TaxPolicyVersion(
            policy_id="DEFAULT_2026",
            version=1,
            tax_type="PPH22",
            rate=Decimal("0.015"),
            is_inclusive=False,
            withholding_rule="WITHHOLD_FROM_PAYABLE",
            rounding_rule="ROUND_HALF_UP"
        )
        db.add_all([p_ppn, p_pph])
        await db.flush()
        tax_policies = [p_ppn, p_pph]

    # Snapshots
    school_snapshot = {
        "id": str(school.id),
        "name": school.name,
        "npsn": school.npsn,
        "address": school.address,
        "email": school.email
    }
    company_snapshot = {
        "id": str(company.id),
        "legal_name": company.legal_name,
        "address": company.address,
        "director_name": company.director_name,
        "director_title": company.director_title
    }
    tax_snapshot = [
        {
            "tax_type": tp.tax_type,
            "rate": str(tp.rate),
            "is_inclusive": tp.is_inclusive,
            "withholding_rule": tp.withholding_rule,
            "rounding_rule": tp.rounding_rule
        }
        for tp in tax_policies
    ]

    # Get school appointments
    res_officials = await db.execute(
        select(OfficialAppointment).where(OfficialAppointment.school_id == school.id)
    )
    officials = res_officials.scalars().all()
    if not officials:
        app_ks = OfficialAppointment(
            school_id=school.id,
            role="KEPALA_SEKOLAH",
            person_name="Drs. H. Mulyadi, M.Pd",
            nip="196501011990031005"
        )
        app_ben = OfficialAppointment(
            school_id=school.id,
            role="BENDAHARA",
            person_name="Siti Rahmawati, S.Pd",
            nip="198005122008012015"
        )
        app_pb = OfficialAppointment(
            school_id=school.id,
            role="PENGURUS_BARANG",
            person_name="Sulistiawati",
            nip="197909092022212008"
        )
        db.add_all([app_ks, app_ben, app_pb])
        await db.flush()
        officials = [app_ks, app_ben, app_pb]

    officials_snapshot = [
        {"role": o.role, "person_name": o.person_name, "name": o.person_name, "nip": o.nip} for o in officials
    ]
    if company:
        officials_snapshot.append({
            "role": "DIREKTUR",
            "person_name": company.director_name or "Bambang Solifian",
            "name": company.director_name or "Bambang Solifian",
            "nip": None
        })

    # 4. Create Package
    prefix = f"PKG/{fiscal_year}/Q2/"
    res_pkgs = await db.execute(select(Package.package_number).where(Package.package_number.like(f"{prefix}%")))
    existing_numbers = res_pkgs.scalars().all()
    max_seq = 0
    for num in existing_numbers:
        suffix = num[len(prefix):]
        if suffix.isdigit():
            val = int(suffix)
            if val > max_seq:
                max_seq = val
    next_seq = max_seq + 1
    while True:
        candidate = f"{prefix}{next_seq:04d}"
        chk = await db.execute(select(Package.id).where(Package.package_number == candidate))
        if not chk.scalar_one_or_none():
            pkg_number = candidate
            break
        next_seq += 1

    package = Package(
        package_number=pkg_number,
        school_id=school.id,
        fiscal_year=fiscal_year,
        quarter=2,
        status="DRAFT"
    )
    db.add(package)
    await db.flush()

    # 5. Create Revision 1
    revision = PackageRevision(
        package_id=package.id,
        revision_number=1,
        version=1,
        school_snapshot=school_snapshot,
        company_snapshot=company_snapshot,
        tax_policy_snapshot=tax_snapshot,
        officials_snapshot=officials_snapshot,
        notes=request.notes
    )
    db.add(revision)
    await db.flush()

    # 6. Create Revision Lines & calculate exact totals
    lines_data = request.confirmed_lines or payload.get("candidate_lines", [])
    subtotal = Decimal("0")

    for idx, l in enumerate(lines_data, start=1):
        qty = Decimal(str(l.get("quantity", 1)))
        hps_price = Decimal(str(l.get("hps_unit_price", 0)))
        offer_price = Decimal(str(l.get("offer_unit_price", 0)))
        final_price = Decimal(str(l.get("final_unit_price", 0)))
        discount = Decimal(str(l.get("discount", 0)))
        line_tot = (qty * final_price) - discount

        subtotal += line_tot

        rev_line = RevisionLine(
            revision_id=revision.id,
            line_number=idx,
            original_description=l.get("original_description", f"Item {idx}"),
            confirmed_description=l.get("confirmed_description", f"Item {idx}"),
            specification=l.get("specification"),
            quantity=qty,
            unit=l.get("unit", "buah"),
            hps_unit_price=hps_price,
            offer_unit_price=offer_price,
            final_unit_price=final_price,
            discount=discount,
            line_total=line_tot,
            condition=l.get("condition", "BAIK")
        )
        db.add(rev_line)

    # Calculate additive tax (e.g. PPN 11%)
    tax_total = Decimal("0")
    for tp in tax_policies:
        if tp.withholding_rule == "NONE" and not tp.is_inclusive:
            tax_total += (subtotal * tp.rate).quantize(Decimal("1"))

    grand_total = subtotal + tax_total

    revision.subtotal = subtotal
    revision.tax_total = tax_total
    revision.grand_total = grand_total
    revision.terbilang_grand_total = terbilang(grand_total)

    # 7. Create Document Events
    events_data = request.confirmed_events or payload.get("events_candidate", [])
    for ev in events_data:
        doc_event = DocumentEvent(
            revision_id=revision.id,
            event_code=ev.get("event_code"),
            event_date=date.fromisoformat(ev.get("event_date")),
            day_name_id=ev.get("day_name_id", "Selasa")
        )
        db.add(doc_event)

    # 8. Create Document Numbers for the 13 required documents
    for i in range(1, 14):
        doc_code = f"D{i:02d}"
        doc_num = DocumentNumber(
            revision_id=revision.id,
            doc_code=doc_code,
            doc_number=f"{i:02d}/PCI/{fiscal_year}",
            issuer="COMPANY" if doc_code in ["D03", "D06", "D07", "D08", "D13"] else "SCHOOL",
            counter_val=i
        )
        db.add(doc_num)

    package.current_revision_id = revision.id
    rec.status = "CONFIRMED"

    await db.commit()
    await db.refresh(package)

    return {
        "message": "Paket pengadaan berhasil dibuat dari data impor.",
        "package_id": str(package.id),
        "package_number": package.package_number,
        "revision_id": str(revision.id),
        "revision_number": revision.revision_number,
        "subtotal": float(subtotal),
        "tax_total": float(tax_total),
        "grand_total": float(grand_total),
        "terbilang": revision.terbilang_grand_total
    }
