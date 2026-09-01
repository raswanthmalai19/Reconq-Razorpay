"""Lightweight pre-filter that flags obvious prompt-injection markers in
narration/memo text before it ever reaches the LLM prompt."""
import re

INJECTION_PATTERNS = [
    r"ignore (all|previous|prior) instructions",
    r"disregard (the|your) (budget|rules|instructions)",
    r"\bsystem\s*:",
    r"\byou are now\b",
    r"\bact as\b",
    r"\[system\]",
    r"</?(system|assistant|user)>",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def scan_text(text: str) -> bool:
    """Returns True if the text matches a known injection marker pattern."""
    if not text:
        return False
    return any(p.search(text) for p in _COMPILED)
