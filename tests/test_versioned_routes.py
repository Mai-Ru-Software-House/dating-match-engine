"""
Versioned Route Tests: validates dynamic /internal/v{version}/ routing,
ensuring support for v1 while rejecting unsupported versions like v2 with 400.
"""

from unittest.mock import AsyncMock

import httpx
import pytest

from app.models.profile import CandidateProfile, UserMatchingProfile
from tests.helpers import assert_single_candidate, build_push_payload


@pytest.mark.asyncio
async def test_get_recommendations_v1(
    async_client: httpx.AsyncClient,
    sample_user_a: UserMatchingProfile,
    mock_matching_pool: AsyncMock,
) -> None:
    """GET /internal/v1/recommendations computes mutual recommendations."""
    # Test canonical v1 route versioning
    response = await async_client.get(
        f"/internal/v1/recommendations?user_id={sample_user_a.user_id}&limit=5"
    )
    assert_single_candidate(response, "user_b")
    mock_matching_pool.assert_awaited_once()


@pytest.mark.asyncio
async def test_post_recommendations_v1(
    async_client: httpx.AsyncClient,
    sample_user_a: UserMatchingProfile,
    sample_candidate_b: CandidateProfile,
) -> None:
    """POST /internal/v1/recommendations endpoint."""
    # Test push recommendation payload over versioned endpoint
    payload = build_push_payload(sample_user_a, sample_candidate_b, limit=5)
    response = await async_client.post("/internal/v1/recommendations", json=payload)
    assert_single_candidate(response, "user_b")


@pytest.mark.asyncio
async def test_post_candidates_search_v1(
    async_client: httpx.AsyncClient, sample_candidate_c1: CandidateProfile
) -> None:
    """POST /internal/v1/candidates/search endpoint."""
    # Test candidate specification filtering under /internal/v1/
    payload = {
        "age_min": 20,
        "age_max": 25,
        "gender": ["G1"],
        "candidates": [sample_candidate_c1.model_dump(mode="json")],
    }
    response = await async_client.post("/internal/v1/candidates/search", json=payload)
    assert_single_candidate(response, "c1")


@pytest.mark.asyncio
async def test_parametric_version_v1_and_unsupported(
    async_client: httpx.AsyncClient,
    sample_user_a: UserMatchingProfile,
    mock_matching_pool: AsyncMock,
) -> None:
    """Dynamic /internal/v{version}/... checks version and rejects unsupported."""
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
    mock_matching_pool.assert_awaited_once()


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
