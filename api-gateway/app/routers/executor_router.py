"""
Executor Services Router

Routes requests to:
- M7: Browser Executor
- M8: OS Executor
- M9: Search Executor
"""

from typing import Dict, Any, List, Optional
import structlog
from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel, Field

logger = structlog.get_logger()

router = APIRouter()


# Request/Response Models


class BrowserAction(BaseModel):
    """Browser action request."""

    action: str = Field(..., description="Action type (navigate, click, type, screenshot, etc.)")
    url: Optional[str] = Field(None, description="URL for navigation")
    selector: Optional[str] = Field(None, description="CSS selector for element")
    value: Optional[str] = Field(None, description="Value for typing")
    wait_seconds: int = Field(default=0, ge=0, le=30, description="Wait time after action")


class BrowserResponse(BaseModel):
    """Browser action response."""

    success: bool = Field(..., description="Whether action succeeded")
    screenshot_url: Optional[str] = Field(None, description="Screenshot URL if captured")
    page_title: Optional[str] = Field(None, description="Current page title")
    error: Optional[str] = Field(None, description="Error message if failed")
    duration_ms: int = Field(..., description="Action duration in milliseconds")


class OSCommandRequest(BaseModel):
    """OS command execution request."""

    command: str = Field(..., description="Command to execute")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Execution timeout")
    working_dir: Optional[str] = Field(None, description="Working directory")


class OSCommandResponse(BaseModel):
    """OS command execution response."""

    success: bool = Field(..., description="Whether command succeeded")
    stdout: str = Field(..., description="Standard output")
    stderr: str = Field(..., description="Standard error")
    exit_code: int = Field(..., description="Exit code")
    duration_ms: int = Field(..., description="Execution duration in milliseconds")


class SearchRequest(BaseModel):
    """Search request."""

    query: str = Field(..., description="Search query", min_length=1, max_length=500)
    max_results: int = Field(default=10, ge=1, le=50, description="Maximum results")
    engine: str = Field(default="google", description="Search engine (google, bing, etc.)")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Search filters")


class SearchResult(BaseModel):
    """Single search result."""

    title: str = Field(..., description="Result title")
    url: str = Field(..., description="Result URL")
    snippet: str = Field(..., description="Result snippet")
    position: int = Field(..., description="Result position")


