from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.config import settings
from app.database import get_db
from app.api.deps import get_current_actor_name
from app.models.masters import (
    Company,
    CompanyOfficial,
    School,
    OfficialAppointment,
    Item,
    Unit,
    BudgetClassification,
    FundingSource,
    PackageProfile,
    TaxPolicyVersion,
    NumberCounter,
    TemplateRegistry,
)
from app.models.packages import Package, RevisionLine
from app.schemas.masters import (
    CompanyCreate,
    CompanyUpdate,
    CompanyResponse,
    CompanyOfficialCreate,
    CompanyOfficialResponse,
    SchoolCreate,
    SchoolUpdate,
    SchoolResponse,
    OfficialAppointmentCreate,
    OfficialAppointmentUpdate,
    OfficialAppointmentResponse,
    ItemCreate,
    ItemUpdate,
    ItemPriceUpdate,
    ItemResponse,
    UnitCreate,
    UnitUpdate,
    UnitResponse,
    BudgetClassificationCreate,
    BudgetClassificationUpdate,
    BudgetClassificationResponse,
    FundingSourceCreate,
    FundingSourceUpdate,
    FundingSourceResponse,
    PackageProfileResponse,
    PackageProfileUpdate,
    TemplateRegistryResponse,
    TemplateConfigUpdate,
    TemplateValidationResult,
    TaxPolicyVersionCreate,
    TaxPolicyVersionResponse,
    NumberCounterResponse,
)
from app.services.audit_service import audit_service
from app.services.export.docx_generator import DOCUMENT_MAP
from app.services.template_registry_service import (
    extract_and_validate_docx_bytes,
    save_and_activate_template,
    get_effective_template_path,
    render_simulation_preview,
)

router = APIRouter(prefix="/masters", tags=["Masters"])


# 1. Companies
@router.get("/companies", response_model=List[CompanyResponse])
async def list_companies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company))
    return result.scalars().all()


