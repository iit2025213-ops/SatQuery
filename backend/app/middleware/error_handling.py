# app/middleware/error_handling.py

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException
import logging

logger = logging.getLogger("satquery")

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware"""
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        
        except HTTPException as exc:
            # FastAPI HTTPExceptions
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": exc.detail,
                    "status_code": exc.status_code,
                    "path": request.url.path
                }
            )
        
        except ValueError as exc:
            # Validation errors
            logger.error(f"Validation error: {str(exc)}")
            return JSONResponse(
                status_code=422,
                content={
                    "error": "Validation error",
                    "detail": str(exc),
                    "path": request.url.path
                }
            )
        
        except Exception as exc:
            # Unexpected errors
            logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "detail": str(exc) if logger.level == logging.DEBUG else "An error occurred",
                    "path": request.url.path
                }
            )
