from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.api.deps import get_current_user_role
from app.models.packages import Package, PackageRevision, RevisionLine, DocumentEvent, DocumentNumber
from app.models.masters import School, Company, TaxPolicyVersion, OfficialAppointment
from app.schemas.packages import (
    PackageCreate,
    PackageResponse,
    PackageRevisionResponse,
    PackageRevisionUpdate,
    RevisionCalculateRequest,
    RevisionCalculateResponse,
    TaxBreakdownItem,
)
from app.core.terbilang import terbilang

router = APIRouter(prefix="/packages", tags=["Packages"])
revisions_router = APIRouter(prefix="/revisions", tags=["Package Revisions"])


@router.get("", response_model=List[PackageResponse])
async def list_packages(
    school_id: Optional[UUID] = None,
    fiscal_year: Optional[int] = None,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Package).options(
        selectinload(Package.revisions).selectinload(PackageRevision.lines),
        selectinload(Package.revisions).selectinload(PackageRevision.events),
        selectinload(Package.revisions).selectinload(PackageRevision.numbers),
    )
    if school_id:
        query = query.where(Package.school_id == school_id)
    if fiscal_year:
        query = query.where(Package.fiscal_year == fiscal_year)
    if status_filter:
        query = query.where(Package.status == status_filter.upper())

    result = await db.execute(query)
    packages = result.scalars().all()
    for pkg in packages:
        setattr(pkg, "package_code", pkg.package_number)
        if pkg.revisions:
            pkg.current_revision = pkg.revisions[-1]
    return packages


