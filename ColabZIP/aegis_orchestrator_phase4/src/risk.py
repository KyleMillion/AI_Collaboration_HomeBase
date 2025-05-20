"""Simple Risk & Review policy layer (Warden hooks)."""

import re
from typing import Dict

# naive patterns -> risk score
_HIGH_RISK_PATTERNS = [
    re.compile(r"\btransfer\b.*\b\$?\d+", re.I),
    re.compile(r"\bdelete\b.*\baccount\b", re.I),
    re.compile(r"\bexecute\b.*\bshell\b", re.I),
]


def score_instruction(instr: str) -> float:
    """Return risk score 0.0‑1.0."""
    score = 0.0
    for pat in _HIGH_RISK_PATTERNS:
        if pat.search(instr):
            score += 0.5
    return min(score, 1.0)


def requires_review(score: float, threshold: float = 0.6) -> bool:
    return score >= threshold
