#!/usr/bin/env python3
"""
Autonomous LinkedIn Post-Scraper & Tailored Email Outreach Engine
Target: Raspberry Pi 3B+ & Windows Desktop (strictly isolated in D:\skill for pi for linkdin agent)

Capabilities:
  1. Inspect specific LinkedIn hiring posts (e.g. lnkd.in links), extract author & email.
  2. Search LinkedIn content feed for live "we are hiring" recruiter posts containing emails.
  3. Fine-tune 3-pillar email tailored to post requirements using Vedant Singh's ground-truth profile.
  4. Attach Vedant_Singh_Base_Resume.pdf and stage both .json and .eml packages.
  5. Send via Gmail SMTP if GMAIL_APP_PASSWORD configured, or stage for human confirmation.
"""

import argparse
import json
import logging
import os
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
from typing import Any, Optional
from urllib.parse import quote

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("post_outreach_agent")

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

CANDIDATE = {
    "name": os.getenv("CANDIDATE_NAME", "Job Applicant"),
    "role": os.getenv("CURRENT_ROLE", "Software Engineer"),
    "education": os.getenv("EDUCATION_TEXT", "B.Tech in CSE"),
    "phone": os.getenv("CANDIDATE_PHONE", ""),
    "email": os.getenv("CANDIDATE_EMAIL", os.getenv("GMAIL_ADDRESS", "")),
    "portfolio": os.getenv("PORTFOLIO_URL", "https://github.com/vineetvedant"),
    "linkedin": os.getenv("LINKEDIN_URL", "https://linkedin.com"),
    "github": os.getenv("GITHUB_URL", "https://github.com/vineetvedant"),
    "resume_path": Path(os.getenv("RESUME_PATH", "Resume.pdf")),
    "yoe": os.getenv("TOTAL_EXPERIENCE_YEARS", "1.5 Years"),
    "location": os.getenv("CURRENT_LOCATION", "Remote / Hybrid"),
}

