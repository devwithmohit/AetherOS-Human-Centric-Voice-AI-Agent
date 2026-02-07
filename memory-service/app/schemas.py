"""Pydantic schemas for API requests and responses."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


# Short-term memory schemas
class ShortTermMemoryCreate(BaseModel):
    key: str = Field(..., description="Memory key")
    value: Any = Field(..., description="Memory value")
    ttl: Optional[int] = Field(None, description="Time-to-live in seconds")
    namespace: str = Field(default="stm", description="Key namespace")


class ShortTermMemoryResponse(BaseModel):
    key: str
    value: Any
    ttl: Optional[int]
    exists: bool


# Long-term memory schemas
class UserPreferencesCreate(BaseModel):
    user_id: str
    preferences: Dict[str, Any]
    language: Optional[str] = "en"
    timezone: Optional[str] = "UTC"
    voice_settings: Optional[Dict[str, Any]] = None


class UserPreferencesResponse(BaseModel):
    user_id: str
    preferences: Dict[str, Any]
    language: str
    timezone: str
    voice_settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConsentCreate(BaseModel):
    user_id: str
    consent_type: str = Field(..., description="Type: data_collection, personalization, analytics")
    granted: bool
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class ConsentResponse(BaseModel):
    user_id: str
    consent_type: str
    granted: bool
    granted_at: Optional[datetime]
    revoked_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ExecutionCreate(BaseModel):
    user_id: str
    session_id: str
    command: str
    tool_name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    result: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None


class ExecutionResponse(BaseModel):
    id: int
    user_id: str
    session_id: str
    command: str
    tool_name: Optional[str]
    parameters: Dict[str, Any]
    result: Optional[str]
    success: bool
    error_message: Optional[str]
    execution_time_ms: Optional[int]
    executed_at: datetime

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    user_id: str
    session_id: str
    title: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    increment_message_count: bool = False


class ConversationResponse(BaseModel):
    id: int
    user_id: str
    session_id: str
    title: Optional[str]
    context: Dict[str, Any]
    message_count: int
    started_at: datetime
    last_activity_at: datetime
    ended_at: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True


class KnowledgeCreate(BaseModel):
    user_id: str
    category: str
    key: str
    value: str
    confidence: int = Field(default=100, ge=0, le=100)
    source: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None


class KnowledgeResponse(BaseModel):
    id: int
    user_id: str
    category: str
    key: str
    value: str
    confidence: int
    source: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


# Episodic memory schemas
class EpisodeCreate(BaseModel):
    user_id: str
    session_id: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    episode_id: Optional[str] = None


class EpisodeQuery(BaseModel):
    user_id: str
    query_text: str
    n_results: int = Field(default=10, ge=1, le=100)
    session_id: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None


class EpisodeResponse(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any]
    distance: Optional[float] = None


# General responses
class StatusResponse(BaseModel):
    status: str
    message: Optional[str] = None
    data: Optional[Any] = None


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    services: Dict[str, str]