@router.post("/companies", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(payload: CompanyCreate, db: AsyncSession = Depends(get_db)):
    company_data = payload.model_dump()
    company = Company(**company_data)
    db.add(company)
    await db.flush()

    # Automatically seed the primary director as CompanyOfficial
    if company.director_name:
        dir_off = CompanyOfficial(
            company_id=company.id,
            person_name=company.director_name,
            role="DIREKTUR",
            role_title=company.director_title or "Direktur",
            position_sk_number=company.director_sk_number or "Akta Notaris Pendirian",
            is_active=True,
        )
        db.add(dir_off)

    await db.commit()
    await db.refresh(company)
    return company


@router.get("/companies/{id}", response_model=CompanyResponse)
async def get_company(id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.id == id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Data perusahaan tidak ditemukan.")
    return company


@router.put("/companies/{id}", response_model=CompanyResponse)
async def update_company(id: UUID, payload: CompanyUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.id == id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Data perusahaan tidak ditemukan.")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(company, field, value)

    # Sync primary director to company_officials if director fields are modified
    if any(k in update_data for k in ["director_name", "director_sk_number", "director_title"]):
        c_off_res = await db.execute(
            select(CompanyOfficial).where(
                CompanyOfficial.company_id == company.id,
                CompanyOfficial.role == "DIREKTUR",
                CompanyOfficial.is_active == True,
            )
        )
        c_off = c_off_res.scalars().first()
        if c_off:
            if "director_name" in update_data and update_data["director_name"]:
                c_off.person_name = update_data["director_name"]
            if "director_sk_number" in update_data:
                c_off.position_sk_number = update_data["director_sk_number"]
            if "director_title" in update_data and update_data["director_title"]:
                c_off.role_title = update_data["director_title"]
        elif company.director_name:
            new_off = CompanyOfficial(
                company_id=company.id,
                person_name=company.director_name,
                role="DIREKTUR",
                role_title=company.director_title or "Direktur",
                position_sk_number=company.director_sk_number or "Akta Notaris",
                is_active=True,
            )
            db.add(new_off)

    await db.commit()
    await db.refresh(company)
    return company


@router.post("/companies/{id}/logo", response_model=CompanyResponse)
async def upload_company_logo(id: UUID, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.id == id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Data perusahaan tidak ditemukan.")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        raise HTTPException(status_code=400, detail="Format berkas harus PNG, JPG, JPEG, atau WebP.")

    target_dir = settings.get_upload_dir() / "letterheads" / "companies"
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"company_{company.id}_{int(datetime.utcnow().timestamp())}{ext}"
    file_path = target_dir / filename

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    rel_path = f"/storage/uploads/letterheads/companies/{filename}"
    company.logo_path = rel_path
    await db.commit()
    await db.refresh(company)
    return company


@router.get("/companies/{company_id}/officials", response_model=List[CompanyOfficialResponse])
async def list_company_officials(company_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CompanyOfficial).where(
            CompanyOfficial.company_id == company_id,
            CompanyOfficial.is_active == True,
        )
    )
    offs = result.scalars().all()
    if not offs:
        # Fallback: synthesize from Company director if exists
        c_res = await db.execute(select(Company).where(Company.id == company_id))
        comp = c_res.scalar_one_or_none()
        if comp and comp.director_name:
            synth = CompanyOfficial(
                id=comp.id,
                company_id=comp.id,
                person_name=comp.director_name,
                role="DIREKTUR",
                role_title=comp.director_title or "Direktur",
                position_sk_number=comp.director_sk_number or "Akta Notaris Pendirian",
                is_active=True,
            )
            return [synth]
    return offs


@router.post("/companies/{company_id}/officials", response_model=CompanyOfficialResponse, status_code=status.HTTP_201_CREATED)
async def create_company_official(
    company_id: UUID,
    payload: CompanyOfficialCreate,
    db: AsyncSession = Depends(get_db)
):
    official_data = payload.model_dump()
    official_data["company_id"] = company_id
    official = CompanyOfficial(**official_data)
    db.add(official)
    await db.commit()
    await db.refresh(official)
    return official


# 2. Schools
@router.get("/schools", response_model=List[SchoolResponse])
async def list_schools(
    active_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    query = select(School)
    if active_only:
        query = query.where(School.is_active == True)
    result = await db.execute(query.order_by(School.name.asc()))
    return result.scalars().all()


@router.post("/schools", response_model=SchoolResponse, status_code=status.HTTP_201_CREATED)
async def create_school(
    payload: SchoolCreate,
    db: AsyncSession = Depends(get_db),
    actor_name: str = Depends(get_current_actor_name),
):
    if payload.npsn and payload.npsn.strip():
        dup = await db.execute(select(School).where(School.npsn == payload.npsn.strip()))
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplikasi Entitas (UC-01 4b): NPSN '{payload.npsn}' sudah terdaftar di master sekolah.",
            )

    school = School(**payload.model_dump())
    db.add(school)
    await db.flush()
    await audit_service.log_event(
        db=db,
        entity_name="School",
        entity_id=str(school.id),
        action="CREATE",
        actor=actor_name,
        after_state={"name": school.name, "npsn": school.npsn},
        reason="Penambahan entitas master sekolah",
    )
    await db.commit()
    await db.refresh(school)
    return school


@router.get("/schools/{id}", response_model=SchoolResponse)
async def get_school(id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(School).where(School.id == id))
    school = result.scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=404, detail="Data sekolah tidak ditemukan.")
    return school


@router.put("/schools/{id}", response_model=SchoolResponse)
async def update_school(
    id: UUID,
    payload: SchoolUpdate,
    db: AsyncSession = Depends(get_db),
    actor_name: str = Depends(get_current_actor_name),
):
    result = await db.execute(select(School).where(School.id == id))
    school = result.scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=404, detail="Data sekolah tidak ditemukan.")

    update_data = payload.model_dump(exclude_unset=True)
    if "npsn" in update_data and update_data["npsn"]:
        dup = await db.execute(
            select(School).where(School.npsn == update_data["npsn"].strip(), School.id != id)
        )
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplikasi Entitas (UC-01 4b): NPSN '{update_data['npsn']}' sudah digunakan sekolah lain.",
            )

    before_state = {"name": school.name, "npsn": school.npsn, "is_active": school.is_active}
    for field, value in update_data.items():
        setattr(school, field, value)

    await audit_service.log_event(
        db=db,
        entity_name="School",
        entity_id=str(school.id),
        action="UPDATE",
        actor=actor_name,
        before_state=before_state,
        after_state={"name": school.name, "npsn": school.npsn, "is_active": school.is_active},
        reason="Pembaruan data master sekolah",
    )
    await db.commit()
    await db.refresh(school)
    return school