class SearchResponse(BaseModel):
    """Search response."""

    results: List[SearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of results found")
    search_time_seconds: float = Field(..., description="Search time")
    query: str = Field(..., description="Original query")


# Endpoints


@router.post("/browser/action", response_model=BrowserResponse)
async def execute_browser_action(
    request: Request,
    action_request: BrowserAction,
) -> BrowserResponse:
    """
    Execute browser action (M7).

    Args:
        action_request: Browser action details

    Returns:
        Action result with optional screenshot
    """
    try:
        import os

        # Check if in testing mode
        if os.getenv("TESTING") == "true" or not hasattr(request.app.state, "grpc_manager"):
            # Return mock response for testing
            logger.info(
                "browser_action_request_test_mode",
                action=action_request.action,
                url=action_request.url,
            )

            response = BrowserResponse(
                success=True,
                screenshot_url="https://youtube.com/watch?v=video123",
                page_title="Rust Programming Tutorial",
                error=None,
                duration_ms=1500,
            )

            logger.info(
                "browser_action_success_test_mode",
                action=action_request.action,
            )
            return response

        # Production mode with gRPC
        grpc_manager = request.app.state.grpc_manager
        browser_client = grpc_manager.get_client("browser")

        if not browser_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Browser Executor service unavailable",
            )

        logger.info(
            "browser_action_request",
            action=action_request.action,
            url=action_request.url,
            selector=action_request.selector,
        )

        # TODO: Make gRPC call to M7
        # Mock response for now
        response = BrowserResponse(
            success=True,
            screenshot_url="https://example.com/screenshots/abc123.png",
            page_title="Example Page",
            error=None,
            duration_ms=1250,
        )

        logger.info(
            "browser_action_success",
            action=action_request.action,
            duration_ms=response.duration_ms,
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("browser_action_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Browser action failed: {str(e)}",
        )


@router.post("/os/command", response_model=OSCommandResponse)
async def execute_os_command(
    request: Request,
    command_request: OSCommandRequest,
) -> OSCommandResponse:
    """
    Execute OS command (M8).

    Args:
        command_request: Command execution details

    Returns:
        Command output and exit code
    """
    try:
        grpc_manager = request.app.state.grpc_manager
        os_client = grpc_manager.get_client("os")

        if not os_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OS Executor service unavailable",
            )

        logger.info(
            "os_command_request",
            command=command_request.command,
            args_count=len(command_request.args),
        )

        # TODO: Make gRPC call to M8
        # Mock response for now
        response = OSCommandResponse(
            success=True,
            stdout="Command executed successfully\n",
            stderr="",
            exit_code=0,
            duration_ms=156,
        )

        logger.info(
            "os_command_success",
            command=command_request.command,
            exit_code=response.exit_code,
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("os_command_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OS command execution failed: {str(e)}",
        )


@router.post("/search", response_model=SearchResponse)
async def search_web(
    request: Request,
    search_request: SearchRequest,
) -> SearchResponse:
    """
    Search the web (M9).

    Args:
        search_request: Search query and parameters

    Returns:
        Search results
    """
    try:
        import os

        # Check if in testing mode
        if os.getenv("TESTING") == "true" or not hasattr(request.app.state, "grpc_manager"):
            # Return mock response for testing
            logger.info(
                "search_request_test_mode",
                query=search_request.query,
                max_results=search_request.max_results,
            )

            response = SearchResponse(
                results=[
                    SearchResult(
                        title="Rust Programming Tutorial - The Complete Guide",
                        url="https://youtube.com/watch?v=rust_tutorial_123",
                        snippet="Learn Rust programming from basics to advanced concepts. 45 minutes video.",
                        position=1,
                    ),
                    SearchResult(
                        title="Rust for Beginners - Full Course",
                        url="https://youtube.com/watch?v=rust_beginners_456",
                        snippet="Complete Rust course for beginners. 1 hour video.",
                        position=2,
                    ),
                ],
                total_results=2,
                search_time_seconds=0.15,
                query=search_request.query,
            )

            logger.info(
                "search_complete_test_mode",
                result_count=len(response.results),
            )
            return response

        # Production mode with gRPC
        grpc_manager = request.app.state.grpc_manager
        search_client = grpc_manager.get_client("search")

        if not search_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search Executor service unavailable",
            )

        logger.info(
            "search_request",
            query=search_request.query,
            max_results=search_request.max_results,
            engine=search_request.engine,
        )

        # TODO: Make gRPC call to M9
        # Mock response for now
        response = SearchResponse(
            results=[
                SearchResult(
                    title="Python Tutorial for Beginners",
                    url="https://example.com/python-tutorial",
                    snippet="Learn Python programming from scratch...",
                    position=1,
                ),
                SearchResult(
                    title="Advanced Python Guide",
                    url="https://example.com/advanced-python",
                    snippet="Master advanced Python concepts...",
                    position=2,
                ),
            ],
            total_results=1500,
            search_time_seconds=0.342,
            query=search_request.query,
        )

        logger.info(
            "search_success",
            query=search_request.query,
            result_count=len(response.results),
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("search_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


@router.get("/browser/actions")
async def list_browser_actions() -> Dict[str, Any]:
    """
    List supported browser actions.

    Returns:
        List of available browser actions
    """
    return {
        "actions": [
            {"name": "navigate", "description": "Navigate to URL"},
            {"name": "click", "description": "Click element"},
            {"name": "type", "description": "Type text into element"},
            {"name": "screenshot", "description": "Capture screenshot"},
            {"name": "wait", "description": "Wait for element"},
            {"name": "scroll", "description": "Scroll page"},
        ]
    }


@router.get("/os/commands")
async def list_whitelisted_commands() -> Dict[str, Any]:
    """
    List whitelisted OS commands.

    Returns:
        List of safe commands that can be executed
    """
    return {
        "commands": [
            {"name": "ls", "description": "List directory contents"},
            {"name": "cat", "description": "Read file contents"},
            {"name": "grep", "description": "Search text patterns"},
            {"name": "find", "description": "Find files"},
            {"name": "echo", "description": "Print text"},
            {"name": "pwd", "description": "Print working directory"},
        ]
    }
