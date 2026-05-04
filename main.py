"""
main.py — Pipeline Orchestrator
---------------------------------
Runs the full claims normalization pipeline and saves results to output/results.json
"""

import json
import logging
import argparse
import time
from pathlib import Path
from datetime import datetime

from pipeline.preprocess import preprocess
from pipeline.rules import run_rules
from pipeline.llm import extract_with_llm
from pipeline.combine import combine
from pipeline.validate import validate
from utils.logger import setup_logging

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


def run_pipeline(raw_text: str) -> dict:
    """Execute the full claims normalization pipeline for a single claim."""
    start = time.time()
    logger.info(f"Pipeline started for input: {raw_text!r}")

    cleaned   = preprocess(raw_text)
    rule_result = run_rules(cleaned)
    llm_result  = extract_with_llm(cleaned)
    combined    = combine(rule_result, llm_result)
    final       = validate(combined)

    elapsed = round(time.time() - start, 3)
    logger.info(f"Pipeline completed in {elapsed}s. Output: {final}")
    return final


def save_results(data: list[dict], filename: str = None):
    """Save results to output/results_<timestamp>.json"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"results_{timestamp}.json"

    filepath = OUTPUT_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Results saved to: {filepath}")
    return filepath


def run_batch(filepath: str) -> list[dict]:
    """Process multiple claims from a text file (one claim per line)."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Batch file not found: {filepath}")

    claims = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    logger.info(f"Batch processing {len(claims)} claims from '{filepath}'")

    results = []
    for i, claim in enumerate(claims, 1):
        logger.info(f"Processing claim {i}/{len(claims)}")
        result = run_pipeline(claim)
        results.append({"input": claim, "output": result})

    return results


if __name__ == "__main__":
    setup_logging()

    parser = argparse.ArgumentParser(description="Claims Description Normalizer")
    parser.add_argument("--batch", type=str, help="Path to batch file (one claim per line)")
    args = parser.parse_args()

    if args.batch:
        results = run_batch(args.batch)
        save_results(results, "batch_results.json")
        print(json.dumps(results, indent=2))
    else:
        sample_claims = [
            "car hit from behind, bumper broken, repair maybe 30k, happened last night",
            "bike stolen from parking lot yesterday evening",
            "engine seized on highway, towed to workshop, total repair cost around 85000",
            "flood damaged car, water entered cabin, seats destroyed",
            "minor dent on front door, just cosmetic, maybe 3000 to fix",
            "house fire started in kitchen, spread to two rooms, total loss",
        ]

        print("=" * 60)
        print("CLAIMS DESCRIPTION NORMALIZER — DEMO")
        print("=" * 60)

        all_results = []
        for claim in sample_claims:
            print(f"\nINPUT:  {claim}")
            result = run_pipeline(claim)
            print(f"OUTPUT: {json.dumps(result, indent=2)}")
            print("-" * 60)
            all_results.append({"input": claim, "output": result})

        # Save all results to file
        save_results(all_results)