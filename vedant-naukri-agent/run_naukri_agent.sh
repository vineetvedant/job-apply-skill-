#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  vedant-naukri-agent — Memory-Safe Runner (Raspberry Pi 3B+ / 1GB RAM)     ║
# ║  Guarantees single Chromium instance across LinkedIn and Naukri via flock. ║
# ║  Usage:  ./run_naukri_agent.sh --mode <login|refresh-profile|search-apply|inbox|email>
# ╚══════════════════════════════════════════════════════════════════════════════╝
set -euo pipefail

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${HOME}/vedant-agent-venv"
# Shared lock file between LinkedIn and Naukri bots to prevent OOM on 1GB RAM
LOCK_FILE="/tmp/vedant_browser_agent.lock"
PYTHON="${VENV_DIR}/bin/python"
AGENT_SCRIPT="${SCRIPT_DIR}/scripts/pi_naukri_agent.py"
ENV_FILE="${SCRIPT_DIR}/.env"

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${GREEN}[NAUKRI-AGENT]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[NAUKRI-AGENT]${NC}  $*"; }
error() { echo -e "${RED}[NAUKRI-AGENT]${NC} $*" >&2; }

# ── Sanity checks ────────────────────────────────────────────────────────────
if [[ ! -f "${PYTHON}" ]]; then
    # Fallback to system python3 if venv not at default path
    if command -v python3 >/dev/null 2>&1; then
        PYTHON="$(command -v python3)"
        warn "Venv not found at ${VENV_DIR}; falling back to system python: ${PYTHON}"
    else
        error "Python not found. Please run setup_naukri_pi.sh first."
        exit 1
    fi
fi

if [[ ! -f "${AGENT_SCRIPT}" ]]; then
    error "Naukri agent script not found at ${AGENT_SCRIPT}."
    exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
    warn ".env not found at ${ENV_FILE}."
    warn "Copy .env.example to .env and configure your Naukri credentials."
else
    # Security: enforce strict owner-only read/write permissions
    chmod 600 "${ENV_FILE}" 2>/dev/null || true
fi

# Security: protect persistent browser session cookies
if [[ -d "${HOME}/.naukri_bot_session" ]]; then
    chmod 700 "${HOME}/.naukri_bot_session" 2>/dev/null || true
fi

# ── Pre-launch cleanup: purge orphan Chromium processes if memory is tight ────
TOTAL_MEM_KB=$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}' || echo 1000000)
AVAIL_MEM_KB=$(grep MemAvailable /proc/meminfo 2>/dev/null | awk '{print $2}' || echo 500000)

if [[ ${AVAIL_MEM_KB} -lt 150000 ]]; then
    warn "Available memory is low (${AVAIL_MEM_KB} kB). Cleaning up zombie processes..."
    pkill -f "chromium-browser --headless" 2>/dev/null || true
    sleep 1
fi

# ── Memory guard: drop filesystem caches before launching Chromium ───────────
if [[ -w /proc/sys/vm/drop_caches ]]; then
    sync
    echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
fi

# ── Acquire exclusive lock across ALL browser automation agents ───────────────
# File descriptor 200 is used as the lock handle.
# flock -n = non-blocking; if LinkedIn or another Naukri run is active, exit gracefully.
exec 200>"${LOCK_FILE}"

if ! flock -n 200; then
    warn "Another browser agent (LinkedIn or Naukri) is currently running."
    warn "Lock held: ${LOCK_FILE}"
    warn "Skipping this run to avoid Raspberry Pi 3B+ memory exhaustion."
    exit 0
fi

info "Exclusive lock acquired on ${LOCK_FILE}"
info "Executing: ${PYTHON} ${AGENT_SCRIPT} $*"
info "────────────────────────────────────────────────────────"

# ── Launch the Python Naukri agent ────────────────────────────────────────────
# Inherit lock handle FD 200 so flock is retained throughout child lifetime
"${PYTHON}" "${AGENT_SCRIPT}" "$@"
EXIT_CODE=$?

# ── Post-run cleanup ──────────────────────────────────────────────────────────
if [[ ${EXIT_CODE} -eq 0 ]]; then
    info "Naukri agent task finished successfully."
else
    error "Naukri agent exited with code ${EXIT_CODE}."
fi

# Release cached memory pages after browser closes
if [[ -w /proc/sys/vm/drop_caches ]]; then
    sync
    echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
fi

exit ${EXIT_CODE}
