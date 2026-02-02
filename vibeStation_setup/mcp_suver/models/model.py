# -*- coding: utf-8 -*-
# Standard
from typing import Any

# Third-Party
from pydantic import BaseModel, Field


# Health and Status Models
class HealthResponse(BaseModel):
    status: str = Field(..., description="Health status")
    timestamp: str = Field(..., description="Timestamp of health check")
    details: dict[str, Any] | None = Field(None, description="Additional health details")


class ReadyResponse(BaseModel):
    ready: bool = Field(..., description="Readiness status")
    timestamp: str = Field(..., description="Timestamp of readiness check")
    details: dict[str, Any] | None = Field(None, description="Additional readiness details")

# Error Models
class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    code: str | None = Field(None, description="Error code")
    details: dict[str, Any] | None = Field(None, description="Additional error details")
