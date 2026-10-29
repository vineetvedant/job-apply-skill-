---
name: vedant-job-agent
description: >
  Autonomous LinkedIn job-hunting agent optimized for Raspberry Pi 3B+ (1 GB RAM).
  Uses headless Chromium via Playwright + Scrapling to scan job posts, extract recruiter
  contacts, generate 3-pillar cold emails, stage referral DMs, and manage inbox replies—
  all within a Human-in-the-Loop safety model. No message is ever sent without explicit
  operator confirmation.
tags:
  - linkedin
  - job-search
  - automation
  - raspberry-pi
  - playwright
  - scrapling
  - cold-email
  - outreach
version: "1.0.0"
author: Vedant Singh
---

# vedant-job-agent

> **Autonomous LinkedIn Job-Hunting Agent for Raspberry Pi 3B+**

An end-to-end skill that turns a $35 single-board computer into a 24/7 job-search
assistant. It scrapes LinkedIn hiring posts, scores job-fit, drafts personalized cold
emails and referral messages, and manages recruiter conversations—all while staying
under a 1 GB RAM ceiling.

---

## Table of Contents

1. [Candidate Profile](#candidate-profile)
2. [Hardware Constraints](#hardware-constraints)
3. [Quick Start](#quick-start)
4. [Workflows](#workflows)
   - [A — Job Screenshot / Link Extraction & Fit Scoring](#a--job-screenshot--link-extraction--fit-scoring)
   - [B — 3-Pillar Cold Email & Referral Outreach](#b--3-pillar-cold-email--referral-outreach)
   - [C — Recruiter Conversation Management & Draft Reply Staging](#c--recruiter-conversation-management--draft-reply-staging)
   - [D — Local Playwright Execution](#d--local-playwright-execution)
5. [Modes Reference](#modes-reference)
6. [Environment Variables](#environment-variables)
7. [Cron Schedule](#cron-schedule)
8. [Security & Ethics](#security--ethics)

---

## Candidate Profile

| Field | Value |
|---|---|
| **Name** | Vedant Singh |
| **Current Role** | Associate Analyst / Software Engineer — Wipro Limited (Enterprise Healthcare, Noida, Jan 2026 – Present) |
| **Education** | B.Tech CSE, SRM Institute of Science and Technology (2021-2025, CGPA 8.21/10) |
| **Core Stack** | Python, FastAPI, Selenium, Playwright, Scrapling, LangChain, Ollama, ChromaDB, SQL, Docker, Jenkins, Terraform, AWS, Linux |
| **Contact** | Configurable via `.env` (`CANDIDATE_PHONE`, `GMAIL_ADDRESS`, `LINKEDIN_EMAIL`) |
| **Online** | Configurable via `.env` (`PORTFOLIO_URL`, `LINKEDIN_URL`, `GITHUB_URL`) |
| **Location** | Delhi NCR, India · Open to hybrid / remote / relocation |

### Prior Experience

| Period | Organization | Role | Highlights |
|---|---|---|---|
| Apr 2025 – Jun 2025 | Altair Engineering × Siemens Energy | HPC Intern | HPC cluster efficiency +37 %; Terraform AWS/OCI rollout 5 d → 3 d |
| Oct 2024 – Jan 2025 | Proeffico Solutions | Software Engineer Intern (AI/CV) | RAG pipeline (30 % lower hallucinations, 10 k+ queries); YOLOv8 activity detection (> 95 % accuracy); C++/Python RPi monitoring (30+ devices, 99 % uptime) |
| Feb 2024 – May 2024 | Tata Motors | Software Engineer Intern | YOLO safety modules (+28 % production checks) |
| Jun 2023 – Jul 2023 | CRIS (Centre for Railway Information Systems) | Intern | Accessible railway ticketing system |

---

## Hardware Constraints

The agent **must** run within these guardrails to avoid OOM kills on a Pi 3B+ (1 GB):

| Constraint | Implementation |
|---|---|
| Native browser only | Execute `/usr/bin/chromium-browser` — never download x86 Playwright bundles |
| RAM caps | `--disable-dev-shm-usage --no-sandbox --single-process --no-zygote --js-flags=--max-old-space-size=256 --disable-gpu` |
| Network interception | Abort routes for `image`, `media`, `font`, `stylesheet` |
| Session persistence | Cache at `~/.linkedin_bot_session` |
| Concurrency lock | `flock -n 200` on `/tmp/vedant_linkedin_agent.lock` |
| Safety | Human-in-the-Loop — drafts only, no auto-submit |

---

## Quick Start

```bash
# 1  Clone / copy the skill into place
cp -r vedant-job-agent/ ~/.agents/skills/vedant-job-agent

# 2  Run the Pi bootstrap (sets swap, gpu_mem, installs deps)
chmod +x vedant-job-agent/setup_pi.sh
sudo vedant-job-agent/setup_pi.sh

# 3  Copy and fill out the env file
cp vedant-job-agent/.env.example vedant-job-agent/.env
nano vedant-job-agent/.env

# 4  First-time LinkedIn login (interactive — stores session cookie)
./vedant-job-agent/run_agent.sh --mode login

# 5  Scan posts for job leads
./vedant-job-agent/run_agent.sh --mode scan-posts

# 6  Send a cold email (draft shown first, you confirm)
./vedant-job-agent/run_agent.sh --mode email

# 7  Stage referral DMs
./vedant-job-agent/run_agent.sh --mode referral

# 8  Manage inbox
./vedant-job-agent/run_agent.sh --mode inbox
```

---

## Workflows

### A — Job Screenshot / Link Extraction & Fit Scoring

**Goal:** Continuously discover relevant openings by monitoring LinkedIn feeds and
search results, then rank each opportunity against the candidate profile.

**Steps:**

1. The agent opens LinkedIn Jobs search (`--mode scan-posts`) with keyword queries
   derived from the candidate's core strengths (Python, FastAPI, Playwright, etc.).
2. Playwright scrolls through the results list, using Scrapling to extract structured
   data: job title, company, location, description snippet, and posting date.
3. Each listing is scored against a weighted checklist:
   - **Stack overlap** (40 %) — how many required skills match.
   - **Experience band** (25 %) — does YOE range match the candidate?
   - **Location fit** (20 %) — remote / hybrid / NCR / relocation-friendly.
   - **Company tier** (15 %) — bonus for target companies or high-growth startups.
4. Results ≥ 60 % fit score are written to a local JSON ledger
   (`~/.vedant_agent_data/leads.json`) for downstream outreach.
5. If emails are found in the post body or profile, they're extracted and stored
   alongside the lead record.

### B — 3-Pillar Cold Email & Referral Outreach

**Goal:** Draft and send personalized cold emails that demonstrate deep relevance,
using the 3-pillar framework (see `references/outreach_templates.md`).

**Pillars:**

| # | Pillar | Maps to |
|---|---|---|
| 1 | Generative AI & LLM Deployment | RAG pipelines, LangChain, Ollama, ChromaDB |
| 2 | Backend Architecture & APIs | FastAPI, Selenium, Playwright, Scrapling |
| 3 | Data Integrity & Cloud Infrastructure | Docker, Terraform, AWS, Jenkins, SQL |

**Steps:**

1. Agent reads the lead from the ledger and hydrates the email template with:
   - Recipient name and company
   - Matching pillar highlights
   - Tailored subject line
2. SMTP is configured via `.env` (Gmail App Password).
3. A draft is printed to the console. **The operator must press Enter to confirm
   sending.**
4. On confirmation, the email is dispatched with the resume PDF attached.

### C — Recruiter Conversation Management, Draft Reply & Follow-Up Staging

**Goal:** Keep recruiter threads warm and proactively nudge unanswered inquiries without risking a poorly-timed auto-reply.

**Steps:**

1. `--mode inbox` opens LinkedIn messaging and runs a two-phase check:
   - **Phase 1 (Unread Replies):** Scans unread incoming messages, classifies them (`interview`, `schedule`, `rejection`, `followup`, `generic`), and types a draft reply into the compose box.
   - **Phase 2 (Follow-Up Detection):** Scans outbound conversations where the candidate sent the last message `FOLLOWUP_DAYS` ago (default: 3 days) with no reply. Stages a polite follow-up nudge DM into the compose box.
2. **ecoMode Integration:** When generating AI replies via Ollama, uses `ecomode` (based on [vineetvedant/ecoMode](https://github.com/vineetvedant/ecoMode)) to sanitize untrusted input, apply semantic prompt compression (<45 instruction tokens), and budget output tokens (`num_predict: 50-80`), conserving Pi 3B+ RAM and compute time.
3. The draft is **typed into the message box but NOT submitted**. The cursor is left in the compose area so the operator can review, edit, and press Send manually.
4. All staged replies and follow-ups are recorded in `inbox_log.json` and `followup_log.json` to prevent repetitive nudges (capped by `MAX_FOLLOWUPS_PER_THREAD`).

### D — Local Playwright Execution

**Prerequisites:**

- Raspberry Pi 3B+ running Raspberry Pi OS Lite (Bookworm or later).
- `setup_pi.sh` has been run (swap, gpu_mem, deps).
- `.env` file is populated with restrictive `chmod 600` permissions.

**Execution:**

```bash
# Always use run_agent.sh — it enforces flock, memory limits, and permission security
./run_agent.sh --mode <mode>

# Run with ecoMode token compression enabled
./run_agent.sh --mode inbox --eco

# Run with ecoMode maximum compression (extreme brevity, delta-only)
./run_agent.sh --mode inbox --eco-max
```

**Troubleshooting:**

| Symptom | Fix |
|---|---|
| `oom-killer` in `dmesg` | Increase swap to 4 GB in `setup_pi.sh`; reduce `--max-old-space-size` to 128 |
| Login CAPTCHA loop | Delete `~/.linkedin_bot_session` and re-run `--mode login` |
| `flock: failed to lock` | Another agent instance is running; wait or kill it |
| Chromium crash on launch | Ensure `gpu_mem=16` is set in `/boot/config.txt` and reboot |

---

## Modes Reference

| Mode | Flag | Description |
|---|---|---|
| Login | `--mode login` | Opens persistent browser for manual LinkedIn login; saves session |
| Easy Apply | `--mode easy-apply` | Searches `f_AL=true` past 48h roles, resolves screening drawer & stages outreach |
| Pipeline | `--mode pipeline` | Runs full continuous loop: scan -> easy-apply -> referral -> inbox |
| Scan Posts | `--mode scan-posts` | Scrapes hiring posts; extracts emails; scores fit |
| Email | `--mode email` | Drafts & sends cold email via SMTP (confirm required) |
| Referral | `--mode referral` | Finds company engineers; stages connection + DM drafts |
| Inbox | `--mode inbox` | Reads unread messages; types draft replies & stages follow-ups (no auto-send) |
| ecoMode | `--eco` / `--eco-max` | Applies token-saving semantic compression and prompt injection defense |

---

## Environment Variables

See [`.env.example`](.env.example) for all required variables:

| Variable | Purpose |
|---|---|
| `LINKEDIN_EMAIL` | LinkedIn login email |
| `LINKEDIN_PASSWORD` | LinkedIn login password |
| `GMAIL_ADDRESS` | Gmail sender address |
| `GMAIL_APP_PASSWORD` | Gmail App Password (not account password) |
| `RESUME_PATH` | Absolute path to resume PDF |
| `CHROMIUM_PATH` | Path to native Chromium binary (default: `/usr/bin/chromium-browser`) |
| `SESSION_DIR` | Path for session persistence (default: `~/.linkedin_bot_session`) |
| `DATA_DIR` | Path for leads ledger and logs (default: `~/.vedant_agent_data`) |
| `OLLAMA_ENDPOINT` | Optional — network Ollama URL for smarter reply drafting |
| `FOLLOWUP_DAYS` | Days without reply before staging a follow-up nudge (default: `3`) |
| `MAX_FOLLOWUPS_PER_THREAD` | Maximum follow-ups per conversation to avoid spam (default: `2`) |
| `ECO_MODE` | Enable token-saving semantic compression (`true`/`false`) |
| `ECO_MODE_LEVEL` | Compression level: `eco` (balanced) or `eco max` (delta-only) |

---

## Cron Schedule

`setup_pi.sh` installs the following crontab entries:

```cron
# Scan LinkedIn posts for new leads every 4 hours (06:00 – 22:00)
0 6,10,14,18,22 * * * /home/pi/vedant-job-agent/run_agent.sh --mode scan-posts >> /home/pi/vedant_agent.log 2>&1

# Check inbox & stage follow-ups every 2 hours (08:00 – 20:00)
0 8,10,12,14,16,18,20 * * * /home/pi/vedant-job-agent/run_agent.sh --mode inbox >> /home/pi/vedant_agent.log 2>&1
```

---

## Security & Ethics

1. **Prompt Injection Defense.** Untrusted external messages and scraped posts are sanitized via `ecomode.sanitize_input()` before entering LLM prompts or templates. Injection markers like `ignore previous instructions`, `<system>`, or extraction attempts are quarantined.
2. **Secret Redaction in Logs.** Passwords, Gmail app passwords, auth cookies (`li_at`), and session tokens are automatically masked via `SensitiveMaskingFormatter`.
3. **Strict Linux File Permissions.** `.env` is locked down to `chmod 600` (read/write owner only) and session directories are set to `chmod 700`, preventing multi-user access on the Raspberry Pi.
4. **Human-in-the-Loop.** Every outgoing email requires console `[y/N]` confirmation. LinkedIn DMs and inbox replies are typed into the browser compose box but never automatically submitted.
5. **Rate limiting & Anti-Ban.** Dynamic delays (`2-5 s`) between page actions mimic authentic human browsing.
6. **Session isolation.** Persistent cookies are stored locally at `~/.linkedin_bot_session` and never transmitted externally.

