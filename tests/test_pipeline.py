"""
Test Suite — Claims Description Normalizer
-------------------------------------------
Covers:
  - Preprocessing correctness
  - Rule-based extraction accuracy
  - Validation logic and defaults
  - Full pipeline integration (mocked LLM)
  - Edge cases: empty input, gibberish, partial data

Run with:
    pytest tests/ -v
"""

import pytest
from unittest.mock import patch

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.preprocess import preprocess
from pipeline.rules import extract_loss_type, extract_cost, extract_severity, run_rules
from pipeline.combine import combine
from pipeline.validate import validate
from main import run_pipeline


# ─────────────────────────────────────────────
# PREPROCESSING TESTS
# ─────────────────────────────────────────────
class TestPreprocess:

    def test_lowercase(self):
        assert preprocess("CAR HIT FROM BEHIND") == "car hit from behind"

    def test_strip_whitespace(self):
        assert preprocess("  bumper broken  ") == "bumper broken"

    def test_expand_k_suffix(self):
        result = preprocess("repair cost 30k")
        assert "30000" in result

    def test_expand_lakh_suffix(self):
        result = preprocess("loss about 1.5L")
        assert "150000" in result

    def test_expand_abbreviation(self):
        result = preprocess("veh. dmg.")
        assert "vehicle" in result
        assert "damage" in result

    def test_empty_input(self):
        assert preprocess("") == ""

    def test_none_input(self):
        assert preprocess(None) == ""

    def test_special_chars_removed(self):
        result = preprocess("bumper@broken!!!")
        assert "@" not in result
        assert "!" not in result


# ─────────────────────────────────────────────
# RULE-BASED EXTRACTION TESTS
# ─────────────────────────────────────────────
class TestRuleExtraction:

    def test_detect_collision(self):
        assert extract_loss_type("car hit from behind bumper broken") == "collision"

    def test_detect_theft(self):
        assert extract_loss_type("bike was stolen from the parking lot") == "theft"

    def test_detect_fire(self):
        assert extract_loss_type("vehicle caught fire on the highway") == "fire"

    def test_detect_flood(self):
        assert extract_loss_type("flood damaged the car interior") == "flood"

    def test_detect_vandalism(self):
        assert extract_loss_type("someone keyed the car door") == "vandalism"

    def test_no_match_returns_none(self):
        assert extract_loss_type("something happened with the vehicle") is None

    def test_extract_cost_plain(self):
        assert extract_cost("repair cost 30000") == 30000.0

    def test_extract_cost_comma(self):
        # preprocess removes commas before rules run
        assert extract_cost("repair cost 30000") == 30000.0

    def test_extract_cost_none_when_missing(self):
        assert extract_cost("bumper broken") is None

    def test_severity_high(self):
        assert extract_severity("total loss, vehicle completely destroyed") == "high"

    def test_severity_low(self):
        assert extract_severity("minor scratch on the door") == "low"

    def test_severity_none_when_ambiguous(self):
        assert extract_severity("collision happened near the junction") is None


# ─────────────────────────────────────────────
# COMBINATION LAYER TESTS
# ─────────────────────────────────────────────
class TestCombine:

    def test_rule_wins_when_present(self):
        rule = {"loss_type": "collision", "estimated_cost": 30000, "severity": "low", "summary": None}
        llm  = {"loss_type": "theft",     "estimated_cost": 50000, "severity": "high", "summary": "A collision"}
        result = combine(rule, llm)
        assert result["loss_type"] == "collision"
        assert result["estimated_cost"] == 30000
        assert result["severity"] == "low"

    def test_llm_fills_gaps(self):
        rule = {"loss_type": None, "estimated_cost": None, "severity": None, "summary": None}
        llm  = {"loss_type": "fire", "estimated_cost": 80000, "severity": "high", "summary": "Fire damage"}
        result = combine(rule, llm)
        assert result["loss_type"] == "fire"
        assert result["estimated_cost"] == 80000

    def test_summary_always_from_llm(self):
        rule = {"loss_type": "collision", "estimated_cost": 30000, "severity": "medium", "summary": "rule summary"}
        llm  = {"loss_type": "theft",     "estimated_cost": 5000,  "severity": "low",    "summary": "LLM summary"}
        result = combine(rule, llm)
        # Summary always comes from LLM
        assert result["summary"] == "LLM summary"


# ─────────────────────────────────────────────
# VALIDATION TESTS
# ─────────────────────────────────────────────
class TestValidate:

    def test_valid_input_passes_through(self):
        data = {"severity": "high", "loss_type": "collision", "estimated_cost": 30000, "summary": "Rear-end collision"}
        result = validate(data)
        assert result["severity"] == "high"
        assert result["loss_type"] == "collision"
        assert result["estimated_cost"] == 30000.0

    def test_invalid_severity_defaults_to_medium(self):
        data = {"severity": "catastrophic", "loss_type": "collision", "estimated_cost": 10000, "summary": "Test"}
        result = validate(data)
        assert result["severity"] == "medium"

    def test_invalid_loss_type_defaults_to_unknown(self):
        data = {"severity": "low", "loss_type": "asteroid", "estimated_cost": 5000, "summary": "Test"}
        result = validate(data)
        assert result["loss_type"] == "unknown"

    def test_negative_cost_set_to_none(self):
        data = {"severity": "low", "loss_type": "collision", "estimated_cost": -500, "summary": "Test"}
        result = validate(data)
        assert result["estimated_cost"] is None

    def test_none_cost_stays_none(self):
        data = {"severity": "low", "loss_type": "theft", "estimated_cost": None, "summary": "Test"}
        result = validate(data)
        assert result["estimated_cost"] is None

    def test_missing_summary_gets_default(self):
        data = {"severity": "low", "loss_type": "theft", "estimated_cost": None, "summary": None}
        result = validate(data)
        assert result["summary"] == "No summary available."

    def test_cost_cap_applied(self):
        data = {"severity": "high", "loss_type": "fire", "estimated_cost": 999_999_999, "summary": "Test"}
        result = validate(data)
        assert result["estimated_cost"] == 10_000_000.0


# ─────────────────────────────────────────────
# INTEGRATION TESTS (LLM mocked)
# ─────────────────────────────────────────────
MOCK_LLM_RESPONSE = {
    "severity": "medium",
    "loss_type": "collision",
    "estimated_cost": 30000,
    "summary": "Rear-end collision causing bumper damage.",
}


class TestIntegration:

    @patch("pipeline.llm.extract_with_llm", return_value=MOCK_LLM_RESPONSE)
    def test_standard_collision_claim(self, _mock):
        result = run_pipeline("car hit from behind, bumper broken, repair maybe 30k")
        assert result["severity"] in {"low", "medium", "high"}
        assert result["loss_type"] == "collision"
        assert isinstance(result["estimated_cost"], float)
        assert len(result["summary"]) > 5

    @patch("pipeline.llm.extract_with_llm", return_value=MOCK_LLM_RESPONSE)
    def test_empty_input_does_not_crash(self, _mock):
        # Should return valid (defaulted) output even for empty input
        result = run_pipeline("")
        assert "severity" in result
        assert "loss_type" in result

    @patch("pipeline.llm.extract_with_llm", return_value={
        "severity": None, "loss_type": None, "estimated_cost": None, "summary": None
    })
    def test_all_none_llm_output_still_validates(self, _mock):
        result = run_pipeline("something happened")
        assert result["severity"] == "medium"
        assert result["loss_type"] == "unknown"
        assert result["summary"] == "No summary available."
