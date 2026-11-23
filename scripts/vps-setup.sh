#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# PCI Procurement & SPJ System — Hardened VPS Bootstrap Script
# Tested on Ubuntu 22.04 / 24.04 & Debian 12 (Run as root or with sudo)
#
# Usage:
#   SSH_PORT=2222 SSH_PUBLIC_KEY="ssh-ed25519 AAAA..." bash scripts/vps-setup.sh
#   (Atau pastikan ~/.ssh/authorized_keys sudah terisi sebelum menjalankan script)
# ==============================================================================

REPO_URL="${1:-https://github.com/naufalfarr/pci-procurement-automation.git}"
BRANCH="${2:-feature-branch}"
APP_DIR="/opt/pci-procurement"
SSH_PORT="${SSH_PORT:-2222}"
SSH_PUBLIC_KEY="${SSH_PUBLIC_KEY:-}"

echo "=== [1/8] Updating system & installing security packages ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl gnupg git ufw fail2ban openssl unattended-upgrades

# Enable automatic security updates
dpkg-reconfigure -f noninteractive unattended-upgrades || true

echo "=== [2/8] Configuring 4GB Swap & Kernel Tuning ==="
if [ ! -f /swapfile ] && [ "$(swapon --show | wc -l)" -eq 0 ]; then
  fallocate -l 4G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
  echo "Created and enabled 4GB /swapfile."
else
  echo "Swap already configured."
fi

sysctl -w vm.swappiness=10
if ! grep -q "^vm.swappiness=" /etc/sysctl.conf; then
  echo "vm.swappiness=10" >> /etc/sysctl.conf
fi

echo "=== [3/8] Installing Docker Engine & Docker Compose plugin ==="
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

echo "=== [4/8] Installing SSH Public Key & Hardening SSHD ==="
mkdir -p /root/.ssh
chmod 700 /root/.ssh
touch /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys

if [ -n "$SSH_PUBLIC_KEY" ]; then
  if ! grep -qxF "$SSH_PUBLIC_KEY" /root/.ssh/authorized_keys; then
    echo "$SSH_PUBLIC_KEY" >> /root/.ssh/authorized_keys
    echo "Added SSH_PUBLIC_KEY to /root/.ssh/authorized_keys."
  fi
fi

if [ -s /root/.ssh/authorized_keys ]; then
  cat <<EOF > /etc/ssh/sshd_config.d/99-pci-hardening.conf
Port ${SSH_PORT}
PermitRootLogin prohibit-password
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
LoginGraceTime 30
X11Forwarding no
AllowAgentForwarding no
ClientAliveInterval 300
ClientAliveCountMax 2
EOF

  # Ubuntu 24.04 uses ssh.socket by default; override its ListenStream port if active
  if systemctl list-unit-files | grep -q "^ssh.socket"; then
    mkdir -p /etc/systemd/system/ssh.socket.d
    cat <<EOF > /etc/systemd/system/ssh.socket.d/override.conf
[Socket]
ListenStream=
ListenStream=${SSH_PORT}
EOF
    systemctl daemon-reload
  fi

  sshd -t
  systemctl restart ssh.socket 2>/dev/null || true
  systemctl restart ssh 2>/dev/null || systemctl restart sshd
  echo "SSH hardened: Port=${SSH_PORT}, PasswordAuthentication=no, PermitRootLogin=prohibit-password."
else
  echo "WARNING: /root/.ssh/authorized_keys is EMPTY!"
  echo "Skipping PasswordAuthentication=no to prevent locking you out."
  echo "Add your SSH public key to /root/.ssh/authorized_keys and re-run this script!"
  SSH_PORT=22
fi

echo "=== [5/8] Configuring UFW Firewall (Only SSH ${SSH_PORT}, HTTP 80, HTTPS 443) ==="
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow "${SSH_PORT}/tcp" comment "SSH"
ufw allow 80/tcp comment "HTTP"
ufw allow 443/tcp comment "HTTPS"
ufw --force enable
ufw status verbose

echo "=== [6/8] Configuring Strict Fail2ban for SSH (Port ${SSH_PORT}) ==="
cat <<EOF > /etc/fail2ban/jail.local
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 3
backend = systemd

[sshd]
enabled = true
port = ${SSH_PORT}
EOF
systemctl enable --now fail2ban
systemctl restart fail2ban

echo "=== [7/8] Preparing SSL Directory (/etc/pci-ssl) ==="
if [ ! -f /etc/pci-ssl/cert.pem ] || [ ! -f /etc/pci-ssl/key.pem ]; then
  mkdir -p /etc/pci-ssl
  openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
    -keyout /etc/pci-ssl/key.pem \
    -out /etc/pci-ssl/cert.pem \
    -subj "/CN=pci-procurement-akpsi.cloud"
  chmod 600 /etc/pci-ssl/key.pem
  echo "Created temporary self-signed SSL cert in /etc/pci-ssl (replace with Cloudflare Origin Cert)."
fi

echo "=== [8/8] Cloning repo, generating .env & starting Docker Compose stack ==="
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

docker compose pull nginx db
docker compose up -d --build --remove-orphans

echo "=================================================================="
echo "Setup & Hardening Complete!"
echo "SSH Port : ${SSH_PORT} (Update GitHub Secret VPS_PORT=${SSH_PORT})"
echo "Web UI   : https://pci-procurement-akpsi.cloud"
echo "Health   : http://127.0.0.1/health"
echo "=================================================================="
