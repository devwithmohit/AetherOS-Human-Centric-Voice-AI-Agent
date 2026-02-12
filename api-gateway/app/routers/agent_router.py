"""
Agent Core Router

Routes requests to:
- M4: Intent Recognition
- M5: Action Planner
- M6: Safety Validator
"""

from typing import Dict, Any, List, Optional
import structlog
from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel, Field

logger = structlog.get_logger()

router = APIRouter()


# Request/Response Models


class IntentRequest(BaseModel):
    """Intent recognition request."""

    text: str = Field(..., description="User input text", min_length=1)
    context: Optional[Dict[str, Any]] = Field(default=None, description="Conversation context")


class Intent(BaseModel):
    """Recognized intent."""

    name: str = Field(..., description="Intent name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities")


class IntentResponse(BaseModel):
    """Intent recognition response."""

    primary_intent: Intent = Field(..., description="Primary detected intent")
    alternative_intents: List[Intent] = Field(
        default_factory=list, description="Alternative intents"
    )
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")


class PlanRequest(BaseModel):
    """Action plan request."""

    intent: str = Field(..., description="Detected intent name")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Intent entities")
    user_context: Optional[Dict[str, Any]] = Field(default=None, description="User context")


class ActionStep(BaseModel):
    """Single action step in a plan."""

    step_id: int = Field(..., description="Step number")
    action_type: str = Field(..., description="Action type (search, browse, execute)")
    executor: str = Field(..., description="Executor module (M7, M8, M9)")
    parameters: Dict[str, Any] = Field(..., description="Action parameters")
    depends_on: List[int] = Field(default_factory=list, description="Dependency step IDs")


class PlanResponse(BaseModel):
    """Action plan response."""

    plan_id: str = Field(..., description="Unique plan ID")
    steps: List[ActionStep] = Field(..., description="Ordered action steps")
    estimated_duration_seconds: int = Field(..., description="Estimated execution time")
    requires_approval: bool = Field(..., description="Whether plan needs user approval")


class SafetyCheckRequest(BaseModel):
    """Safety validation request."""

    action_type: str = Field(..., description="Type of action to validate")
    parameters: Dict[str, Any] = Field(..., description="Action parameters")
    user_id: str = Field(..., description="User ID")


class SafetyCheckResponse(BaseModel):
    """Safety validation response."""

    is_safe: bool = Field(..., description="Whether action is safe")
    risk_level: str = Field(..., description="Risk level (none, low, medium, high)")
    warnings: List[str] = Field(default_factory=list, description="Safety warnings")
    blocked_reason: Optional[str] = Field(None, description="Reason if blocked")


# Endpoints


@router.post("/intent", response_model=IntentResponse)
async def recognize_intent(
    request: Request,
    intent_request: IntentRequest,
) -> IntentResponse:
    """
    Recognize user intent from text (M4).

    Args:
        intent_request: User input and context

    Returns:
        Detected intents with confidence scores
    """
    try:
        grpc_manager = request.app.state.grpc_manager
        intent_client = grpc_manager.get_client("intent")

        if not intent_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Intent Recognition service unavailable",
            )

        logger.info(
            "intent_request",
            text_length=len(intent_request.text),
            has_context=intent_request.context is not None,
        )

        # TODO: Make gRPC call to M4
        # Mock response for now
        response = IntentResponse(
            primary_intent=Intent(
                name="search_web",
                confidence=0.92,
                entities={"query": "Python tutorials", "source": "web"},
            ),
            alternative_intents=[
                Intent(name="open_browser", confidence=0.65, entities={}),
            ],
            processing_time_ms=85,
        )

        logger.info(
            "intent_recognized",
            intent=response.primary_intent.name,
            confidence=response.primary_intent.confidence,
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("intent_recognition_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Intent recognition failed: {str(e)}",
        )


@router.post("/plan", response_model=PlanResponse)
async def create_plan(
    request: Request,
    plan_request: PlanRequest,
) -> PlanResponse:
    """
    Create action plan from intent (M5).

    Args:
        plan_request: Intent and context

    Returns:
        Execution plan with ordered steps
    """
    try:
        grpc_manager = request.app.state.grpc_manager
        planner_client = grpc_manager.get_client("planner")

        if not planner_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Action Planner service unavailable",
            )

        logger.info(
            "plan_request",
            intent=plan_request.intent,
            entity_count=len(plan_request.entities),
        )

        # TODO: Make gRPC call to M5
        # Mock response for now
        response = PlanResponse(
            plan_id="plan_abc123",
            steps=[
                ActionStep(
                    step_id=1,
                    action_type="search",
                    executor="M9",
                    parameters={"query": "Python tutorials", "max_results": 10},
                    depends_on=[],
                ),
                ActionStep(
                    step_id=2,
                    action_type="browse",
                    executor="M7",
                    parameters={"url": "{step_1_results[0].url}"},
                    depends_on=[1],
                ),
            ],
            estimated_duration_seconds=15,
            requires_approval=False,
        )

        logger.info(
            "plan_created",
            plan_id=response.plan_id,
            step_count=len(response.steps),
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("plan_creation_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Plan creation failed: {str(e)}",
        )


@router.post("/safety/check", response_model=SafetyCheckResponse)
async def check_safety(
    request: Request,
    safety_request: SafetyCheckRequest,
) -> SafetyCheckResponse:
    """
    Validate action safety (M6).

    Args:
        safety_request: Action to validate

    Returns:
        Safety validation result
    """
    try:
        grpc_manager = request.app.state.grpc_manager
        safety_client = grpc_manager.get_client("safety")

        if not safety_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Safety Validator service unavailable",
            )

        logger.info(
            "safety_check_request",
            action_type=safety_request.action_type,
            user_id=safety_request.user_id,
        )

        # TODO: Make gRPC call to M6
        # Mock response for now
        response = SafetyCheckResponse(
            is_safe=True,
            risk_level="low",
            warnings=["Action involves internet search"],
            blocked_reason=None,
        )

        logger.info(
            "safety_check_complete",
            is_safe=response.is_safe,
            risk_level=response.risk_level,
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("safety_check_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Safety check failed: {str(e)}",
        )


@router.get("/intents")
async def list_intents() -> Dict[str, Any]:
    """
    List supported intents.

    Returns:
        List of available intents
    """
    return {
        "intents": [
            {"name": "search_web", "description": "Search the web"},
            {"name": "open_browser", "description": "Open web browser"},
            {"name": "execute_command", "description": "Execute OS command"},
            {"name": "remember", "description": "Store information in memory"},
            {"name": "recall", "description": "Retrieve information from memory"},
        ]
    }
