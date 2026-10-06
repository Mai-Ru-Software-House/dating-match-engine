"""
Internal API Endpoints: handles internal recommendation and search routes
exclusively mounted under versioned prefixes (/internal/v1/...).
"""

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.models.request import (
    DEFAULT_PAGE_LIMIT,
    CandidateSearchRequest,
    RecommendationRequest,
)
from app.models.response import CandidateSearchResponse, RecommendationResponse
from app.services.matching import MatchingService
from app.services.search import SearchService

logger = logging.getLogger(__name__)

router = APIRouter()
internal_router = router

versioned_router = APIRouter()
internal_versioned_router = versioned_router


def get_matching_service() -> MatchingService:
    """Dependency provider for MatchingService.

    Returns:
        Instance of MatchingService.
    """
    return MatchingService()


def get_search_service() -> SearchService:
    """Dependency provider for SearchService.

    Returns:
        Instance of SearchService.
    """
    return SearchService()


MatchingServiceDep = Annotated[MatchingService, Depends(get_matching_service)]
SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]


def validate_api_version(version: str) -> str:
    """Validate that requested API version is supported.

    Args:
        version: The version string from URL path (e.g. '1', 'v1').

    Returns:
        The normalized version string.

    Raises:
        HTTPException: If the version is not supported.
    """
    clean_ver = version.lstrip("v").strip()
    if clean_ver != "1":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"API version 'v{version}' is not supported. Supported versions: v1",
        )
    return clean_ver


async def handle_get_recommendations(
    user_id: str,
    limit: int,
    matching_service: MatchingService,
) -> RecommendationResponse:
    """Core handler for recommendation generation.

    Args:
        user_id: Requesting user identifier.
        limit: Maximum number of candidates to return.
        matching_service: Service instance for recommendation computation.

    Returns:
        RecommendationResponse containing ranked candidates.

    Raises:
        HTTPException: On backend errors or missing user profile.
    """
    try:
        return await matching_service.get_recommendations(user_id=user_id, limit=limit)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{user_id}' matching profile not found in backend",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Backend service responded with status {exc.response.status_code}",
        ) from exc
    except httpx.RequestError as exc:
        logger.error("Failed to connect to backend: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to connect to backend service",
        ) from exc


async def handle_post_recommendations(
    request: RecommendationRequest,
    matching_service: MatchingService,
) -> RecommendationResponse:
    """Core handler for recommendation computation with direct payload.

    Args:
        request: RecommendationRequest containing user and candidate data.
        matching_service: Service instance for recommendation computation.

    Returns:
        RecommendationResponse containing ranked candidates.

    Raises:
        HTTPException: On backend errors or missing user profile.
    """
    try:
        return await matching_service.get_recommendations(
            user_id=request.user_id,
            limit=request.limit,
            user=request.user,
            candidates=request.candidates,
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{request.user_id}' profile not found in backend",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Backend service responded with status {exc.response.status_code}",
        ) from exc
    except httpx.RequestError as exc:
        logger.error("Failed to connect to backend: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to connect to backend service",
        ) from exc


async def handle_search_candidates(
    request: CandidateSearchRequest,
    search_service: SearchService,
) -> CandidateSearchResponse:
    """Core handler for candidate specification search.

    Args:
        request: CandidateSearchRequest containing criteria.
        search_service: Service instance for candidate search filtering.

    Returns:
        CandidateSearchResponse containing matching candidates.

    Raises:
        HTTPException: On backend connection or status errors.
    """
    try:
        return await search_service.search_candidates(spec=request)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Backend service responded with status {exc.response.status_code}",
        ) from exc
    except httpx.RequestError as exc:
        logger.error("Failed to connect to backend: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to connect to backend service",
        ) from exc


@router.get(
    "/recommendations",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get mutually eligible candidate recommendations",
    description="Retrieves data from backend and computes ranked scores.",
)
async def get_recommendations(
    matching_service: MatchingServiceDep,
    user_id: Annotated[
        str | None,
        Query(
            alias="user_id",
            description="Requesting user ID",
        ),
    ] = None,
    user_id_camel: Annotated[
        str | None,
        Query(
            alias="userId",
            description="Requesting user ID (camelCase alias)",
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            description="Maximum candidates to return",
            ge=1,
        ),
    ] = DEFAULT_PAGE_LIMIT,
) -> RecommendationResponse:
    """Generate recommendations for the requesting user."""
    effective_user_id = user_id or user_id_camel
    if not effective_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter 'user_id' or 'userId' is required",
        )
    return await handle_get_recommendations(
        user_id=effective_user_id,
        limit=limit,
        matching_service=matching_service,
    )


@router.post(
    "/recommendations",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute recommendations with optional direct payload",
    description="Computes mutual recommendations directly or from backend.",
)
async def post_recommendations(
    request: RecommendationRequest,
    matching_service: MatchingServiceDep,
) -> RecommendationResponse:
    """Compute recommendations using payload or backend pool."""
    return await handle_post_recommendations(
        request=request, matching_service=matching_service
    )


@router.post(
    "/candidates/search",
    response_model=CandidateSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search candidates by explicit specification",
    description="Filters candidate pool based on age, gender, and radius.",
)
async def search_candidates(
    request: CandidateSearchRequest,
    search_service: SearchServiceDep,
) -> CandidateSearchResponse:
    """Search candidates meeting specified filter criteria."""
    return await handle_search_candidates(
        request=request, search_service=search_service
    )


@versioned_router.get(
    "/recommendations",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get recommendations (Dynamic version)",
)
async def get_recommendations_versioned(
    version: Annotated[str, Path(description="API version, e.g. 1 or v1")],
    matching_service: MatchingServiceDep,
    user_id: Annotated[
        str | None,
        Query(
            alias="user_id",
            description="Requesting user ID",
        ),
    ] = None,
    user_id_camel: Annotated[
        str | None,
        Query(
            alias="userId",
            description="Requesting user ID (camelCase alias)",
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            description="Maximum candidates to return",
            ge=1,
        ),
    ] = DEFAULT_PAGE_LIMIT,
) -> RecommendationResponse:
    """Generate recommendations with dynamic API version verification."""
    validate_api_version(version)
    effective_user_id = user_id or user_id_camel
    if not effective_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter 'user_id' or 'userId' is required",
        )
    return await handle_get_recommendations(
        user_id=effective_user_id,
        limit=limit,
        matching_service=matching_service,
    )


@versioned_router.post(
    "/recommendations",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute recommendations (Dynamic version)",
)
async def post_recommendations_versioned(
    version: Annotated[str, Path(description="API version, e.g. 1 or v1")],
    request: RecommendationRequest,
    matching_service: MatchingServiceDep,
) -> RecommendationResponse:
    """Compute recommendations with dynamic API version verification."""
    validate_api_version(version)
    return await handle_post_recommendations(
        request=request, matching_service=matching_service
    )


@versioned_router.post(
    "/candidates/search",
    response_model=CandidateSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search candidates by specification (Dynamic version)",
)
async def search_candidates_versioned(
    version: Annotated[str, Path(description="API version, e.g. 1 or v1")],
    request: CandidateSearchRequest,
    search_service: SearchServiceDep,
) -> CandidateSearchResponse:
    """Search candidates with dynamic API version verification."""
    validate_api_version(version)
    return await handle_search_candidates(
        request=request, search_service=search_service
    )
