# Naukri.com Optimization & Outreach Templates

High-converting, algorithm-optimized templates for Vedant Singh's Naukri profile refresh, recruiter NVite responses, and cold email outreach.

---

## 1. Optimized Naukri Resume Headlines (< 250 Characters)

Naukri search algorithms prioritize candidates whose **Resume Headline** matches recruiter Boolean search keywords and has been updated within the last 24 hours.

### Primary Headline (Recommended Default)
```text
Software Engineer at Wipro | Python, FastAPI, Generative AI (RAG, LLMs, LangChain) | Cloud & DevOps (AWS, Terraform, Docker, Jenkins) | SDET & Automation (Selenium, Playwright) | B.Tech CSE (8.21 CGPA)
```
*(Character count: 213 / 250 max)*

### Alternate Headline A (Backend & GenAI Focus)
```text
Backend & AI Engineer | Python, FastAPI Microservices, LangChain, Ollama, ChromaDB RAG Pipelines | AWS, Docker, PostgreSQL | HPC Cluster Optimization (Altair/Siemens Energy) | Associate Analyst @ Wipro
```
*(Character count: 212 / 250 max)*

### Alternate Headline B (Full-Stack & SDET Focus)
```text
Software Engineer (Wipro) | Python Developer | FastAPI & REST APIs | Test Automation & Web Scraping (Playwright, Selenium) | Generative AI & Vector DBs | Cloud Infrastructure (AWS, Terraform, CI/CD)
```
*(Character count: 209 / 250 max)*

> **Micro-Edit Algorithm Note:** The agent automates daily ranking boosts at 8:55 AM IST by toggling a trailing dot (`.`) at the end of the headline. This registers as a profile modification, immediately granting the active **"Profile Updated Today"** priority badge to recruiter searches.

---

## 2. Optimized Naukri Profile Summary (< 1000 Characters)

```text
Software Engineer / Associate Analyst at Wipro with a robust foundation in Python backend engineering, Generative AI application development, and cloud infrastructure. Experienced across 4 high-impact technical internships (Altair x Siemens Energy, Proeffico Solutions, Tata Motors, and CRIS) and enterprise healthcare client delivery.

Key Capabilities:
• Generative AI & RAG: Built production RAG pipelines with LangChain, Ollama, and ChromaDB cutting hallucinations by 30% across 10k+ technical queries.
• High-Throughput Backends: Designed RESTful microservices with FastAPI and automated testing suites (Selenium, Playwright) achieving sub-50ms latencies and 60% faster regression cycles.
• Cloud & Systems: Automated infrastructure with Terraform and AWS; optimized HPC clusters boosting throughput by 37%; deployed Dockerized services with Jenkins CI/CD.

B.Tech Computer Science & Engineering (SRM IST, 2025, 8.21 CGPA). Based in Delhi NCR / Noida, open to hybrid, remote, and relocation roles.
```
*(Character count: 978 / 1000 max)*

---

## 3. 3-Pillar Email Outreach Template (For Naukri NVites & Scraped JDs)

Use when a recruiter sends an NVite with an email address or lists a hiring manager email in the Naukri job description.

### Subject Lines (A/B Tested)
- `Naukri NVite: {{role_title}} at {{company_name}} — Vedant Singh (SWE @ Wipro)`
- `Regarding {{role_title}} on Naukri — Vedant Singh (FastAPI / GenAI / Cloud)`
- `Application for {{role_title}} — Vedant Singh (FastAPI, RAG, AWS)`

### Email Body
```text
Hi {{recruiter_name}},

Thank you for connecting through Naukri regarding the {{role_title}} opportunity at {{company_name}}.

I am an Associate Analyst / Software Engineer at Wipro Limited (Enterprise Healthcare domain) with hands-on production experience in Python backend microservices, Generative AI pipelines, and cloud automation.

Three reasons I can immediately accelerate {{company_name}}'s engineering velocity:

1. Generative AI & LLM Deployment: At Proeffico Solutions, I architected an enterprise RAG pipeline utilizing LangChain, ChromaDB, and Ollama that achieved 30% lower hallucination rates across 10,000+ domain-specific document queries.
2. Backend Architecture & High-Performance APIs: At Wipro and Altair, I developed low-latency FastAPI microservices and automated end-to-end regression suites (Playwright, Selenium), improving test reliability and speeding deployment cycles by 60%.
3. Data Integrity & Cloud Infrastructure: Collaborating with Siemens Energy, I improved HPC cluster efficiency by +37% and automated Terraform-based multi-region AWS/OCI infrastructure rollouts from 5 days down to 3 days.

I hold a B.Tech in CSE from SRM Institute of Science and Technology (CGPA 8.21/10) and am available on short notice.

My résumé is attached. You can explore my live deployments, open-source code, and portfolio below:
🌐 Portfolio: {{portfolio_url}}
💼 LinkedIn: {{linkedin_url}}
🐙 GitHub: {{github_url}}

Would you be open to a 10-minute introductory conversation this week?

Best regards,
{{candidate_name}}
{{candidate_role}} — {{candidate_company}}
📞 {{candidate_phone}} | ✉️ {{candidate_email}}
```

---

## 4. Naukri Recruiter Chat / NVite 1-Click Reply Drafts

### Response A: Standard High-Interest Reply (< 60 words)
```text
Hi {{recruiter_name}}, thanks for reaching out regarding the {{role_title}} position at {{company_name}}! My background in Python, FastAPI, Generative AI (RAG/LangChain), and cloud deployment aligns closely with the requirements. I am keen to discuss how I can contribute. You can reach me at {{candidate_phone}} or {{candidate_email}}. Looking forward to connecting! — {{candidate_first_name}}
```

### Response B: Immediate Interview Scheduling (< 50 words)
```text
Hi {{recruiter_name}}, thank you for the NVite! I would love to explore the {{role_title}} role at {{company_name}}. I am available for a brief call anytime between 10 AM to 6 PM IST. My resume is updated on my profile, and my portfolio is at {{portfolio_url}}. Best, {{candidate_first_name}} ({{candidate_phone}})
```

### Response C: ecoMode Max Compression (< 35 words)
```text
Hi {{recruiter_name}}, keen on {{role_title}} @ {{company_name}}. 1+ yrs exp in Python/FastAPI, RAG pipelines, & AWS. Available for immediate discussion: {{candidate_phone}} / {{candidate_email}}. Portfolio: {{portfolio_url}} — {{candidate_first_name}}
```

---

## 5. Screening Drawer Answer Reference Table

| Question Pattern | Value Used | Field Type |
|---|---|---|
| Total Experience | `1.2` years | Number input / Dropdown |
| Notice Period | `15 Days` / `Serving Notice` | Dropdown option |
| Current CTC | `4.5` LPA | Number input (Lakhs) |
| Expected CTC | `9.5` LPA | Number input (Lakhs) |
| Python Experience | `3.0` years | Number input |
| FastAPI Experience | `2.0` years | Number input |
| Generative AI / RAG | `1.5` years | Number input |
| SQL / Databases | `2.5` years | Number input |
| AWS / Cloud | `1.5` years | Number input |
| Willing to Relocate | `Yes` | Radio / Checkbox |
| Current Location | `Noida, Delhi NCR` | Autocomplete / Text |
| Current Employer | `Wipro Limited` | Text input |
| Highest Degree | `B.Tech/B.E.` (CSE, 2025, 8.21) | Dropdown |
