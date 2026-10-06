"""
Search Service: filters candidate pools against explicit specification criteria
(age range, gender list, geographic distance) without personalized scoring.
"""

import logging

from app.models.profile import CandidateProfile
from app.models.request import CandidateSearchRequest
from app.models.response import CandidateSearchResponse, SearchCandidate
from app.services.backend_client import BackendClient
from app.services.eligibility import matches_search_specification

logger = logging.getLogger(__name__)

DISTANCE_DECIMALS: int = 2


class SearchService:
    """Service executing specification-based candidate searches."""

    def __init__(self, backend_client: BackendClient | None = None) -> None:
        """Initialize search service.

        Args:
            backend_client: Optional HTTP client for backend queries.
        """
        self.backend_client = backend_client or BackendClient()

    def filter_candidates(
        self,
        spec: CandidateSearchRequest,
        candidates: list[CandidateProfile],
    ) -> CandidateSearchResponse:
        """Filter candidate pool against the specification criteria.

        Args:
            spec: Search specification parameters.
            candidates: Pool of candidate profiles to filter.

        Returns:
            CandidateSearchResponse with matching candidates.
        """
        matched_candidates: list[SearchCandidate] = []

        for candidate in candidates:
            is_match, distance = matches_search_specification(candidate, spec)
            if not is_match:
                continue

            rounded_distance = (
                round(distance, DISTANCE_DECIMALS) if distance is not None else None
            )

            matched_candidates.append(
                SearchCandidate(
                    user_id=candidate.user_id,
                    distance_km=rounded_distance,
                )
            )

        if spec.location is not None:
            matched_candidates.sort(
                key=lambda c: (
                    c.distance_km if c.distance_km is not None else float("inf")
                )
            )

        return CandidateSearchResponse(candidates=matched_candidates[: spec.limit])

    async def search_candidates(
        self,
        spec: CandidateSearchRequest,
    ) -> CandidateSearchResponse:
        """Execute candidate search query.

        Args:
            spec: Search specification request.

        Returns:
            CandidateSearchResponse containing matching candidates.
        """
        candidates = spec.candidates
        if candidates is None:
            candidates = await self.backend_client.get_candidates()

        return self.filter_candidates(spec=spec, candidates=candidates)
