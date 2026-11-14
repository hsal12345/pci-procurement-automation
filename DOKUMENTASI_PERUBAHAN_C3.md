# Dokumentasi Penyelarasan Aplikasi terhadap Dokumen `CSIM801012-KELOMPOK C3.docx`

Dokumen ini mencatat seluruh penambahan dan penyesuaian pada aplikasi **PCI Procurement Automation** agar selaras dengan kebutuhan sistem pada dokumen `CSIM801012-KELOMPOK C3.docx` (Skenario 3).

## Prinsip Pendekatan

1. **Pertahankan Fitur Eksisting**: Fitur yang sudah ada di aplikasi dan tidak dibahas dalam dokumen tetap dipertahankan tanpa dihapus atau diubah secara radikal.
2. **Penambahan Terfokus**: Fitur yang dibutuhkan dokumen namun belum tersedia atau belum lengkap ditambahkan secara inkremental pada backend maupun frontend.
3. **Tanpa Perubahan Radikal**: Pola arsitektur FastAPI + SQLAlchemy (backend) dan Next.js 14 App Router (frontend) tetap dipertahankan.
4. **Integrasi Google Drive Ditunda**: Mekanisme sinkronisasi/outbox yang terdekupel tetap dipertahankan tanpa mengaktifkan koneksi live Google Drive API karena kredensial/key belum dikonfigurasi.

---

## Pemetaan Kebutuhan Utama (FR & UC)

| Area | Cakupan Implementasi | Lokasi Utama |
| :--- | :--- | :--- |
| **FR-01 / UC-01** (Master Data & Penonaktifan Lunak) | Penambahan atribut katalog & anggaran (`kbli`, `reference_price`, `is_active`, `funding_scheme`), pengecekan duplikasi NPSN/SKU/rekening (Flow 4b), serta soft-deactivation (`is_active = false`) ketika master data telah direferensikan oleh transaksi (Flow 2a). | `backend/app/models/masters.py`, `backend/app/api/v1/masters.py`, `frontend/src/app/(dashboard)/catalog/page.tsx` |
| **FR-02 / Input Paket & Katalog** | Pemilihan sumber dana (`fund_source`), kegiatan & kode rekening belanja BOS/BOP (`budget_id`), serta pemilihan barang dari katalog master ke tabel item paket dengan pengisian otomatis SKU, KBLI, satuan, dan harga acuan. | `backend/app/schemas/packages.py`, `backend/app/api/v1/packages.py`, `frontend/src/components/packages/create-package-modal.tsx`, `frontend/src/components/packages/tabs/tab-items.tsx` |
| **FR-03 / UC-03** (Manajemen Profil Paket & Template SPJ) | Model `PackageProfile` & `TemplateRegistry` (`D01`–`D13`), konversi token placeholder termasuk alias Bahasa Indonesia (`nama_sekolah`, `npsn_sekolah`, `nama_perusahaan`, `nilai_kontrak`, `terbilang_kontrak`, `nomor_paket`, `tahun_anggaran`, `triwulan`), validasi sintaks Jinja2 & deteksi token tidak dikenal (Flow 4a), aktivasi template kustom di `storage/templates/active/`, dan pratinjau simulasi DOCX. | `backend/app/models/masters.py`, `backend/app/services/template_registry_service.py`, `backend/app/services/export/context_builder.py`, `backend/app/services/export/docx_generator.py`, `frontend/src/app/(dashboard)/templates/page.tsx` |
| **Kronologi Hari Libur Nasional (BR12)** | Penambahan daftar hari libur nasional Indonesia (2025–2026) pada rule kronologi backend maupun helper tanggal frontend untuk menandai tanggal jatuh pada akhir pekan/hari libur sebagai peringatan BR12 dan memperhitungkannya dalam perhitungan hari kerja. | `backend/app/core/rules/chronology.py`, `frontend/src/components/packages/tabs/tab-dates-numbers.tsx` |
| **UC-10 / Pelacakan Logistik** | Input `No. Resi / Surat Jalan (UC-10)` (`delivery_reference`) serta penegakan validasi kronologi logistik agar `receipt_date` tidak mendahului `dispatch_date` maupun tanggal `PESANAN.event_date` (Flow 4a, HTTP 422 di backend dan blokir validasi di UI). | `backend/app/services/logistics_service.py`, `frontend/src/components/packages/tabs/tab-logistics.tsx` |
| **UC-09 / Portal Laporan Jejak Audit** | Endpoint pencarian multi-kriteria (`entity_id`, `entity_name`, `action`, `actor`, `date_from`, `date_to`, `q`, `limit`), tampilan diff before/after via `AuditDiffPanel`, serta ekspor laporan ke CSV dan JSON. | `backend/app/api/v1/audit.py`, `frontend/src/components/audit/audit-diff-viewer.tsx`, `frontend/src/components/packages/tabs/tab-audit.tsx`, `frontend/src/app/(dashboard)/audit/page.tsx` |
| **Bab 5.3 / Ringkasan Eksekutif & Filter Paket** | Penambahan 4 kartu KPI eksekutif (`Total Bundel SPJ`, `Menunggu Persetujuan`, `Disetujui & Terbit`, `Efisiensi Waktu Kerja` dibanding baseline manual 50 menit) serta filter `fundSourceFilter` dan `quarterFilter` pada daftar paket. | `frontend/src/app/(dashboard)/packages/page.tsx` |

