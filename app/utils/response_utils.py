"""
Response utility functions for standardized API responses.
"""
from typing import Any, Optional

from fastapi.responses import JSONResponse


def success_response(
    message: str = "Response was successful",
    data: Optional[Any] = None,
    status_code: int = 200,
    **kwargs
) -> JSONResponse:
    """
    Create a standardized success response using FastAPI JSONResponse.

    Args:
        message: Success message
        data: Response data (optional)
        status_code: HTTP status code (default: 200)
        **kwargs: Additional fields to include

    Returns:
        JSONResponse with standardized success response structure
    """
    response = {
        "status": "success",
        "message": message,
        "data": data if data is not None else {}
    }

    # Add any additional fields
    response.update(kwargs)

    return JSONResponse(content=response, status_code=status_code)


def error_response(
    message: str = "An error occurred",
    data: Optional[Any] = None,
    status_code: int = 400,
    **kwargs
) -> JSONResponse:
    """
    Create a standardized error response using FastAPI JSONResponse.

    Args:
        message: Error message
        data: Additional error data (optional)
        status_code: HTTP status code (default: 400)
        **kwargs: Additional fields to include

    Returns:
        JSONResponse with standardized error response structure
    """
    response = {
        "status": "error",
        "message": message,
        "data": data if data is not None else {}
    }

    # Add any additional fields
    response.update(kwargs)

    return JSONResponse(content=response, status_code=status_code)
