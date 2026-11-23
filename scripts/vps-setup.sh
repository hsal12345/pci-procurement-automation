#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# PCI Procurement & SPJ System — VPS Bootstrap & Security Hardening Script
# Tested on Ubuntu 22.04 / 24.04 & Debian 12 (Run as root or with sudo)
# ==============================================================================

REPO_URL="${1:-https://github.com/naufalfarr/pci-procurement-automation.git}"
BRANCH="${2:-feature-branch}"
APP_DIR="/opt/pci-procurement"

echo "=== [1/6] Installing base packages, UFW firewall & Fail2ban ==="
apt-get update -y
apt-get install -y ca-certificates curl gnupg git ufw fail2ban openssl

echo "=== [2/6] Installing Docker Engine & Docker Compose plugin ==="
if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  . /etc/os-release
  curl -fsSL "https://download.docker.com/linux/${ID}/gpg" | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${ID} \
    ${VERSION_CODENAME} stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
else
  echo "Docker already installed: $(docker --version)"
fi

echo "=== [3/6] Configuring UFW Firewall (Only SSH 22, HTTP 80, HTTPS 443) ==="
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
ufw status verbose

echo "=== [4/6] Enabling Fail2ban SSH protection ==="
systemctl enable --now fail2ban

echo "=== [5/6] Tuning vm.swappiness=10 for 4GB RAM + 4GB Swap VPS ==="
sysctl vm.swappiness=10
if ! grep -q "vm.swappiness=10" /etc/sysctl.conf; then
  echo "vm.swappiness=10" >> /etc/sysctl.conf
fi

echo "=== [6/6] Cloning repo & starting Docker Compose stack ==="
if [ ! -d "$APP_DIR/.git" ]; then
  mkdir -p "$APP_DIR"
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"
git fetch --all --prune
git checkout "$BRANCH"
git reset --hard "origin/$BRANCH"

if [ ! -f .env ]; then
  cp .env.example .env
  RAND_DB_PASS=$(openssl rand -hex 24)
  RAND_SECRET=$(openssl rand -hex 32)
  sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${RAND_DB_PASS}|" .env
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${RAND_SECRET}|" .env
  chmod 600 .env
  echo "Generated secure .env with randomized credentials (chmod 600)."
fi

docker compose up -d --build

echo "=== Setup Complete! ==="
echo "Web UI : http://$(curl -fsS https://ifconfig.me || echo '<VPS_IP>')"
echo "API Doc: http://$(curl -fsS https://ifconfig.me || echo '<VPS_IP>')/docs"
