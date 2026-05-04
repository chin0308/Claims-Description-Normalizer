"""
Combination Layer
------------------
Merges outputs from the rule-based and LLM extractors.

Strategy:
- Rule-based wins when it finds a confident answer (deterministic = reliable)
- LLM fills in gaps where rules returned None
- For estimated_cost: rule-based is preferred (numbers from text = exact)
- For summary: always use LLM (rules can't generate prose)
- For severity: rules win on extreme signals; otherwise use LLM

Think of rules as "fast, certain lanes" and LLM as the "fallback expert".
"""

import logging

logger = logging.getLogger(__name__)


def _calculate_confidence(rule_value, llm_value, field_name):
    """
    Calculate confidence score based on which extractor provided the value.

    Confidence scoring:
    - Rules alone: 0.90 (deterministic pattern match)
    - LLM alone: 0.70 (semantic analysis, less certain)
    - Both agree: 0.95 (very high confidence)
    - Both disagree: 0.65 (prefer rules but lower confidence on decision)
    - Missing: 0.0 (not extracted)
    """
    if rule_value is None and llm_value is None:
        return 0.0
    if rule_value is not None and llm_value is None:
        return 0.90  # Rules-only is deterministic
    if rule_value is None and llm_value is not None:
        return 0.70  # LLM-only is good but less certain
    if rule_value == llm_value:
        return 0.95  # Both agree = very confident
    # Both present but different — prefer rule but lower confidence
    return 0.65


def combine(rule_output: dict, llm_output: dict) -> dict:
    """
    Merge rule-based and LLM outputs into one unified result.

    Precedence logic per field:
    - loss_type:      rules → LLM
    - estimated_cost: rules → LLM  (rules extract exact numbers from text)
    - severity:       rules → LLM  (rules detect extreme signals reliably)
    - summary:        always LLM   (rules cannot generate prose)

    Metadata tracking:
    - source: which extractor provided the value ("rules", "llm", or "none")
    - confidence: confidence score (0.0-1.0)

    Args:
        rule_output: Partial dict from rule-based extractor (some None values expected)
        llm_output:  Full dict from LLM extractor (may also have None values)

    Returns:
        Combined dict with best available values for each field + metadata
    """
    def prefer_rule(field: str) -> any:
        """Return rule value if present, else fall back to LLM value."""
        return rule_output.get(field) or llm_output.get(field)

    combined = {
        "loss_type":      prefer_rule("loss_type"),
        "estimated_cost": prefer_rule("estimated_cost"),
        "severity":       prefer_rule("severity"),
        "summary":        llm_output.get("summary"),   # LLM only
    }

    # NEW: Track source and confidence for each field
    metadata = {}
    for field in ["loss_type", "estimated_cost", "severity"]:
        rule_val = rule_output.get(field)
        llm_val = llm_output.get(field)
        source = "rules" if rule_val is not None else ("llm" if llm_val is not None else "none")
        confidence = _calculate_confidence(rule_val, llm_val, field)

        metadata[field] = {
            "source": source,
            "confidence": round(confidence, 2)
        }
        logger.debug(f"Field '{field}': source={source}, confidence={confidence}")

    # Summary is always from LLM
    metadata["summary"] = {
        "source": "llm",
        "confidence": 0.85  # Fixed confidence for LLM-generated summaries
    }

    combined["metadata"] = metadata
    logger.info(f"Combined result: {combined}")
    return combined
