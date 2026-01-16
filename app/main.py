import os
import time
import logging
from typing import List, Any

from fastapi import FastAPI
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

# ---------- logging ----------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("inference-api")

# ---------- prometheus metrics ----------
REQUESTS_TOTAL = Counter(
    "inference_requests_total",
    "Total number of prediction requests",
    ["endpoint", "status"]
)

REQUEST_LATENCY_SECONDS = Histogram(
    "inference_request_latency_seconds",
    "Latency of prediction requests in seconds",
    ["endpoint"]
)

DRIFT_DETECTED_TOTAL = Counter(
    "drift_detected_total",
    "Total number of drift detections",
)

# ---------- app ----------
app = FastAPI(title="Inference API", version="0.1.0")

class PredictRequest(BaseModel):
    instances: List[List[float]] = Field(..., description="List of feature vectors")

class PredictResponse(BaseModel):
    predictions: List[Any]
    drift_detected: bool = False

def dummy_predict(instances: List[List[float]]) -> List[int]:
    """
    Temporary predictor.
    Later we will replace it with MLflow-loaded model.predict(...)
    """
    # simple deterministic output to test the pipeline
    return [int(sum(x) > 10) for x in instances]

def drift_detector_stub(instances: List[List[float]]) -> bool:
    """
    Drift detector stub.
    Later: Alibi Detect or Great Expectations.
    For now: return True if any feature value is too large (toy rule).
    """
    for row in instances:
        if any(v > 100 for v in row):
            return True
    return False

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest):
    endpoint = "/predict"
    start = time.time()

    try:
        logger.info("request.instances=%s", payload.instances)

        drift = drift_detector_stub(payload.instances)
        if drift:
            DRIFT_DETECTED_TOTAL.inc()
            logger.warning("Drift detected")

        preds = dummy_predict(payload.instances)

        logger.info("response.predictions=%s drift_detected=%s", preds, drift)

        REQUESTS_TOTAL.labels(endpoint=endpoint, status="success").inc()
        return PredictResponse(predictions=preds, drift_detected=drift)

    except Exception as e:
        logger.exception("predict_failed: %s", e)
        REQUESTS_TOTAL.labels(endpoint=endpoint, status="error").inc()
        raise

    finally:
        REQUEST_LATENCY_SECONDS.labels(endpoint=endpoint).observe(time.time() - start)
