#!/usr/bin/env python3
"""
vedant-naukri-agent — Autonomous Naukri.com Job Automation Agent
Optimized for Raspberry Pi 3B+ (1GB RAM) with native Chromium, Playwright & Scrapling.

Candidate: Vedant Singh (Associate Analyst / SWE @ Wipro Limited)
Core Strengths: Python, FastAPI, Generative AI (RAG, LLM), AWS, Terraform, Docker.

Features:
  1. --mode login           : Interactive session initialization and cookie caching.
  2. --mode refresh-profile : Micro-edits Resume Headline at 8:55 AM IST so profile ranks #1.
  3. --mode search-apply    : 1-Click Apply on direct Naukri jobs & answers screening questions.
  4. --mode inbox           : Monitors Recruiter Messages & NVites; extracts leads and stages replies.
  5. --mode email           : Dispatches 3-pillar cold outreach with PDF resume via Gmail SMTP.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import re
import smtplib
import sys
import time
from datetime import datetime, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Import local ecoMode if available (from sibling or local scripts) ──────────
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR.parent.parent / "vedant-job-agent" / "scripts"))

try:
    import ecomode
    ECOMODE_AVAILABLE = True
except ImportError:
    ECOMODE_AVAILABLE = False

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(path: Optional[str] = None) -> None:
        if path and Path(path).exists():
            for line in Path(path).read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())

try:
    from rich.console import Console
    from rich.table import Table
    console = Console()
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    console = None

try:
    from playwright.sync_api import sync_playwright, BrowserContext, Page, Route
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS & GROUND TRUTH
# ═══════════════════════════════════════════════════════════════════════════════

NAUKRI_BASE = "https://www.naukri.com"
NAUKRI_LOGIN_URL = "https://www.naukri.com/nlogin/login"
NAUKRI_PROFILE_URL = "https://www.naukri.com/mnjuser/profile"
NAUKRI_INBOX_URL = "https://www.naukri.com/mnjuser/inbox"
NAUKRI_SEARCH_URL = "https://www.naukri.com/{slug}-jobs?k={keyword}&experience=1&jobAge=3"

DEFAULT_HEADLINE = (
    "Software Engineer at Wipro | Python, FastAPI, Generative AI (RAG, LLMs, LangChain) | "
    "Cloud & DevOps (AWS, Terraform, Docker, Jenkins) | SDET & Automation (Selenium, Playwright) | "
    "B.Tech CSE (8.21 CGPA)"
)

# Ad and tracking domains to abort on Pi 3B+ to save RAM
BLOCKED_URL_PATTERNS = [
    "google-analytics.com",
    "googletagmanager.com",
    "doubleclick.net",
    "naukri.com/ads",
    "adnxs.com",
    "facebook.net",
    "scorecardresearch.com",
    "clarity.ms",
    "hotjar.com",
]

# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY & LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

log = logging.getLogger("vedant-naukri-agent")


class SensitiveMaskingFormatter(logging.Formatter):
    """Redacts secrets, passwords, and tokens from all log messages."""

    def format(self, record: logging.LogRecord) -> str:
        orig = super().format(record)
        if ECOMODE_AVAILABLE:
            return ecomode.mask_sensitive(orig)
        return re.sub(r"(?i)(password|secret|pwd)=['\"]?[^\s'\"&]+['\"]?", r"\1=***REDACTED***", orig)


def setup_logging(level: str = "INFO") -> None:
    """Configure logging with timestamp, level, and secret redaction."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    numeric = getattr(logging, level.upper(), logging.INFO) if hasattr(level, "upper") else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        SensitiveMaskingFormatter(
            fmt="%(asctime)s  %(levelname)-8s  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root_log = logging.getLogger()
    root_log.setLevel(numeric)
    root_log.handlers = [handler]


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

