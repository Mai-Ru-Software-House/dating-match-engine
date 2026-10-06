"""
Candidate Search Endpoints & Service Tests: validates explicit specification
filtering (age, gender, radius), sorting by distance, and input validation.
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.models.profile import CandidateProfile


@pytest.mark.asyncio
async def test_search_candidates_direct_payload(
    async_client: httpx.AsyncClient,
) -> None:
    """POST /internal/v1/candidates/search with specification and direct pool."""
    # Candidates set up with distinct distances and matching characteristics
    c1 = CandidateProfile(
        user_id="c1",
        age=22,
        gender="G1",
        latitude=13.7600,
        longitude=100.5100,
    )
    c2 = CandidateProfile(
        user_id="c2",
        age=24,
        gender="G3",
        latitude=13.7700,
        longitude=100.5200,
    )
    c_out_of_age = CandidateProfile(
        user_id="c_old",
        age=32,
        gender="G1",
        latitude=13.7600,
        longitude=100.5100,
    )
    c_out_of_range = CandidateProfile(
        user_id="c_far",
        age=23,
        gender="G1",
        latitude=18.7883,
        longitude=98.9853,
    )

    payload = {
        "age_min": 20,
        "age_max": 25,
        "gender": ["G1", "G3"],
        "radius_km": 10.0,
        "location": {
            "lat": 13.7563,
            "lng": 100.5018,
        },
        "limit": 20,
        "candidates": [
            c1.model_dump(mode="json"),
            c2.model_dump(mode="json"),
            c_out_of_age.model_dump(mode="json"),
            c_out_of_range.model_dump(mode="json"),
        ],
    }

    response = await async_client.post("/internal/v1/candidates/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["candidates"]) == 2

    # c1 (~0.98 km) is closer than c2 (~2.5 km), so c1 ranks first
    assert data["candidates"][0]["user_id"] == "c1"
    assert data["candidates"][1]["user_id"] == "c2"
    assert data["candidates"][0]["distance_km"] <= data["candidates"][1]["distance_km"]
    # Feature 2 response must not return age and gender (decorating is backend's role)
    assert "age" not in data["candidates"][0]
    assert "gender" not in data["candidates"][0]


@pytest.mark.asyncio
async def test_search_candidates_backend_fallback(
    async_client: httpx.AsyncClient,
) -> None:
    """When candidates are omitted in body, fetch from backend via /internal/v1."""
    c1 = CandidateProfile(
        user_id="c1",
        age=22,
        gender="G1",
        latitude=13.7600,
        longitude=100.5100,
    )
    with patch(
        "app.services.backend_client.BackendClient.get_candidates",
        new_callable=AsyncMock,
    ) as mock_get_cands:
        mock_get_cands.return_value = [c1]

        payload = {
            "age_min": 20,
            "age_max": 25,
            "gender": ["G1"],
            "limit": 10,
        }
        response = await async_client.post(
            "/internal/v1/candidates/search", json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["candidates"]) == 1
        assert data["candidates"][0]["user_id"] == "c1"


@pytest.mark.asyncio
async def test_search_validation_errors(async_client: httpx.AsyncClient) -> None:
    """Validation errors for invalid parameters."""
    # 1. Specifying radius_km without location coordinates must fail with 400
    bad_radius = {
        "radius_km": 10.0,
    }
    resp1 = await async_client.post("/internal/v1/candidates/search", json=bad_radius)
    assert resp1.status_code == 400
    assert resp1.json()["error"]["code"] == "INVALID_INPUT"

    # 2. Inverted age bounds (age_min > age_max) must fail with 400
    bad_age = {
        "age_min": 30,
        "age_max": 20,
    }
    resp2 = await async_client.post("/internal/v1/candidates/search", json=bad_age)
    assert resp2.status_code == 400
    assert resp2.json()["error"]["code"] == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_unversioned_candidates_search_returns_404(
    async_client: httpx.AsyncClient,
) -> None:
    """Unversioned /internal/candidates/search should return 404 Not Found."""
    # Ensure unversioned route is rejected; only /internal/v1/... is allowed
    payload = {"age_min": 20, "age_max": 25}
    response = await async_client.post("/internal/candidates/search", json=payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_health_check(async_client: httpx.AsyncClient) -> None:
    """Health check endpoint should return 200 ok."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "dating-match-engine"}


@pytest.mark.asyncio
async def test_search_with_large_limit_and_unrestricted_age(
    async_client: httpx.AsyncClient,
) -> None:
    """Search supports limits > 100 and ages unrestricted by hardcoded bounds."""
    # Verifies Match Engine does not reject ages or limits outside former bounds
    cand = CandidateProfile(
        user_id="special_age_cand",
        age=17,
        gender="G1",
        latitude=13.75,
        longitude=100.5,
    )
    payload = {
        "age_min": 16,
        "age_max": 18,
        "gender": ["G1"],
        "limit": 500,
        "candidates": [cand.model_dump(mode="json")],
    }
    response = await async_client.post("/internal/v1/candidates/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["candidates"]) == 1
    assert data["candidates"][0]["user_id"] == "special_age_cand"
