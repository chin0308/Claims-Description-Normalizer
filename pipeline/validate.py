"""
Validation Module
------------------
Enforces schema correctness and business rules on the combined output.

This is the "quality gate" before data leaves the pipeline.
A corrupt or invalid output reaching downstream systems is worse than no output.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Schema constraints
# ─────────────────────────────────────────────
VALID_SEVERITIES  = {"low", "medium", "high"}
VALID_LOSS_TYPES  = {"collision", "theft", "fire", "flood", "vandalism",
                     "natural", "mechanical", "unknown"}
DEFAULT_SEVERITY  = "medium"   # Safest assumption when unknown
DEFAULT_LOSS_TYPE = "unknown"
MAX_COST          = 10_000_000  # Sanity cap: ₹1 crore / $10M


def validate(data: dict) -> dict:
    """
    Validate and auto-correct the combined extraction output.

    Corrections applied:
    - severity: must be in {low, medium, high} → default "medium" if invalid
    - loss_type: must be in known set → default "unknown" if invalid
    - estimated_cost: must be a positive number → set to None if invalid
    - summary: must be a non-empty string → set to "No summary available" if missing

    NOW: Also preserves metadata (source, confidence) from combine layer.

    Args:
        data: Combined output from the combination layer

    Returns:
        Validated, corrected dict ready for output with metadata preserved
    """
    result = dict(data)  # Avoid mutating the original
    metadata = result.pop("metadata", {})  # Extract metadata before validation

    # ── Severity ──────────────────────────────
    severity = _coerce_str(result.get("severity"))
    if severity not in VALID_SEVERITIES:
        logger.warning(f"Invalid severity '{severity}' → defaulting to '{DEFAULT_SEVERITY}'")
        severity = DEFAULT_SEVERITY
    result["severity"] = severity

    # ── Loss Type ─────────────────────────────
    loss_type = _coerce_str(result.get("loss_type"))
    if loss_type not in VALID_LOSS_TYPES:
        logger.warning(f"Invalid loss_type '{loss_type}' → defaulting to '{DEFAULT_LOSS_TYPE}'")
        loss_type = DEFAULT_LOSS_TYPE
    result["loss_type"] = loss_type

    # ── Estimated Cost ────────────────────────
    cost = result.get("estimated_cost")
    result["estimated_cost"] = _validate_cost(cost)

    # ── Summary ───────────────────────────────
    summary = result.get("summary")
    if not summary or not isinstance(summary, str) or not summary.strip():
        logger.warning("Missing or empty summary → using default.")
        summary = "No summary available."
    result["summary"] = summary.strip()

    # NEW: Preserve metadata at end
    result["metadata"] = metadata
    logger.info(f"Validation complete: {result}")
    return result


def _coerce_str(value: Any) -> str:
    """Convert value to lowercase string, or empty string if None."""
    if value is None:
        return ""
    return str(value).strip().lower()


def _validate_cost(cost: Any) -> float | None:
    """
    Ensure estimated_cost is a positive finite number within sanity bounds.
    Returns None if it cannot be coerced to a valid value.
    """
    if cost is None:
        return None
    try:
        cost = float(cost)
        if cost <= 0:
            logger.warning(f"Non-positive cost {cost} → setting to None")
            return None
        if cost > MAX_COST:
            logger.warning(f"Cost {cost} exceeds max cap {MAX_COST} → capping")
            return float(MAX_COST)
        return cost
    except (ValueError, TypeError):
        logger.warning(f"Unparseable cost value '{cost}' → setting to None")
        return None