class Config:
    """Loads and validates Naukri environment variables and screening defaults."""

    def __init__(self) -> None:
        script_dir = Path(__file__).resolve().parent.parent
        env_path = script_dir / ".env"
        load_dotenv(str(env_path))

        self.naukri_email: str = os.getenv("NAUKRI_EMAIL", "")
        self.naukri_password: str = os.getenv("NAUKRI_PASSWORD", "")
        self.gmail_address: str = os.getenv("GMAIL_ADDRESS", "")
        self.gmail_app_password: str = os.getenv("GMAIL_APP_PASSWORD", "")
        self.resume_path: str = os.getenv("RESUME_PATH", "/home/pi/Resume.pdf")
        self.chromium_path: str = os.getenv("CHROMIUM_PATH", "/usr/bin/chromium-browser")
        self.session_dir: str = os.path.expanduser(os.getenv("SESSION_DIR", "~/.naukri_bot_session"))
        self.data_dir: str = os.path.expanduser(os.getenv("DATA_DIR", "~/.vedant_naukri_data"))

        # Candidate details
        self.candidate_name: str = os.getenv("CANDIDATE_NAME", "Job Applicant")
        self.candidate_phone: str = os.getenv("CANDIDATE_PHONE", "")
        self.current_company: str = os.getenv("CURRENT_COMPANY", "Tech Company")
        self.current_role: str = os.getenv("CURRENT_ROLE", "Software Engineer")
        self.total_experience_years: float = float(os.getenv("TOTAL_EXPERIENCE_YEARS", "1.5"))
        self.current_ctc_lpa: float = float(os.getenv("CURRENT_CTC_LPA", "5.0"))
        self.expected_ctc_lpa: float = float(os.getenv("EXPECTED_CTC_LPA", "10.0"))
        self.notice_period_days: int = int(os.getenv("NOTICE_PERIOD_DAYS", "15"))
        self.notice_period_text: str = os.getenv("NOTICE_PERIOD_TEXT", "15 Days / Immediate")
        self.current_location: str = os.getenv("CURRENT_LOCATION", "Delhi NCR")
        self.ready_to_relocate: str = os.getenv("READY_TO_RELOCATE", "Yes")

        # Job search keywords
        raw_keywords = os.getenv(
            "SEARCH_KEYWORDS",
            "Python Developer,Generative AI Engineer,FastAPI Backend,SDET Python",
        )
        self.search_keywords: list[str] = [k.strip() for k in raw_keywords.split(",") if k.strip()]

        # Search locations
        raw_locations = os.getenv("SEARCH_LOCATIONS", "Noida,Delhi / NCR,Gurgaon / Gurugram,Bengaluru,Remote")
        self.search_locations: list[str] = [l.strip() for l in raw_locations.split(",") if l.strip()]

        # Operational parameters
        self.min_fit_score: int = int(os.getenv("MIN_FIT_SCORE", "60"))
        self.max_applications_per_run: int = int(os.getenv("MAX_APPLICATIONS_PER_RUN", "20"))
        self.job_posted_days: int = int(os.getenv("JOB_POSTED_DAYS", "3"))
        self.action_delay_min: float = float(os.getenv("ACTION_DELAY_MIN", "2"))
        self.action_delay_max: float = float(os.getenv("ACTION_DELAY_MAX", "5"))
        self.auto_submit_apply: bool = os.getenv("AUTO_SUBMIT_APPLY", "true").lower() in ("true", "1", "yes")
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")

        # ecoMode
        self.eco_mode: bool = os.getenv("ECO_MODE", "true").lower() in ("true", "1", "yes")
        self.eco_mode_level: str = os.getenv("ECO_MODE_LEVEL", "eco")

        # Ensure directories exist
        Path(self.session_dir).mkdir(parents=True, exist_ok=True)
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)

    @property
    def screening_answers_file(self) -> Path:
        return Path(__file__).resolve().parent.parent / "data" / "screening_answers.json"

    @property
    def applied_ledger_file(self) -> Path:
        return Path(self.data_dir) / "applied_jobs.json"

    @property
    def external_jobs_file(self) -> Path:
        return Path(self.data_dir) / "external_jobs_queue.json"

    @property
    def recruiter_leads_file(self) -> Path:
        return Path(self.data_dir) / "recruiter_leads.json"

    @property
    def pending_replies_file(self) -> Path:
        return Path(self.data_dir) / "pending_replies.json"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA PERSISTENCE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def load_json_list(path: Path) -> list[dict[str, Any]]:
    """Loads a JSON array from disk, or returns an empty list."""
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return []


def save_json_list(path: Path, data: list[dict[str, Any]]) -> None:
    """Atomically saves a JSON array to disk."""
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    temp_path.replace(path)


# ═══════════════════════════════════════════════════════════════════════════════
# HARDWARE CONSTRAINT ENFORCEMENT & BROWSER FACTORY (Pi 3B+)
# ═══════════════════════════════════════════════════════════════════════════════