---

## Ringkasan Perubahan Backend

1. **Models & Exports**
   - `backend/app/models/masters.py`:
     - Menambahkan kolom `kbli`, `reference_price`, dan `is_active` pada model `Item`.
     - Menambahkan kolom `funding_scheme` dan `is_active` pada model `BudgetClassification`.
     - Menambahkan model `TemplateRegistry` (`doc_code`, `doc_name`, `funding_scheme`, `is_mandatory`, `version`, `filename`, `file_path`, `sha256_hash`, `required_tokens`, `detected_tokens`, `is_active`, `uploaded_by`).
   - `backend/app/models/__init__.py`:
     - Mengekspor `TemplateRegistry` pada import dan `__all__`.

2. **Schemas**
   - `backend/app/schemas/masters.py`:
     - Memperbarui/menambahkan skema `ItemBase`, `ItemCreate`, `ItemUpdate`, `ItemPriceUpdate`, `ItemResponse`, `UnitUpdate`, `BudgetClassificationBase`, `BudgetClassificationCreate`, `BudgetClassificationUpdate`, `BudgetClassificationResponse`, `FundingSourceBase`, `FundingSourceCreate`, `FundingSourceUpdate`, `FundingSourceResponse`, `PackageProfileResponse`, `PackageProfileUpdate`, `TemplateRegistryResponse`, `TemplateConfigUpdate`, dan `TemplateValidationResult`.
   - `backend/app/schemas/packages.py`:
     - Menambahkan field `fund_source` pada `PackageCreate`.

3. **Services & Business Rules**
   - `backend/app/services/template_registry_service.py` *(file baru)*:
     - Menyediakan `KNOWN_ROOT_TOKENS`, `build_sample_context`, `extract_and_validate_docx_bytes` (normalisasi tag Jinja2 `{%tr`, `{%tc`, `{%p`, `{%r`, validasi sintaks, serta penolakan token tidak dikenal sesuai UC-03 Flow 4a), `save_and_activate_template`, `get_effective_template_path`, dan `render_simulation_preview`.
   - `backend/app/services/export/context_builder.py`:
     - Menambahkan alias token ringkas Bahasa Indonesia (`nama_sekolah`, `npsn_sekolah`, `nama_perusahaan`, `nilai_kontrak`, `terbilang_kontrak`, `nomor_paket`, `tahun_anggaran`, `triwulan`).
   - `backend/app/services/export/docx_generator.py`:
     - Menambahkan `ACTIVE_TEMPLATES_DIR` dan `resolve_template_path()` agar template `.docx` aktif pada `storage/templates/active/` diprioritaskan dengan fallback ke `TEMPLATES_DIR`.
   - `backend/app/services/logistics_service.py`:
     - Memuat `PackageRevision.events` dan menegakkan UC-10 Flow 4a (mengembalikan HTTP 422 jika `receipt_date < dispatch_date` atau `receipt_date < PESANAN.event_date`).
   - `backend/app/core/rules/chronology.py`:
     - Menambahkan `INDONESIAN_NATIONAL_HOLIDAYS` (2025–2026) serta memperbarui `validate_br12_holiday_or_unusual_date` agar mengeluarkan BR12 `WARNING` pada hari libur nasional selain akhir pekan.

