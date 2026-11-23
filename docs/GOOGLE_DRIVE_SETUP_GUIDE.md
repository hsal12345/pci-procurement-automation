# Panduan Persiapan & Konfigurasi Google Drive API (Untuk Pengguna / Admin)

Panduan ini menjelaskan langkah-langkah yang perlu Anda lakukan untuk mendapatkan **Google Drive API JSON Key**, menyiapkan folder arsip di Google Drive, dan menghubungkannya ke aplikasi **PCI Procurement Automation**.

> [!IMPORTANT]
> **Catatan Penting Mengenai Akun Google (Personal Gmail vs Google Workspace Shared Drive):**
> Secara default, **Service Account** tidak memiliki kuota penyimpanan Google Drive sendiri.
> - Jika Anda menggunakan **Google Workspace** (domain perusahaan/sekolah), buatlah **Shared Drive (Drive Bersama)** dan tambahkan Service Account sebagai **Content Manager / Pengelola Konten** — ini adalah cara yang direkomendasikan dan bebas masalah kuota.
> - Jika Anda hanya menggunakan **Gmail pribadi (`@gmail.com`)**, Service Account **tidak bisa** menjadi pemilik file baru di *My Drive* biasa (akan muncul error `403: Service Accounts do not have storage quota`). Untuk pengujian dengan Gmail pribadi, Anda perlu menggunakan **OAuth 2.0 Refresh Token** atau **Google Workspace Shared Drive**.

---

## Ringkasan Langkah yang Perlu Anda Lakukan

1. Membuat Project di **Google Cloud Console**.
2. Mengaktifkan **Google Drive API**.
3. Membuat **Service Account** dan mengunduh **JSON Key**.
4. Menyiapkan **Folder Induk Arsip** di Google Drive & mencatat **Folder ID**.
5. Membagikan Folder Induk tersebut ke **Email Service Account**.
6. Menempatkan file JSON Key & mengisi konfigurasi `.env` di proyek.

---

## Langkah 1: Buat Project di Google Cloud Console