def create_naukri_browser_context(pw: Any, config: Config, headless: bool = True) -> BrowserContext:
    """
    Spawns Chromium on Raspberry Pi 3B+ under strict memory caps:
      - Native ARM binary: /usr/bin/chromium-browser
      - Max V8 heap: 256MB
      - Single-process & no-zygote
      - Persistent profile: ~/.naukri_bot_session
      - Intercepts and blocks images, fonts, media, and heavy ad trackers.
    """
    chromium_bin = config.chromium_path
    if not (chromium_bin and Path(chromium_bin).exists()):
        if Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe").exists():
            chromium_bin = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        elif Path("/usr/bin/chromium").exists():
            chromium_bin = "/usr/bin/chromium"
        elif Path("/usr/bin/chromium-browser").exists():
            chromium_bin = "/usr/bin/chromium-browser"
        else:
            log.warning(f"Native Chromium not at {chromium_bin}; Playwright will try default.")
            chromium_bin = None

    chromium_args = [
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--single-process",
        "--no-zygote",
        "--js-flags=--max-old-space-size=256",
        "--disable-gpu",
        "--disable-extensions",
        "--disable-background-networking",
        "--disable-default-apps",
        "--disable-sync",
        "--disable-translate",
        "--blink-settings=imagesEnabled=false",
    ]

    if os.name == "nt":
        drop_flags = {"--single-process", "--no-zygote", "--disable-dev-shm-usage"}
        chromium_args = [a for a in chromium_args if a not in drop_flags]
        chromium_args.append("--disable-blink-features=AutomationControlled")

    launch_kwargs: dict[str, Any] = {
        "user_data_dir": config.session_dir,
        "headless": headless,
        "args": chromium_args,
        "viewport": {"width": 1280, "height": 800},
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ) if os.name == "nt" else (
            "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
    }
    if chromium_bin:
        launch_kwargs["executable_path"] = chromium_bin

    has_session = False
    sess_path = Path(config.session_dir)
    if sess_path.exists():
        for f in sess_path.rglob("*"):
            if "cookie" in f.name.lower() and f.is_file() and f.stat().st_size > 512:
                has_session = True
                break

    if not headless or has_session:
        context = pw.chromium.launch_persistent_context(**launch_kwargs)
    else:
        exec_path = launch_kwargs.get("executable_path")
        browser = pw.chromium.launch(
            headless=headless,
            args=chromium_args,
            executable_path=exec_path,
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=launch_kwargs["user_agent"],
            locale="en-US",
            timezone_id="Asia/Kolkata",
            ignore_https_errors=True,
            java_script_enabled=True,
        )

    # Apply network route interception to conserve RAM
    def _block_bloat_resources(route: Route) -> None:
        req = route.request
        url_lower = req.url.lower()

        # Block heavy static media
        if req.resource_type in ("image", "media", "font"):
            route.abort()
            return

        # Block ad and tracking networks
        if any(bad in url_lower for bad in BLOCKED_URL_PATTERNS):
            route.abort()
            return

        route.continue_()

    context.route("**/*", _block_bloat_resources)
    return context


def human_delay(config: Config, multiplier: float = 1.0) -> None:
    """Randomized delay to simulate realistic human browsing."""
    delay = random.uniform(config.action_delay_min, config.action_delay_max) * multiplier
    time.sleep(delay)


# ═══════════════════════════════════════════════════════════════════════════════
# MODE 1: LOGIN (Interactive Session Setup)
# ═══════════════════════════════════════════════════════════════════════════════

