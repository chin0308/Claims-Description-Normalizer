"""
FastAPI Application
--------------------
Serves the claims normalization pipeline as a REST API
AND serves the frontend UI at http://localhost:8000/

Run with:
    uvicorn api.app:app --reload --port 8000
"""

import logging
import sys, os, time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import run_pipeline
from utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Claims Description Normalizer",
    description="Hybrid rule-based + LLM pipeline for insurance claim extraction.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Serve the frontend HTML ──────────────────────────────────
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

@app.get("/", include_in_schema=False)
def serve_ui():
    """Serve the main frontend UI."""
    return FileResponse(FRONTEND_DIR / "index.html")


# ── Pydantic schemas ─────────────────────────────────────────
class ClaimRequest(BaseModel):
    claim_text: str = Field(
        ..., min_length=3, max_length=2000,
        example="car hit from behind, bumper broken, repair maybe 30k"
    )

class FieldMetadata(BaseModel):
    source:      str  # "rules", "llm", or "none"
    confidence:  float  # 0.0 to 1.0

class ClaimResponse(BaseModel):
    severity:           str
    loss_type:          str
    estimated_cost:     Optional[float]
    summary:            str
    processing_time_ms: float
    metadata:           Optional[dict[str, FieldMetadata]] = None  # New optional field


# ── Endpoints ────────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "service": "claims-normalizer"}


@app.post("/process_claim", response_model=ClaimResponse, tags=["Claims"])
def process_claim(request: ClaimRequest):
    """Process a single insurance claim description."""
    logger.info(f"POST /process_claim — {request.claim_text!r}")
    start = time.time()
    try:
        result = run_pipeline(request.claim_text)
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    result["processing_time_ms"] = round((time.time() - start) * 1000, 2)
    return result


@app.post("/process_batch", tags=["Claims"])
async def process_batch(file: UploadFile = File(...)):
    """Process multiple claims from an uploaded .txt file (one claim per line)."""
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are supported.")

    content = await file.read()
    claims = [l.strip() for l in content.decode("utf-8").splitlines() if l.strip()]

    if not claims:
        raise HTTPException(status_code=400, detail="File is empty.")
    if len(claims) > 100:
        raise HTTPException(status_code=400, detail="Max 100 claims per batch.")

    logger.info(f"POST /process_batch — {len(claims)} claims")
    results = [{"input": c, "output": run_pipeline(c)} for c in claims]
    return {"total": len(results), "results": results}