@router.post("", response_model=PackageResponse, status_code=status.HTTP_201_CREATED)
async def create_package(payload: PackageCreate, db: AsyncSession = Depends(get_db)):
    # Check school exists
    res_school = await db.execute(select(School).where(School.id == payload.school_id))
    school = res_school.scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=404, detail="Sekolah tidak ditemukan.")

    if payload.package_number:
        pkg_number = payload.package_number
    else:
        prefix = f"PKG/{payload.fiscal_year}/Q{payload.quarter}/"
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
        fiscal_year=payload.fiscal_year,
        quarter=payload.quarter,
        funding_source_id=payload.funding_source_id,
        budget_id=payload.budget_id,
        status="DRAFT"
    )
    db.add(package)
    await db.flush()

    # Create empty Revision 1
    school_snapshot = {
        "id": str(school.id),
        "name": school.name,
        "npsn": school.npsn,
        "address": school.address,
        "email": school.email,
        "level": school.level,
    }
    company_res = await db.execute(select(Company).where(Company.is_active == True))
    company = company_res.scalar_one_or_none()
    company_snapshot = {
        "id": str(company.id) if company else None,
        "name": company.legal_name if company else "CV. PUSTAKA CEMERLANG INDONESIA",
        "legal_name": company.legal_name if company else "CV. PUSTAKA CEMERLANG INDONESIA",
        "npwp": company.npwp if company else "",
        "address": company.address if company else "",
        "director_name": company.director_name if company else "Bambang Solifian",
        "director_title": company.director_title if company else "Direktur",
        "bank_name": company.bank_name if company else "",
        "bank_account_number": company.bank_account_number if company else "",
        "bank_account_holder": company.bank_account_holder if company else "",
    }

    # Query active tax policies dynamically from DB (auto-seed if table is empty)
    res_taxes = await db.execute(select(TaxPolicyVersion).where(TaxPolicyVersion.is_active == True))
    tax_policies = res_taxes.scalars().all()
    if not tax_policies:
        p_ppn = TaxPolicyVersion(
            policy_id=f"DEFAULT_{payload.fiscal_year}",
            version=1,
            tax_type="PPN",
            rate=Decimal("0.11"),
            is_inclusive=False,
            withholding_rule="NONE",
            rounding_rule="ROUND_HALF_UP",
            is_active=True,
        )
        p_pph = TaxPolicyVersion(
            policy_id=f"DEFAULT_{payload.fiscal_year}",
            version=1,
            tax_type="PPH22",
            rate=Decimal("0.015"),
            is_inclusive=False,
            withholding_rule="WITHHOLD_FROM_PAYABLE",
            rounding_rule="ROUND_HALF_UP",
            is_active=True,
        )
        db.add_all([p_ppn, p_pph])
        await db.flush()
        tax_policies = [p_ppn, p_pph]

    tax_policy_snapshot = [
        {
            "tax_type": tp.tax_type,
            "rate": str(tp.rate),
            "is_inclusive": tp.is_inclusive,
            "withholding_rule": tp.withholding_rule,
            "rounding_rule": tp.rounding_rule,
        }
        for tp in tax_policies
    ]

    # Query only officially registered school appointments (PRD: do not create fake dummy officials)
    res_officials = await db.execute(
        select(OfficialAppointment).where(
            OfficialAppointment.school_id == school.id,
            OfficialAppointment.is_active == True,
        )
    )
    officials = res_officials.scalars().all()
    officials_snapshot = [
        {
            "role": o.role,
            "role_title": o.role.replace("_", " ").title(),
            "person_name": o.person_name,
            "name": o.person_name,
            "nip": o.nip,
            "position_sk_number": "",
        }
        for o in officials
    ]
    if company:
        officials_snapshot.append({
            "role": "DIREKTUR",
            "role_title": "Direktur Rekanan",
            "person_name": company.director_name or "Bambang Solifian",
            "name": company.director_name or "Bambang Solifian",
            "nip": None,
            "position_sk_number": "",
        })

    revision = PackageRevision(
        package_id=package.id,
        revision_number=1,
        version=1,
        school_snapshot=school_snapshot,
        company_snapshot=company_snapshot,
        tax_policy_snapshot=tax_policy_snapshot,
        officials_snapshot=officials_snapshot,
        subtotal=Decimal("0"),
        tax_total=Decimal("0"),
        grand_total=Decimal("0"),
        terbilang_grand_total="Nol Rupiah",
    )
    db.add(revision)
    await db.flush()

    # Pre-reserve internal COMPANY document numbers only (PRD: do not allocate school letter numbers)
    # Canonical: D03 = Penawaran, D06 = Faktur, D08 = Surat Jalan, D13 = BAST Rekanan
    company_docs = [
        ("D03", "Surat Penawaran"),
        ("D06", "Faktur Tagihan Pajak"),
        ("D08", "Surat Jalan"),
        ("D13", "BAST Rekanan"),
    ]
    for seq, (doc_code, _) in enumerate(company_docs, start=1):
        doc_num = DocumentNumber(
            revision_id=revision.id,
            doc_code=doc_code,
            doc_number=f"{doc_code}/PCI/{payload.fiscal_year}",
            issuer="COMPANY",
            counter_val=seq,
            is_reserved=True,
        )
        db.add(doc_num)

    package.current_revision_id = revision.id
    await db.commit()

    result = await db.execute(
        select(Package)
        .options(
            selectinload(Package.revisions).selectinload(PackageRevision.lines),
            selectinload(Package.revisions).selectinload(PackageRevision.events),
            selectinload(Package.revisions).selectinload(PackageRevision.numbers),
        )
        .where(Package.id == package.id)
    )
    loaded_package = result.scalar_one()
    setattr(loaded_package, "package_code", loaded_package.package_number)
    if loaded_package.revisions:
        loaded_package.current_revision = loaded_package.revisions[-1]

    return loaded_package



@router.get("/{id}", response_model=PackageResponse)
async def get_package(id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Package)
        .options(
            selectinload(Package.revisions).selectinload(PackageRevision.lines),
            selectinload(Package.revisions).selectinload(PackageRevision.events),
            selectinload(Package.revisions).selectinload(PackageRevision.numbers),
        )
        .where(Package.id == id)
    )
    package = result.scalar_one_or_none()
    if not package:
        raise HTTPException(status_code=404, detail="Paket pengadaan tidak ditemukan.")
    setattr(package, "package_code", package.package_number)
    if package.revisions:
        package.current_revision = package.revisions[-1]
    return package


