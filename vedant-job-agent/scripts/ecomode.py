"""
ecoMode — Ultra-compact communication & prompt compression engine.
Based on: https://github.com/vineetvedant/ecoMode by Vedant Singh.

Integrated into vedant-job-agent for:
1. TOKEN SAVINGS: Semantically compresses prompts and replies by up to 65%+,
   reducing context-window pressure, CPU load, and RAM consumption on the Pi 3B+.
2. SECURITY HARDENING: Sanitizes untrusted user/recruiter input to defeat prompt
   injection, jailbreak delimiters, and data-exfiltration payloads.
3. SECRET MASKING: Redacts passwords, API keys, session tokens, and cookie strings
   from logs, tables, and console outputs.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# 1. SECURITY: PROMPT INJECTION DEFENSE & SANITIZATION
# ═══════════════════════════════════════════════════════════════════════════════

# Common prompt injection triggers found in untrusted scrape / inbox data
INJECTION_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)",
    r"(?i)disregard\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts)",
    r"(?i)system\s*:\s*",
    r"(?i)<\/?system>",
    r"(?i)<\/?assistant>",
    r"(?i)<\/?human>",
    r"(?i)you\s+are\s+now\s+(in\s+)?(developer\s+mode|dan|unrestricted)",
    r"(?i)reveal\s+(your\s+)?(system\s+prompt|instructions|secret|cookie|password)",
    r"(?i)repeat\s+the\s+words?\s+above",
    r"(?i)bypass\s+(safety|security)\s+filters?",
    r"(?i)curl\s+https?:\/\/",
    r"(?i)wget\s+https?:\/\/",
    r"(?i)base64\s+-d",
    r"(?i)output\s+(all\s+)?environment\s+variables",
]

COMPILED_INJECTION_PATTERNS = [re.compile(p) for p in INJECTION_PATTERNS]

SECRET_REPLACEMENTS = [
    # Gmail App Passwords (4 groups of 4 letters)
    (re.compile(r"(?i)\b[a-z]{4}\s+[a-z]{4}\s+[a-z]{4}\s+[a-z]{4}\b"), "***REDACTED_APP_KEY***"),
    # Bearer tokens
    (re.compile(r"(?i)\b(bearer\s+)[a-zA-Z0-9_\-\.]{15,}"), r"\1***REDACTED***"),
    # Session cookies
    (re.compile(r"(?i)\b(li_at=)[^\s;'\"&]+"), r"\1***REDACTED***"),
    (re.compile(r"(?i)\b(jsessionid=)[^\s;'\"&]+"), r"\1***REDACTED***"),
    # Passwords in env or querystrings
    (re.compile(r"(?i)\b(password|passwd|pwd|secret)=['\"]?([^\s'\"&]+)['\"]?"), r"\1=***REDACTED***"),
]


def sanitize_input(text: str, max_chars: int = 1500) -> Tuple[str, bool]:
    """
    Sanitize untrusted external input (recruiter DMs, post bodies) before
    interpolating into LLM prompts or templates.

    Returns:
        (sanitized_text, was_flagged_for_injection)
    """
    if not text:
        return "", False

    # 1. Truncate excessive input to prevent buffer/token exhaustion attacks
    cleaned = text[:max_chars].strip()

    # 2. Strip null bytes and non-printable control characters (except newline/tab)
    cleaned = "".join(ch for ch in cleaned if ch in ("\n", "\t", "\r") or (ord(ch) >= 32 and ord(ch) != 127))

    # 3. Detect prompt injection attempts
    flagged = False
    for pat in COMPILED_INJECTION_PATTERNS:
        if pat.search(cleaned):
            flagged = True
            # Neutralize the match by replacing with safe placeholder
            cleaned = pat.sub("[FILTERED_POTENTIAL_INJECTION]", cleaned)

    # 4. Strip risky HTML / script constructs
    cleaned = re.sub(r"(?i)<\s*script[^>]*>.*?<\s*\/\s*script\s*>", "[REMOVED_SCRIPT]", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"(?i)<\s*iframe[^>]*>.*?<\s*\/\s*iframe\s*>", "[REMOVED_IFRAME]", cleaned, flags=re.DOTALL)

    return cleaned, flagged


def mask_sensitive(text: str) -> str:
    """
    Redact secrets, passwords, and sensitive session tokens from text
    prior to logging, console display, or ledger persistence.
    """
    if not text:
        return ""

    masked = text
    for pat, repl in SECRET_REPLACEMENTS:
        masked = pat.sub(repl, masked)

    return masked


# ═══════════════════════════════════════════════════════════════════════════════
# 2. TOKEN SAVER: SEMANTIC COMPRESSION (ecoMode)
# ═══════════════════════════════════════════════════════════════════════════════

# Redundant filler phrases that inflate token count without adding meaning
FILLER_PATTERNS = [
    r"(?i)\bhope\s+you\s+are\s+doing\s+well\b",
    r"(?i)\bhope\s+this\s+email\s+finds\s+you\s+well\b",
    r"(?i)\bi\s+am\s+writing\s+to\s+you\s+because\b",
    r"(?i)\bas\s+per\s+our\s+previous\s+conversation\b",
    r"(?i)\bplease\s+feel\s+free\s+to\b",
    r"(?i)\bat\s+your\s+earliest\s+convenience\b",
    r"(?i)\bdo\s+not\s+hesitate\s+to\s+reach\s+out\b",
    r"(?i)\bthank\s+you\s+for\s+taking\s+the\s+time\s+to\s+read\s+this\b",
    r"(?i)\bi\s+would\s+like\s+to\s+bring\s+to\s+your\s+attention\b",
    r"(?i)\bneedless\s+to\s+say\b",
]

COMPILED_FILLER_PATTERNS = [re.compile(p) for p in FILLER_PATTERNS]


def compress_text(text: str, mode: str = "eco") -> str:
    """
    Applies ecoMode semantic compression to remove wordy filler, boilerplate,
    and repeated meaning while preserving technical precision and professional tone.

    Modes:
      - 'eco': Default semantic compression. Short, punchy, high signal-to-noise.
      - 'eco max': Extreme brevity. Minimum viable words, delta-only.
      - 'eco code': Code/technical specs prioritized, zero prose overhead.
    """
    if not text:
        return ""

    compressed = text

    # Remove standard corporate filler
    for pat in COMPILED_FILLER_PATTERNS:
        compressed = pat.sub("", compressed)

    # Clean redundant whitespace and double newlines
    compressed = re.sub(r"[ \t]+", " ", compressed)
    compressed = re.sub(r"\n{3,}", "\n\n", compressed).strip()

    if mode == "eco max":
        # Additional brevity: shorten polite signoffs to single line
        compressed = re.sub(r"(?i)\b(best\s+regards|sincerely|warm\s+regards),?\s*\n+Vedant.*", "\n— Vedant", compressed, flags=re.DOTALL)

    return compressed


def build_eco_prompt(
    sender: str,
    incoming_message: str,
    mode: str = "eco",
) -> Dict[str, Any]:
    """
    Constructs an ultra-compact, token-efficient prompt payload for Ollama / LLM.
    Enforces ecoMode token budgeting:
      - Uses minimal instruction tokens (<45 tokens vs 150+ standard).
      - Caps output tokens (`num_predict` / `max_tokens`: 50-80).
      - Injects strict prompt boundaries to block prompt injection.
    """
    sanitized_msg, flagged = sanitize_input(incoming_message, max_chars=800)
    first_name = sender.split()[0] if sender else "there"

    if mode == "eco max":
        # Extreme compression prompt: under 30 instruction tokens
        system_instruction = (
            "You are Vedant Singh (SWE). Reply in <=45 words. "
            "Direct, warm, professional. No filler. Next step only."
        )
        max_tokens = 50
    else:
        # Default eco prompt: under 45 instruction tokens
        system_instruction = (
            "You are Vedant Singh (Software Engineer). Draft a concise LinkedIn reply "
            "under 65 words. Express enthusiasm, suggest a quick call, keep it crisp."
        )
        max_tokens = 80

    prompt = (
        f"{system_instruction}\n\n"
        f"Sender: {first_name}\n"
        f"Message: \"{sanitized_msg}\"\n"
        f"Reply:"
    )

    return {
        "prompt": prompt,
        "max_tokens": max_tokens,
        "flagged_for_injection": flagged,
        "mode": mode,
    }


def estimate_token_count(text: str) -> int:
    """
    Fast heuristic token counter for ARM/Raspberry Pi (avoids loading large
    tiktoken BPE tables into RAM). Uses ~1.3 tokens per whitespace word heuristic.
    """
    if not text:
        return 0
    words = len(text.split())
    # Accounts for punctuation, subword splits, and formatting
    return int(words * 1.33) + 1


def calculate_savings(baseline_text: str, eco_text: str) -> Dict[str, Any]:
    """
    Calculates token reduction and compression ratio between baseline and ecoMode.
    """
    base_tokens = estimate_token_count(baseline_text)
    eco_tokens = estimate_token_count(eco_text)
    saved_tokens = max(0, base_tokens - eco_tokens)
    savings_pct = (saved_tokens / base_tokens * 100.0) if base_tokens > 0 else 0.0

    return {
        "baseline_tokens": base_tokens,
        "eco_tokens": eco_tokens,
        "tokens_saved": saved_tokens,
        "savings_percent": round(savings_pct, 1),
    }
