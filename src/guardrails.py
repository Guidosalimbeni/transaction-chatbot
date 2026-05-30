"""Lightweight guardrails for the PoC.

In production these would be replaced by a real guardrails service
(Guardrails AI, NVIDIA NeMo, Lakera, in-house). The point here is to
show the architectural seam — input checks before the agent, output
checks before responding to the user.
"""
from __future__ import annotations

import re

# Out-of-scope intents that should be deflected to a human or to the FAQ.
OUT_OF_SCOPE_PATTERNS = [
    r"\b(invest|investment advice|should i buy|stock tip)\b",
    r"\b(mortgage|loan) application\b",
    r"\b(close my account|cancel my account)\b",
    r"\b(transfer|send money|pay) (?!.*history)\b",  # Read-only in MVP
]

# Patterns that look like the user is trying to manipulate the system prompt.
PROMPT_INJECTION_PATTERNS = [
    r"ignore (the |all |previous |any |my )*?(instructions|prompt|rules)",
    r"you are now",
    r"system prompt",
    r"reveal your (instructions|prompt|system)",
]


def check_input(user_message: str) -> dict:
    """Run input guardrails. Returns {'ok': bool, 'reason': str | None}."""
    lower = user_message.lower()

    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, lower):
            return {
                "ok": False,
                "reason": (
                    "I can only help with questions about your balance and "
                    "transactions. Could you rephrase what you're trying to find out?"
                ),
            }

    for pattern in OUT_OF_SCOPE_PATTERNS:
        if re.search(pattern, lower):
            return {
                "ok": False,
                "reason": (
                    "I can only help you check balances, browse your transaction "
                    "history, and look into unfamiliar charges. For anything else "
                    "(transfers, advice, account changes), please contact a Lloyds "
                    "agent through the main app."
                ),
            }

    return {"ok": True, "reason": None}


# Patterns we never want to leak in an output (very light demo version).
SENSITIVE_OUTPUT_PATTERNS = [
    (r"\b\d{16}\b", "[CARD NUMBER REDACTED]"),
    (r"\b\d{2}-\d{2}-\d{2}\b", "[SORT CODE REDACTED]"),
]


def check_output(response: str) -> str:
    """Redact obvious sensitive patterns from the response."""
    out = response
    for pattern, replacement in SENSITIVE_OUTPUT_PATTERNS:
        out = re.sub(pattern, replacement, out)
    return out