1. Buka [Google Cloud Console](https://console.cloud.google.com/) dan login dengan akun Google yang akan mengelola integrasi.
2. Klik dropdown pemilih project di bagian kiri atas, lalu klik **New Project**.
3. Isi nama project, misalnya: `pci-procurement-drive-sync`.
4. Klik **Create**, lalu pastikan project baru tersebut sudah terpilih di bagian atas.

---

## Langkah 2: Aktifkan Google Drive API

1. Di menu navigasi kiri, buka **APIs & Services** → **Library**.
2. Pada kolom pencarian, ketik **`Google Drive API`**.
3. Klik hasil **Google Drive API** (dari Google), lalu klik tombol **Enable**.

---

## Langkah 3: Buat Service Account & Unduh File JSON Key

1. Di menu navigasi kiri, buka **APIs & Services** → **Credentials** (atau **IAM & Admin** → **Service Accounts**).
2. Klik **+ CREATE CREDENTIALS** → pilih **Service account**.
3. Isi detail Service Account:
   - **Service account name**: `pci-drive-sync-worker`
   - **Service account ID**: otomatis terisi (contoh: `pci-drive-sync-worker@pci-procurement-drive-sync.iam.gserviceaccount.com`)
   - **Description**: `Worker otomatis pengarsipan dokumen SPJ ke Google Drive`
4. Klik **Create and Continue** → pada bagian *Grant this service account access to project* dan *Grant users access*, Anda bisa langsung klik **Done** (tidak perlu role IAM khusus karena akses Drive diatur melalui sharing folder).
5. Pada daftar **Service Accounts**, klik email Service Account yang baru saja dibuat.
6. Buka tab **Keys** → klik **Add Key** → pilih **Create new key**.
7. Pilih format **JSON**, lalu klik **Create**.
8. File JSON akan otomatis terunduh ke komputer Anda (contoh nama: `pci-procurement-drive-sync-xxxx.json`).

> [!WARNING]
> **Jaga Kerahasiaan File JSON Key!**
> File JSON ini berisi `private_key` yang memberikan akses penuh ke folder Drive yang dibagikan. **Jangan pernah** mengunggah file ini ke GitHub/repository publik atau membagikannya di chat.

---

## Langkah 4: Siapkan Folder Arsip di Google Drive & Bagikan ke Service Account

### Opsi A (Direkomendasikan — Google Workspace Shared Drive)
1. Buka [Google Drive](https://drive.google.com/) menggunakan akun Google Workspace perusahaan.
2. Di panel kiri, klik **Shared drives** (Drive Bersama) → klik **+ New**.
3. Beri nama, misalnya: `Arsip SPJ PCI`.
4. Di dalam Shared Drive tersebut, klik **Manage members** (Kelola anggota).
5. Masukkan **email Service Account** (ambil dari nilai `"client_email"` di dalam file JSON, contoh: `pci-drive-sync-worker@....iam.gserviceaccount.com`).
6. Berikan peran **Content manager** (Pengelola konten) → klik **Send**.
7. Buka Shared Drive atau subfolder induk yang ingin dijadikan root arsip, lalu salin **Folder ID** dari URL browser:
   ```text
   https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz123456
                                          └────────── INI FOLDER ID ──────────┘
   ```

### Opsi B (Folder Biasa di My Drive Pribadi `@gmail.com` — Menggunakan OAuth 2.0)

> [!IMPORTANT]
> **Mengapa Service Account saja tidak cukup untuk My Drive pribadi (`@gmail.com`)?**
> Google Drive memberikan kuota **0 byte** kepada Service Account di My Drive pribadi, sehingga upload file penuh ditolak (`403 storageQuotaExceeded`) atau hanya menghasilkan file `0 byte` jika tanpa autentikasi user. Agar file SPJ terunggah dengan **ukuran penuh**, hubungkan akun Google pemilik folder via **OAuth 2.0**.

1. Buka [Google Drive](https://drive.google.com/) → buat folder induk (contoh: `pci-storage`), salin **Folder ID**-nya ke `backend/credentials/gdrive-folder-id.txt`.
2. Di **Google Cloud Console** project Anda (`pci-procurement-drive-sync`), buka **APIs & Services** → **OAuth consent screen**:
   - Pilih **External** → klik **Create**.
   - Isi App name (`PCI Procurement Drive Sync`), User support email & Developer email → **Save and Continue**.
   - Pada bagian **Scopes**, tambahkan `https://www.googleapis.com/auth/drive` → **Save and Continue**.
   - Pada bagian **Test users** (saat status *Testing*), tambahkan alamat Gmail pribadi Anda (pemilik folder `pci-storage`) → **Save and Continue**.
3. Buka **APIs & Services** → **Credentials** → **+ CREATE CREDENTIALS** → **OAuth client ID**:
   - **Application type**: pilih **Web application**.
   - **Name**: `PCI Procurement Local Backend`.
   - **Authorized redirect URIs**: klik **+ ADD URI** dan masukkan persis:
     ```text
     http://localhost:8000/api/v1/archive/oauth/callback
     ```
   - Klik **Create**, lalu klik **DOWNLOAD JSON**.
4. Simpan file JSON yang terunduh sebagai:
   ```text
   backend/credentials/gdrive-oauth-client.json
   ```
5. Buka salah satu paket berstatus `APPROVED` → tab **Dokumen** → klik tombol **"Hubungkan Akun Google (OAuth 2.0)"**, login dengan Gmail Anda, lalu izinkan akses. Token refresh akan otomatis tersimpan di `backend/credentials/gdrive-oauth-token.json` dan semua unggahan akan memakai kuota penuh akun Google Anda.

---

## Langkah 5: Simpan JSON Key & Konfigurasi Proyek

1. Struktur folder `backend/credentials/` di dalam proyek Anda:
   ```text
   pci-procurement-automation/
   └── backend/
       └── credentials/
           ├── gdrive-folder-id.txt          # ID folder induk Drive
           ├── gdrive-service-account.json   # Service Account (untuk Shared Drive / listing)
           ├── gdrive-oauth-client.json      # OAuth 2.0 Client ID (untuk My Drive pribadi)
           └── gdrive-oauth-token.json       # Terbuat otomatis setelah login OAuth di UI
   ```
2. Pastikan `backend/credentials/` sudah tercantum di file `.gitignore` agar tidak ikut ter-commit ke Git.
3. Variabel pada `docker-compose.yml` / `.env`:

   ```env
   # Google Drive Integration
   DRIVE_SYNC_ENABLED=true
   DRIVE_SYNC_MODE=live
   GOOGLE_DRIVE_CREDENTIALS_PATH=credentials/gdrive-service-account.json
   GOOGLE_DRIVE_FOLDER_ID_PATH=credentials/gdrive-folder-id.txt
   GOOGLE_DRIVE_OAUTH_CLIENT_PATH=credentials/gdrive-oauth-client.json
   GOOGLE_DRIVE_OAUTH_TOKEN_PATH=credentials/gdrive-oauth-token.json
   GOOGLE_DRIVE_OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/archive/oauth/callback
   ```

4. Volume mount pada service `backend` di `docker-compose.yml` (harus read-write agar `gdrive-oauth-token.json` bisa disimpan otomatis saat callback OAuth):
   ```yaml
   volumes:
     - pci_backend_storage:/app/storage
     - ./backend/credentials:/app/credentials
   ```

---

## Langkah 6: Verifikasi Setelah Implementasi Selesai

1. **Cek Kesehatan Koneksi & Kuota**:
   - Panggil `GET http://localhost:8000/api/v1/archive/health` (dengan token Bearer peran `ADMINISTRATION`, `FINANCE_DIRECTOR`, atau `SYSTEM_ADMINISTRATOR` — atau header `X-User-Role` saat pengujian lokal) dan pastikan `"connected": true` serta `"can_upload_binary": true`.
2. **Generate Lokal Terlebih Dahulu**:
   - Generate dokumen selalu menyimpan lokal (`29` berkas) terlebih dahulu dan **tidak** langsung mengunggah ke Google Drive.
3. **Uji Unggah Manual ke Google Drive (Status `APPROVED` / `ISSUED`, Peran Admin / SysAdmin)**:
   - Pastikan revisi berstatus `APPROVED` atau `ISSUED`, buka tab **6. Dokumen & Generator**, dan klik **"Unggah Paket ke Google Drive"**.
   - Pantau progress bar real-time (`10% -> 100%`) dan pastikan struktur folder `Lv1 ({Sekolah}) -> Lv2 ({Tahun}) -> Lv3 (Triwulan {Triwulan}) -> Lv4 (Berkas SPJ)` terunggah dengan ukuran non-zero bytes.
   - Uji unggah ulang / revisi baru dan pastikan berkas lama di Drive **tertimpa (overwrite)** tanpa duplikat.

---

## Troubleshooting Umum

| Gejala / Error | Penyebab Umum | Solusi |
| :--- | :--- | :--- |
| `404 File not found: <FOLDER_ID>` | Folder ID di `gdrive-folder-id.txt` salah atau folder belum di-share ke Service Account / akun OAuth. | Periksa ulang ID folder di URL dan pastikan akun yang terhubung memiliki akses Editor / Content Manager. |
| `403 storageQuotaExceeded` atau file `0 byte` | Service Account mencoba mengunggah isi file ke *My Drive* akun Gmail pribadi (kuota SA = 0 byte). | Gunakan **OAuth 2.0** (`gdrive-oauth-client.json` + tombol **Hubungkan Akun Google (OAuth 2.0)**) atau gunakan **Google Workspace Shared Drive**. |
| `invalid_grant` / `Could not deserialize key data` | File JSON key korup, atau token OAuth kedaluwarsa/dicabut. | Unduh ulang JSON atau klik **Putuskan OAuth** lalu hubungkan ulang via OAuth 2.0. |
| File terduplikasi saat retry | Pencarian file eksisting tidak menyertakan `supportsAllDrives=True` & `includeItemsFromAllDrives=True`. | Pastikan seluruh pemanggilan `files().list()` dan `files().create()` mengaktifkan flag Shared Drive tersebut. |