@router.delete("/{id}", status_code=status.HTTP_200_OK)
async def delete_package(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    role: str = Depends(get_current_user_role)
):
    """Deletes a draft package and all associated child revisions, lines, events, numbers.
    Only packages that have not reached APPROVED or ISSUED status can be permanently deleted.
    """
    if role not in ("ADMINISTRATION", "SYSTEM_ADMINISTRATOR"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Peran '{role}' tidak berwenang menghapus draf paket pengadaan."
        )

    result = await db.execute(
        select(Package)
        .options(selectinload(Package.revisions))
        .where(Package.id == id)
    )
    package = result.scalar_one_or_none()
    if not package:
        raise HTTPException(status_code=404, detail="Paket pengadaan tidak ditemukan.")

    has_issued_or_approved = any(
        rev.status in ("APPROVED", "ISSUED") for rev in package.revisions
    )
    if has_issued_or_approved or package.status == "ISSUED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paket pengadaan yang sudah disetujui (APPROVED) atau diterbitkan (ISSUED) tidak dapat dihapus. Gunakan fungsi pembatalan paket (CANCEL)."
        )

    pkg_num = package.package_number
    # Disassociate current_revision_id to avoid circular foreign key constraint during deletion
    package.current_revision_id = None
    await db.flush()

    await db.delete(package)
    await db.commit()

    return {
        "message": f"Draf paket pengadaan {pkg_num} berhasil dihapus permanen.",
        "package_id": str(id),
        "package_number": pkg_num
    }


@router.get("/{id}/revisions/{revision_id}", response_model=PackageRevisionResponse)
@router.get("/revisions/{revision_id}", response_model=PackageRevisionResponse)
@revisions_router.get("/{revision_id}", response_model=PackageRevisionResponse)
async def get_package_revision(
    revision_id: UUID,
    id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(PackageRevision)
        .options(
            selectinload(PackageRevision.lines),
            selectinload(PackageRevision.events),
            selectinload(PackageRevision.numbers),
        )
        .where(PackageRevision.id == revision_id)
    )
    if id is not None:
        query = query.where(PackageRevision.package_id == id)
    result = await db.execute(query)
    revision = result.scalar_one_or_none()
    if not revision:
        raise HTTPException(status_code=404, detail="Revisi paket tidak ditemukan.")
    return revision


