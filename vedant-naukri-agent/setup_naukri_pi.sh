#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  vedant-naukri-agent — Pi 3B+ Bootstrap & Cron Installer                   ║
# ║  Configures Raspberry Pi OS Lite, native Chromium, venv, and staggered cron║
# ║  Usage:  sudo ./setup_naukri_pi.sh                                          ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
set -euo pipefail

# ── Check root ────────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (use sudo): sudo ./setup_naukri_pi.sh" >&2
    exit 1
fi

AGENT_USER="${SUDO_USER:-$(whoami)}"
USER_HOME=$(eval echo "~${AGENT_USER}")
AGENT_DIR="${USER_HOME}/vedant-naukri-agent"
VENV_DIR="${USER_HOME}/vedant-agent-venv"
SESSION_DIR="${USER_HOME}/.naukri_bot_session"
DATA_DIR="${USER_HOME}/.vedant_naukri_data"
LOG_FILE="${USER_HOME}/vedant_naukri_agent.log"

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${GREEN}[SETUP-NAUKRI]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[SETUP-NAUKRI]${NC}  $*"; }
error() { echo -e "${RED}[SETUP-NAUKRI]${NC} $*" >&2; }

info "Starting setup for user '${AGENT_USER}' (home: ${USER_HOME})…"

# ══════════════════════════════════════════════════════════════════════════════
# 1. SWAP CONFIGURATION (2 GB)
# ══════════════════════════════════════════════════════════════════════════════
SWAP_CONF="/etc/dphys-swapfile"
if [[ -f "${SWAP_CONF}" ]]; then
    CURRENT_SWAP=$(grep -E "^CONF_SWAPSIZE=" "${SWAP_CONF}" | cut -d= -f2 || echo 0)
    if [[ "${CURRENT_SWAP}" -lt 2048 ]]; then
        info "Increasing swap to 2048 MB in ${SWAP_CONF}…"
        sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' "${SWAP_CONF}"
        if grep -q "^#CONF_MAXSWAP=" "${SWAP_CONF}"; then
            sed -i 's/^#CONF_MAXSWAP=.*/CONF_MAXSWAP=2048/' "${SWAP_CONF}"
        elif ! grep -q "^CONF_MAXSWAP=" "${SWAP_CONF}"; then
            echo "CONF_MAXSWAP=2048" >> "${SWAP_CONF}"
        fi
        dphys-swapfile swapoff || true
        dphys-swapfile setup
        dphys-swapfile swapon
        info "Swap upgraded to 2048 MB."
    else
        info "Swap is already >= 2048 MB (${CURRENT_SWAP} MB). Skipping."
    fi
else
    warn "${SWAP_CONF} not found. Skipping swap resize."
fi

# ══════════════════════════════════════════════════════════════════════════════
# 2. CHROMIUM & SYSTEM PACKAGES
# ══════════════════════════════════════════════════════════════════════════════
info "Checking required system packages…"
apt-get update -y

PACKAGES=(
    chromium-browser
    python3-venv
    python3-pip
    python3-dev
    libffi-dev
    libssl-dev
    util-linux
)

TO_INSTALL=()
for pkg in "${PACKAGES[@]}"; do
    if ! dpkg -s "${pkg}" >/dev/null 2>&1; then
        TO_INSTALL+=("${pkg}")
    fi
done

