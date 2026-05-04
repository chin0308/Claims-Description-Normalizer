# 🛡️ Claims Description Normalizer

A **production-grade GenAI pipeline** that converts messy, unstructured insurance claim descriptions into clean, structured JSON using a **hybrid rule-based + LLM extraction** approach.

---

## 🎯 Problem Statement

Insurance companies receive thousands of claim descriptions daily — written by policyholders, agents, and surveyors — in wildly inconsistent formats:

> *"car hit from behind, bumper broken, repair maybe 30k, happened last night"*
> *"veh. dmg. approx 85K, engine seized, total loss"*
> *"bike stolen frm parkng lot ystrdy evng"*

Downstream automation systems (fraud detection, routing, reserve calculation) need **structured, validated JSON** — not free-form text. This pipeline bridges that gap.

---

## 🏗️ Architecture

```
Raw Claim Text
      │
      ▼
┌─────────────────┐
│  Preprocessing  │  Normalize text, expand shorthands, fix "30k" → 30000
└────────┬────────┘
         │
    ┌────┴─────────────────────┐
    ▼                          ▼
┌──────────────┐     ┌──────────────────┐
│  Rule-Based  │     │  LLM Extraction  │  Claude API (claude-sonnet)
│  Extraction  │     │  (Anthropic)     │
└──────┬───────┘     └────────┬─────────┘
       │                      │
       └──────────┬───────────┘
                  ▼
         ┌────────────────┐
         │ Combination    │  Rules win on high-confidence fields
         │ Layer          │  LLM fills gaps + generates summary
         └───────┬────────┘
                 │
                 ▼
         ┌────────────────┐
         │  Validation    │  Enforce schema, fix invalid values
         └───────┬────────┘
                 │
                 ▼
         ┌────────────────┐
         │  Output JSON   │
         └────────────────┘
```

---

## 📦 Project Structure

```
claims-normalizer/
├── main.py                  # Pipeline orchestrator + CLI
├── pipeline/
│   ├── preprocess.py        # Text cleaning and normalization
│   ├── rules.py             # Regex/keyword-based extraction
│   ├── llm.py               # Claude API extraction
│   ├── combine.py           # Merge rule + LLM outputs
│   └── validate.py          # Schema enforcement and correction
├── api/
│   └── app.py               # FastAPI REST endpoints
├── utils/
│   └── logger.py            # Centralized rotating log setup
├── tests/
│   └── test_pipeline.py     # Full test suite (unit + integration)
├── data/
│   └── sample_claims.txt    # Sample batch input
├── logs/                    # Auto-generated log files
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup

### 1. Clone & install dependencies
```bash
git clone <repo>
cd claims-normalizer
pip install -r requirements.txt
```

### 2. Set your Anthropic API key
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

### 3. Run the demo
```bash
python main.py
```

### 4. Run batch processing
```bash
python main.py --batch data/sample_claims.txt
```

### 5. Start the API server
```bash
uvicorn api.app:app --reload --port 8000
```

Visit: http://localhost:8000/docs for interactive API docs.

---

## 🔌 API Endpoints

### `POST /process_claim`
Process a single claim description.

**Request:**
```json
{
  "claim_text": "car hit from behind, bumper broken, repair maybe 30k"
}
```

**Response:**
```json
{
  "severity": "medium",
  "loss_type": "collision",
  "estimated_cost": 30000.0,
  "summary": "Rear-end collision causing bumper damage requiring repair.",
  "processing_time_ms": 842.5
}
```

### `POST /process_batch`
Upload a `.txt` file with one claim per line. Returns structured results for all claims.

### `GET /health`
Health check endpoint.

---

## 🧪 Example Inputs & Outputs

| Input | severity | loss_type | estimated_cost | summary |
|-------|----------|-----------|----------------|---------|
| "car hit from behind, bumper broken, repair 30k" | medium | collision | 30000 | Rear-end collision causing bumper damage |
| "bike stolen from parking lot" | medium | theft | null | Vehicle theft reported from parking area |
| "engine seized on highway, repair 85000" | high | mechanical | 85000 | Engine failure causing vehicle breakdown |
| "minor scratch on door, 1500 to fix" | low | collision | 1500 | Minor cosmetic damage to vehicle door |
| "flood damaged car, seats destroyed" | high | flood | null | Flood damage affecting vehicle interior |

---

## 🧠 Why This Approach Is Robust

### Hybrid Extraction
- **Rules are fast, free, and deterministic** — they extract numbers and keywords reliably
- **LLM handles ambiguity** — "total loss" semantics, implied severity, generating summaries
- Neither alone is sufficient; together they're resilient

### Validation Layer
- Even if both extractors fail, validation ensures the output is always schema-valid
- Corrupt data never leaves the pipeline

### Modular Design
- Each module is independently testable and replaceable
- Swap Claude for GPT-4 by changing only `llm.py`
- Add new fields (e.g., `injury_reported`) by extending rules, LLM prompt, and validator

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

Tests cover:
- Preprocessing correctness (abbreviations, k-suffix expansion)
- Rule extraction accuracy (all loss types, cost, severity)
- Combination layer precedence logic
- Validation defaults and corrections
- End-to-end integration with mocked LLM

---

## 📝 Logging

Logs are written to `logs/pipeline.log` (rotating, max 5MB × 3 files).
Console shows INFO; file captures full DEBUG trace including what each module extracted and why.
