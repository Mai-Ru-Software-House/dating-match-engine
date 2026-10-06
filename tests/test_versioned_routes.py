"""
Versioned Route Tests: validates dynamic /internal/v{version}/ routing,
ensuring support for v1 while rejecting unsupported versions like v2 with 400.
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.models.profile import CandidateProfile, UserMatchingProfile


@pytest.mark.asyncio
async def test_get_recommendations_v1(
    async_client: httpx.AsyncClient,
    sample_user_a: UserMatchingProfile,
    sample_candidate_b: CandidateProfile,
) -> None:
    """GET /internal/v1/recommendations computes mutual recommendations."""
    # Test canonical v1 route versioning
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


@pytest.mark.asyncio
async def test_post_recommendations_v1(
    async_client: httpx.AsyncClient,
    sample_user_a: UserMatchingProfile,
    sample_candidate_b: CandidateProfile,
) -> None:
    """POST /internal/v1/recommendations endpoint."""
    # Test push recommendation payload over versioned endpoint
    payload = {
        "user_id": sample_user_a.user_id,
        "limit": 5,
        "user": sample_user_a.model_dump(mode="json"),
        "candidates": [sample_candidate_b.model_dump(mode="json")],
    }
    response = await async_client.post("/internal/v1/recommendations", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["candidates"]) == 1
    assert data["candidates"][0]["user_id"] == "user_b"


@pytest.mark.asyncio
async def test_post_candidates_search_v1(async_client: httpx.AsyncClient) -> None:
    """POST /internal/v1/candidates/search endpoint."""
    # Test candidate specification filtering under /internal/v1/
    c1 = CandidateProfile(
        user_id="c1",
        age=22,
        gender="G1",
        latitude=13.7600,
        longitude=100.5100,
    )
    payload = {
        "age_min": 20,
        "age_max": 25,
        "gender": ["G1"],
        "candidates": [c1.model_dump(mode="json")],
    }
    response = await async_client.post("/internal/v1/candidates/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["candidates"]) == 1
    assert data["candidates"][0]["user_id"] == "c1"


@pytest.mark.asyncio
async def test_parametric_version_v1_and_unsupported(
    async_client: httpx.AsyncClient,
    sample_user_a: UserMatchingProfile,
    sample_candidate_b: CandidateProfile,
) -> None:
    """Dynamic /internal/v{version}/... checks version and rejects unsupported."""
    with patch(
        "app.services.backend_client.BackendClient.get_matching_pool",
        new_callable=AsyncMock,
    ) as mock_get_pool:
        mock_get_pool.return_value = (sample_user_a, [sample_candidate_b])

        # Valid version v1 succeeds
        res_v1_num = await async_client.get(
            f"/internal/v1/recommendations?user_id={sample_user_a.user_id}"
        )
        assert res_v1_num.status_code == 200

        # Unsupported version 'v2' must return 400 Bad Request
        res_v2 = await async_client.get(
            f"/internal/v2/recommendations?user_id={sample_user_a.user_id}"
        )
        assert res_v2.status_code == 400
        assert "not supported" in res_v2.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_search_parametric_version_unsupported(
    async_client: httpx.AsyncClient,
) -> None:
    """POST /internal/v2/candidates/search returns 400 for unsupported version."""
    payload = {
        "age_min": 20,
        "age_max": 25,
    }
    response = await async_client.post("/internal/v2/candidates/search", json=payload)
    assert response.status_code == 400
    assert "not supported" in response.json()["error"]["message"].lower()