@router.delete("/schools/{id}")
async def delete_or_deactivate_school(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    actor_name: str = Depends(get_current_actor_name),
):
    """UC-01 2a: Entities referenced by transactions are soft-deactivated instead of hard deleted."""
    result = await db.execute(select(School).where(School.id == id))
    school = result.scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=404, detail="Data sekolah tidak ditemukan.")

    pkg_count = (await db.execute(select(func.count(Package.id)).where(Package.school_id == id))).scalar() or 0
    if pkg_count > 0:
        school.is_active = False
        await audit_service.log_event(
            db=db,
            entity_name="School",
            entity_id=str(school.id),
            action="DEACTIVATE",
            actor=actor_name,
            before_state={"is_active": True},
            after_state={"is_active": False, "referenced_packages": pkg_count},
            reason="Penonaktifan sekolah terpakai transaksi historis (UC-01 2a)",
        )
        await db.commit()
        return {
            "status": "DEACTIVATED",
            "id": str(id),
            "message": f"Sekolah '{school.name}' dirujuk oleh {pkg_count} paket transaksi historis, sehingga dinonaktifkan (soft-deactivate) sesuai UC-01 2a.",
        }

    await db.delete(school)
    await audit_service.log_event(
        db=db,
        entity_name="School",
        entity_id=str(id),
        action="DELETE",
        actor=actor_name,
        before_state={"name": school.name, "npsn": school.npsn},
        reason="Penghapusan sekolah master yang belum terpakai transaksi",
    )
    await db.commit()
    return {"status": "DELETED", "id": str(id), "message": f"Sekolah '{school.name}' berhasil dihapus."}


@router.post("/schools/{id}/letterhead", response_model=SchoolResponse)
async def upload_school_letterhead(id: UUID, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(School).where(School.id == id))
    school = result.scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=404, detail="Data sekolah tidak ditemukan.")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        raise HTTPException(status_code=400, detail="Format berkas harus PNG, JPG, JPEG, atau WebP.")

    target_dir = settings.get_upload_dir() / "letterheads" / "schools"
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"school_{school.id}_{int(datetime.utcnow().timestamp())}{ext}"
    file_path = target_dir / filename

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    rel_path = f"/storage/uploads/letterheads/schools/{filename}"
    school.letterhead_path = rel_path
    await db.commit()
    await db.refresh(school)
    return school


# 3. Official Appointments
@router.get("/schools/{school_id}/officials", response_model=List[OfficialAppointmentResponse])
async def list_school_officials(school_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OfficialAppointment).where(OfficialAppointment.school_id == school_id)
    )
    return result.scalars().all()


@router.post("/schools/{school_id}/officials", response_model=OfficialAppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_school_official(
    school_id: UUID,
    payload: OfficialAppointmentCreate,
    db: AsyncSession = Depends(get_db)
):
    official_data = payload.model_dump()
    official_data["school_id"] = school_id
    official = OfficialAppointment(**official_data)
    db.add(official)
    await db.commit()
    await db.refresh(official)
    return official


@router.put("/schools/{school_id}/officials/{official_id}", response_model=OfficialAppointmentResponse)
async def update_school_official(
    school_id: UUID,
    official_id: UUID,
    payload: OfficialAppointmentUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OfficialAppointment).where(
            OfficialAppointment.id == official_id,
            OfficialAppointment.school_id == school_id,
        )
    )
    official = result.scalar_one_or_none()
    if not official:
        raise HTTPException(status_code=404, detail="Data pejabat tidak ditemukan.")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(official, field, value)

    await db.commit()
    await db.refresh(official)
    return official


@router.delete("/schools/{school_id}/officials/{official_id}")
async def delete_school_official(
    school_id: UUID,
    official_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OfficialAppointment).where(
            OfficialAppointment.id == official_id,
            OfficialAppointment.school_id == school_id,
        )
    )
    official = result.scalar_one_or_none()
    if not official:
        raise HTTPException(status_code=404, detail="Data pejabat tidak ditemukan.")

    await db.delete(official)
    await db.commit()
    return {"message": "Pejabat berhasil dihapus", "id": str(official_id)}


