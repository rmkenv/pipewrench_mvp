"""
Pydantic models for request/response validation.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


class SessionCreateResponse(BaseModel):
    """Response model for session creation."""
    session_id: str


class SessionStatusResponse(BaseModel):
    """Response model for session status."""
    session_id: str
    created_at: str
    last_accessed: str
    document_count: int
    question_count: int


class QueryRequest(BaseModel):
    """Request model for AI query."""
    question: str = Field(..., min_length=1, max_length=2000)
    department: str = Field(default="general_public_works")
    role: Optional[str] = None
    session_id: Optional[str] = None
    api_key: Optional[str] = None


class QueryResponse(BaseModel):
    """Response model for AI query."""
    answer: str
    department: str
    timestamp: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""
    filename: str
    analysis: str
    department: str
    file_size: Optional[str] = None


class ReportResponse(BaseModel):
    """Response model for report generation."""
    html_content: str
    session_id: str
    generated_at: str


class HealthCheckResponse(BaseModel):
    """Response model for health check."""
    status: str
    timestamp: str
    version: str
    environment: str
    api_key_configured: bool
    active_sessions: int


class DepartmentInfo(BaseModel):
    """Model for department information."""
    value: str
    name: str


class RoleInfo(BaseModel):
    """Model for role information."""
    value: str
    title: str


class SystemInfoResponse(BaseModel):
    """Response model for system information."""
    total_whitelisted_urls: int
    whitelisted_domains: List[str]
    roles: List[str]
    departments: List[str]
    config: dict


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str
    detail: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