if [[ ${#TO_INSTALL[@]} -gt 0 ]]; then
    info "Installing: ${TO_INSTALL[*]}…"
    apt-get install -y "${TO_INSTALL[@]}"
else
    info "All required system packages are already installed."
fi

# ══════════════════════════════════════════════════════════════════════════════
# 3. PYTHON VIRTUAL ENVIRONMENT
# ══════════════════════════════════════════════════════════════════════════════
if [[ ! -d "${VENV_DIR}" ]]; then
    info "Creating Python virtual environment at ${VENV_DIR}…"
    sudo -u "${AGENT_USER}" python3 -m venv "${VENV_DIR}"
else
    info "Python virtual environment already exists at ${VENV_DIR}."
fi

info "Installing Python dependencies into venv…"
sudo -u "${AGENT_USER}" "${VENV_DIR}/bin/pip" install --upgrade pip
sudo -u "${AGENT_USER}" "${VENV_DIR}/bin/pip" install \
    playwright \
    playwright-stealth \
    scrapling \
    python-dotenv \
    requests \
    rich

info "Python venv is ready. Playwright will use native Chromium (/usr/bin/chromium-browser)."

# ══════════════════════════════════════════════════════════════════════════════
# 4. DIRECTORIES & SECURITY PERMISSIONS
# ══════════════════════════════════════════════════════════════════════════════
info "Creating directories with restricted permissions…"
sudo -u "${AGENT_USER}" mkdir -p "${SESSION_DIR}"
sudo -u "${AGENT_USER}" mkdir -p "${DATA_DIR}"
sudo -u "${AGENT_USER}" touch "${LOG_FILE}"

# Security hardening: restrict permissions to owner only
chmod 700 "${SESSION_DIR}"
chmod 700 "${DATA_DIR}"
chmod 600 "${LOG_FILE}"

# ══════════════════════════════════════════════════════════════════════════════
# 5. COPY & CONFIGURE AGENT FILES
# ══════════════════════════════════════════════════════════════════════════════
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${SCRIPT_DIR}" != "${AGENT_DIR}" ]]; then
    info "Installing agent files into ${AGENT_DIR}…"
    sudo -u "${AGENT_USER}" mkdir -p "${AGENT_DIR}"
    cp -r "${SCRIPT_DIR}/"* "${AGENT_DIR}/"
    chown -R "${AGENT_USER}:${AGENT_USER}" "${AGENT_DIR}"
fi

chmod +x "${AGENT_DIR}/run_naukri_agent.sh"
chmod +x "${AGENT_DIR}/setup_naukri_pi.sh"

if [[ ! -f "${AGENT_DIR}/.env" && -f "${AGENT_DIR}/.env.example" ]]; then
    info "Creating .env from .env.example…"
    sudo -u "${AGENT_USER}" cp "${AGENT_DIR}/.env.example" "${AGENT_DIR}/.env"
    chmod 600 "${AGENT_DIR}/.env"
fi

# ══════════════════════════════════════════════════════════════════════════════
# 6. STAGGERED CRON JOBS (OFFSET FROM LINKEDIN TO PREVENT RAM COLLISION)
# ══════════════════════════════════════════════════════════════════════════════
info "Configuring staggered cron jobs for Naukri…"

CRON_MARKER="# vedant-naukri-agent managed cron"
CRON_BLOCK=$(cat <<CRON
${CRON_MARKER} — DO NOT EDIT BELOW THIS LINE
# 1. Daily Profile Refresh at 8:55 AM IST (Mon–Sat) to rank #1 before recruiter searches at 9:00 AM
55 8 * * 1-6 ${AGENT_DIR}/run_naukri_agent.sh --mode refresh-profile >> ${LOG_FILE} 2>&1

# 2. Search & 1-Click Direct Apply at 12:00 PM and 5:30 PM IST (Offset from LinkedIn scans)
0 12,17 * * * ${AGENT_DIR}/run_naukri_agent.sh --mode search-apply >> ${LOG_FILE} 2>&1

# 3. Check Recruiter Inbox & NVites at 1:30 PM and 7:30 PM IST
30 13,19 * * * ${AGENT_DIR}/run_naukri_agent.sh --mode inbox >> ${LOG_FILE} 2>&1
${CRON_MARKER} — DO NOT EDIT ABOVE THIS LINE
CRON
)

EXISTING_CRON=$(sudo -u "${AGENT_USER}" crontab -l 2>/dev/null || true)
CLEAN_CRON=$(echo "${EXISTING_CRON}" | sed "/${CRON_MARKER}/,/${CRON_MARKER}/d")
echo "${CLEAN_CRON}
${CRON_BLOCK}" | sudo -u "${AGENT_USER}" crontab -

info "Staggered cron schedule installed. View with: crontab -l"

# ══════════════════════════════════════════════════════════════════════════════
# 7. SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  ✅  vedant-naukri-agent — Pi setup successfully completed!         ║"
echo "╠══════════════════════════════════════════════════════════════════════╣"
echo "║                                                                      ║"
echo "║  Next steps:                                                         ║"
echo "║   1. Edit credentials:  nano ${AGENT_DIR}/.env                       ║"
echo "║   2. Place resume PDF:  cp Vedant_Resume.pdf /home/pi/               ║"
echo "║   3. One-time login:    ${AGENT_DIR}/run_naukri_agent.sh --mode login║"
echo "║   4. Test refresh:      ${AGENT_DIR}/run_naukri_agent.sh --mode refresh-profile ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