STAGED_DIR = BASE_DIR / "data" / "staged_outreach"
STAGED_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_STATE_PATH = BASE_DIR / ".session" / "storage_state.json"
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def craft_finetuned_email(post_body: str, author_name: str, target_email: str) -> dict[str, str]:
    """
    Reads the recruiter's post body and synthesizes a tailored 3-pillar application email
    specifically aligned with the required tech stack and responsibilities.
    """
    body_lower = post_body.lower()
    first_name = author_name.split()[0] if author_name and author_name != "Hiring Manager" else "Hiring Team"

    # Identify role
    role = "Software / AI Engineer"
    if "data science" in body_lower or "data scientist" in body_lower:
        role = "Data Science Engineer"
    elif "genai" in body_lower or "generative ai" in body_lower or "rag" in body_lower or "llm" in body_lower:
        role = "Generative AI Engineer"
    elif "fastapi" in body_lower or "backend" in body_lower:
        role = "Backend / FastAPI Engineer"
    elif "python" in body_lower:
        role = "Python Developer"

    # Identify company
    company = "your team"
    domain = target_email.split("@")[-1].split(".")[0]
    if domain not in ["gmail", "yahoo", "hotmail", "outlook", "icloud", "proton"]:
        m = re.search(rf"\b({re.escape(domain)})\b", post_body, re.IGNORECASE)
        if m:
            # find original casing from text
            start, end = m.span()
            company = post_body[start:end]
        else:
            company = domain.capitalize()
    else:
        comp_patterns = re.findall(r"(?:at|join|with)\s+([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)?)", post_body)
        if comp_patterns:
            candidates = [c for c in comp_patterns if c.lower() not in ["our", "the", "bengaluru", "india", "pvt", "ltd", "git", "aws"]]
            if candidates:
                company = candidates[0]

    # Select and tune pillars based on post content
    pillars = []

    # Pillar: GenAI & RAG
    if any(k in body_lower for k in ["rag", "llm", "embedding", "prompt", "genai", "generative ai", "langchain"]):
        pillars.append(
            "1. Production RAG Pipelines & LLM Deployment:\n"
            "   At Proeffico Solutions, I architected an enterprise RAG pipeline (LangChain + ChromaDB) with dense vector\n"
            "   retrieval and chunking strategies that reduced hallucination rates by 30% across 10,000+ live queries.\n"
            "   I am deeply familiar with prompt engineering, embedding fine-tuning, and LLM API integrations."
        )
    else:
        pillars.append(
            "1. Scalable Backend Systems & APIs:\n"
            "   At Wipro Limited (Enterprise Healthcare domain), I engineer reliable microservices, automated workflows,\n"
            "   and optimized SQL analytical layers in Python & FastAPI, maintaining rigorous enterprise compliance."
        )

    # Pillar: FastAPI & Model APIs
    if any(k in body_lower for k in ["fastapi", "api", "rest", "backend", "deploy", "microservices"]):
        pillars.append(
            "2. High-Throughput FastAPI Inference APIs & Automation:\n"
            "   FastAPI is my primary framework for deploying model APIs and serving real-time inferences. I pair this with\n"
            "   browser automation harnesses (Playwright, Selenium, Scrapling) and end-to-end testing frameworks to ensure\n"
            "   seamless production reliability."
        )
    elif any(k in body_lower for k in ["sql", "data", "pipeline"]):
        pillars.append(
            "2. Data Pipelines & Analytical SQL:\n"
            "   Strong foundation in feature engineering, relational data modeling (PostgreSQL, MySQL), and building\n"
            "   reproducible data ETL workflows for machine learning models and reporting."
        )

    # Pillar: Core ML / Cloud / Computer Vision
    if any(k in body_lower for k in ["ml", "scikit", "pandas", "numpy", "yolo", "cv", "vision", "churn", "segmentation"]):
        pillars.append(
            "3. Applied Machine Learning & High Ownership:\n"
            "   Hands-on experience in NumPy, Pandas, scikit-learn, and real-time YOLOv8 activity detection models (>95% accuracy).\n"
            "   At Tata Motors, I integrated computer vision safety modules that boosted production checks by 28%.\n"
            "   I hold a B.Tech in CSE from SRM IST (CGPA: 8.21/10) and thrive in fast-paced product environments."
        )
    else:
        pillars.append(
            "3. Cloud Infrastructure & DevOps:\n"
            "   During my HPC engagement at Altair × Siemens Energy, I authored Terraform playbooks on AWS/OCI that\n"
            "   compressed infrastructure rollouts from 5 days to 3 (+37% efficiency). Highly proficient in Docker and Linux."
        )

    subject = f"Application: {role} — {CANDIDATE['name']} (Python / FastAPI / Cloud)"

    email_body = f"""Dear {first_name},

I saw your hiring post regarding the {role} opportunity at {company} and wanted to reach out directly with my resume.

Given your emphasis on shipping production-grade features and high-ownership execution, my hands-on background in Python, FastAPI, and applied AI is directly aligned with your team's needs:

{chr(10).join(pillars)}

I have attached my resume ({CANDIDATE['resume_path'].name}) for your review. You can also inspect my live portfolio and projects at {CANDIDATE['portfolio']} and my code repositories at {CANDIDATE['github']}.

I would welcome the opportunity to discuss how I can hit the ground running on your team. Would you be open to a 10–15 minute conversation this week?

Best regards,

{CANDIDATE['name']}
{CANDIDATE['role']}
{CANDIDATE['education']}
📱 Phone: {CANDIDATE['phone']}
✉️ Email: {CANDIDATE['email']}
🌐 Portfolio: {CANDIDATE['portfolio']}
💼 LinkedIn: {CANDIDATE['linkedin']}
🐙 GitHub: {CANDIDATE['github']}
📍 Location: {CANDIDATE['location']}
"""

    return {
        "role": role,
        "company": company,
        "recipient_name": author_name,
        "recipient_email": target_email,
        "subject": subject,
        "body": email_body,
    }


