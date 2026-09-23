from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.masters import (
    Company,
    School,
    OfficialAppointment,
    Item,
    Unit,
    TaxPolicyVersion,
    NumberCounter,
)
from app.schemas.masters import (
    CompanyCreate,
    CompanyResponse,
    SchoolCreate,
    SchoolResponse,
    OfficialAppointmentCreate,
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
    company = Company(**payload.model_dump())
    db.add(company)
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