@router.patch("/{id}/revisions/{revision_id}", response_model=PackageRevisionResponse)
@router.put("/{id}/revisions/{revision_id}", response_model=PackageRevisionResponse)
@router.patch("/revisions/{revision_id}", response_model=PackageRevisionResponse)
@router.put("/revisions/{revision_id}", response_model=PackageRevisionResponse)
@router.put("/revisions/{revision_id}/lines", response_model=PackageRevisionResponse)
@revisions_router.patch("/{revision_id}", response_model=PackageRevisionResponse)
@revisions_router.put("/{revision_id}", response_model=PackageRevisionResponse)
@revisions_router.put("/{revision_id}/lines", response_model=PackageRevisionResponse)
async def update_package_revision(
    revision_id: UUID,
    payload: PackageRevisionUpdate,
    id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    role: str = Depends(get_current_user_role)
):
    """Updates revision items or events with optimistic concurrency locking.
    Throws 403 Forbidden if user role is not ADMINISTRATION.
    Throws 409 Conflict if revision is locked or expected_version does not match current version.
    """
    if role == "LOGISTICS":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Peran Bagian Logistik tidak berwenang mengubah rincian barang atau harga pengadaan."
        )
    if role == "FINANCE_DIRECTOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Direktur Keuangan tidak dapat mengubah rincian item secara langsung tanpa mengembalikan revisi (RETURN)."
        )
    if role not in ("ADMINISTRATION", "SYSTEM_ADMINISTRATOR"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Peran '{role}' tidak berwenang memperbarui rincian revisi paket pengadaan."
        )

    query = (
        select(PackageRevision)
        .options(
            selectinload(PackageRevision.lines),
            selectinload(PackageRevision.events),
            selectinload(PackageRevision.numbers),
        )
        .where(PackageRevision.id == revision_id)
    )
    if id is not None:
        query = query.where(PackageRevision.package_id == id)
    result = await db.execute(query)
    revision = result.scalar_one_or_none()
    if not revision:
        raise HTTPException(status_code=404, detail="Revisi paket tidak ditemukan.")

    if revision.is_locked or revision.status in ("UNDER_REVIEW", "APPROVED", "ISSUED", "SUPERSEDED", "CANCELLED"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Revisi ini telah berstatus '{revision.status}' (terkunci) dan tidak dapat dimodifikasi lagi."
        )

    # Optimistic concurrency check
    if revision.version != payload.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Konflik persaingan pembaruan (Optimistic Lock Error): "
                f"versi yang Anda kirimkan ({payload.expected_version}) berbeda dengan versi sistem ({revision.version}). "
                f"Data telah dimodifikasi oleh pengguna lain."
            )
        )

    # Update snapshots if provided
    if payload.school_snapshot is not None:
        revision.school_snapshot = payload.school_snapshot
    if payload.company_snapshot is not None:
        revision.company_snapshot = payload.company_snapshot
    if payload.tax_policy_snapshot is not None:
        revision.tax_policy_snapshot = payload.tax_policy_snapshot
        if payload.lines is None:
            subtotal = revision.subtotal or Decimal("0")
            tax_total = Decimal("0")
            for tp in revision.tax_policy_snapshot or []:
                rate = Decimal(str(tp.get("rate", "0")))
                withholding = tp.get("withholding_rule", "NONE")
                is_inc = tp.get("is_inclusive", False)
                if withholding == "NONE" and not is_inc:
                    tax_total += (subtotal * rate).quantize(Decimal("1"))
            grand_total = subtotal + tax_total
            revision.tax_total = tax_total
            revision.grand_total = grand_total
            revision.terbilang_grand_total = terbilang(grand_total)
    if payload.officials_snapshot is not None:
        revision.officials_snapshot = payload.officials_snapshot

    # Update lines if provided
    if payload.lines is not None:
        await db.execute(delete(RevisionLine).where(RevisionLine.revision_id == revision.id))
        await db.flush()

        subtotal = Decimal("0")
        for idx, l in enumerate(payload.lines, start=1):
            qty = Decimal(str(l.quantity))
            hps = Decimal(str(l.hps_unit_price))
            offer = Decimal(str(l.offer_unit_price))
            final = Decimal(str(l.final_unit_price))
            disc = Decimal(str(l.discount))
            line_tot = (qty * final) - disc
            subtotal += line_tot

            new_line = RevisionLine(
                revision_id=revision.id,
                line_number=idx,
                item_id=l.item_id,
                original_description=l.original_description,
                confirmed_description=l.confirmed_description,
                specification=l.specification,
                quantity=qty,
                unit=l.unit,
                hps_unit_price=hps,
                offer_unit_price=offer,
                final_unit_price=final,
                discount=disc,
                line_total=line_tot,
                condition=l.condition,
                notes=l.notes
            )
            db.add(new_line)

        # Recompute tax from active snapshot
        tax_total = Decimal("0")
        for tp in revision.tax_policy_snapshot or []:
            rate = Decimal(str(tp.get("rate", "0")))
            withholding = tp.get("withholding_rule", "NONE")
            is_inc = tp.get("is_inclusive", False)
            if withholding == "NONE" and not is_inc:
                tax_total += (subtotal * rate).quantize(Decimal("1"))

        grand_total = subtotal + tax_total

        revision.subtotal = subtotal
        revision.tax_total = tax_total
        revision.grand_total = grand_total
        revision.terbilang_grand_total = terbilang(grand_total)

    # Update events if provided
    if payload.events is not None:
        await db.execute(delete(DocumentEvent).where(DocumentEvent.revision_id == revision.id))
        await db.flush()
        for ev in payload.events:
            new_event = DocumentEvent(
                revision_id=revision.id,
                event_code=ev.event_code,
                event_date=ev.event_date,
                day_name_id=ev.day_name_id,
                location=ev.location or "Jakarta",
                notes=ev.notes
            )
            db.add(new_event)

    # Update numbers if provided
    if payload.numbers is not None:
        await db.execute(delete(DocumentNumber).where(DocumentNumber.revision_id == revision.id))
        await db.flush()
        for num in payload.numbers:
            new_number = DocumentNumber(
                revision_id=revision.id,
                doc_code=num.doc_code,
                doc_number=num.doc_number,
                issuer=num.issuer,
                counter_val=num.counter_val,
                issue_date=num.issue_date,
                is_reserved=num.is_reserved,
            )
            db.add(new_number)

    if payload.notes is not None:
        revision.notes = payload.notes

    # Increment optimistic concurrency version
    revision.version += 1

    await db.commit()
    
    rev_reloaded = await db.execute(
        select(PackageRevision)
        .options(
            selectinload(PackageRevision.lines),
            selectinload(PackageRevision.events),
            selectinload(PackageRevision.numbers),
        )
        .where(PackageRevision.id == revision.id)
    )
    return rev_reloaded.scalar_one()


