---
name: vedant-naukri-agent
description: >
  Autonomous job-hunting and recruiter outreach agent for Naukri.com, optimized to
  run 24/7 on a Raspberry Pi 3B+ (1GB RAM) with headless native Chromium, Playwright,
  Scrapling, and Antigravity CLI. Performs 8:55 AM IST daily profile refresh micro-edits
  to rank #1 in recruiter searches, executes direct 1-click applies with auto-screening
  drawer questionnaire resolution, tracks external portal redirects, monitors recruiter
  NVites/messages, and stages 3-pillar follow-up emails.
tags:
  - job-automation
  - naukri
  - playwright
  - raspberry-pi
  - python
  - web-scraping
  - cold-email
  - recruiter-outreach
version: "1.0.0"
author: Vedant Singh
---

# vedant-naukri-agent — Autonomous Naukri Automation Agent

An autonomous, memory-constrained agent that manages job hunting on **Naukri.com** directly from a Raspberry Pi 3B+ (1GB RAM).

---

## Candidate Profile (Ground-Truth Data)

| Field | Detail |
|---|---|
| **Candidate** | **Vedant Singh** |
| **Current Role** | Associate Analyst / Software Engineer at **Wipro Limited** (Enterprise Healthcare domain, Noida, Jan 2026 – Present) |
| **Prior Roles** | • **Altair Engineering x Siemens Energy:** HPC Intern (Apr 2025 – Jun 2025) — HPC cluster efficiency +37%, Terraform AWS/OCI rollout 5d -> 3d.<br>• **Proeffico Solutions:** Software Engineer Intern (AI/CV) (Oct 2024 – Jan 2025) — RAG pipeline with 30% lower hallucinations across 10k+ queries; YOLOv8 activity detection (>95% accuracy); C++/Python Raspberry Pi monitoring (30+ devices, 99% uptime).<br>• **Tata Motors:** Software Engineer Intern (Feb 2024 – May 2024) — YOLO safety modules (+28% production checks).<br>• **CRIS:** Summer Intern (Jun 2023 – Jul 2023) — Accessible railway ticketing system. |
| **Education** | **B.Tech in CSE**, SRM Institute of Science and Technology (2021 – 2025, CGPA: **8.21/10**) |
| **Core Skills** | Python, FastAPI, Generative AI, RAG, LLM, LangChain, Ollama, ChromaDB, Selenium, Playwright, Scrapling, SQL, AWS, Terraform, Jenkins CI/CD, Linux, Docker, YOLOv8, C++. |
| **Contact** | Configurable via `.env` (`CANDIDATE_PHONE`, `NAUKRI_EMAIL`) |
| **Online** | Configurable via `.env` (`PORTFOLIO_URL`, `LINKEDIN_URL`, `GITHUB_URL`) |

---

## Hardware Architecture (Raspberry Pi 3B+ / 1GB RAM)

Naukri's single-page web app is notoriously resource-heavy. To prevent Out-Of-Memory (OOM) kernel crashes, this skill strictly enforces:

1. **Native ARM64 Chromium:** Points Playwright directly to `/usr/bin/chromium-browser` via `executable_path`. Never downloads Playwright's default x86 binaries.
2. **Aggressive V8 & Chrome Caps:**
   - `--js-flags=--max-old-space-size=256` (limits V8 engine to 256 MB)
   - `--disable-dev-shm-usage` (uses `/tmp` instead of limited `/dev/shm`)
   - `--single-process`, `--no-zygote`, `--no-sandbox`, `--disable-gpu`