4. **API Routers & Startup Lifecycle**
   - `backend/app/main.py`:
     - Menambahkan `_ensure_schema_columns` (perintah `ALTER TABLE` idempoten untuk `items`, `budget_classifications`, dan `funding_sources`) serta auto-seeding saat startup untuk `Unit`, `FundingSource`, `BudgetClassification`, `Item`, `PackageProfile`, dan `TemplateRegistry`.
   - `backend/app/api/v1/masters.py`:
     - Menambahkan pengecekan duplikasi NPSN/SKU/rekening (UC-01 Flow 4b).
     - Menambahkan endpoint soft-deactivation `DELETE /schools/{id}`, `DELETE /items/{id}`, `DELETE /budgets/{id}`, dan `DELETE /funding-sources/{id}` ketika sudah terhubung dengan transaksi (UC-01 Flow 2a).
     - Menambahkan CRUD lengkap untuk `/items` (termasuk `PATCH /items/{item_id}/price`), `/units`, `/budgets`, `/funding-sources`, `GET/PUT /package-profiles`, serta `/templates` (`GET`, `PATCH /{doc_code}/config`, `POST /{doc_code}/validate`, `POST /{doc_code}/upload`, `POST /{doc_code}/simulate`).
   - `backend/app/api/v1/audit.py`:
     - Memperbarui `GET /audit` dan `GET /audit/events` dengan filter multi-kriteria UC-09 (`entity_id`, `entity_name`, `action`, `actor`, `date_from`, `date_to`, `q`, `limit`).
   - `backend/app/api/v1/packages.py`:
     - Menyelesaikan pemetaan `funding_source_id` dari `FundingSource.code` berdasarkan `fund_source` saat pembuatan paket dan menambahkan helper `_attach_package_computed_fields` untuk mengisi `fund_source`.

---

## Ringkasan Perubahan Frontend

1. **API Client & Navigasi**
   - `frontend/src/lib/api-client.ts`:
     - Memperbarui `getAuditEvents` dan `getSchools(activeOnly?)`.
     - Menambahkan fungsi API untuk `deleteSchool`, CRUD `items` + `updateItemPrice`, `units`, `budgets`, `fundingSources`, `getPackageProfiles`/`updatePackageProfile`, serta `getTemplates`/`updateTemplateConfig`/`validateTemplate`/`uploadTemplate`/`simulateTemplate`.
   - `frontend/src/components/layout/sidebar.tsx`:
     - Menambahkan menu navigasi `"Katalog & Anggaran"` (`/catalog`), `"Paket & Template SPJ"` (`/templates`), dan `"Portal Jejak Audit"` (`/audit`).

2. **Halaman Baru**
   - `frontend/src/app/(dashboard)/catalog/page.tsx` *(file baru)*:
     - Halaman Master Data dengan 3 tab: **Katalog Barang & Harga Acuan** (termasuk `updateHarga`), **Kode Rekening & Kegiatan BOS/BOP**, dan **Satuan & Sumber Dana**.
   - `frontend/src/app/(dashboard)/templates/page.tsx` *(file baru)*:
     - Halaman pengelolaan **Paket & Template SPJ** (`PackageProfile` BOS/BOP mandatory/optional toggles, tabel template `D01`–`D13`, modal Validate & Upload `.docx` dengan umpan balik UC-03 Flow 4a, serta modal Live Simulation Preview).
   - `frontend/src/app/(dashboard)/audit/page.tsx` *(file baru)*:
     - Halaman **Portal Jejak Audit** (UC-09) dengan filter multi-kriteria (`q`, `entity_name`, `action`, `date_from`, `date_to`), ekspansi diff baris via `AuditDiffPanel`, serta ekspor CSV dan JSON.

