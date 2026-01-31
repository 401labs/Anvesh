"""
Standardized API Response Models and Helpers.

Provides uniform response structure across all API endpoints.
"""
from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Any, Optional, Generic, TypeVar
from datetime import datetime, date

# Generic type for response data
T = TypeVar('T')


class APIResponse(BaseModel):
    """
    Standard API response model for OpenAPI documentation.
    
    All endpoints return this structure.
    """
    success: bool = Field(description="Whether the request was successful")
    message: str = Field(description="Human-readable message")
    data: Optional[Any] = Field(default=None, description="Response data")
    error: bool = Field(description="Whether an error occurred")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "message": "Operation completed successfully",
                    "data": {"id": 1, "name": "Example"},
                    "error": False
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """
    Standard error response model for OpenAPI documentation.
    """
    success: bool = Field(default=False, description="Always false for errors")
    message: str = Field(description="Error message")
    data: Optional[Any] = Field(default=None, description="Additional error details")
    error: bool = Field(default=True, description="Always true for errors")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": False,
                    "message": "Validation error",
                    "data": {"errors": ["field -> error message"]},
                    "error": True
                }
            ]
        }
    }


# Standard response definitions for OpenAPI
STANDARD_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Bad Request"},
    401: {"model": ErrorResponse, "description": "Unauthorized - Invalid API key"},
    403: {"model": ErrorResponse, "description": "Forbidden - Admin access required"},
    404: {"model": ErrorResponse, "description": "Not Found"},
    422: {"model": ErrorResponse, "description": "Validation Error"},
    500: {"model": ErrorResponse, "description": "Internal Server Error"},
}


def _serialize_value(val: Any) -> Any:
    """Convert non-JSON-serializable values."""
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    return val


def _serialize_data(data: Any) -> Any:
    """Recursively serialize data for JSON compatibility."""
    if data is None:
        return None
    if isinstance(data, dict):
        return {k: _serialize_data(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_serialize_data(item) for item in data]
    return _serialize_value(data)


def api_success(
    message: str = "Success",
    data: Any = None,
    status_code: int = status.HTTP_200_OK
) -> JSONResponse:
    """
    Return a successful API response.
    
    Args:
        message: Human-readable success message
        data: Response data (dict, list, or any serializable object)
        status_code: HTTP status code (default: 200)
    
    Returns:
        JSONResponse with standard structure
    
    Example:
        return api_success("User created", {"id": 1}, status_code=201)
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "message": message,
            "data": _serialize_data(data),
            "error": False
        }
    )


def api_error(
    message: str = "An error occurred",
    data: Any = None,
    status_code: int = status.HTTP_400_BAD_REQUEST
) -> JSONResponse:
    """
    Return an error API response.
    
    Args:
        message: Human-readable error message
        data: Additional error details (optional)
        status_code: HTTP status code (default: 400)
    
    Returns:
        JSONResponse with standard structure
    
    Example:
        return api_error("Invalid input", status_code=422)
        return api_error("Not found", status_code=404)
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": message,
            "data": _serialize_data(data),
            "error": True
        }
    )
