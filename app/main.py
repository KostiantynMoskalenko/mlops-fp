from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MLOps Inference Service", version="1.0.0")

class PredictRequest(BaseModel):
    input: Any

class PredictResponse(BaseModel):
    prediction: float
    drift_detected: Optional[bool] = None

class ModelLoader:
    def __init__(self):
        self.model = None
        self.drift_detector = None
        self._load_model()
        self._load_drift_detector()
    
    def _load_model(self):
        logger.info("Loading model...")
        self.model = MockModel()
        logger.info("Model loaded successfully")
    
    def _load_drift_detector(self):
        logger.info("Loading drift detector...")
        self.drift_detector = MockDriftDetector()
        logger.info("Drift detector loaded successfully")
    
    def get_model(self):
        return self.model
    
    def get_drift_detector(self):
        return self.drift_detector

class MockModel:
    def predict(self, data: Any) -> float:
        import random
        return random.random()

class MockDriftDetector:
    async def detect(self, data: Any) -> bool:
        await asyncio.sleep(0.01)
        import random
        return random.random() < 0.1

model_loader = ModelLoader()

def predict(data: Any) -> float:
    model = model_loader.get_model()
    prediction = model.predict(data)
    return prediction

async def detect_drift(data: Any) -> Optional[bool]:
    drift_detector = model_loader.get_drift_detector()
    if drift_detector is None:
        return None
    try:
        drift_detected = await drift_detector.detect(data)
        if drift_detected:
            logger.warning("Drift detected in input data")
            print("Drift detected")
        return drift_detected
    except Exception as e:
        logger.error(f"Error in drift detection: {e}")
        return None

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up inference service...")
    logger.info("Model and drift detector are ready")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "model_loaded": model_loader.model is not None}

@app.post("/predict", response_model=PredictResponse)
async def predict_endpoint(request: PredictRequest):
    try:
        prediction = predict(request.input)
        drift_detected = await detect_drift(request.input)
        
        return PredictResponse(
            prediction=prediction,
            drift_detected=drift_detected
        )
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "MLOps Inference Service", "docs": "/docs"}

