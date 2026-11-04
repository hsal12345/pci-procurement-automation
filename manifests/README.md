# PCI Procurement & SPJ System — Application Manifests

Dokumen ini memuat panduan lengkap seluruh berkas **Manifest** untuk **Docker App** dan **Web App** pada proyek CV Pustaka Cemerlang Indonesia.

---

## Struktur Berkas Manifest

```text
pci-procurement-automation/
├── manifests/
│   ├── k8s/                                # Kubernetes Deployment Manifests
│   │   ├── 00-namespace.yaml               # Namespace 'pci-procurement'
│   │   ├── 01-postgres-manifest.yaml       # Database (Secret, PVC, Deployment, Service)
│   │   ├── 02-docker-app-manifest.yaml     # 1. Docker App (Backend FastAPI + Probes + Volume)
│   │   ├── 03-web-app-manifest.yaml        # 2. Web App (Frontend Next.js + Probes)
│   │   ├── 04-ingress-manifest.yaml        # Ingress routing (Nginx Ingress Controller)
│   │   └── complete-manifest.yaml          # All-in-One manifest (Deploy sekaligus)
│   ├── docker/
│   │   └── docker-app-manifest.yml         # Docker Compose Application Manifest
│   └── web/
│       └── manifest.json                   # W3C Standard Web App Manifest reference
├── frontend/
│   ├── public/
│   │   └── manifest.json                   # Static Web App Manifest (PWA)
│   └── src/app/
│       └── manifest.ts                     # Next.js App Router Dynamic Web App Manifest
└── docker-compose.yml                      # Root Docker Compose Multi-Container Manifest
```

---

## 1. Manifest untuk Docker App

Dalam konteks arsitektur kontainer, berkas manifest untuk **Docker App** (Backend API & Services) disediakan dalam dua standar industri:

### A. Kubernetes Manifest (`manifests/k8s/02-docker-app-manifest.yaml`)
Mendeklarasikan deployment kontainer backend FastAPI dengan spesifikasi:
- **ConfigMap & Secret**: Konfigurasi koneksi database PostgreSQL, mode runtime AI, Secret Key JWT, dan batas anggaran.
- **PersistentVolumeClaim**: Storage 10Gi untuk `/app/storage` (dokumen SPJ, template docx, bukti foto fisik BAPB, dan kop surat).
- **Deployment**: 2 Replicas, rolling update (`maxSurge: 1`, `maxUnavailable: 0`), batas CPU/Memory, serta Liveness dan Readiness Probes pada `/health`.
- **Service**: ClusterIP exposing port `8000`.

### B. Docker Compose Application Manifest (`manifests/docker/docker-app-manifest.yml` & `docker-compose.yml`)
Mendeklarasikan stack kontainer lengkap (Database, Docker App Backend, Web App Frontend, dan DBeaver Web GUI) dengan dependensi healthcheck, volume persisten, dan network bridge.

#### Cara Menjalankan Docker App:
```bash
# Menjalankan seluruh stack Docker
docker compose up -d

# Memeriksa status kesehatan kontainer
docker compose ps
```

---

## 2. Manifest untuk Web App

Untuk **Web App** (Frontend Next.js), manifest disediakan dalam dua aspek:

### A. W3C Web App Manifest (`manifest.json` & `manifest.ts` PWA)
Standar W3C Web App Manifest untuk menjadikan antarmuka web sebagai aplikasi PWA (Progressive Web App) yang dapat di-install pada perangkat desktop maupun mobile:
- **Lokasi Proyek:**
  - `frontend/src/app/manifest.ts` (Next.js 14 App Router Dynamic Route)
  - `frontend/public/manifest.json` (Berkas JSON statis)
- **Atribut Utama:**
  - `name`: "PCI Procurement & SPJ System"
  - `short_name`: "PCI SPJ"
  - `display`: "standalone"
  - `theme_color`: "#02569D" (Biru identitas resmi CV PCI)
  - `background_color`: "#FFFFFF"
  - `icons`: 192x192 & 512x512 maskable/any icons.
  - `shortcuts`: Tautan cepat untuk *Buat Paket Pengadaan*, *Impor Spreadsheet*, dan *AI & Audit*.

### B. Kubernetes Web App Manifest (`manifests/k8s/03-web-app-manifest.yaml`)
Mendeklarasikan deployment kontainer frontend Next.js pada klaster Kubernetes:
- **Deployment**: 2 Replicas Next.js production image (`NODE_ENV=production`), terhubung ke backend internal via `http://pci-docker-app-service:8000`.
- **Service**: ClusterIP exposing port `3000`.
- **Ingress Controller**: Memetakan traffic domain publik `/` ke Web App dan `/api/`, `/storage/`, `/docs`, `/health` ke Docker App backend.

---

## Cara Deployment ke Kubernetes

Cukup jalankan satu perintah berikut pada klaster Kubernetes Anda (Minikube, K3s, MicroK8s, EKS, GKE, atau AKS):

```bash
# 1. Terapkan seluruh manifest sekaligus
kubectl apply -f manifests/k8s/complete-manifest.yaml

# 2. Atau terapkan secara bertahap
kubectl apply -f manifests/k8s/00-namespace.yaml
kubectl apply -f manifests/k8s/01-postgres-manifest.yaml
kubectl apply -f manifests/k8s/02-docker-app-manifest.yaml
kubectl apply -f manifests/k8s/03-web-app-manifest.yaml
kubectl apply -f manifests/k8s/04-ingress-manifest.yaml

# 3. Pantau status pod dan service
kubectl get pods,svc,pvc,ingress -n pci-procurement
```

