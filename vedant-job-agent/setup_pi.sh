#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  vedant-job-agent — Raspberry Pi 3B+ Setup Script                          ║
# ║  Run once:  sudo ./setup_pi.sh                                             ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
set -euo pipefail

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── Pre-flight ────────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root.  Use: sudo $0"
    exit 1
fi

AGENT_USER="${SUDO_USER:-pi}"
AGENT_HOME=$(eval echo "~${AGENT_USER}")
AGENT_DIR="${AGENT_HOME}/vedant-job-agent"
VENV_DIR="${AGENT_HOME}/vedant-agent-venv"
DATA_DIR="${AGENT_HOME}/.vedant_agent_data"
SESSION_DIR="${AGENT_HOME}/.linkedin_bot_session"
LOG_FILE="${AGENT_HOME}/vedant_agent.log"

info "Agent user : ${AGENT_USER}"
info "Agent home : ${AGENT_HOME}"
info "Agent dir  : ${AGENT_DIR}"

# ══════════════════════════════════════════════════════════════════════════════
# 1. SWAP CONFIGURATION  (2 GB)
# ══════════════════════════════════════════════════════════════════════════════
info "Configuring 2 GB swap…"

SWAP_CONF="/etc/dphys-swapfile"
if [[ -f "${SWAP_CONF}" ]]; then
    # Backup original
    cp "${SWAP_CONF}" "${SWAP_CONF}.bak.$(date +%s)"

    # Set CONF_SWAPSIZE=2048
    if grep -q "^CONF_SWAPSIZE" "${SWAP_CONF}"; then
        sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' "${SWAP_CONF}"
    else
        echo "CONF_SWAPSIZE=2048" >> "${SWAP_CONF}"
    fi

    # Set CONF_MAXSWAP=2048
    if grep -q "^CONF_MAXSWAP" "${SWAP_CONF}"; then
        sed -i 's/^CONF_MAXSWAP=.*/CONF_MAXSWAP=2048/' "${SWAP_CONF}"
    else
        echo "CONF_MAXSWAP=2048" >> "${SWAP_CONF}"
    fi

    # Restart swap service
    dphys-swapfile swapoff  || true
    dphys-swapfile setup
    dphys-swapfile swapon
    info "Swap configured: $(swapon --show | tail -1)"
else
    warn "${SWAP_CONF} not found — skipping swap config (non-Pi OS?)."
fi

# Set swappiness
SYSCTL_CONF="/etc/sysctl.d/99-vedant-agent.conf"
cat > "${SYSCTL_CONF}" <<'SYSCTL'
# vedant-job-agent: encourage swap usage on low-RAM Pi
vm.swappiness=60
vm.vfs_cache_pressure=50
SYSCTL
sysctl --system > /dev/null 2>&1
info "vm.swappiness set to 60."

# ══════════════════════════════════════════════════════════════════════════════
# 2. GPU MEMORY SPLIT  (16 MB — headless, no desktop)
# ══════════════════════════════════════════════════════════════════════════════
info "Setting gpu_mem=16 in /boot/config.txt…"

BOOT_CONFIG="/boot/config.txt"
# Also check /boot/firmware/config.txt (Bookworm+)
if [[ -f "/boot/firmware/config.txt" ]]; then
    BOOT_CONFIG="/boot/firmware/config.txt"
fi

if grep -q "^gpu_mem=" "${BOOT_CONFIG}"; then
    sed -i 's/^gpu_mem=.*/gpu_mem=16/' "${BOOT_CONFIG}"
else
    echo "gpu_mem=16" >> "${BOOT_CONFIG}"
fi
info "GPU memory set to 16 MB in ${BOOT_CONFIG}."

# ══════════════════════════════════════════════════════════════════════════════
# 3. DEFAULT BOOT TARGET  (multi-user / headless CLI)
# ══════════════════════════════════════════════════════════════════════════════
info "Setting default boot target to multi-user (headless CLI)…"
systemctl set-default multi-user.target
info "Boot target: $(systemctl get-default)"

# ══════════════════════════════════════════════════════════════════════════════
# 4. SYSTEM PACKAGES  (Chromium + ARM shared libraries)
# ══════════════════════════════════════════════════════════════════════════════
info "Installing system packages…"
apt-get update -qq

apt-get install -y -qq \
    chromium-browser \
    chromium-codecs-ffmpeg-extra \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-glib-1-2 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xvfb \
    python3 \
    python3-pip \
    python3-venv \
    git \
    flock \
    curl \
    jq

info "Chromium version: $(chromium-browser --version 2>/dev/null || echo 'not found')"

