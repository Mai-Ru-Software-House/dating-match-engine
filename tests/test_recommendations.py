"""
Recommendation Endpoints & Service Tests: validates ranking, limits,
error handling, and direct payload processing on /internal/v1/recommendations.
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.models.profile import CandidateProfile, UserMatchingProfile
from app.services.matching import MatchingService


def test_ranking_descending_and_limit(
    sample_user_a: UserMatchingProfile,
    sample_candidate_b: CandidateProfile,
    sample_candidate_c: CandidateProfile,
    sample_candidate_ineligible_age: CandidateProfile,
) -> None:
    """Candidate B is closer (5km) than C (12km) and closer to midpoint age.

    B must rank higher than C. Ineligible candidates must be excluded.
    """
    service = MatchingService()
    candidates = [
        sample_candidate_c,
        sample_candidate_ineligible_age,
        sample_candidate_b,
    ]

    response = service.rank_candidates(
        user=sample_user_a, candidates=candidates, limit=10
    )

    # Ineligible candidate should be excluded from final recommendation results
    assert len(response.candidates) == 2
    # B should score higher than C due to closer distance and optimal age midpoint
    assert response.candidates[0].user_id == "user_b"
    assert response.candidates[1].user_id == "user_c"
    assert response.candidates[0].match_score > response.candidates[1].match_score

    # Check that batch limit parameter truncates candidate output correctly
    limited_resp = service.rank_candidates(
        user=sample_user_a, candidates=candidates, limit=1
    )
    assert len(limited_resp.candidates) == 1
    assert limited_resp.candidates[0].user_id == "user_b"


@pytest.mark.asyncio
async def test_post_recommendations_direct_payload(
    async_client: httpx.AsyncClient,
    sample_user_a: UserMatchingProfile,
    sample_candidate_b: CandidateProfile,
) -> None:
    """POST /internal/v1/recommendations with direct user and candidates payload."""
    # Push mode: Elysia backend provides profiles directly, avoiding extra query
    payload = {
        "user_id": sample_user_a.user_id,
        "limit": 10,
        "user": sample_user_a.model_dump(mode="json"),
        "candidates": [sample_candidate_b.model_dump(mode="json")],
    }
    response = await async_client.post("/internal/v1/recommendations", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "candidates" in data
    assert len(data["candidates"]) == 1
    assert data["candidates"][0]["user_id"] == "user_b"
    assert 0.0 <= data["candidates"][0]["match_score"] <= 100.0
    # Feature 1 response must also include geographic distance in kilometers
    assert "distance_km" in data["candidates"][0]
    assert data["candidates"][0]["distance_km"] > 0.0


@pytest.mark.asyncio
async def test_get_recommendations_endpoint_success(
    async_client: httpx.AsyncClient,
    sample_user_a: UserMatchingProfile,
    sample_candidate_b: CandidateProfile,
) -> None:
    """GET /internal/v1/recommendations computes candidate recommendation scores."""
    # Pull mode: engine queries backend DAL at /internal/v1/matching-pool
    with patch(
        "app.services.backend_client.BackendClient.get_matching_pool",
        new_callable=AsyncMock,
    ) as mock_get_pool:
        mock_get_pool.return_value = (sample_user_a, [sample_candidate_b])

        response = await async_client.get(
            f"/internal/v1/recommendations?user_id={sample_user_a.user_id}&limit=5"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["candidates"]) == 1
        assert data["candidates"][0]["user_id"] == "user_b"
        assert isinstance(data["candidates"][0]["match_score"], float)
        assert "distance_km" in data["candidates"][0]
        assert data["candidates"][0]["distance_km"] > 0.0


@pytest.mark.asyncio
async def test_get_recommendations_backend_404(
    async_client: httpx.AsyncClient,
) -> None:
    """When backend returns 404 for unknown user, endpoint returns 404."""
    with patch(
        "app.services.backend_client.BackendClient.get_matching_pool",
        new_callable=AsyncMock,
    ) as mock_get_pool:
        mock_response = httpx.Response(
            status_code=404, request=httpx.Request("GET", "http://backend")
        )
        mock_get_pool.side_effect = httpx.HTTPStatusError(
            message="Not found",
            request=mock_response.request,
            response=mock_response,
        )

        response = await async_client.get(
            "/internal/v1/recommendations?user_id=unknown_user"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_get_recommendations_backend_unreachable(
    async_client: httpx.AsyncClient,
) -> None:
    """When backend connection fails, endpoint returns 502 Bad Gateway."""
    with patch(
        "app.services.backend_client.BackendClient.get_matching_pool",
        new_callable=AsyncMock,
    ) as mock_get_pool:
        mock_get_pool.side_effect = httpx.ConnectError("Connection refused")

        response = await async_client.get("/internal/v1/recommendations?user_id=user_a")
        assert response.status_code == 502
        assert "failed to connect" in response.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_unversioned_endpoint_returns_404(
    async_client: httpx.AsyncClient,
) -> None:
    """Unversioned /internal/recommendations should return 404 Not Found."""
    # Ensure all matching routes require explicit versioning per API conventions
    response = await async_client.get("/internal/recommendations?user_id=user_a")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_recommendations_with_large_limit(
    async_client: httpx.AsyncClient,
    sample_user_a: UserMatchingProfile,
    sample_candidate_b: CandidateProfile,
) -> None:
    """Limits above the former 100 ceiling are supported without validation errors."""
    # Backend Prisma DAL controls batch sizing, Match Engine does not artificially cap
    payload = {
        "user_id": sample_user_a.user_id,
        "limit": 250,
        "user": sample_user_a.model_dump(mode="json"),
        "candidates": [sample_candidate_b.model_dump(mode="json")],
    }
    response = await async_client.post("/internal/v1/recommendations", json=payload)
    assert response.status_code == 200
    assert len(response.json()["candidates"]) == 1
