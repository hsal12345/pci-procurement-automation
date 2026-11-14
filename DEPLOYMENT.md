# Panduan Deployment VPS (Docker Compose + Nginx + GitHub Actions CI/CD)

Dokumen ini menjelaskan arsitektur deployment, pengerasan keamanan (*security hardening*), dan otomasi CI/CD untuk **PCI Procurement & SPJ System** pada VPS Linux (2 vCPU / 4 GB RAM + 4 GB Swap).

---

## 1. Arsitektur & Pengerasan Keamanan (*Security Hardening*)

1. **Port Isolation (`127.0.0.1` binding)**:
   - Port database PostgreSQL (`5432`), API Backend (`8000`), Frontend (`3000`), dan CloudBeaver (`8978`) diikat eksklusif ke `127.0.0.1` di dalam [docker-compose.yml](file:///c:/Coding/AKPSI%20PROJECT/docker-compose.yml), sehingga **tidak terekspos ke internet publik**.
   - Hanya **Nginx Reverse Proxy** (port `80` / `443`) yang menerima traffic publik.
2. **Nginx Reverse Proxy Hardening** ([nginx/default.conf](file:///c:/Coding/AKPSI%20PROJECT/nginx/default.conf)):
   - **Rate Limiting**: Endpoint login (`/api/v1/auth/login`) dibatasi `5 request/menit` (`burst=5`) untuk mencegah *brute-force*; endpoint `/api/` dibatasi `30 request/detik`.
   - **Security Headers**: `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `X-XSS-Protection`, dan `Permissions-Policy`.
   - **Hidden Files Blocked**: Semua akses ke path diawali titik (`.env`, `.git`, dll.) diblokir.
   - **Timeout Panjang untuk Generate Dokumen**: Timeout proxy diatur `300s` dengan ukuran upload maksimal `50M` agar proses render PDF LibreOffice dan download ZIP berjalan lancar.
3. **Container Security & Optimasi RAM 4 GB**:
   - Semua container dijalankan dengan `no-new-privileges:true`.
   - Container **DBeaver/CloudBeaver** dipindahkan ke Docker Compose profile `tools` agar **tidak menyala otomatis** dan menghemat ~500 MB RAM.
4. **Host Firewall & Secrets**:
   - Script [scripts/vps-setup.sh](file:///c:/Coding/AKPSI%20PROJECT/scripts/vps-setup.sh) mengaktifkan `UFW` (hanya membuka port SSH `22`, HTTP `80`, dan HTTPS `443`) serta `fail2ban` untuk memblokir percobaan *brute-force* SSH.
   - File `.env` pada VPS otomatis digenerate dengan password PostgreSQL & `SECRET_KEY` acak (`openssl rand -hex`), dengan permission `chmod 600`.

---

## 2. Persiapan Awal di VPS (Sekali Saja)

Login ke VPS via SSH, lalu jalankan bootstrap script (atau jalankan manual):

```bash
# Unduh atau jalankan script setup setelah repo di-push
curl -fsSL https://raw.githubusercontent.com/naufalfarr/pci-procurement-automation/feature-branch/scripts/vps-setup.sh -o vps-setup.sh
chmod +x vps-setup.sh
./vps-setup.sh https://github.com/naufalfarr/pci-procurement-automation.git feature-branch
```

> **Catatan SSH Key untuk GitHub Actions**:
> Jika Anda memakai SSH key khusus untuk deploy, pastikan *public key*-nya sudah ada di `~/.ssh/authorized_keys` pada VPS, dan *private key*-nya disimpan di GitHub Secret `VPS_SSH_KEY`.

---

## 3. Pipeline CI/CD (GitHub Actions Free Tier)

Workflow berada di [.github/workflows/ci-cd.yml](file:///c:/Coding/AKPSI%20PROJECT/.github/workflows/ci-cd.yml) dan aktif pada branch `feature-branch` dan `main`:

1. **`ci-verify` (Berjalan di Runner Gratis GitHub)**:
   - Menjalankan automated test backend (`pytest`) dengan `USE_SQLITE_FALLBACK=true`.
   - Menjalankan pengecekan TypeScript frontend (`pnpm tsc --noEmit`).
   - Jika ada yang gagal, deployment ke VPS dibatalkan secara otomatis.
2. **`cd-deploy` (Berjalan via SSH ke VPS jika `ci-verify` lulus pada `push`)**:
   - Melakukan `git fetch` & `git reset --hard` ke commit terbaru di `/opt/pci-procurement`.
   - Menjalankan `docker compose up -d --build --remove-orphans`.
   - Melakukan verifikasi healthcheck (`http://127.0.0.1/health`) hingga backend dan PostgreSQL siap.
   - Membersihkan image Docker lama (`docker image prune -f`) agar disk 80 GB tetap lega.

### GitHub Secrets yang Digunakan
Pastikan berada di *Settings → Secrets and variables → Actions*:
- `VPS_HOST`: IP publik VPS Anda
- `VPS_USER`: Username SSH (misal `root`)
- `VPS_SSH_KEY`: Isi private key SSH (OpenSSH format)
- `VPS_PORT` *(opsional)*: Port SSH jika bukan `22`

---

## 4. Operasional Harian & Akses DBeaver Aman

### Cek Status & Log di VPS
```bash
cd /opt/pci-procurement
docker compose ps
docker compose logs -f --tail=100 backend nginx
```

### Mengakses DBeaver / CloudBeaver Secara Aman (SSH Tunnel)
Karena DBeaver dimatikan default untuk hemat RAM dan diikat ke `127.0.0.1:8978`:
1. Nyalakan sementara di VPS:
   ```bash
   cd /opt/pci-procurement
   docker compose --profile tools up -d dbeaver
   ```
2. Buka SSH Tunnel dari laptop Anda:
   ```powershell
   ssh -L 8978:127.0.0.1:8978 root@<IP_VPS_ANDA>
   ```
3. Buka browser di laptop ke `http://localhost:8978`.
4. Setelah selesai, matikan kembali di VPS:
   ```bash
   docker compose --profile tools stop dbeaver
   ```

### Backup Database PostgreSQL Manual
```bash
cd /opt/pci-procurement
docker compose exec -T db pg_dump -U postgres pci_spjed > backup_$(date +%Y%m%d).sql
```