# ══════════════════════════════════════════════════════════════════════════════
# 5. PYTHON VIRTUAL ENVIRONMENT & DEPENDENCIES
# ══════════════════════════════════════════════════════════════════════════════
info "Creating Python virtual environment at ${VENV_DIR}…"
sudo -u "${AGENT_USER}" python3 -m venv "${VENV_DIR}"

info "Installing Python packages…"
sudo -u "${AGENT_USER}" "${VENV_DIR}/bin/pip" install --upgrade pip setuptools wheel

sudo -u "${AGENT_USER}" "${VENV_DIR}/bin/pip" install \
    playwright \
    playwright-stealth \
    scrapling \
    python-dotenv \
    requests \
    beautifulsoup4 \
    lxml \
    rich \
    pydantic

# NOTE: We do NOT run `playwright install` because that downloads x86 Chromium.
# Instead, we point Playwright at /usr/bin/chromium-browser via executable_path.
info "Python venv ready.  Playwright will use native Chromium — no download needed."

# ══════════════════════════════════════════════════════════════════════════════
# 6. DATA & SESSION DIRECTORIES
# ══════════════════════════════════════════════════════════════════════════════
info "Creating data directories…"
sudo -u "${AGENT_USER}" mkdir -p "${DATA_DIR}"
sudo -u "${AGENT_USER}" mkdir -p "${SESSION_DIR}"
sudo -u "${AGENT_USER}" touch "${LOG_FILE}"
# Security hardening: restrict permissions so other system users cannot read credentials/sessions
chmod 700 "${DATA_DIR}" "${SESSION_DIR}"
chmod 600 "${LOG_FILE}"
info "Data dir    : ${DATA_DIR}"
info "Session dir : ${SESSION_DIR}"
info "Log file    : ${LOG_FILE}"

# ══════════════════════════════════════════════════════════════════════════════
# 7. COPY AGENT FILES  (if not already in place)
# ══════════════════════════════════════════════════════════════════════════════
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${SCRIPT_DIR}" != "${AGENT_DIR}" ]]; then
    info "Copying agent files to ${AGENT_DIR}…"
    sudo -u "${AGENT_USER}" mkdir -p "${AGENT_DIR}"
    cp -r "${SCRIPT_DIR}/"* "${AGENT_DIR}/"
    chown -R "${AGENT_USER}:${AGENT_USER}" "${AGENT_DIR}"
fi
chmod +x "${AGENT_DIR}/run_agent.sh"
chmod +x "${AGENT_DIR}/setup_pi.sh"

# ══════════════════════════════════════════════════════════════════════════════
# 8. CRON JOBS
# ══════════════════════════════════════════════════════════════════════════════
info "Installing cron jobs for ${AGENT_USER}…"

CRON_MARKER="# vedant-job-agent managed cron"
CRON_BLOCK=$(cat <<CRON
${CRON_MARKER} — DO NOT EDIT BELOW THIS LINE
# Scan LinkedIn posts for new leads every 4 hours (06:00 – 22:00)
0 6,10,14,18,22 * * * ${AGENT_DIR}/run_agent.sh --mode scan-posts >> ${LOG_FILE} 2>&1
# Check inbox for new messages every 2 hours (08:00 – 20:00)
0 8,10,12,14,16,18,20 * * * ${AGENT_DIR}/run_agent.sh --mode inbox >> ${LOG_FILE} 2>&1
${CRON_MARKER} — DO NOT EDIT ABOVE THIS LINE
CRON
)

# Remove old managed block if present, then append new
EXISTING_CRON=$(sudo -u "${AGENT_USER}" crontab -l 2>/dev/null || true)
CLEAN_CRON=$(echo "${EXISTING_CRON}" | sed "/${CRON_MARKER}/,/${CRON_MARKER}/d")
echo "${CLEAN_CRON}
${CRON_BLOCK}" | sudo -u "${AGENT_USER}" crontab -

info "Cron jobs installed.  Verify with: crontab -l"

# ══════════════════════════════════════════════════════════════════════════════
# 9. SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  ✅  vedant-job-agent — Pi setup complete!                         ║"
echo "╠══════════════════════════════════════════════════════════════════════╣"
echo "║                                                                    ║"
echo "║  Next steps:                                                       ║"
echo "║   1. cp ${AGENT_DIR}/.env.example ${AGENT_DIR}/.env               ║"
echo "║   2. nano ${AGENT_DIR}/.env   # fill in credentials               ║"
echo "║   3. ${AGENT_DIR}/run_agent.sh --mode login                       ║"
echo "║   4. Reboot to apply gpu_mem & swap changes:  sudo reboot         ║"
echo "║                                                                    ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
