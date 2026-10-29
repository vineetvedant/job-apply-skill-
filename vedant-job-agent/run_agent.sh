#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  vedant-job-agent — Memory-Safe Runner                                     ║
# ║  Guarantees single Chromium instance via flock.                            ║
# ║  Usage:  ./run_agent.sh --mode <login|scan-posts|easy-apply|pipeline|email|referral|inbox> ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
set -euo pipefail

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${HOME}/vedant-agent-venv"
# Shared browser lock across LinkedIn and Naukri agents to prevent Pi 3B+ OOM crashes
LOCK_FILE="/tmp/vedant_browser_agent.lock"
PYTHON="${VENV_DIR}/bin/python"
AGENT_SCRIPT="${SCRIPT_DIR}/scripts/pi_linkedin_agent.py"
ENV_FILE="${SCRIPT_DIR}/.env"

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[AGENT]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[AGENT]${NC}  $*"; }
error() { echo -e "${RED}[AGENT]${NC} $*" >&2; }

# ── Sanity checks ────────────────────────────────────────────────────────────
if [[ ! -f "${PYTHON}" ]]; then
    error "Python venv not found at ${VENV_DIR}."
    error "Run setup_pi.sh first."
    exit 1
fi

if [[ ! -f "${AGENT_SCRIPT}" ]]; then
    error "Agent script not found at ${AGENT_SCRIPT}."
    exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
    warn ".env not found at ${ENV_FILE} — agent may fail."
    warn "Copy .env.example to .env and fill in your credentials."
else
    # Security: enforce strict owner-only permissions on secrets
    chmod 600 "${ENV_FILE}" 2>/dev/null || true
fi

# Security: enforce private permissions on session cookie store
if [[ -d "${HOME}/.linkedin_bot_session" ]]; then
    chmod 700 "${HOME}/.linkedin_bot_session" 2>/dev/null || true
fi

# ── Memory guard: drop filesystem caches before launch ────────────────────────
if [[ -w /proc/sys/vm/drop_caches ]]; then
    sync
    echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
fi

# ── Acquire exclusive lock (flock) ────────────────────────────────────────────
# File descriptor 200 is used as the lock handle.
# flock -n = non-blocking; if another instance holds the lock, exit immediately.
exec 200>"${LOCK_FILE}"

if ! flock -n 200; then
    error "Another vedant-job-agent instance is already running."
    error "Lock file: ${LOCK_FILE}"
    error "Wait for it to finish, or kill the process manually."
    exit 1
fi

info "Lock acquired: ${LOCK_FILE}"
info "Starting agent with args: $*"
info "────────────────────────────────────────────────────────"

# ── Launch the Python agent ───────────────────────────────────────────────────
# Inherit the lock FD so flock remains held for the duration of the child.
"${PYTHON}" "${AGENT_SCRIPT}" "$@"
EXIT_CODE=$?

# ── Cleanup ───────────────────────────────────────────────────────────────────
# Lock is automatically released when FD 200 closes (script exit).
if [[ ${EXIT_CODE} -eq 0 ]]; then
    info "Agent finished successfully."
else
    error "Agent exited with code ${EXIT_CODE}."
fi

exit ${EXIT_CODE}