# 4. Items (KatalogBarang - FR-01 / UC-01 / Tabel 12.2.1)
@router.get("/items", response_model=List[ItemResponse])
async def list_items(
    active_only: bool = Query(default=False),
    q: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Item)
    if active_only:
        query = query.where(Item.is_active == True)
    result = await db.execute(query.order_by(Item.canonical_description.asc()))
    items = result.scalars().all()
    if q and q.strip():
        needle = q.strip().lower()
        items = [
            it for it in items
            if needle in (it.canonical_description or "").lower()
            or needle in (it.sku or "").lower()
            or needle in (it.kbli or "").lower()
            or needle in (it.category or "").lower()
        ]
    return items


@router.post("/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    payload: ItemCreate,
    db: AsyncSession = Depends(get_db),
    actor_name: str = Depends(get_current_actor_name),
):
    if payload.sku and payload.sku.strip():
        dup = await db.execute(select(Item).where(Item.sku == payload.sku.strip()))
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplikasi Entitas (UC-01 4b): SKU barang '{payload.sku}' sudah terdaftar pada katalog.",
            )

    item = Item(**payload.model_dump())
    db.add(item)
    await db.flush()
    await audit_service.log_event(
        db=db,
        entity_name="Item",
        entity_id=str(item.id),
        action="CREATE",
        actor=actor_name,
        after_state={
            "sku": item.sku,
            "kbli": item.kbli,
            "canonical_description": item.canonical_description,
            "reference_price": float(item.reference_price or 0),
        },
        reason="Penambahan item ke katalog barang master",
    )
    await db.commit()
    await db.refresh(item)
    return item


