# Rencana Implementasi Integrasi Google Drive — PCI Procurement Automation

Dokumen ini merupakan rencana teknis dan arsitektural untuk mengimplementasikan fitur integrasi **Google Drive** pada aplikasi **PCI Procurement Automation** berdasarkan spesifikasi pada **`CSIM801012-KELOMPOK C3.docx`** (Skenario 3 — Complete FR, Sprint 7 / WBS 3.7) serta klarifikasi alur bisnis aktual.

---

## 1. Referensi Kebutuhan & Aturan Bisnis

| Kode / Bagian | Deskripsi Kebutuhan (`CSIM801012-KELOMPOK C3.docx` & Klarifikasi) | Implikasi Implementasi |
| :--- | :--- | :--- |
| **Aktor Eksternal: Google Drive Workspace API** | Repositori cloud storage terpusat untuk mengorganisasi dan mengarsipkan bundel dokumen final hasil *generate*. | Klien asinkron Google Drive REST API v3 ([`google_drive_service.py`](file:///d:/Personal/Website/AKPSI-T1/pci-procurement-automation/backend/app/services/google_drive_service.py)) menggunakan autentikasi JWT RS256 Service Account (`httpx` + `cryptography`) dengan dukungan *My Drive* bersama maupun *Shared Drive* (`supportsAllDrives=True`). |
| **Penyimpanan Lokal saat Generate** | Paket 13 dokumen hasil generate (`D01`–`D13` DOCX/PDF, `XLSX`, `MERGED_PDF`, `ZIP`) **tidak** langsung diunggah ke Google Drive saat proses generate. | `generation_worker.py` menyimpan seluruh berkas ke storage lokal dan menandai `Artifact.archive_status = "PENDING"`. |
| **Gerbang Status `APPROVED`** | Paket pengadaan hanya boleh disimpan ke Google Drive apabila statusnya sudah **Disetujui (`APPROVED` / `ISSUED`)**; dokumen hasil generate dalam status `APPROVED`/`ISSUED` tidak memakai watermark `DRAFT`. | Endpoint unggah menolak status selain `APPROVED`/`ISSUED` (HTTP 400). `generation_worker.py` mengecek `revision.status` dan `package.status` agar revisi `APPROVED` mencetak dokumen bersih. |
| **Tombol Unggah Admin / SysAdmin + Progress Report** | Setelah `APPROVED`, peran **Admin (`ADMINISTRATION`)** atau **SysAdmin (`SYSTEM_ADMINISTRATOR`)** dapat menekan tombol unggah ke Google Drive dengan laporan progres *real-time*. | RBAC di backend (`ALLOWED_UPLOAD_ROLES = {"ADMINISTRATION", "SYSTEM_ADMINISTRATOR"}`, HTTP 403 untuk peran lain) serta panel progres *real-time* (persentase, `uploaded_files / total_files`, tahap 4 langkah) di [`tab-documents.tsx`](file:///d:/Personal/Website/AKPSI-T1/pci-procurement-automation/frontend/src/components/packages/tabs/tab-documents.tsx). |
| **Timpa Berkas pada Revisi (`Overwrite`)** | Apabila terdapat revisi baru atau unggah ulang untuk sekolah/tahun/triwulan yang sama, berkas lama di Google Drive ditimpa (*overwrite*) tanpa membuat duplikat. | Nama file ZIP dinormalisasi menjadi `00_PAKET_ARSIP_LENGKAP.zip`; unggah memeriksa file eksisting di folder target lalu melakukan `PATCH` (dan membersihkan duplikat jika ada). `ArchiveRecord` revisi lama ditandai `SUPERSEDED`. |
| **NFR-10 & Mitigasi Kuota My Drive** | Retensi & integritas arsip (`sha256_hash`), pengecekan kesehatan & kuota Drive. | Endpoint `GET /api/v1/archive/health`. Jika folder *My Drive* personal dengan Service Account terkena `403 storageQuotaExceeded` (`limit=0`), tersedia *fallback* pencatatan entri metadata 0-byte agar struktur folder & tautan tetap terbentuk. |
| **FR-09 & UC-09 (Immutable Audit Trail)** | Seluruh aktivitas sinkronisasi dan perubahan status arsip wajib tercatat dalam `AuditLog` (*append-only*). | Catat event `ARCHIVE_SYNCED` dan `ARCHIVE_FAILED` via `audit_service.log_event()`. |

---

## 2. Arsitektur Folder Hierarkis (4 Level)

Sesuai klarifikasi kebutuhan struktur folder pada root folder `backend/credentials/gdrive-folder-id.txt`:

```text
<GOOGLE_DRIVE_ROOT_FOLDER_ID>/ (pci-storage)
└── {Nama_Sekolah}/                    # Lv1 (Sekolah), contoh: SD NEGERI KEBON KOSONG 09
    └── {Tahun_Anggaran}/              # Lv2 (Year), contoh: 2026
        └── Triwulan {Q}/              # Lv3 (Triwulan), contoh: Triwulan 2
            ├── 00_PAKET_PENGADAAN.xlsx        # Lv4 (The Files)
            ├── 00_PAKET_LENGKAP.pdf
            ├── 00_PAKET_ARSIP_LENGKAP.zip
            ├── D01_HPS.docx
            ├── D01_HPS.pdf
            └── ... (D02 s.d. D13 DOCX & PDF)
```

Setiap level folder (`Lv1` → `Lv2` → `Lv3`) dibuat secara **idempoten**: mencari folder eksisting berdasarkan `name` dan `parents` (`trashed = false`); jika belum ada barulah membuat folder baru.

---

## 3. Ringkasan Implementasi

1. **Konfigurasi & Keamanan Kredensial**:
   - [`.gitignore`](file:///d:/Personal/Website/AKPSI-T1/pci-procurement-automation/.gitignore): mengecualikan `backend/credentials/`, `*.service-account*.json`, dan `*gdrive*.json`.
   - [`docker-compose.yml`](file:///d:/Personal/Website/AKPSI-T1/pci-procurement-automation/docker-compose.yml): mount volume `./backend/credentials:/app/credentials:ro` dan variabel `DRIVE_SYNC_*` / `GOOGLE_DRIVE_*`.
   - [`backend/app/config.py`](file:///d:/Personal/Website/AKPSI-T1/pci-procurement-automation/backend/app/config.py): pembacaan otomatis `gdrive-service-account.json` dan `gdrive-folder-id.txt` dengan mode `auto` / `live` / `mock`.

2. **Model Database & Skema API**:
   - [`backend/app/models/archive.py`](file:///d:/Personal/Website/AKPSI-T1/pci-procurement-automation/backend/app/models/archive.py): penambahan `drive_folder_url`, `progress_percent`, `current_step`, `uploaded_files`, `total_files`, `total_bytes`.
   - [`backend/app/models/generation.py`](file:///d:/Personal/Website/AKPSI-T1/pci-procurement-automation/backend/app/models/generation.py): penambahan `drive_file_id`, `drive_web_view_link`, `drive_synced_at`.
   - [`backend/app/main.py`](file:///d:/Personal/Website/AKPSI-T1/pci-procurement-automation/backend/app/main.py): migrasi kolom idempoten pada `_sync_ensure_schema_columns`.
   - [`backend/app/schemas/archive.py`](file:///d:/Personal/Website/AKPSI-T1/pci-procurement-automation/backend/app/schemas/archive.py) & [`backend/app/schemas/generation.py`](file:///d:/Personal/Website/AKPSI-T1/pci-procurement-automation/backend/app/schemas/generation.py): ekspos field tautan Drive & metrik progres.

3. **Layanan Backend & Worker**:
   - [`backend/app/services/generation_worker.py`](file:///d:/Personal/Website/AKPSI-T1/pci-procurement-automation/backend/app/services/generation_worker.py): set `archive_status="PENDING"` dan perbaiki penentuan `is_draft` untuk status `APPROVED`/`ISSUED`.
   - [`backend/app/services/google_drive_service.py`](file:///d:/Personal/Website/AKPSI-T1/pci-procurement-automation/backend/app/services/google_drive_service.py): autentikasi Service Account, pembuatan hierarki 3-level folder, upload/overwrite berkas, dan pengecekan kesehatan `/archive/health`.
   - [`backend/app/services/drive_sync.py`](file:///d:/Personal/Website/AKPSI-T1/pci-procurement-automation/backend/app/services/drive_sync.py): `execute_revision_drive_upload()` dengan pembaruan progres per-berkas dan pencatatan `AuditEvent`.
   - [`backend/app/api/v1/archive.py`](file:///d:/Personal/Website/AKPSI-T1/pci-procurement-automation/backend/app/api/v1/archive.py):
     - `GET /api/v1/revisions/{revision_id}/archive`
     - `POST /api/v1/revisions/{revision_id}/archive/upload`
     - `GET /api/v1/archive/health`

4. **Antarmuka Pengguna (Next.js)**:
   - [`frontend/src/types/documents.ts`](file:///d:/Personal/Website/AKPSI-T1/pci-procurement-automation/frontend/src/types/documents.ts) & [`frontend/src/lib/api-client.ts`](file:///d:/Personal/Website/AKPSI-T1/pci-procurement-automation/frontend/src/lib/api-client.ts)
   - [`frontend/src/app/(dashboard)/packages/[id]/page.tsx`](file:///d:/Personal/Website/AKPSI-T1/pci-procurement-automation/frontend/src/app/(dashboard)/packages/%5Bid%5D/page.tsx)
   - [`frontend/src/components/packages/tabs/tab-documents.tsx`](file:///d:/Personal/Website/AKPSI-T1/pci-procurement-automation/frontend/src/components/packages/tabs/tab-documents.tsx): kartu **Integrasi Penyimpanan Google Drive**, pratinjau folder 4-level, gerbang status `APPROVED`, tombol unggah khusus Admin/SysAdmin, progress bar & 4-tahap sinkronisasi, tombol **Buka Folder Google Drive**, serta lencana tautan `Drive` di tabel dokumen.

5. **Pengujian**:
   - [`backend/tests/test_drive_sync.py`](file:///d:/Personal/Website/AKPSI-T1/pci-procurement-automation/backend/tests/test_drive_sync.py): pengujian unit/integrasi untuk gerbang `APPROVED`, RBAC Admin/SysAdmin, struktur folder 4-level, *overwrite* pada revisi baru, serta audit log.
