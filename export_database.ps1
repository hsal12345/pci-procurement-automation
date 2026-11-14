# Script Ekspor Database PCI Procurement Automation
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   PENGUNDUHAN / BACKUP DATABASE (PCI PROCUREMENT)        " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Cek ketersediaan Docker
try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Docker Desktop belum aktif. Silakan buka aplikasi Docker Desktop di Windows terlebih dahulu." -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "[!] Docker CLI tidak dapat dihubungi. Pastikan Docker Desktop sedang berjalan." -ForegroundColor Red
    exit 1
}

Write-Host "[1/3] Memastikan kontainer database 'pci-procurement-db' berjalan..." -ForegroundColor Green
docker compose up -d db

# 2. Tunggu healthcheck PostgreSQL siap
Write-Host "[2/3] Menunggu PostgreSQL siap menerima koneksi..." -ForegroundColor Green
$maxWait = 30
$ready = $false
for ($i = 1; $i -le $maxWait; $i++) {
    $check = docker exec pci-procurement-db pg_isready -U postgres -d pci_spjed 2>&1
    if ($LASTEXITCODE -eq 0) {
        $ready = $true
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $ready) {
    Write-Host "[!] Gagal terhubung ke database di dalam kontainer." -ForegroundColor Red
    exit 1
}

# 3. Jalankan pg_dump
$outputFile = Join-Path $PSScriptRoot "pci_spjed_backup.sql"
Write-Host "[3/3] Mengekspor database ke: $outputFile ..." -ForegroundColor Green

# Eksekusi pg_dump via docker exec
docker exec -t pci-procurement-db pg_dump -U postgres -d pci_spjed | Out-File -FilePath $outputFile -Encoding utf8

if (Test-Path $outputFile) {
    $fileSize = (Get-Item $outputFile).Length
    $fileSizeKB = [math]::Round($fileSize / 1KB, 2)
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host "[BERHASIL] File backup database berhasil dibuat!" -ForegroundColor Green
    Write-Host "Lokasi : $outputFile" -ForegroundColor Yellow
    Write-Host "Ukuran : $fileSizeKB KB ($fileSize bytes)" -ForegroundColor Yellow
    Write-Host "==========================================================" -ForegroundColor Cyan
} else {
    Write-Host "[!] Gagal membuat file backup." -ForegroundColor Red
}