@router.put("/items/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: UUID,
    payload: ItemUpdate,
    db: AsyncSession = Depends(get_db),
    actor_name: str = Depends(get_current_actor_name),
):
    res = await db.execute(select(Item).where(Item.id == item_id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item katalog tidak ditemukan.")

    update_data = payload.model_dump(exclude_unset=True)
    if "sku" in update_data and update_data["sku"]:
        dup = await db.execute(select(Item).where(Item.sku == update_data["sku"].strip(), Item.id != item_id))
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplikasi Entitas (UC-01 4b): SKU '{update_data['sku']}' sudah dipakai item lain.",
            )

    before_state = {
        "sku": item.sku,
        "kbli": item.kbli,
        "canonical_description": item.canonical_description,
        "reference_price": float(item.reference_price or 0),
        "is_active": item.is_active,
    }
    for field, value in update_data.items():
        setattr(item, field, value)

    await audit_service.log_event(
        db=db,
        entity_name="Item",
        entity_id=str(item.id),
        action="UPDATE",
        actor=actor_name,
        before_state=before_state,
        after_state={
            "sku": item.sku,
            "kbli": item.kbli,
            "canonical_description": item.canonical_description,
            "reference_price": float(item.reference_price or 0),
            "is_active": item.is_active,
        },
        reason="Pembaruan data item katalog barang",
    )
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/items/{item_id}/price", response_model=ItemResponse)
async def update_item_price(
    item_id: UUID,
    payload: ItemPriceUpdate,
    db: AsyncSession = Depends(get_db),
    actor_name: str = Depends(get_current_actor_name),
):
    """Implements KatalogBarang.updateHarga() from Class Diagram Tabel 12.2.1."""
    res = await db.execute(select(Item).where(Item.id == item_id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item katalog tidak ditemukan.")

    old_price = float(item.reference_price or 0)
    item.reference_price = payload.reference_price
    await audit_service.log_event(
        db=db,
        entity_name="Item",
        entity_id=str(item.id),
        action="UPDATE_PRICE",
        actor=actor_name,
        before_state={"reference_price": old_price},
        after_state={"reference_price": float(payload.reference_price)},
        reason="Pembaruan harga acuan katalog barang (updateHarga)",
    )
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/items/{item_id}")
async def delete_or_deactivate_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    actor_name: str = Depends(get_current_actor_name),
):
    """UC-01 2a: Soft-deactivate item if referenced in RevisionLine history."""
    res = await db.execute(select(Item).where(Item.id == item_id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item katalog tidak ditemukan.")

    ref_count = (await db.execute(select(func.count(RevisionLine.id)).where(RevisionLine.item_id == item_id))).scalar() or 0
    if ref_count > 0:
        item.is_active = False
        await audit_service.log_event(
            db=db,
            entity_name="Item",
            entity_id=str(item.id),
            action="DEACTIVATE",
            actor=actor_name,
            before_state={"is_active": True},
            after_state={"is_active": False, "referenced_lines": ref_count},
            reason="Penonaktifan item terpakai transaksi (UC-01 2a)",
        )
        await db.commit()
        return {
            "status": "DEACTIVATED",
            "id": str(item_id),
            "message": f"Item '{item.canonical_description}' dirujuk oleh {ref_count} baris transaksi sehingga dinonaktifkan (UC-01 2a).",
        }

    await db.delete(item)
    await audit_service.log_event(
        db=db,
        entity_name="Item",
        entity_id=str(item_id),
        action="DELETE",
        actor=actor_name,
        before_state={"sku": item.sku, "canonical_description": item.canonical_description},
        reason="Penghapusan item katalog yang belum terpakai transaksi",
    )
    await db.commit()
    return {"status": "DELETED", "id": str(item_id), "message": "Item katalog berhasil dihapus."}


# 5. Units
@router.get("/units", response_model=List[UnitResponse])
async def list_units(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Unit).order_by(Unit.code.asc()))
    return result.scalars().all()


@router.post("/units", response_model=UnitResponse, status_code=status.HTTP_201_CREATED)
async def create_unit(payload: UnitCreate, db: AsyncSession = Depends(get_db)):
    dup = await db.execute(select(Unit).where(Unit.code == payload.code.strip()))
    if dup.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplikasi Entitas (UC-01 4b): Kode satuan '{payload.code}' sudah terdaftar.",
        )
    unit = Unit(**payload.model_dump())
    db.add(unit)
    await db.commit()
    await db.refresh(unit)
    return unit


@router.put("/units/{unit_id}", response_model=UnitResponse)
async def update_unit(unit_id: UUID, payload: UnitUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Unit).where(Unit.id == unit_id))
    unit = res.scalar_one_or_none()
    if not unit:
        raise HTTPException(status_code=404, detail="Satuan tidak ditemukan.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(unit, field, value)
    await db.commit()
    await db.refresh(unit)
    return unit


@router.delete("/units/{unit_id}")
async def delete_unit(unit_id: UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Unit).where(Unit.id == unit_id))
    unit = res.scalar_one_or_none()
    if not unit:
        raise HTTPException(status_code=404, detail="Satuan tidak ditemukan.")
    await db.delete(unit)
    await db.commit()
    return {"status": "DELETED", "id": str(unit_id), "message": "Satuan berhasil dihapus."}


# 5b. Budget Classifications (Kode Rekening & Kegiatan Anggaran BOS/BOP - FR-01 / UC-01)
@router.get("/budgets", response_model=List[BudgetClassificationResponse])
async def list_budgets(
    active_only: bool = Query(default=False),
    funding_scheme: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    query = select(BudgetClassification)
    if active_only:
        query = query.where(BudgetClassification.is_active == True)
    if funding_scheme:
        query = query.where(BudgetClassification.funding_scheme == funding_scheme.upper())
    res = await db.execute(query.order_by(BudgetClassification.fiscal_year.desc(), BudgetClassification.account_code.asc()))
    return res.scalars().all()


@router.post("/budgets", response_model=BudgetClassificationResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    payload: BudgetClassificationCreate,
    db: AsyncSession = Depends(get_db),
    actor_name: str = Depends(get_current_actor_name),
):
    if payload.account_code:
        dup = await db.execute(
            select(BudgetClassification).where(
                BudgetClassification.account_code == payload.account_code.strip(),
                BudgetClassification.fiscal_year == payload.fiscal_year,
                BudgetClassification.activity_code == payload.activity_code,
            )
        )
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplikasi Entitas (UC-01 4b): Kode rekening '{payload.account_code}' untuk kegiatan '{payload.activity_code}' tahun {payload.fiscal_year} sudah terdaftar.",
            )

    budget = BudgetClassification(**payload.model_dump())
    db.add(budget)
    await db.flush()
    await audit_service.log_event(
        db=db,
        entity_name="BudgetClassification",
        entity_id=str(budget.id),
        action="CREATE",
        actor=actor_name,
        after_state={"account_code": budget.account_code, "activity_name": budget.activity_name, "funding_scheme": budget.funding_scheme},
        reason="Penambahan kode rekening & kegiatan anggaran BOS/BOP",
    )
    await db.commit()
    await db.refresh(budget)
    return budget


@router.put("/budgets/{budget_id}", response_model=BudgetClassificationResponse)
async def update_budget(
    budget_id: UUID,
    payload: BudgetClassificationUpdate,
    db: AsyncSession = Depends(get_db),
    actor_name: str = Depends(get_current_actor_name),
):
    res = await db.execute(select(BudgetClassification).where(BudgetClassification.id == budget_id))
    budget = res.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="Data kode rekening anggaran tidak ditemukan.")

    before_state = {"account_code": budget.account_code, "activity_name": budget.activity_name, "is_active": budget.is_active}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(budget, field, value)

    await audit_service.log_event(
        db=db,
        entity_name="BudgetClassification",
        entity_id=str(budget.id),
        action="UPDATE",
        actor=actor_name,
        before_state=before_state,
        after_state={"account_code": budget.account_code, "activity_name": budget.activity_name, "is_active": budget.is_active},
        reason="Pembaruan kode rekening & kegiatan anggaran BOS/BOP",
    )
    await db.commit()
    await db.refresh(budget)
    return budget