def mode_login(config: Config) -> None:
    """
    Opens browser with the persistent session so the user can log in once.
    Cookies are saved at ~/.naukri_bot_session for all future headless runs.
    """
    if not PLAYWRIGHT_AVAILABLE:
        log.error("Playwright is not installed.")
        sys.exit(1)

    log.info("Starting browser for interactive Naukri login...")
    with sync_playwright() as pw:
        # Launch with headless=False so operator can see browser / solve captcha if prompted
        ctx = create_naukri_browser_context(pw, config, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        log.info(f"Navigating to {NAUKRI_LOGIN_URL}...")
        page.goto(NAUKRI_LOGIN_URL, wait_until="domcontentloaded", timeout=45000)

        # Pre-fill email if field is available
        try:
            email_field = page.query_selector("input[placeholder*='Username'], input[placeholder*='Email']")
            if email_field and config.naukri_email:
                email_field.fill(config.naukri_email)
                log.info(f"Pre-filled email: {config.naukri_email}")
        except Exception:
            pass

        print("\n" + "═" * 65)
        print("  🔑  NAUKRI INTERACTIVE LOGIN REQUIRED")
        print("  1. Complete login (Enter OTP or Password in the open browser).")
        print("  2. Verify you see your Naukri homepage / dashboard.")
        print("  3. Come back to this terminal and press [Enter] to save session.")
        print("═" * 65 + "\n")

        try:
            input("Press [Enter] after successful login: ")
        except (EOFError, KeyboardInterrupt):
            pass

        # Verify login state
        cookies = ctx.cookies()
        session_cookies = [c for c in cookies if "naukri" in c.get("domain", "")]
        log.info(f"Captured {len(session_cookies)} Naukri session cookies.")

        ctx.close()
        log.info(f"✅ Session successfully saved to {config.session_dir}")


# ═══════════════════════════════════════════════════════════════════════════════
# MODE 2: REFRESH PROFILE (Headline Micro-Edit at 8:55 AM IST)
# ═══════════════════════════════════════════════════════════════════════════════

def mode_refresh_profile(config: Config) -> None:
    """
    Daily Profile Optimizer:
      1. Navigates to naukri.com/mnjuser/profile
      2. Toggles trailing dot on Resume Headline (or updates to keyword-rich headline).
      3. Clicks Save -> triggers Naukri's 'Profile Updated Today' badge for recruiters.
      4. Optionally re-uploads the base resume PDF to refresh resume timestamp.
    """
    if not PLAYWRIGHT_AVAILABLE:
        log.error("Playwright is not installed.")
        sys.exit(1)

    log.info("Starting Naukri daily profile refresh...")
    with sync_playwright() as pw:
        ctx = create_naukri_browser_context(pw, config, headless=True)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        log.info(f"Navigating to {NAUKRI_PROFILE_URL}...")
        try:
            page.goto(NAUKRI_PROFILE_URL, wait_until="domcontentloaded", timeout=45000)
            human_delay(config)
        except Exception as exc:
            log.error(f"Failed to load profile page: {exc}")
            ctx.close()
            return

        # Verify not bounced to login
        if "login" in page.url.lower():
            log.error("Session expired or not logged in. Please run: ./run_naukri_agent.sh --mode login")
            ctx.close()
            return

        # ── 1. Update Resume Headline ─────────────────────────────────────────
        try:
            log.info("Locating Resume Headline section...")
            # Click edit icon on resume headline
            edit_headline_btn = page.query_selector(
                "div.resumeHeadline span.edit.icon, "
                "div.resumeHeadline a.edit, "
                "span:has-text('Resume headline') ~ span.edit, "
                "div.widgetHead:has-text('Resume headline') span.edit"
            )

            if edit_headline_btn:
                edit_headline_btn.click()
                human_delay(config, multiplier=0.8)

                # Locate headline textarea
                headline_input = page.query_selector(
                    "div.resumeHeadline div.custom-textarea textarea, "
                    "textarea#resumeHeadlineTxt, "
                    "div.drawer-wrapper textarea"
                )

                if headline_input:
                    current_text = headline_input.input_value().strip()
                    log.info(f"Current Headline: {current_text[:80]}...")

                    # Algorithm: toggle trailing dot or set default optimized headline
                    if not current_text or len(current_text) < 30:
                        new_text = DEFAULT_HEADLINE
                    elif current_text.endswith("."):
                        new_text = current_text[:-1].strip()
                    else:
                        new_text = current_text + "."

                    # Ensure length constraint (<250 chars)
                    if len(new_text) > 245:
                        new_text = new_text[:240].rstrip() + "."

                    headline_input.fill(new_text)
                    human_delay(config, multiplier=0.5)

                    # Click Save button
                    save_btn = page.query_selector(
                        "div.action button:has-text('Save'), "
                        "button.btn-dark-ot:has-text('Save'), "
                        "div.resumeHeadline form button[type='submit']"
                    )
                    if save_btn:
                        save_btn.click()
                        human_delay(config, multiplier=1.5)
                        log.info(f"✅ Resume Headline updated: {new_text[:80]}...")
                        log.info("🌟 'Profile Updated Today' status successfully refreshed!")
                    else:
                        log.warning("Save button not found for resume headline.")
                else:
                    log.warning("Headline textarea not found.")
            else:
                log.warning("Resume headline edit button not found; attempting direct selector.")
        except Exception as exc:
            log.error(f"Error while updating resume headline: {exc}")

        # ── 2. Re-upload Resume PDF (if present) ──────────────────────────────
        resume_file = Path(config.resume_path)
        if resume_file.exists():
            log.info(f"Re-uploading latest resume: {resume_file.name}...")
            try:
                upload_input = page.query_selector("input#attachCV, input[type='file'][name*='resume']")
                if upload_input:
                    upload_input.set_input_files(str(resume_file))
                    human_delay(config, multiplier=2.0)
                    log.info("✅ Resume PDF re-uploaded successfully.")
                else:
                    log.debug("Resume file upload input element not visible on page.")
            except Exception as exc:
                log.warning(f"Resume upload micro-step failed: {exc}")
        else:
            log.debug(f"Resume file not found at {config.resume_path}; skipping PDF re-upload.")

        ctx.close()
        log.info("Profile refresh cycle complete.")


# ═══════════════════════════════════════════════════════════════════════════════
# MODE 3: SEARCH & 1-CLICK DIRECT APPLY (With Screening Questionnaire Bot)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_naukri_fit_score(job_text: str, config: Config) -> int:
    """Scores candidate stack alignment against Naukri job description (0-100)."""
    text = job_text.lower()
    score = 40  # Base score for passing search filter

    # Core tech stack keywords
    tech_keywords = {
        "python": 15,
        "fastapi": 15,
        "genai": 10,
        "generative ai": 10,
        "rag": 10,
        "llm": 10,
        "sql": 10,
        "aws": 10,
        "docker": 5,
        "playwright": 10,
        "selenium": 5,
        "terraform": 5,
    }

    matched = 0
    for kw, weight in tech_keywords.items():
        if re.search(rf"\b{re.escape(kw)}\b", text):
            score += weight
            matched += 1

    return min(100, score)


def extract_recruiter_contacts(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extracts email and phone numbers mentioned inside JD text."""
    email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    phone_match = re.search(r"(?:\+91[\-\s]?)?[6-9]\d{9}", text)

    email = email_match.group(0).strip() if email_match else None
    phone = phone_match.group(0).strip() if phone_match else None
    return email, phone


def answer_screening_drawer(page: Page, config: Config) -> int:
    """
    Answers side-drawer questionnaire chatbot modal on Naukri 1-click applies.
    Uses regex patterns to resolve CTC, Notice Period, Skills, and Relocation.
    """
    answers_resolved = 0
    try:
        # Load questions mapping
        screening_data = {}
        if config.screening_answers_file.exists():
            screening_data = json.loads(config.screening_answers_file.read_text(encoding="utf-8"))

        patterns = screening_data.get("question_patterns", [])

        # Find question containers
        question_blocks = page.query_selector_all(
            "div.bot-container, div.question-container, div.drawer-wrapper div.form-group, li.question"
        )

        for block in question_blocks:
            q_text = block.inner_text().strip().lower()
            if not q_text:
                continue

            # Look for inputs
            text_input = block.query_selector("input[type='text'], input[type='number'], textarea")
            radio_btns = block.query_selector_all("input[type='radio'], label")
            dropdown = block.query_selector("select, div.dropdown")

            # Check matches against patterns
            for pat in patterns:
                if re.search(pat["regex"], q_text):
                    ans_type = pat.get("answer_type", "text")
                    val = pat.get("value", "")

                    if ans_type in ("text", "number") and text_input:
                        text_input.fill(str(val))
                        answers_resolved += 1
                        break
                    elif ans_type == "boolean":
                        # Click Yes
                        for r in radio_btns:
                            if "yes" in r.inner_text().lower():
                                r.click()
                                answers_resolved += 1
                                break
                        break
                    elif ans_type == "option":
                        pref_opts = pat.get("preferred_values", [])
                        clicked = False
                        for opt_name in pref_opts:
                            for r in radio_btns:
                                if opt_name.lower() in r.inner_text().lower():
                                    r.click()
                                    clicked = True
                                    answers_resolved += 1
                                    break
                            if clicked:
                                break
                        break

    except Exception as exc:
        log.debug(f"Screening drawer parser note: {exc}")

    return answers_resolved


def mode_search_apply(config: Config) -> None:
    """
    Searches fresh jobs on Naukri, distinguishes 1-click apply from external portals,
    auto-resolves screening questionnaires, and logs external redirect leads.
    """
    if not PLAYWRIGHT_AVAILABLE:
        log.error("Playwright is not installed.")
        sys.exit(1)

    applied_jobs = load_json_list(config.applied_ledger_file)
    applied_urls = {job.get("url") for job in applied_jobs if job.get("url")}

    external_queue = load_json_list(config.external_jobs_file)
    recruiter_leads = load_json_list(config.recruiter_leads_file)

    total_applied = 0

    with sync_playwright() as pw:
        ctx = create_naukri_browser_context(pw, config, headless=True)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        for keyword in config.search_keywords:
            if total_applied >= config.max_applications_per_run:
                break

            slug = keyword.lower().replace(" ", "-")
            url = NAUKRI_SEARCH_URL.format(slug=slug, keyword=keyword.replace(" ", "%20"))
            log.info(f"Searching Naukri: '{keyword}'...")

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=40000)
                human_delay(config)
            except Exception as exc:
                log.warning(f"Failed to fetch search page for {keyword}: {exc}")
                continue

            # Scroll down to load lazy cards
            page.evaluate("window.scrollBy(0, 800)")
            human_delay(config, multiplier=0.7)

            job_cards = page.query_selector_all(
                "div.srp-jobtuple-wrapper, article.jobTuple, div.cust-job-tuple"
            )
            log.info(f"  Found {len(job_cards)} job cards for '{keyword}'.")

            for card in job_cards:
                if total_applied >= config.max_applications_per_run:
                    break

                try:
                    title_el = card.query_selector("a.title, a.job-title")
                    company_el = card.query_selector("a.comp-name, a.company-name")
                    link_el = title_el or card.query_selector("a[href*='job-listings']")

                    if not link_el:
                        continue

                    title = title_el.inner_text().strip() if title_el else "Software Engineer"
                    company = company_el.inner_text().strip() if company_el else "Tech Company"
                    job_url = link_el.get_attribute("href") or ""
                    job_url = job_url.split("?")[0]  # Strip tracking query params

                    if job_url in applied_urls:
                        continue

                    snippet_el = card.query_selector("div.job-desc, div.ellipsis")
                    snippet = snippet_el.inner_text().strip() if snippet_el else ""

                    # Compute alignment score
                    fit_score = compute_naukri_fit_score(f"{title} {snippet}", config)
                    if fit_score < config.min_fit_score:
                        log.debug(f"  [Skip] {title} @ {company} (Score {fit_score} < {config.min_fit_score})")
                        continue

                    # Check for external apply vs direct apply
                    apply_btn = card.query_selector(
                        "button:has-text('Apply'), a:has-text('Apply'), span:has-text('Apply')"
                    )
                    is_external = False
                    if apply_btn:
                        btn_text = apply_btn.inner_text().lower()
                        if "company" in btn_text or "external" in btn_text:
                            is_external = True

                    # Extract any recruiter contacts in snippet
                    recruiter_email, recruiter_phone = extract_recruiter_contacts(snippet)
                    if recruiter_email:
                        recruiter_leads.append({
                            "email": recruiter_email,
                            "phone": recruiter_phone,
                            "company": company,
                            "title": title,
                            "job_url": job_url,
                            "source": "Naukri Search Snippet",
                            "found_at": datetime.now(timezone.utc).isoformat(),
                        })

                    # Handle external redirect vs 1-click direct apply
                    if is_external:
                        log.info(f"  🌐 [External] {title} @ {company} -> Logged to queue.")
                        external_queue.append({
                            "title": title,
                            "company": company,
                            "url": job_url,
                            "score": fit_score,
                            "discovered_at": datetime.now(timezone.utc).isoformat(),
                        })
                        applied_urls.add(job_url)
                        continue

                    # Direct 1-Click Apply Flow
                    log.info(f"  ⚡ [1-Click Apply] {title} @ {company} (Score: {fit_score}/100)...")

                    # Open job details in tab
                    detail_page = ctx.new_page()
                    detail_page.goto(job_url, wait_until="domcontentloaded", timeout=35000)
                    human_delay(config, multiplier=0.8)

                    # Click direct apply button on page
                    detail_apply_btn = detail_page.query_selector(
                        "button.apply-button:has-text('Apply'), "
                        "button#apply-button, "
                        "button:has-text('Apply on Naukri')"
                    )

                    if detail_apply_btn:
                        detail_apply_btn.click()
                        human_delay(config, multiplier=1.2)

                        # Answer screening drawer questions if they appear
                        answered = answer_screening_drawer(detail_page, config)
                        if answered > 0:
                            log.info(f"    Resolved {answered} screening questions in drawer.")

                        # Submit application if configured
                        if config.auto_submit_apply:
                            submit_btn = detail_page.query_selector(
                                "button:has-text('Submit'), "
                                "button:has-text('Apply now'), "
                                "div.drawer-wrapper button.btn-primary"
                            )
                            if submit_btn:
                                submit_btn.click()
                                human_delay(config, multiplier=1.5)

                        log.info(f"    ✅ Applied to {title} @ {company}.")
                        total_applied += 1
                        applied_jobs.append({
                            "title": title,
                            "company": company,
                            "url": job_url,
                            "score": fit_score,
                            "applied_at": datetime.now(timezone.utc).isoformat(),
                        })
                        applied_urls.add(job_url)
                    else:
                        log.debug(f"    Direct apply button not found for {title}.")

                    detail_page.close()
                    human_delay(config)

                except Exception as card_exc:
                    log.debug(f"Error processing job card: {card_exc}")
                    continue

        ctx.close()

    # Save state
    save_json_list(config.applied_ledger_file, applied_jobs)
    save_json_list(config.external_jobs_file, external_queue)
    save_json_list(config.recruiter_leads_file, recruiter_leads)

    log.info(f"Search & Apply finished. {total_applied} jobs submitted, {len(external_queue)} external logged.")


# ═══════════════════════════════════════════════════════════════════════════════
# MODE 4: INBOX & NVITES (Recruiter Message Monitoring)
# ═══════════════════════════════════════════════════════════════════════════════

def mode_inbox(config: Config) -> None:
    """
    Monitors Naukri Recruiter Messages & NVites at naukri.com/mnjuser/inbox:
      - Extracts recruiter name, email, phone, and role.
      - Classifies message.
      - Stages personalized reply into data/pending_replies.json for approval.
    """
    if not PLAYWRIGHT_AVAILABLE:
        log.error("Playwright is not installed.")
        sys.exit(1)

    pending_replies = load_json_list(config.pending_replies_file)
    recruiter_leads = load_json_list(config.recruiter_leads_file)

    log.info("Checking Naukri Recruiter Messages & NVites...")
    with sync_playwright() as pw:
        ctx = create_naukri_browser_context(pw, config, headless=True)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        try:
            page.goto(NAUKRI_INBOX_URL, wait_until="domcontentloaded", timeout=40000)
            human_delay(config)
        except Exception as exc:
            log.error(f"Failed to load Naukri inbox: {exc}")
            ctx.close()
            return

        # Query messages / nvite items
        nvite_items = page.query_selector_all(
            "div.msg-thread, div.nvite-item, div.message-card, li.message-item"
        )
        log.info(f"Found {len(nvite_items)} recruiter items in inbox.")

        for item in nvite_items[:15]:
            try:
                recruiter_el = item.query_selector("span.recruiter-name, div.recruiter-name, h4")
                role_el = item.query_selector("span.designation, div.job-title, a.title")
                body_el = item.query_selector("p.msg-body, div.snippet, div.desc")

                recruiter_name = recruiter_el.inner_text().strip() if recruiter_el else "Recruiter"
                role_title = role_el.inner_text().strip() if role_el else "Software Engineer"
                msg_body = body_el.inner_text().strip() if body_el else ""

                email, phone = extract_recruiter_contacts(msg_body)
                first_name = recruiter_name.split()[0] if recruiter_name else "there"

                # Draft high-impact reply
                reply_draft = (
                    f"Hi {first_name}, thanks for reaching out regarding the {role_title} opening! "
                    "My background in Python, FastAPI, Generative AI (RAG pipelines), and AWS cloud "
                    f"aligns well with the team's needs. I'm keen to connect: {config.candidate_phone or ''} or "
                    f"{config.naukri_email}. — {config.candidate_name}"
                )

                if config.eco_mode and ECOMODE_AVAILABLE:
                    reply_draft = ecomode.compress_text(reply_draft, mode=config.eco_mode_level)

                pending_replies.append({
                    "recruiter": recruiter_name,
                    "role": role_title,
                    "email": email,
                    "phone": phone,
                    "message": msg_body[:300],
                    "draft_reply": reply_draft,
                    "staged_at": datetime.now(timezone.utc).isoformat(),
                })

                if email:
                    recruiter_leads.append({
                        "email": email,
                        "phone": phone,
                        "company": "Naukri NVite",
                        "title": role_title,
                        "recruiter": recruiter_name,
                        "source": "Naukri NVite / Recruiter Chat",
                        "found_at": datetime.now(timezone.utc).isoformat(),
                    })

                log.info(f"  📩 Staged draft for {recruiter_name} ({role_title})")

            except Exception as msg_exc:
                log.debug(f"Error parsing inbox item: {msg_exc}")
                continue

        ctx.close()

    save_json_list(config.pending_replies_file, pending_replies)
    save_json_list(config.recruiter_leads_file, recruiter_leads)

    log.info(f"Inbox check complete. {len(pending_replies)} pending replies staged.")


# ═══════════════════════════════════════════════════════════════════════════════
# MODE 5: EMAIL DISPATCHER (3-Pillar Outreach via Gmail SMTP)
# ═══════════════════════════════════════════════════════════════════════════════

def mode_email(config: Config) -> None:
    """
    Dispatches 3-pillar follow-up emails to recruiters found in Naukri JDs / NVites.
    Requires manual console approval [y/N/s/q] before sending.
    """
    recruiter_leads = load_json_list(config.recruiter_leads_file)
    if not recruiter_leads:
        log.info("No recruiter email leads in queue. Run --mode search-apply or --mode inbox first.")
        return

    if not config.gmail_app_password or config.gmail_app_password == "CHANGE_ME":
        log.error("GMAIL_APP_PASSWORD not set in .env. Cannot dispatch emails.")
        return

    resume_path = Path(config.resume_path)
    has_resume = resume_path.exists()

    log.info(f"Loaded {len(recruiter_leads)} recruiter leads for outreach.")

    for lead in list(recruiter_leads):
        email = lead.get("email")
        if not email:
            continue

        company = lead.get("company", "your team")
        role = lead.get("title", "Software Engineer")
        recruiter = lead.get("recruiter", "Hiring Team")

        subject = f"Regarding {role} on Naukri — {config.candidate_name}"
        body = (
            f"Hi {recruiter},\n\n"
            f"I came across your opening for {role} at {company} on Naukri.\n\n"
            f"I am a {config.current_role} at {config.current_company} "
            f"with production experience in Python backend microservices, Generative AI pipelines, and cloud automation.\n\n"
            f"Three ways I can immediately deliver value for {company}:\n\n"
            f"1. Generative AI & LLM Deployment: Built production RAG pipelines with LangChain, Ollama, "
            f"and ChromaDB cutting hallucinations across domain document queries.\n"
            f"2. Backend Architecture & High-Performance APIs: Developed low-latency FastAPI microservices "
            f"and automated Playwright/Selenium regression suites improving execution velocity.\n"
            f"3. Data Integrity & Cloud Infrastructure: Optimized infrastructure throughput "
            f"and automated cloud deployment workflows.\n\n"
            f"My resume is attached.\n\n"
            f"Available on short notice. Would you be open to a 10-minute introductory call?\n\n"
            f"Best regards,\n{config.candidate_name}\n{config.current_role} — {config.current_company}\n"
            f"📞 {config.candidate_phone} | ✉️ {config.naukri_email}\n"
        )

        print("\n" + "═" * 65)
        print(f"  TO      : {email}")
        print(f"  SUBJECT : {subject}")
        print(f"  ROLE    : {role} @ {company}")
        print("─" * 65)
        print(body[:300] + "...\n[Full 3-Pillar Body]")
        print("═" * 65)

        confirm = input("Send this email via Gmail SMTP? [y/N/s(kip)/q(uit)]: ").strip().lower()
        if confirm == "q":
            break
        elif confirm in ("s", "n", ""):
            continue
        elif confirm == "y":
            try:
                msg = MIMEMultipart()
                msg["From"] = config.gmail_address
                msg["To"] = email
                msg["Subject"] = subject
                msg.attach(MIMEText(body, "plain", "utf-8"))

                if has_resume:
                    part = MIMEBase("application", "pdf")
                    part.set_payload(resume_path.read_bytes())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f'attachment; filename="{resume_path.name}"')
                    msg.attach(part)

                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                    server.login(config.gmail_address, config.gmail_app_password)
                    server.send_message(msg)

                log.info(f"✅ Dispatched email to {email}.")
                recruiter_leads.remove(lead)
                save_json_list(config.recruiter_leads_file, recruiter_leads)
            except Exception as send_exc:
                log.error(f"Failed to send email to {email}: {send_exc}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="vedant-naukri-agent",
        description="Autonomous Naukri.com automation agent for Raspberry Pi 3B+.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s --mode login            # First-time interactive session setup\n"
            "  %(prog)s --mode refresh-profile  # 8:55 AM IST daily ranking boost\n"
            "  %(prog)s --mode search-apply     # Search & 1-click apply with screening bot\n"
            "  %(prog)s --mode inbox            # Check recruiter messages & NVites\n"
            "  %(prog)s --mode email            # Dispatch 3-pillar cold email via SMTP\n"
        ),
    )

    parser.add_argument(
        "--mode",
        required=True,
        choices=["login", "refresh-profile", "search-apply", "inbox", "email"],
        help="Operation mode to execute.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose DEBUG logging.",
    )
    parser.add_argument(
        "--eco",
        action="store_true",
        help="Enable ecoMode token-saving semantic compression.",
    )
    parser.add_argument(
        "--eco-max",
        action="store_true",
        help="Enable ecoMode max compression (extreme brevity).",
    )

    args = parser.parse_args()

    config = Config()
    if args.eco_max:
        config.eco_mode = True
        config.eco_mode_level = "eco max"
    elif args.eco:
        config.eco_mode = True
        config.eco_mode_level = "eco"

    log_level = "DEBUG" if args.verbose else config.log_level
    setup_logging(log_level)

    log.info("╔══════════════════════════════════════════════╗")
    log.info("║  vedant-naukri-agent  v1.0.0                 ║")
    log.info(f"║  Mode: {args.mode:<39s} ║")
    log.info("╚══════════════════════════════════════════════╝")

    mode_map = {
        "login": mode_login,
        "refresh-profile": mode_refresh_profile,
        "search-apply": mode_search_apply,
        "inbox": mode_inbox,
        "email": mode_email,
    }

    handler = mode_map[args.mode]
    try:
        handler(config)
    except KeyboardInterrupt:
        log.info("\nInterrupted by user. Exiting gracefully.")
        sys.exit(0)
    except Exception as exc:
        log.error(f"Fatal error in --mode {args.mode}: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
