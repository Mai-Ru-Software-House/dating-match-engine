"""
Backend Client Tests: tests HTTP communication with Elysia Backend Prisma DAL.
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.models.profile import CandidateProfile, UserMatchingProfile
from app.services.backend_client import BackendClient


@pytest.mark.asyncio
async def test_get_matching_pool_success(
    sample_user_a: UserMatchingProfile, sample_candidate_b: CandidateProfile
) -> None:
    """Test successful retrieval of user profile and candidates from matching-pool."""
    client = BackendClient(base_url="http://testserver")

    # Wire format from Elysia Prisma DAL uses camelCase keys
    mock_payload = {
        "user": sample_user_a.model_dump(mode="json", by_alias=True),
        "candidates": [sample_candidate_b.model_dump(mode="json", by_alias=True)],
    }

    mock_resp = httpx.Response(
        status_code=200,
        json=mock_payload,
        request=httpx.Request("GET", "http://testserver/internal/v1/matching-pool"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        user, candidates = await client.get_matching_pool("user_a")
        # Assert model hydration properly deserialized both user and candidate objects
        assert user.user_id == sample_user_a.user_id
        assert len(candidates) == 1
        assert candidates[0].user_id == sample_candidate_b.user_id
        mock_get.assert_awaited_once_with(
            "/internal/v1/matching-pool", params={"userId": "user_a"}
        )


@pytest.mark.asyncio
async def test_get_matching_pool_http_error() -> None:
    """Test that 404/500 responses raise HTTPStatusError."""
    client = BackendClient(base_url="http://testserver")

    # Backend responds with uniform error envelope on resource failure
    mock_resp = httpx.Response(
        status_code=404,
        json={"error": {"code": "NOT_FOUND", "message": "User not found"}},
        request=httpx.Request("GET", "http://testserver/internal/v1/matching-pool"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        with pytest.raises(httpx.HTTPStatusError):
            await client.get_matching_pool("missing_user")


@pytest.mark.asyncio
async def test_get_candidates_success(sample_candidate_b: CandidateProfile) -> None:
    """Test successful retrieval of candidates pool for search."""
    client = BackendClient(base_url="http://testserver")

    mock_payload = {
        "candidates": [sample_candidate_b.model_dump(mode="json", by_alias=True)],
    }

    mock_resp = httpx.Response(
        status_code=200,
        json=mock_payload,
        request=httpx.Request("GET", "http://testserver/internal/v1/candidates"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        candidates = await client.get_candidates()
        assert len(candidates) == 1
        assert candidates[0].user_id == sample_candidate_b.user_id
        mock_get.assert_awaited_once_with("/internal/v1/candidates")


@pytest.mark.asyncio
async def test_get_candidates_http_error() -> None:
    """Test that failure in get_candidates raises HTTPStatusError."""
    client = BackendClient(base_url="http://testserver")

    mock_resp = httpx.Response(
        status_code=500,
        json={"error": {"code": "INTERNAL", "message": "Server error"}},
        request=httpx.Request("GET", "http://testserver/internal/v1/candidates"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        with pytest.raises(httpx.HTTPStatusError):
            await client.get_candidates()
