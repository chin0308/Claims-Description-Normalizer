"""
Rule-Based Extraction Module
-----------------------------
Deterministic, fast extraction using regex and keyword matching.

No LLM here — this is cheap, predictable, and runs first.
Think of it as the "first line of analysis" before the expensive AI step.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Keyword maps for loss type detection
# ─────────────────────────────────────────────
LOSS_TYPE_KEYWORDS: dict[str, list[str]] = {
    "collision":    ["hit", "crash", "collide", "collision", "rear.end", "rammed", "bumper", "fender", "accident"],
    "theft":        ["stolen", "theft", "robbed", "missing vehicle", "broke in", "burglary"],
    "fire":         ["fire", "burned", "burnt", "flame", "ignite", "smoke"],
    "flood":        ["flood", "submerge", "water damage", "waterlog", "inundated", "rain damage"],
    "vandalism":    ["vandal", "scratch", "keyed", "graffiti", "broken window", "smashed"],
    "natural":      ["hail", "storm", "earthquake", "tornado", "hurricane", "lightning", "fallen tree"],
    "mechanical":   ["engine failure", "breakdown", "mechanical", "seized", "overheated"],
}

# ─────────────────────────────────────────────
# Severity signals
# ─────────────────────────────────────────────
SEVERITY_HIGH_SIGNALS   = ["total loss", "totaled", "completely destroyed", "write.off",
                            "major", "severe", "extensive damage", "fatal", "hospitalized"]
SEVERITY_LOW_SIGNALS    = ["minor", "small", "tiny", "scratch", "dent", "cosmetic",
                            "superficial", "slight", "hairline"]


def extract_loss_type(text: str) -> Optional[str]:
    """
    Match the claim text against known loss type keyword groups.
    Returns the first matched category, or None if no match.
    """
    for loss_type, keywords in LOSS_TYPE_KEYWORDS.items():
        pattern = r"\b(" + "|".join(keywords) + r")\b"
        if re.search(pattern, text, re.IGNORECASE):
            logger.debug(f"Rule matched loss_type='{loss_type}'")
            return loss_type
    return None


def extract_cost(text: str) -> Optional[float]:
    """
    Extract the first numeric cost mention from the text.

    Handles formats like:
    - "30000", "30,000", "₹ 30,000", "$ 1500", "about 50000", "around 20000"
    """
    # Remove currency symbols for cleaner matching
    cleaned = re.sub(r"[₹$,]", "", text)

    # Look for patterns like "repair 30000" or "cost around 50000"
    match = re.search(r"\b(\d{3,7}(?:\.\d{1,2})?)\b", cleaned)
    if match:
        try:
            value = float(match.group(1))
            if value > 0:
                logger.debug(f"Rule extracted cost={value}")
                return value
        except ValueError:
            pass
    return None


def extract_severity(text: str) -> Optional[str]:
    """
    Determine severity from strong keyword signals only.
    If no clear signal, returns None (let LLM decide).
    """
    for signal in SEVERITY_HIGH_SIGNALS:
        if re.search(signal, text, re.IGNORECASE):
            return "high"
    for signal in SEVERITY_LOW_SIGNALS:
        if re.search(signal, text, re.IGNORECASE):
            return "low"
    return None


def run_rules(text: str) -> dict:
    """
    Run all rule-based extractors and return a partial result dict.

    Fields not found by rules will be None — LLM will fill those in.

    Returns:
        dict with keys: loss_type, estimated_cost, severity (all optional)
    """
    result = {
        "loss_type":      extract_loss_type(text),
        "estimated_cost": extract_cost(text),
        "severity":       extract_severity(text),
        "summary":        None,   # Rules don't generate summaries
    }
    logger.info(f"Rule-based extraction result: {result}")
    return result
