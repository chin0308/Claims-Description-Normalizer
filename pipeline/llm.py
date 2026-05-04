"""
LLM Extraction Module
----------------------
Uses Google Gemini (google-genai package) to extract structured fields
from claim text.
"""

import json
import logging
import os
import re
from typing import Optional
from google import genai

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are an expert insurance claims analyst with 15 years of experience.
Your job is to extract structured data from messy, real-world insurance claim descriptions.

You MUST respond with ONLY a valid JSON object. No explanation, no markdown, no commentary.

The JSON must have exactly these keys:
- "severity": one of "low", "medium", or "high"
- "loss_type": one of "collision", "theft", "fire", "flood", "vandalism", "natural", "mechanical", "unknown"
- "estimated_cost": a number (integer or float), or null if not mentioned
- "summary": a concise 1-sentence professional summary of the claim

Rules:
- severity "low" = minor cosmetic damage, no injuries
- severity "medium" = moderate damage, functional impact, significant repair needed
- severity "high" = total loss, injury, major structural damage
- If something is uncertain, make your best professional judgment
- estimated_cost must be a raw number, never a string with currency symbols

Now extract structured information from this insurance claim:

"{claim_text}"

Respond with only valid JSON."""


def extract_with_llm(text: str, api_key: Optional[str] = None) -> dict:
    """
    Call the Gemini API (gemini-2.0-flash) to extract structured fields.
    Falls back to safe empty dict if extraction fails.
    """
    raw_output = ""
    try:
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY is not set.")

        client = genai.Client(api_key=key)
        prompt = PROMPT_TEMPLATE.format(claim_text=text)

        logger.info("Calling Gemini API for LLM extraction...")
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        raw_output = response.text.strip()
        logger.debug(f"Raw Gemini response: {raw_output}")

        # Strip markdown fences if present
        raw_output = re.sub(r"^```(?:json)?\s*", "", raw_output)
        raw_output = re.sub(r"\s*```$", "", raw_output).strip()

        result = json.loads(raw_output)
        logger.info(f"LLM extraction successful: {result}")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Gemini returned invalid JSON: {e}. Raw: {raw_output!r}")
        return _empty_llm_result()

    except Exception as e:
        logger.error(f"Unexpected error in LLM extraction: {e}")
        return _empty_llm_result()


def _empty_llm_result() -> dict:
    """Return safe defaults if LLM extraction fails entirely."""
    return {
        "severity":       None,
        "loss_type":      None,
        "estimated_cost": None,
        "summary":        None,
    }