"""
Intent Classifier FastAPI Server
Provides HTTP endpoints for intent classification and entity extraction.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Intent Classifier Service",
    description="NLP-based intent classification and entity extraction",
    version="1.0.0",
)


class ClassificationRequest(BaseModel):
    text: str
    context: Optional[Dict[str, Any]] = None


class ClassificationResponse(BaseModel):
    intent: str
    confidence: float
    entities: Dict[str, Any]


@app.on_event("startup")
async def startup_event():
    """Initialize classifier on startup."""
    logger.info("Intent Classifier service starting...")
    try:
        # Import classifier here to avoid import errors if models aren't ready
        from app import classifier

        logger.info("Classifier initialized successfully")
    except Exception as e:
        logger.warning(f"Classifier initialization delayed: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "intent-classifier", "version": "1.0.0"}


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "Intent Classifier",
        "version": "1.0.0",
        "endpoints": {
            "/health": "Health check",
            "/classify": "POST - Classify intent from text",
            "/intents": "GET - List available intents",
        },
    }


@app.post("/classify", response_model=ClassificationResponse)
async def classify_intent(request: ClassificationRequest):
    """
    Classify user intent from text input.

    Args:
        request: Classification request with text and optional context

    Returns:
        Intent classification results with confidence and entities
    """
    try:
        from app.classifier import IntentClassifier

        classifier = IntentClassifier()
        result = classifier.classify(request.text, context=request.context)

        return ClassificationResponse(
            intent=result.get("intent", "unknown"),
            confidence=result.get("confidence", 0.0),
            entities=result.get("entities", {}),
        )
    except Exception as e:
        logger.error(f"Classification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/intents")
async def list_intents():
    """Get list of available intents."""
    try:
        from app.intents import INTENT_PATTERNS

        return {"intents": list(INTENT_PATTERNS.keys()), "count": len(INTENT_PATTERNS)}
    except Exception as e:
        return {"intents": [], "count": 0, "error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8006)