@router.delete("/budgets/{budget_id}")
async def delete_or_deactivate_budget(
    budget_id: UUID,
    db: AsyncSession = Depends(get_db),
    actor_name: str = Depends(get_current_actor_name),
):
    res = await db.execute(select(BudgetClassification).where(BudgetClassification.id == budget_id))
    budget = res.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="Data kode rekening anggaran tidak ditemukan.")

    ref_count = (await db.execute(select(func.count(Package.id)).where(Package.budget_id == budget_id))).scalar() or 0
    if ref_count > 0:
        budget.is_active = False
        await audit_service.log_event(
            db=db,
            entity_name="BudgetClassification",
            entity_id=str(budget.id),
            action="DEACTIVATE",
            actor=actor_name,
            before_state={"is_active": True},
            after_state={"is_active": False, "referenced_packages": ref_count},
            reason="Penonaktifan kode rekening terpakai transaksi historis (UC-01 2a)",
        )
        await db.commit()
        return {
            "status": "DEACTIVATED",
            "id": str(budget_id),
            "message": f"Rekening '{budget.account_code}' dirujuk oleh {ref_count} paket sehingga dinonaktifkan (UC-01 2a).",
        }

    await db.delete(budget)
    await db.commit()
    return {"status": "DELETED", "id": str(budget_id), "message": "Kode rekening berhasil dihapus."}


# 5c. Funding Sources (Sumber Dana BOS / BOP)
@router.get("/funding-sources", response_model=List[FundingSourceResponse])
async def list_funding_sources(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(FundingSource).order_by(FundingSource.code.asc()))
    return res.scalars().all()


@router.post("/funding-sources", response_model=FundingSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_funding_source(payload: FundingSourceCreate, db: AsyncSession = Depends(get_db)):
    dup = await db.execute(select(FundingSource).where(FundingSource.code == payload.code.strip()))
    if dup.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplikasi Entitas (UC-01 4b): Kode sumber dana '{payload.code}' sudah terdaftar.",
        )
    fs = FundingSource(**payload.model_dump())
    db.add(fs)
    await db.commit()
    await db.refresh(fs)
    return fs


