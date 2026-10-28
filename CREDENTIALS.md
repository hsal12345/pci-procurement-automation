# PCI Procurement & SPJ System — Account Credentials & RBAC Guide

> **Note:** Self-registration is disabled. New user accounts, role assignments, and password resets can only be managed by a **System Administrator** via the User Management Dashboard (`/users`).

---

## 1. Application URLs
- **Login Page:** `http://localhost:3000/login`
- **Main Dashboard:** `http://localhost:3000/packages`
- **User Management Dashboard (SysAdmin only):** `http://localhost:3000/users`
- **Backend API & Swagger Docs:** `http://localhost:8000/docs`
- **DBeaver Web GUI (CloudBeaver):** `http://localhost:8978`

---

## 2. Default Seeded Accounts

All default accounts can sign in using **either** their **Username** or **Email** along with the password below:

| Role Label | Role Code (`RBAC`) | Full Name | Username | Email | Default Password |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Administrator Sistem** | `SYSTEM_ADMINISTRATOR` | Administrator Sistem | `sysadmin` | `sysadmin@pci.co.id` | `Admin123!` |
| **Staf Administrasi** | `ADMINISTRATION` | Staf Administrasi Pengadaan | `admin` | `administrasi@pci.co.id` | `Admin123!` |
| **Direktur Keuangan** | `FINANCE_DIRECTOR` | Bambang Solifian | `direktur` | `direktur@pci.co.id` | `Admin123!` |
| **Petugas Logistik** | `LOGISTICS` | Petugas Logistik & Pengiriman | `logistik` | `logistik@pci.co.id` | `Admin123!` |

---

## 3. Role-Based Access Control (RBAC) Matrix

| Module / Capability | `SYSTEM_ADMINISTRATOR` | `ADMINISTRATION` | `FINANCE_DIRECTOR` | `LOGISTICS` |
| :--- | :---: | :---: | :---: | :---: |
| **Paket Pengadaan (`/packages`)** — View Packages & Revisions | ✅ | ✅ | ✅ | ✅ |
| **Buat / Edit Draf Paket, Item, Tanggal & Nomor** | ✅ | ✅ | ❌ | ❌ |
| **Impor Spreadsheet Excel (`/imports`)** | ✅ | ✅ | ❌ | ❌ |
| **Master Sekolah & Pejabat (`/schools`)** | ✅ | ✅ | ✅ | ❌ |
| **Master Rekanan / Perusahaan (`/companies`)** | ✅ | ✅ | ✅ | ❌ |
| **Validasi Aturan (BR01–BR15) & Ajukan Review (`Submit`)** | ✅ | ✅ | ❌ | ❌ |
| **Persetujuan Direktur (`Approve`, `Return`, `Issue`, `Reopen`, `Cancel`)** | ✅ | ❌ | ✅ | ❌ |
| **Fakta Logistik, Pemeriksaan BAPB & Unggah Bukti Foto** | ✅ | ✅ | ❌ | ✅ |
| **Cetak & Unduh 13 Dokumen SPJ (`XLSX`, `DOCX`, `PDF`, `ZIP`)** | ✅ | ✅ | ✅ | ✅ |
| **AI & Audit Usage (`/ai/usage`)** | ✅ | ✅ | ✅ | ❌ |
| **Manajemen Pengguna (`/users`) — Tambah / Edit / Nonaktifkan / Hapus User** | ✅ | ❌ | ❌ | ❌ |

---

## 4. Managing Users & Passwords
1. **Adding a New User:**
   - Log in as `sysadmin` (`Admin123!`).
   - Open **Manajemen Pengguna** (`http://localhost:3000/users`) from the left sidebar.
   - Click **+ Tambah Pengguna Baru**, fill in the user's Full Name, Username, Email, Initial Password, and select their RBAC Role.
2. **Resetting a User's Password / Changing Role:**
   - In **Manajemen Pengguna** (`/users`), click **Edit / Sandi** on the target user row.
   - Enter a new password in the **Reset Kata Sandi** field or choose a new RBAC role, then click **Simpan Perubahan**.
3. **Changing Your Own Password:**
   - Any logged-in user can click **Ubah Sandi** at the bottom of the left sidebar to update their own password.

---

## 5. Database & Management Tools Access

### A. DBeaver Web GUI (CloudBeaver) Portal Login
- **URL:** `http://localhost:8978`
- **Username:** `pci-admin`
- **Password:** `mCSXjZT3VW6R6mh`

### B. DBeaver Connection Configuration (Verified)
Gunakan parameter berikut saat menambahkan koneksi database di dalam CloudBeaver:

| Pengaturan Form | Nilai | Keterangan |
| :--- | :--- | :--- |
| **Driver** | `PostgreSQL` | Driver default |
| **Configuration** | `Manual` | - |
| **Host** | `db` | ⚠️ *Gunakan `db` (bukan `localhost`) agar terhubung via jaringan Docker* |
| **Port** | `5432` | Port internal PostgreSQL |
| **Database** | `pci_spjed` | Database utama proyek |
| **Authentication model** | `Username/password` | - |
| **User name** | `postgres` | User database default |
| **User password** | `postgres` | Password database default |

### C. Direct Connection from Host Machine (Desktop Apps: DBeaver Desktop / pgAdmin / TablePlus / psql)
- **Host:** `localhost` atau `127.0.0.1`
- **Port:** `5432`
- **Database:** `pci_spjed`
- **Username:** `postgres`
- **Password:** `postgres`