3. **Network Interception & Bloat Stripping:** Aborts requests for `image`, `media`, `font`, `stylesheet`, and ad networks (`google-analytics.com`, `doubleclick.net`, `naukri.com/ads`).
4. **Session Persistence:** Saves all login state and cookies at `~/.naukri_bot_session`.
5. **Shared Concurrency Lock:** Acquires an exclusive `flock -n 200 /tmp/vedant_browser_agent.lock` shared with `vedant-job-agent` so LinkedIn and Naukri browsers **never run concurrently** in RAM.
6. **ecoMode Integration:** Uses [vineetvedant/ecoMode](https://github.com/vineetvedant/ecoMode) for semantic compression of prompts and messages, saving token budgets and CPU overhead.

---

## Quick Start

```bash
# 1. Clone/copy into place on the Pi
cp -r vedant-naukri-agent/ ~/vedant-naukri-agent

# 2. Run Pi setup (configures 2GB swap, installs deps & staggered crontab)
chmod +x ~/vedant-naukri-agent/setup_naukri_pi.sh
sudo ~/vedant-naukri-agent/setup_naukri_pi.sh

# 3. Configure credentials
cp ~/vedant-naukri-agent/.env.example ~/vedant-naukri-agent/.env
chmod 600 ~/vedant-naukri-agent/.env
nano ~/vedant-naukri-agent/.env

# 4. One-time interactive login (stores session cookie in ~/.naukri_bot_session)
~/vedant-naukri-agent/run_naukri_agent.sh --mode login

# 5. Test profile refresh (micro-edits Resume Headline)
~/vedant-naukri-agent/run_naukri_agent.sh --mode refresh-profile

# 6. Test 1-click apply & screening drawer resolution
~/vedant-naukri-agent/run_naukri_agent.sh --mode search-apply

# 7. Check recruiter inbox & NVites
~/vedant-naukri-agent/run_naukri_agent.sh --mode inbox

# 8. Send 3-pillar follow-up email via SMTP (Human-in-the-Loop approval)
~/vedant-naukri-agent/run_naukri_agent.sh --mode email
```

---

## Workflows

### A — Daily Profile Optimizer (8:55 AM IST Peak Recruiter Refresh)
**Goal:** Guarantee Vedant's profile appears with the **"Profile Updated Today"** priority tag at the very top of Indian recruiter search filters when HR teams log in at 9:00 AM IST.

1. Agent opens `https://www.naukri.com/mnjuser/profile`.
2. Locates the **Resume headline** widget.
3. Performs a micro-edit by toggling a trailing period (`.`) on the headline.
4. Clicks **Save**. Naukri immediately updates the candidate's last-modified timestamp.
5. Re-uploads the latest `Vedant_Singh_Base_Resume.pdf` if present on disk.

### B — Targeted Job Scraping & Stack Alignment Scoring
**Goal:** Discover and evaluate new openings posted within the last 3 days matching Python, FastAPI, and GenAI.

1. Queries Naukri search endpoints using prioritized technical queries (`Python Developer`, `Generative AI Engineer`, `FastAPI Backend`, `SDET Python`).
2. Evaluates each listing against a fit score matrix (FastAPI, LangChain, RAG, SQL, AWS, Playwright).
3. Distinguishes between **Direct 1-Click Apply** vs. **External Portal Redirects**.

### C — 1-Click Apply & Screening Questionnaire Chatbot Resolution
**Goal:** Automatically complete direct applications without getting blocked by side-drawer screening forms.

1. Clicks "Apply on Naukri".
2. When the side-drawer chatbot modal appears asking standard questions, resolves them using `data/screening_answers.json`:
   - **Current CTC / Expected CTC:** 4.5 LPA / 9.5 LPA
   - **Notice Period:** 15 Days / Immediate Buyout
   - **Skill Experience:** Python (3 yrs), FastAPI (2 yrs), GenAI/RAG (1.5 yrs), SQL (2.5 yrs)
   - **Relocation / Work From Office:** "Yes"
3. Submits application (or stages for review if `AUTO_SUBMIT_APPLY=false`) and logs to `data/applied_jobs.json`.

### D — External Redirect Queue & Recruiter Extraction
**Goal:** Capture high-fit roles that redirect to Workday, Greenhouse, or Taleo.

1. Captures external job URL, company, and title into `data/external_jobs_queue.json`.
2. Scrapes any recruiter emails or hiring manager contacts mentioned in the JD snippet and logs them to `data/recruiter_leads.json`.

### E — Recruiter Messages & NVites Follow-Up
**Goal:** Never miss an inbound recruiter inquiry or direct NVite.

1. Opens `https://www.naukri.com/mnjuser/inbox`.
2. Extracts recruiter name, role, contact phone/email, and JD snippets.
3. Stages personalized reply drafts in `data/pending_replies.json`.
4. `--mode email` triggers Gmail SMTP dispatch of the 3-pillar outreach message with resume PDF attached, requiring terminal confirmation `[y/N]`.

---

## Modes Reference

| Mode | Command Flag | Description |
|---|---|---|
| **Login** | `--mode login` | Interactive browser launch to sign into Naukri; caches session cookies. |
| **Profile Refresh** | `--mode refresh-profile` | Toggles headline micro-edit at 8:55 AM IST to claim "#1 Updated Today". |
| **Search & Apply** | `--mode search-apply` | 1-Click applies to matching jobs and resolves screening chatbots. |
| **Inbox & NVites** | `--mode inbox` | Checks recruiter inbox, extracts emails, and stages responses. |
| **Email Outreach** | `--mode email` | Dispatches 3-pillar cold email via Gmail SMTP (interactive confirm). |
| **ecoMode** | `--eco` / `--eco-max` | Applies token-saving compression to drafts and LLM calls. |

---

## Environment Variables (`.env`)

See [`.env.example`](.env.example) for all parameters:

| Variable | Default | Purpose |
|---|---|---|
| `NAUKRI_EMAIL` | `your_email@example.com` | Login username |
| `NAUKRI_PASSWORD` | `CHANGE_ME` | Login password |
| `GMAIL_ADDRESS` | `your_gmail@example.com` | SMTP sender |
| `GMAIL_APP_PASSWORD` | `CHANGE_ME` | 16-character Google App Password |
| `RESUME_PATH` | `/home/pi/Resume.pdf` | Resume PDF path |
| `CHROMIUM_PATH` | `/usr/bin/chromium-browser` | Native ARM Chromium binary |
| `SESSION_DIR` | `~/.naukri_bot_session` | Persistent cookie directory |
| `DATA_DIR` | `~/.vedant_naukri_data` | Ledger, logs, and queue directory |
| `AUTO_SUBMIT_APPLY` | `true` | Auto-submit 1-click apply after answering drawer |
| `MIN_FIT_SCORE` | `60` | Minimum score (0–100) to apply |
| `ECO_MODE` | `true` | Token saving semantic compression |

---

## Staggered Cron Schedule (No RAM Collision)

`setup_naukri_pi.sh` installs the following schedule, strategically offset from the LinkedIn agent:

```cron
# 8:55 AM IST (Mon–Sat): Peak Recruiter Search Boost
55 8 * * 1-6 /home/pi/vedant-naukri-agent/run_naukri_agent.sh --mode refresh-profile >> /home/pi/vedant_naukri_agent.log 2>&1

# 12:00 PM & 5:30 PM IST: 1-Click Search & Apply
0 12,17 * * * /home/pi/vedant-naukri-agent/run_naukri_agent.sh --mode search-apply >> /home/pi/vedant_naukri_agent.log 2>&1

# 1:30 PM & 7:30 PM IST: Recruiter Messages & NVites
30 13,19 * * * /home/pi/vedant-naukri-agent/run_naukri_agent.sh --mode inbox >> /home/pi/vedant_naukri_agent.log 2>&1
```

---

## Security & Ethics

1. **Shared Concurrency Lock:** Uses `flock -n 200 /tmp/vedant_browser_agent.lock` so Chromium never runs simultaneously across agents.
2. **Strict File Permissions:** `.env` is locked to `chmod 600` and session directories to `chmod 700`.
3. **Secret Redaction:** Passwords and session cookies are masked in logs and exceptions.
4. **Human-in-the-Loop Email:** Cold emails require interactive terminal confirmation `[y/N]` before transmission.
5. **Human Mimicry:** Dynamic delay intervals (`2-5 s`) between page interactions avoid anti-bot tripwires.