@router.put("/funding-sources/{source_id}", response_model=FundingSourceResponse)
async def update_funding_source(source_id: UUID, payload: FundingSourceUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(FundingSource).where(FundingSource.id == source_id))
    fs = res.scalar_one_or_none()
    if not fs:
        raise HTTPException(status_code=404, detail="Sumber dana tidak ditemukan.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(fs, field, value)
    await db.commit()
    await db.refresh(fs)
    return fs


@router.delete("/funding-sources/{source_id}")
async def delete_funding_source(source_id: UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(FundingSource).where(FundingSource.id == source_id))
    fs = res.scalar_one_or_none()
    if not fs:
        raise HTTPException(status_code=404, detail="Sumber dana tidak ditemukan.")
    ref_count = (await db.execute(select(func.count(Package.id)).where(Package.funding_source_id == source_id))).scalar() or 0
    if ref_count > 0:
        fs.is_active = False
        await db.commit()
        return {"status": "DEACTIVATED", "id": str(source_id), "message": "Sumber dana dirujuk paket transaksi sehingga dinonaktifkan (UC-01 2a)."}
    await db.delete(fs)
    await db.commit()
    return {"status": "DELETED", "id": str(source_id), "message": "Sumber dana berhasil dihapus."}


# 5d. Package Profiles & Document Templates Registry (FR-03 / UC-03)
@router.get("/package-profiles", response_model=List[PackageProfileResponse])
async def list_package_profiles(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(PackageProfile).order_by(PackageProfile.code.asc()))
    return res.scalars().all()


@router.put("/package-profiles/{profile_id}", response_model=PackageProfileResponse)
async def update_package_profile(
    profile_id: UUID,
    payload: PackageProfileUpdate,
    db: AsyncSession = Depends(get_db),
    actor_name: str = Depends(get_current_actor_name),
):
    res = await db.execute(select(PackageProfile).where(PackageProfile.id == profile_id))
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil paket dokumen tidak ditemukan.")
    before_docs = list(profile.required_doc_codes or [])
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    await audit_service.log_event(
        db=db,
        entity_name="PackageProfile",
        entity_id=str(profile.id),
        action="UPDATE",
        actor=actor_name,
        before_state={"required_doc_codes": before_docs},
        after_state={"required_doc_codes": profile.required_doc_codes},
        reason=f"Konfigurasi daftar dokumen wajib/opsional skema {profile.code} (FR-03)",
    )
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/templates", response_model=List[TemplateRegistryResponse])
async def list_templates(
    funding_scheme: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    query = select(TemplateRegistry)
    if funding_scheme and funding_scheme.upper() != "ALL":
        query = query.where(TemplateRegistry.funding_scheme.in_(["ALL", funding_scheme.upper()]))
    res = await db.execute(query.order_by(TemplateRegistry.doc_code.asc()))
    return res.scalars().all()


@router.patch("/templates/{doc_code}/config", response_model=TemplateRegistryResponse)
async def update_template_config(
    doc_code: str,
    payload: TemplateConfigUpdate,
    db: AsyncSession = Depends(get_db),
    actor_name: str = Depends(get_current_actor_name),
):
    code = doc_code.upper()
    res = await db.execute(select(TemplateRegistry).where(TemplateRegistry.doc_code == code))
    tmpl = res.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail=f"Template '{code}' tidak ditemukan.")

    before_state = {"is_mandatory": tmpl.is_mandatory, "funding_scheme": tmpl.funding_scheme, "is_active": tmpl.is_active}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tmpl, field, value)

    await audit_service.log_event(
        db=db,
        entity_name="TemplateRegistry",
        entity_id=str(tmpl.id),
        action="UPDATE",
        actor=actor_name,
        before_state=before_state,
        after_state={"is_mandatory": tmpl.is_mandatory, "funding_scheme": tmpl.funding_scheme, "is_active": tmpl.is_active},
        reason=f"Pembaruan konfigurasi kewajiban dokumen {code} (UC-03)",
    )
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


@router.post("/templates/{doc_code}/validate", response_model=TemplateValidationResult)
async def validate_template_file(
    doc_code: str,
    file: Optional[UploadFile] = File(default=None),
    db: AsyncSession = Depends(get_db),
):
    code = doc_code.upper()
    if code not in DOCUMENT_MAP:
        raise HTTPException(status_code=404, detail=f"Kode dokumen '{code}' tidak valid.")

    res = await db.execute(select(TemplateRegistry).where(TemplateRegistry.doc_code == code))
    tmpl = res.scalar_one_or_none()
    req_tokens = (tmpl.required_tokens if tmpl else []) or []

    if file is not None:
        filename = file.filename or f"{code}.docx"
        file_bytes = await file.read()
    else:
        eff_path = get_effective_template_path(code)
        filename = eff_path.name
        file_bytes = eff_path.read_bytes()

    result = extract_and_validate_docx_bytes(code, filename, file_bytes, req_tokens)
    return result


