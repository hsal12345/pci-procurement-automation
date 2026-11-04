from datetime import datetime
from pathlib import Path
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.database import get_db
from app.models.masters import (
    Company,
    CompanyOfficial,
    School,
    OfficialAppointment,
    Item,
    Unit,
    TaxPolicyVersion,
    NumberCounter,
)
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
    ItemResponse,
    UnitCreate,
    UnitResponse,
    TaxPolicyVersionCreate,
    TaxPolicyVersionResponse,
    NumberCounterResponse,
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
async def list_schools(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(School))
    return result.scalars().all()


@router.post("/schools", response_model=SchoolResponse, status_code=status.HTTP_201_CREATED)
async def create_school(payload: SchoolCreate, db: AsyncSession = Depends(get_db)):
    school = School(**payload.model_dump())
    db.add(school)
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
async def update_school(id: UUID, payload: SchoolUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(School).where(School.id == id))
    school = result.scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=404, detail="Data sekolah tidak ditemukan.")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(school, field, value)

    await db.commit()
    await db.refresh(school)
    return school


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


# 4. Items
@router.get("/items", response_model=List[ItemResponse])
async def list_items(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Item))
    return result.scalars().all()


@router.post("/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(payload: ItemCreate, db: AsyncSession = Depends(get_db)):
    item = Item(**payload.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


# 5. Units
@router.get("/units", response_model=List[UnitResponse])
async def list_units(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Unit))
    return result.scalars().all()


@router.post("/units", response_model=UnitResponse, status_code=status.HTTP_201_CREATED)
async def create_unit(payload: UnitCreate, db: AsyncSession = Depends(get_db)):
    unit = Unit(**payload.model_dump())
    db.add(unit)
    await db.commit()
    await db.refresh(unit)
    return unit


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