def stage_and_save_email(email_data: dict[str, str], post_url: str = "") -> tuple[Path, Path]:
    """Saves email draft as JSON and EML with resume attached."""
    clean_id = re.sub(r"[^a-zA-Z0-9]", "_", email_data["recipient_email"])
    json_path = STAGED_DIR / f"outreach_post_{clean_id}.json"
    eml_path = STAGED_DIR / f"outreach_post_{clean_id}.eml"

    # JSON representation
    payload = {
        "type": "post_cold_email",
        "post_url": post_url,
        "recipient": email_data["recipient_name"],
        "email": email_data["recipient_email"],
        "role": email_data["role"],
        "company": email_data["company"],
        "subject": email_data["subject"],
        "body": email_data["body"],
        "resume_path": str(CANDIDATE["resume_path"]),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "staged",
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # EML representation (standard RFC 822 format with attachment)
    msg = MIMEMultipart()
    msg["From"] = f"{CANDIDATE['name']} <{CANDIDATE['email']}>"
    msg["To"] = email_data["recipient_email"]
    msg["Subject"] = email_data["subject"]
    msg.attach(MIMEText(email_data["body"], "plain", "utf-8"))

    if CANDIDATE["resume_path"].exists():
        with open(CANDIDATE["resume_path"], "rb") as f:
            part = MIMEBase("application", "pdf")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", 'attachment; filename="Vedant_Singh_Resume.pdf"')
            msg.attach(part)

    with open(eml_path, "wb") as f:
        f.write(msg.as_bytes())

    log.info(f"  💾 Staged email JSON: {json_path.name}")
    log.info(f"  📧 Staged RFC822 EML: {eml_path.name}")
    return json_path, eml_path


def send_staged_email(email_data: dict[str, str]) -> bool:
    """Attempts to send via Gmail SMTP if credentials configured."""
    gmail_addr = os.getenv("GMAIL_ADDRESS", CANDIDATE["email"])
    gmail_pwd = os.getenv("GMAIL_APP_PASSWORD", "").strip()

    if not gmail_pwd:
        log.warning("GMAIL_APP_PASSWORD is not set in .env. Email is STAGED and ready in data/staged_outreach/.")
        return False

    msg = MIMEMultipart()
    msg["From"] = f"{CANDIDATE['name']} <{gmail_addr}>"
    msg["To"] = email_data["recipient_email"]
    msg["Subject"] = email_data["subject"]
    msg.attach(MIMEText(email_data["body"], "plain", "utf-8"))

    if CANDIDATE["resume_path"].exists():
        with open(CANDIDATE["resume_path"], "rb") as f:
            part = MIMEBase("application", "pdf")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", 'attachment; filename="Vedant_Singh_Resume.pdf"')
            msg.attach(part)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.starttls()
            server.login(gmail_addr, gmail_pwd)
            server.sendmail(gmail_addr, email_data["recipient_email"], msg.as_string())
        log.info(f"  ✅ Email successfully SENT to {email_data['recipient_email']}")
        return True
    except Exception as exc:
        log.error(f"  ❌ SMTP error sending to {email_data['recipient_email']}: {exc}")
        return False


def select_best_recruiter_email(emails: list[str], author_name: str, body_text: str) -> str:
    """Selects the genuine recruiter email, filtering out candidate comment spam."""
    if not emails:
        return ""

    # Split off comments section if present
    main_section = body_text
    for marker in ["\nComments\n", "\n23 Comments", "Like\nComment\nShare", "See more comments"]:
        if marker in main_section:
            main_section = main_section.split(marker)[0]

    main_emails = [
        e.lower() for e in EMAIL_REGEX.findall(main_section)
        if not any(b in e.lower() for b in ["example.com", "email.com", "domain.com", "sentry.io"])
    ]
    candidates = main_emails if main_emails else emails

    # 1. Author name match
    first = author_name.lower().split()[0] if author_name else ""
    if first and len(first) > 2:
        for e in candidates:
            if first in e.lower():
                return e.lower()

    # 2. Corporate domain priority (not @gmail.com)
    corporate = [
        e.lower() for e in candidates
        if not any(f in e.lower() for f in ["@gmail.com", "@yahoo.", "@outlook.", "@hotmail."])
    ]
    if corporate:
        return corporate[0].lower()

    return candidates[0].lower()


def process_single_post_url(post_url: str) -> Optional[dict[str, Any]]:
    """Fetches a specific post URL, extracts content and email, fine-tunes body, and stages."""
    log.info(f"Inspecting post: {post_url}")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
        page = ctx.new_page()
        try:
            page.goto(post_url, wait_until="domcontentloaded", timeout=40000)
            time.sleep(3)
        except Exception as e:
            log.error(f"Failed to load post URL: {e}")
            browser.close()
            return None

        # Resolve redirect URL
        real_url = page.url
        post_text = page.inner_text("body")
        browser.close()

    emails = EMAIL_REGEX.findall(post_text)
    clean_emails = [
        e.lower() for e in set(emails)
        if not any(b in e.lower() for b in ["example.com", "email.com", "domain.com", "sentry.io"])
    ]

    if not clean_emails:
        log.warning(f"No contact email found in post: {post_url}")
        return None

    # Determine author
    author_match = re.search(r"posts/([a-zA-Z0-9-]+?)(?:_[a-z]|-)", real_url)
    author_name = "Hiring Team"
    if author_match:
        raw_slug = author_match.group(1).replace("-", " ")
        author_name = re.sub(r"\d+", "", raw_slug).strip().title()

    target_email = select_best_recruiter_email(clean_emails, author_name, post_text)
    log.info(f"Found Recruiter: {author_name} ({target_email})")

    email_data = craft_finetuned_email(post_text, author_name, target_email)
    json_path, eml_path = stage_and_save_email(email_data, post_url=real_url)

    # Try SMTP dispatch
    sent = send_staged_email(email_data)

    return {
        "email_data": email_data,
        "json_path": str(json_path),
        "eml_path": str(eml_path),
        "sent": sent,
    }


def scan_and_stage_hiring_posts(max_posts: int = 10) -> list[dict[str, Any]]:
    """
    Autonomously searches LinkedIn content stream for hiring posts containing emails,
    synthesizes tailored emails for each post, and stages them.
    """
    search_queries = [
        'hiring ("python" OR "data science" OR "fastapi" OR "genai") "email" india',
        'we are hiring ("backend" OR "ai" OR "rag" OR "llm") "send resume" india',
    ]

    results = []
    seen_emails = set()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            storage_state=str(STORAGE_STATE_PATH) if STORAGE_STATE_PATH.exists() else None,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
        page = ctx.new_page()

        for query in search_queries:
            encoded_q = quote(query)
            search_url = f"https://www.linkedin.com/search/results/content/?keywords={encoded_q}&sortBy=%22date_posted%22"
            log.info(f"Scanning LinkedIn content feed for: '{query}'...")

            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=40000)
                time.sleep(4)
            except Exception as e:
                log.warning(f"Could not load search URL: {e}")
                continue

            for _ in range(4):
                page.evaluate("window.scrollBy(0, window.innerHeight * 1.5)")
                time.sleep(2)

            all_text = page.inner_text("main") if page.query_selector("main") else page.inner_text("body")
            chunks = all_text.split("Feed post")

            for c in chunks[1:]:
                found_emails = EMAIL_REGEX.findall(c)
                valid_emails = [
                    e.lower() for e in set(found_emails)
                    if not any(b in e.lower() for b in ["example.com", "email.com", "domain.com", "sentry.io", "w3.org"])
                ]

                if not valid_emails:
                    continue

                for target_email in valid_emails:
                    if target_email in seen_emails:
                        continue
                    seen_emails.add(target_email)

                    # Extract author from chunk header
                    lines = [line.strip() for line in c.split("\n") if line.strip()]
                    author_name = lines[0] if lines else "Hiring Manager"
                    # Clean author name
                    author_name = author_name.split("•")[0].split("·")[0].strip()

                    log.info(f"  🎯 Found Hiring Lead: {author_name} <{target_email}>")
                    email_data = craft_finetuned_email(c, author_name, target_email)
                    json_path, eml_path = stage_and_save_email(email_data)
                    results.append({
                        "email_data": email_data,
                        "json_path": str(json_path),
                        "eml_path": str(eml_path),
                    })

                    if len(results) >= max_posts:
                        break
                if len(results) >= max_posts:
                    break
            if len(results) >= max_posts:
                break

        browser.close()

    log.info(f"Finished content post scan. Found and staged {len(results)} tailored email leads.")
    return results


def main():
    parser = argparse.ArgumentParser(description="LinkedIn Post Outreach Engine")
    parser.add_argument("--url", type=str, help="Specific LinkedIn post URL to process")
    parser.add_argument("--scan", action="store_true", help="Search and process live hiring posts from LinkedIn")
    parser.add_argument("--max", type=int, default=10, help="Max posts to process in scan mode")
    args = parser.parse_args()

    if args.url:
        process_single_post_url(args.url)
    elif args.scan:
        scan_and_stage_hiring_posts(max_posts=args.max)
    else:
        # Default: process Sanjana Jilludimudi's target post
        default_url = "https://lnkd.in/p/gGapVWwN"
        process_single_post_url(default_url)


if __name__ == "__main__":
    main()
