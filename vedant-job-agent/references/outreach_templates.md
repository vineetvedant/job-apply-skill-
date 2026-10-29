# Outreach Templates

> **Author:** Vedant Singh  
> **Last Updated:** 2026-10-24  
> **Usage:** These templates are consumed by `pi_linkedin_agent.py --mode email` and
> `--mode referral`. Placeholders wrapped in `{{double_braces}}` are hydrated at
> runtime from the leads ledger.

---

## Table of Contents

1. [3-Pillar Cold Email](#3-pillar-cold-email)
2. [LinkedIn DM — Referral Request](#linkedin-dm--referral-request)
3. [Follow-Up Email (5-Day)](#follow-up-email-5-day)
4. [Signature Block](#signature-block)

---

## 3-Pillar Cold Email

### Subject Line Options (agent rotates)

```
1. "{{company_name}} + Vedant Singh — 3 reasons I'd ship fast on your team"
2. "Quick note from an engineer who cut HPC rollout time by 40% — re: {{role_title}}"
3. "RAG pipelines, FastAPI, Terraform — a fit for {{role_title}} at {{company_name}}?"
```

### Body

```
Hi {{recipient_first_name}},

I came across the {{role_title}} opening at {{company_name}} and wanted to share
three concrete reasons I'd contribute from week one:


━━━ 1. Generative AI & LLM Deployment ━━━

At Proeffico Solutions I built a production RAG pipeline (LangChain + ChromaDB)
that reduced hallucination rates by 30% across 10,000+ user queries, while
deploying a YOLOv8-based activity detection system that exceeded 95% accuracy on
real-time video feeds.  I'm comfortable operating across the full LLM stack—from
prompt engineering and vector-store tuning through to inference serving.


━━━ 2. Backend Architecture & APIs ━━━

I design APIs in FastAPI and wire them to browser-automation harnesses
(Playwright, Selenium, Scrapling) that drive end-to-end testing and data
extraction at scale.  At Tata Motors, I integrated YOLO safety-inspection
modules that boosted production-line quality checks by 28%.


━━━ 3. Data Integrity & Cloud Infrastructure ━━━

During my HPC internship at Altair Engineering × Siemens Energy, I authored
Terraform playbooks that compressed AWS/OCI cluster rollouts from 5 days to 3
while improving overall cluster efficiency by 37%.  I'm equally at home with
Docker, Jenkins CI/CD pipelines, and SQL-backed data layers that keep systems
reliable under load.


I've attached my résumé for a deeper look.  Would a 15-minute call this week or
next work for you?

{{signature_block}}
```

---

## LinkedIn DM — Referral Request

> **Usage:** `--mode referral` pastes this into the LinkedIn message compose box.
> The agent **does not** click Send.

```
Hi {{recipient_first_name}},

I noticed you're a {{recipient_role}} at {{company_name}} — really impressive
work on {{something_specific_if_available}}.

I'm a Software Engineer (currently at Wipro, enterprise healthcare) with hands-on
experience in Python/FastAPI APIs, RAG pipelines (LangChain + ChromaDB), and cloud
infra (Terraform on AWS/OCI).  I recently helped compress HPC cluster rollouts by
40% at Altair × Siemens Energy.

I spotted the {{role_title}} opening on your team and believe my background could
be a strong fit.  Would you be open to a brief chat or, if appropriate, an
internal referral?  Happy to share my résumé — no pressure at all.

Thanks for your time!
— Vedant
Portfolio: https://sshconnect.space/
```

---

## Follow-Up Email (5-Day)

### Subject Line

```
Re: {{original_subject_line}}
```

### Body

```
Hi {{recipient_first_name}},

Just floating this back to the top of your inbox — I know things get busy.

Since my last note I've also been working on a Playwright-based LinkedIn
automation agent that runs on a Raspberry Pi 3B+ under 1 GB RAM, which speaks
to the kind of resource-constrained engineering I enjoy.

Would love to find 15 minutes to chat about how I can help {{company_name}}.
Let me know if there's a better time or a colleague I should reach out to.

{{signature_block}}
```

---

## Signature Block

Used by all email templates:

```
Best regards,
{{candidate_name}}

{{candidate_role}} — {{candidate_company}}
{{candidate_education}}

📧  {{candidate_email}}
📱  {{candidate_phone}}
🌐  {{portfolio_url}}
💼  {{linkedin_url}}
🐙  {{github_url}}

{{candidate_location}} · Open to {{open_to}}
```

---

## LinkedIn DM Follow-Up Nudges (Stale Outbound)

Used automatically by `--mode inbox` when an outbound connection or referral DM has had no reply after `FOLLOWUP_DAYS` (default 3 days):

### Nudge 1 (Standard Follow-Up)
```
Hi {{recipient_first_name}},

Just floating this back up — I know things get busy! I'm still very keen to chat about the {{role_title}} opening.

Would any time this week or next work for a quick call? Happy to adjust to your schedule.

Best,
Vedant
Portfolio: https://sshconnect.space/
```

### Nudge 2 (Project Hook / Gentle Check-in)
```
Hi {{recipient_first_name}},

Hope you're doing well! Wanted to gently check in on our earlier conversation. I've been working on some exciting projects recently (including a Playwright-based automation agent on a Raspberry Pi!) and would love to share more.

Let me know if you'd like to reconnect — no rush at all.

Cheers,
Vedant
```

---

## ecoMode Ultra-Compact Templates (vineetvedant/ecoMode)

Semantic compression templates for token saving and maximum recruiter readability:

### ecoMode Cold Email (Delta-Only)
```
Subject: {{company_name}} + Vedant Singh (SWE) — Quick Intro

Hi {{recipient_first_name}},

Noticed {{company_name}} is hiring for {{role_title}}. Three quick reasons I can deliver immediate value:

1. Gen AI & RAG: Built RAG pipelines cutting hallucinations 30% across 10k+ docs (LangChain, ChromaDB, Ollama).
2. Backend APIs: Production FastAPI microservices at Wipro with sub-50ms latency and high throughput.
3. Infra & Cloud: Optimized HPC clusters (+37% efficiency) and automated Terraform rollouts.

Full portfolio: https://sshconnect.space/
Résumé attached. Would love 10 minutes to connect if timing aligns.

— {{candidate_name}} ({{candidate_phone}})
```

### ecoMode Max Referral DM (<40 words)
```
Hi {{recipient_first_name}}, spotted {{company_name}}'s {{role_title}} opening. Background in FastAPI, AI pipelines, & cloud infra. Open to an internal referral or quick chat? No pressure! Portfolio: https://sshconnect.space/ — Vedant
```

---

## Template Variables Reference

| Variable | Source | Example |
|---|---|---|
| `{{recipient_first_name}}` | Lead record / scraped profile | Priya |
| `{{company_name}}` | Lead record | Razorpay |
| `{{role_title}}` | Lead record | Senior Backend Engineer |
| `{{recipient_role}}` | Scraped LinkedIn headline | Staff Engineer, Payments |
| `{{something_specific_if_available}}` | Scraped from recent post/activity | "your blog post on event-driven microservices" |
| `{{original_subject_line}}` | Stored from initial email | "Razorpay + Vedant Singh — 3 reasons…" |
| `{{signature_block}}` | Constant — see above | — |

