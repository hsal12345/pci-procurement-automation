import asyncio
from datetime import date
from pathlib import Path
from sqlalchemy import select
from app.database import async_engine, AsyncSessionLocal, Base
import app.models  # noqa: F401
from app.models.masters import School, OfficialAppointment, Company, CompanyOfficial


async def seed():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    backend_dir = Path(__file__).resolve().parent
    default_school_kop = "/storage/uploads/letterheads/schools/kop_sekolah.png"
    default_company_kop = "/storage/uploads/letterheads/companies/kop_rekanan.png"
    has_school_kop = (backend_dir / default_school_kop.lstrip("/")).is_file()
    has_company_kop = (backend_dir / default_company_kop.lstrip("/")).is_file()

    async with AsyncSessionLocal() as session:
        # 1. School 1: SD NEGERI KEBON KOSONG 09
        sc_kk09 = (await session.execute(select(School).where(School.name.like("%KEBON KOSONG%")))).scalar_one_or_none()
        if not sc_kk09:
            sc_kk09 = School(
                name="SD NEGERI KEBON KOSONG 09",
                npsn="20101234",
                level="SD",
                address="Jl. Dakota V No. 12",
                subdistrict="Kemayoran",
                postal_code="10630",
                letterhead_path=default_school_kop if has_school_kop else None,
            )
            session.add(sc_kk09)
            await session.flush()
        elif has_school_kop and not sc_kk09.letterhead_path:
            sc_kk09.letterhead_path = default_school_kop

        # Seed officials for KK09
        offs_kk09 = (await session.execute(select(OfficialAppointment).where(OfficialAppointment.school_id == sc_kk09.id))).scalars().all()
        if not offs_kk09:
            session.add_all([
                OfficialAppointment(
                    school_id=sc_kk09.id,
                    role="KEPALA_SEKOLAH",
                    person_name="Drs. H. Mulyadi, M.Pd",
                    nip="196501011990031005",
                    position_sk_number="800/014/SK/2025",
                    valid_from=date(2025, 1, 1),
                ),
                OfficialAppointment(
                    school_id=sc_kk09.id,
                    role="BENDAHARA",
                    person_name="Siti Rahmawati, S.Pd",
                    nip="198005122008012015",
                    position_sk_number="800/015/SK/2025",
                    valid_from=date(2025, 1, 1),
                ),
                OfficialAppointment(
                    school_id=sc_kk09.id,
                    role="PENGURUS_BARANG",
                    person_name="Sulistiawati",
                    nip="197909092022212008",
                    position_sk_number="800/016/SK/2025",
                    valid_from=date(2025, 1, 1),
                ),
            ])
            print("Seeded officials for SD NEGERI KEBON KOSONG 09")
        else:
            for o in offs_kk09:
                if o.role == "KEPALA_SEKOLAH":
                    o.position_sk_number = "800/014/SK/2025"
                elif o.role == "BENDAHARA":
                    o.position_sk_number = "800/015/SK/2025"
                elif o.role == "PENGURUS_BARANG":
                    o.position_sk_number = "800/016/SK/2025"
            print("Updated officials SK for SD NEGERI KEBON KOSONG 09")

        # 2. School 2: SDN CEMPAKA PUTIH 01 (for testing school switching)
        sc_cp01 = (await session.execute(select(School).where(School.name.like("%CEMPAKA PUTIH%")))).scalar_one_or_none()
        if not sc_cp01:
            sc_cp01 = School(
                name="SDN CEMPAKA PUTIH BARAT 01",
                npsn="20104321",
                level="SD",
                address="Jl. Percetakan Negara IX No. 5",
                subdistrict="Cempaka Putih",
                postal_code="10520",
            )
            session.add(sc_cp01)
            await session.flush()

        offs_cp01 = (await session.execute(select(OfficialAppointment).where(OfficialAppointment.school_id == sc_cp01.id))).scalars().all()
        if not offs_cp01:
            session.add_all([
                OfficialAppointment(
                    school_id=sc_cp01.id,
                    role="KEPALA_SEKOLAH",
                    person_name="Dra. Hj. Nurjanah, M.Pd",
                    nip="196703151992032004",
                    position_sk_number="800/041/SK-DISDIK/2025",
                    valid_from=date(2025, 1, 1),
                ),
                OfficialAppointment(
                    school_id=sc_cp01.id,
                    role="BENDAHARA",
                    person_name="Rahmat Hidayat, S.E",
                    nip="198506202010011018",
                    position_sk_number="800/042/SK-DISDIK/2025",
                    valid_from=date(2025, 1, 1),
                ),
                OfficialAppointment(
                    school_id=sc_cp01.id,
                    role="PENGURUS_BARANG",
                    person_name="Tri Wahyuni, A.Md",
                    nip="199011122019032007",
                    position_sk_number="800/043/SK-DISDIK/2025",
                    valid_from=date(2025, 1, 1),
                ),
            ])
            print("Seeded officials for SDN CEMPAKA PUTIH BARAT 01")

        # 3. Company 1: CV. PUSTAKA CEMERLANG INDONESIA
        cp_pci = (await session.execute(select(Company).where(Company.legal_name.like("%PUSTAKA CEMERLANG%")))).scalar_one_or_none()
        if not cp_pci:
            cp_pci = Company(
                legal_name="CV. PUSTAKA CEMERLANG INDONESIA",
                npwp="02.456.789.0-034.000",
                address="Wisma Mitra Sunter Unit 3-03, Jl. Yos Sudarso Kav. 89",
                subdistrict="Sunter Jaya",
                city="Jakarta Utara",
                postal_code="14350",
                email="pustakacemerlang@gmail.com",
                phone="021-65301234",
                bank_name="Bank DKI",
                bank_account_number="10121008899",
                bank_account_holder="CV. Pustaka Cemerlang Indonesia",
                director_name="Bambang Solifian",
                director_title="Direktur",
                director_sk_number="Akta Notaris No. 12 Th 2020",
                logo_path=default_company_kop if has_company_kop else None,
            )
            session.add(cp_pci)
            await session.flush()
            session.add(CompanyOfficial(
                company_id=cp_pci.id,
                person_name="Bambang Solifian",
                role="DIREKTUR",
                role_title="Direktur",
                position_sk_number="Akta Notaris No. 12 Th 2020",
            ))
            print("Seeded CV. PUSTAKA CEMERLANG INDONESIA")
        else:
            cp_pci.director_sk_number = "Akta Notaris No. 12 Th 2020"
            if has_company_kop and not cp_pci.logo_path:
                cp_pci.logo_path = default_company_kop
            cp_off = (await session.execute(select(CompanyOfficial).where(CompanyOfficial.company_id == cp_pci.id))).scalar_one_or_none()
            if not cp_off:
                session.add(CompanyOfficial(
                    company_id=cp_pci.id,
                    person_name=cp_pci.director_name or "Bambang Solifian",
                    role="DIREKTUR",
                    role_title="Direktur",
                    position_sk_number="Akta Notaris No. 12 Th 2020",
                ))
            else:
                cp_off.position_sk_number = "Akta Notaris No. 12 Th 2020"
            print("Updated CV. PUSTAKA CEMERLANG INDONESIA")

        # 4. Company 2: PT. SARANA EDUKASI NUSANTARA (for testing company switching)
        cp_sen = (await session.execute(select(Company).where(Company.legal_name.like("%SARANA EDUKASI%")))).scalar_one_or_none()
        if not cp_sen:
            cp_sen = Company(
                legal_name="PT. SARANA EDUKASI NUSANTARA",
                npwp="02.987.654.3-021.000",
                address="Komp. Perkantoran Graha Niaga Lt. 3 No. 15",
                city="Jakarta Pusat",
                director_name="Ir. H. Gunawan Wibisono",
                director_title="Direktur Utama",
                director_sk_number="Akta Notaris No. 88 Th 2021",
                bank_name="Bank Mandiri",
                bank_account_number="1200098765432",
                bank_account_holder="PT Sarana Edukasi Nusantara",
            )
            session.add(cp_sen)
            await session.flush()
            session.add(CompanyOfficial(
                company_id=cp_sen.id,
                person_name="Ir. H. Gunawan Wibisono",
                role="DIREKTUR",
                role_title="Direktur Utama",
                position_sk_number="Akta Notaris No. 88 Th 2021",
            ))
            print("Seeded PT. SARANA EDUKASI NUSANTARA")

        await session.commit()
        print("Database seeding completed successfully.")


if __name__ == "__main__":
    asyncio.run(seed())

