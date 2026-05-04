"""
Preprocessing Module
--------------------
Cleans and normalizes raw claim text before it hits any extraction logic.
Think of this as the "washing station" for messy input.
"""

import re
import logging

logger = logging.getLogger(__name__)


def preprocess(text: str) -> str:
    """
    Normalize raw claim text for consistent downstream processing.

    Steps:
    1. Lowercase everything
    2. Strip extra whitespace
    3. Expand common shorthand (e.g., "approx" → "approximately")
    4. Remove special characters that add no signal
    5. Fix number formatting (e.g., "30k" → "30000")

    Args:
        text: Raw claim description from user

    Returns:
        Cleaned, normalized string
    """
    if not text or not isinstance(text, str):
        logger.warning("Received empty or non-string input.")
        return ""

    original = text
    text = text.lower().strip()

    # Expand shorthand
    abbreviations = {
        r"\bapprox\.?\b": "approximately",
        r"\bamt\.?\b": "amount",
        r"\bveh\.?\b": "vehicle",
        r"\bdmg\.?\b": "damage",
        r"\bw/\b": "with",
        r"\bw/o\b": "without",
        r"\binc\.?\b": "including",
    }
    for pattern, replacement in abbreviations.items():
        text = re.sub(pattern, replacement, text)

    # Convert "30k" or "30K" → "30000", "1.5L" → "150000"
    text = re.sub(
        r"(\d+(\.\d+)?)\s*k\b",
        lambda m: str(int(float(m.group(1)) * 1000)),
        text
    )
    text = re.sub(
        r"(\d+(\.\d+)?)\s*l\b",  # lakh (Indian context)
        lambda m: str(int(float(m.group(1)) * 100000)),
        text
    )

    # Remove stray special characters but keep ₹, $, digits, letters, spaces
    text = re.sub(r"[^\w\s₹$.,\-]", " ", text)

    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()

    logger.debug(f"Preprocessed: '{original}' → '{text}'")
    return text
