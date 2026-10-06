"""
Match Engine Application: entry point for the FastAPI standalone service,
configuring versioned routers and structured error responses.
"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.internal import internal_router, internal_versioned_router
from app.config import get_settings
from app.models.response import HealthResponse

settings = get_settings()

app = FastAPI(
    title="Match Engine",
    description="Standalone Match Engine microservice for candidate recommendations.",
    version="1.0.0",
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Format HTTP exceptions into standard Mai Ru error response shape.

    Args:
        request: The incoming request.
        exc: The raised HTTPException.

    Returns:
        JSONResponse with error shape { "error": { "code": "...", "message": "..." } }.
    """
    code_map = {
        status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_502_BAD_GATEWAY: "BAD_GATEWAY",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_SERVER_ERROR",
    }
    code = code_map.get(exc.status_code, "ERROR")
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": message}},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Format validation errors into standard Mai Ru error response shape.

    Args:
        request: The incoming request.
        exc: The raised RequestValidationError.

    Returns:
        JSONResponse with HTTP 400 and standard error envelope.
    """
    errors = exc.errors()
    if errors:
        first_error = errors[0]
        field_loc = " -> ".join(
            str(loc) for loc in first_error.get("loc", []) if loc != "body"
        )
        reason = first_error.get("msg", "Invalid input value")
        message = f"{field_loc}: {reason}" if field_loc else reason
    else:
        message = "Invalid input provided"

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": {"code": "INVALID_INPUT", "message": message}},
    )


# 1. Versioned routes: /internal/v1/...
app.include_router(
    internal_router,
    prefix="/internal/v1",
    tags=["Internal Match Engine (v1)"],
)

# 2. Dynamic parametric version routes: /internal/v{version}/...
app.include_router(
    internal_versioned_router,
    prefix="/internal/v{version}",
    include_in_schema=False,
)


@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["System"],
    summary="Health Check",
)
async def health_check() -> HealthResponse:
    """Service health check endpoint used by Docker/Nginx orchestration.

    Returns:
        HealthResponse indicating service status.
    """
    return HealthResponse(status="ok", service="dating-match-engine")


@app.get(
    "/",
    status_code=status.HTTP_200_OK,
    tags=["System"],
    summary="Root Info",
)
async def root() -> dict[str, str]:
    """Service root endpoint returning basic metadata.

    Returns:
        Dictionary containing service name, status, and environment.
    """
    return {
        "service": "dating-match-engine",
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "apiVersion": "v1",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=(settings.ENVIRONMENT == "development"),
    )