@router.post("/templates/{doc_code}/upload", response_model=TemplateRegistryResponse)
async def upload_and_activate_template(
    doc_code: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    actor_name: str = Depends(get_current_actor_name),
):
    """UC-03: Validates .docx Jinja2 tokens (rejecting on Alur 4a unknown/broken syntax),
    increments version, and activates new template without altering historical artifacts."""
    code = doc_code.upper()
    if code not in DOCUMENT_MAP:
        raise HTTPException(status_code=404, detail=f"Kode dokumen '{code}' tidak valid.")

    filename = file.filename or f"{code}.docx"
    if not filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Format acuan template harus berupa berkas Microsoft Word (.docx).")

    res = await db.execute(select(TemplateRegistry).where(TemplateRegistry.doc_code == code))
    tmpl = res.scalar_one_or_none()
    req_tokens = (tmpl.required_tokens if tmpl else []) or []

    file_bytes = await file.read()
    validation = extract_and_validate_docx_bytes(code, filename, file_bytes, req_tokens)
    if not validation["is_valid"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=validation["message"],
        )

    new_version = (tmpl.version + 1) if tmpl else 1
    active_path, sha256_hash = save_and_activate_template(code, filename, file_bytes, new_version)

    before_state = {"version": tmpl.version, "filename": tmpl.filename, "sha256_hash": tmpl.sha256_hash} if tmpl else None
    if tmpl:
        tmpl.version = new_version
        tmpl.filename = filename
        tmpl.file_path = str(active_path)
        tmpl.sha256_hash = sha256_hash
        tmpl.detected_tokens = validation["detected_tokens"]
        tmpl.uploaded_by = actor_name
    else:
        tmpl = TemplateRegistry(
            doc_code=code,
            doc_name=code,
            funding_scheme="ALL",
            is_mandatory=True,
            version=new_version,
            filename=filename,
            file_path=str(active_path),
            sha256_hash=sha256_hash,
            required_tokens=req_tokens,
            detected_tokens=validation["detected_tokens"],
            is_active=True,
            uploaded_by=actor_name,
        )
        db.add(tmpl)
        await db.flush()

    await audit_service.log_event(
        db=db,
        entity_name="TemplateRegistry",
        entity_id=str(tmpl.id),
        action="UPLOAD_TEMPLATE",
        actor=actor_name,
        before_state=before_state,
        after_state={
            "doc_code": code,
            "version": new_version,
            "filename": filename,
            "sha256_hash": sha256_hash,
            "detected_tokens": validation["detected_tokens"],
        },
        reason=f"Aktivasi versi template {code} v{new_version} (UC-03)",
    )
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


@router.post("/templates/{doc_code}/simulate")
async def simulate_template(
    doc_code: str,
    download: bool = Query(default=False),
    file: Optional[UploadFile] = File(default=None),
):
    """UC-03 Step 5: Generates preview simulation of merged template using sample transaction context."""
    code = doc_code.upper()
    if code not in DOCUMENT_MAP:
        raise HTTPException(status_code=404, detail=f"Kode dokumen '{code}' tidak valid.")

    custom_bytes = await file.read() if file is not None else None
    try:
        sim = render_simulation_preview(code, custom_bytes=custom_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Gagal menjalankan simulasi penggabungan template {code}: {exc}",
        )

    if download:
        return Response(
            content=sim["docx_bytes"],
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="SIMULASI_{code}.docx"'},
        )

    return {
        "doc_code": sim["doc_code"],
        "sample_context_summary": sim["sample_context_summary"],
        "paragraphs": sim["paragraphs"],
        "tables": sim["tables"],
    }


# 6. Tax Policies
@router.get("/tax-policies", response_model=List[TaxPolicyVersionResponse])
async def list_tax_policies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaxPolicyVersion))
    policies = result.scalars().all()
    if not policies:
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
        db.add_all([p_ppn, p_pph])
        await db.commit()
        result = await db.execute(select(TaxPolicyVersion))
        policies = result.scalars().all()
    return policies


@router.post("/tax-policies", response_model=TaxPolicyVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_tax_policy(payload: TaxPolicyVersionCreate, db: AsyncSession = Depends(get_db)):
    policy = TaxPolicyVersion(**payload.model_dump())
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


# 7. Number Counters
@router.get("/counters", response_model=List[NumberCounterResponse])
async def list_number_counters(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NumberCounter))
    return result.scalars().all()