@revisions_router.post("/{revision_id}/calculate", response_model=RevisionCalculateResponse)
@router.post("/revisions/{revision_id}/calculate", response_model=RevisionCalculateResponse)
@router.post("/{id}/revisions/{revision_id}/calculate", response_model=RevisionCalculateResponse)
async def calculate_revision_totals(
    revision_id: UUID,
    payload: RevisionCalculateRequest,
    id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    """Server-authoritative calculation of subtotal, taxes, grand total, and terbilang text."""
    rev_res = await db.execute(select(PackageRevision).where(PackageRevision.id == revision_id))
    revision = rev_res.scalar_one_or_none()

    subtotal = Decimal("0")
    for l in payload.lines:
        qty = Decimal(str(l.quantity))
        final = Decimal(str(l.final_unit_price))
        disc = Decimal(str(l.discount))
        factor = Decimal("1") - (disc / Decimal("100"))
        line_tot = (qty * final * factor).quantize(Decimal("1"))
        subtotal += line_tot

    tax_policies = (revision.tax_policy_snapshot if revision and revision.tax_policy_snapshot else None) or [
        {"tax_type": "PPN", "rate_percent": 11, "is_withholding": False}
    ]

    tax_breakdown = []
    tax_total = Decimal("0")
    for p in tax_policies:
        rate_val = Decimal(str(p.get("rate_percent") or p.get("rate") or 11))
        if Decimal("0") < rate_val < Decimal("1"):
            rate_pct = rate_val * Decimal("100")
            amt = (subtotal * rate_val).quantize(Decimal("1"))
        else:
            rate_pct = rate_val
            amt = (subtotal * (rate_val / Decimal("100"))).quantize(Decimal("1"))

        is_withholding = p.get("is_withholding", False) or p.get("withholding_rule", "NONE") != "NONE"
        tax_breakdown.append(TaxBreakdownItem(
            tax_type=p.get("tax_type", "PPN"),
            amount=float(amt),
            rate=float(rate_pct)
        ))
        if not is_withholding:
            tax_total += amt

    grand_total = subtotal + tax_total
    terbilang_text = terbilang(grand_total)

    return RevisionCalculateResponse(
        subtotal=float(subtotal),
        tax_total=float(tax_total),
        grand_total=float(grand_total),
        terbilang=terbilang_text,
        tax_breakdown=tax_breakdown
    )

