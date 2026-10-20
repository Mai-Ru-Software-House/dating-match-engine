"""
Shared Test Helpers: payload builders and response assertions reused across
the internal API route tests.
"""

from typing import Any

import httpx

from app.models.profile import CandidateProfile, UserMatchingProfile


def build_push_payload(
    user: UserMatchingProfile, candidate: CandidateProfile, limit: int
) -> dict[str, Any]:
    """Build a direct (push mode) recommendation payload for one candidate."""
    return {
        "user_id": user.user_id,
        "limit": limit,
        "user": user.model_dump(mode="json"),
        "candidates": [candidate.model_dump(mode="json")],
    }


def assert_single_candidate(
    response: httpx.Response, expected_user_id: str
) -> dict[str, Any]:
    """Assert a 200 response containing exactly one candidate and return its body."""
    assert response.status_code == 200
    data: dict[str, Any] = response.json()
    assert len(data["candidates"]) == 1
    assert data["candidates"][0]["user_id"] == expected_user_id
    return data