3. **Komponen & Halaman Eksisting yang Diperkaya**
   - `frontend/src/components/audit/audit-diff-viewer.tsx` *(file baru)*:
     - Komponen `AuditDiffPanel` bersama serta helper `downloadAuditCsv` dan `downloadAuditJson`.
   - `frontend/src/components/packages/tabs/tab-audit.tsx`:
     - Memperbaiki tampilan diff baris agar dapat diekspansi menggunakan `AuditDiffPanel`, menambah filter pencarian/aksi, dan tombol unduh CSV.
   - `frontend/src/components/packages/tabs/tab-items.tsx`:
     - Menambahkan dropdown `"+ Pilih dari Katalog Barang..."` untuk memasukkan item katalog beserta SKU/KBLI/satuan/`reference_price`.
   - `frontend/src/components/packages/create-package-modal.tsx`:
     - Memuat daftar `budgets` aktif, menambahkan pemilih `Kegiatan & Kode Rekening Belanja BOS/BOP`, dan meneruskan `fund_source` serta `budget_id` saat pembuatan paket.
   - `frontend/src/components/packages/tabs/tab-logistics.tsx`:
     - Menambahkan input `No. Resi / Surat Jalan (UC-10)` (`delivery_reference`) serta validasi sisi klien yang memblokir `receipt_date < dispatch_date`.
   - `frontend/src/components/packages/tabs/tab-dates-numbers.tsx`:
     - Menambahkan `INDONESIAN_NATIONAL_HOLIDAYS`, `isHolidayOrWeekend`, `addBusinessDays` yang memperhitungkan hari libur nasional, dan lencana peringatan BR12 hari libur/akhir pekan.
   - `frontend/src/app/(dashboard)/packages/page.tsx`:
     - Menambahkan 4 kartu KPI eksekutif (`Total Bundel SPJ`, `Menunggu Persetujuan`, `Disetujui & Terbit`, `Efisiensi Waktu Kerja` vs baseline manual 50 menit) serta dropdown `fundSourceFilter` dan `quarterFilter`.

---

## Status Integrasi Google Drive

Sesuai prinsip pendekatan pada proyek ini, **integrasi live Google Drive API masih ditunda** karena API key/kredensial belum diatur. Endpoint status dan arsitektur outbox sinkronisasi yang terdekupel tetap dipertahankan agar dapat dihubungkan di fase berikutnya tanpa mengubah alur pembuatan dokumen inti.

---

## Hasil Verifikasi Terakhir

- **Kompilasi Sintaks Backend** (`python -m py_compile` terhadap 13 berkas `.py` yang diubah/dibuat): **Lulus** (`PY_COMPILE_OK`, exit code `0`).
- **Pemeriksaan Tipe TypeScript Frontend** (`npx tsc --noEmit` di `frontend/`): **Lulus** (exit code `0`, tanpa error).
- **Build Produksi Next.js** (`npm run build` di `frontend/`): **Lulus** (exit code `0`, 17/17 halaman statis termasuk rute `/audit`, `/catalog`, `/templates`, `/packages`, dan rute dinamis `/packages/[id]` berhasil dikompilasi; hanya terdapat warning ESLint `no-unused-vars` / `no-img-element` bawaan).
- **Catatan Pengujian Runtime Backend (`pytest`)**: Suite tes pada `backend/tests/` belum dapat dijalankan pada mesin lingkungan saat ini karena interpreter Python yang tersedia tidak memiliki dependensi proyek terpasang (`fastapi`, `pytest`). Disarankan menjalankan `pytest` di dalam virtualenv proyek pada lingkungan deployment/pengembangan yang sudah terinstal dependensi `backend/requirements.txt`.
