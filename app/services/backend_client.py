"""
Backend Client: asynchronous HTTP client to retrieve user profiles
and candidate pools from the Elysia Backend Prisma DAL (/internal/v1/...).
"""

import logging

import httpx

from app.config import get_settings
from app.models.profile import CandidateProfile, UserMatchingProfile

logger = logging.getLogger(__name__)


class BackendClient:
    """HTTP client communicating with Elysia Backend internal endpoints.

    Respects network boundaries: Elysia owns PostgreSQL / Prisma DAL;
    Match Engine only queries internal /internal/v1/ APIs.
    """

    def __init__(
        self, base_url: str | None = None, timeout: float | None = None
    ) -> None:
        """Initialize backend HTTP client.

        Args:
            base_url: Optional override for Elysia backend URL.
            timeout: Optional override for HTTP request timeout in seconds.
        """
        settings = get_settings()
        self.base_url = (base_url or settings.BACKEND_URL).rstrip("/")
        self.timeout = (
            timeout if timeout is not None else settings.BACKEND_TIMEOUT_SECONDS
        )

    async def get_matching_pool(
        self, user_id: str
    ) -> tuple[UserMatchingProfile, list[CandidateProfile]]:
        """Fetch requesting user profile and potential candidates from Elysia backend.

        Queries the Prisma DAL at /internal/v1/matching-pool.

        Args:
            user_id: The ID of the user requesting recommendations.

        Returns:
            Tuple of (requesting_user_profile, candidate_profiles).

        Raises:
            httpx.HTTPStatusError: If backend returns 4xx/5xx responses.
            httpx.RequestError: If connection to backend fails.
        """
        settings = get_settings()
        async with httpx.AsyncClient(
            base_url=self.base_url, timeout=self.timeout
        ) as client:
            response = await client.get(
                settings.BACKEND_MATCHING_POOL_PATH,
                params={"userId": user_id},
            )
            response.raise_for_status()
            data = response.json()
            user = UserMatchingProfile.model_validate(data["user"])
            raw_candidates = data.get("candidates", [])
            candidates = [CandidateProfile.model_validate(c) for c in raw_candidates]
            return user, candidates

    async def get_candidates(self) -> list[CandidateProfile]:
        """Fetch candidate pool for specification search from Elysia backend.

        Queries the Prisma DAL at /internal/v1/candidates.

        Returns:
            List of candidate profiles.

        Raises:
            httpx.HTTPStatusError: If backend returns 4xx/5xx responses.
            httpx.RequestError: If connection to backend fails.
        """
        settings = get_settings()
        async with httpx.AsyncClient(
            base_url=self.base_url, timeout=self.timeout
        ) as client:
            response = await client.get(settings.BACKEND_CANDIDATES_PATH)
            response.raise_for_status()
            data = response.json()
            raw_candidates = (
                data if isinstance(data, list) else data.get("candidates", [])
            )
            return [CandidateProfile.model_validate(c) for c in raw_candidates]
