"""
Matching Service: coordinates mutual eligibility verification,
bidirectional scoring computation, and top-N candidate ranking.
"""

import logging

from app.models.profile import CandidateProfile, UserMatchingProfile
from app.models.request import DEFAULT_PAGE_LIMIT
from app.models.response import RecommendationResponse, RecommendedCandidate
from app.scoring.match import compute_pair_match_score
from app.services.backend_client import BackendClient
from app.services.eligibility import is_mutually_eligible

logger = logging.getLogger(__name__)

DISTANCE_DECIMALS: int = 2


class MatchingService:
    """Service orchestrating candidate recommendation ranking."""

    def __init__(self, backend_client: BackendClient | None = None) -> None:
        """Initialize matching service.

        Args:
            backend_client: Optional HTTP client for backend queries.
        """
        self.backend_client = backend_client or BackendClient()

    def rank_candidates(
        self,
        user: UserMatchingProfile,
        candidates: list[CandidateProfile],
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> RecommendationResponse:
        """Filter candidates by mutual eligibility and rank by match score.

        Args:
            user: Profile of the requesting user.
            candidates: Pool of candidate profiles to evaluate.
            limit: Maximum number of ranked recommendations to return.

        Returns:
            RecommendationResponse containing top candidates sorted descending.
        """
        scored_candidates: list[RecommendedCandidate] = []

        pref_a = user.target_preference
        assert user.age is not None

        for candidate in candidates:
            eligible, distance = is_mutually_eligible(user, candidate)
            if not eligible:
                continue

            assert candidate.age is not None
            assert candidate.target_preference is not None
            pref_b = candidate.target_preference

            score = compute_pair_match_score(
                age_a=user.age,
                age_min_a=pref_a.age_min,
                age_max_a=pref_a.age_max,
                radius_a=pref_a.radius_km,
                age_b=candidate.age,
                age_min_b=pref_b.age_min,
                age_max_b=pref_b.age_max,
                radius_b=pref_b.radius_km,
                distance_km=distance,
            )

            scored_candidates.append(
                RecommendedCandidate(
                    user_id=candidate.user_id,
                    match_score=score,
                    distance_km=round(distance, DISTANCE_DECIMALS),
                )
            )

        scored_candidates.sort(key=lambda c: c.match_score, reverse=True)

        return RecommendationResponse(candidates=scored_candidates[:limit])

    async def get_recommendations(
        self,
        user_id: str,
        limit: int = DEFAULT_PAGE_LIMIT,
        user: UserMatchingProfile | None = None,
        candidates: list[CandidateProfile] | None = None,
    ) -> RecommendationResponse:
        """Obtain matching data and return top recommended candidates.

        Args:
            user_id: ID of the user requesting recommendations.
            limit: Maximum number of candidates to return.
            user: Optional pre-fetched user matching profile.
            candidates: Optional pre-fetched candidate pool.

        Returns:
            RecommendationResponse containing top candidates.
        """
        resolved_user = user
        resolved_candidates = candidates

        if (resolved_user is None) or (resolved_candidates is None):
            backend_user, backend_cands = await self.backend_client.get_matching_pool(
                user_id
            )
            resolved_user = resolved_user or backend_user
            resolved_candidates = (
                resolved_candidates
                if resolved_candidates is not None
                else backend_cands
            )

        return self.rank_candidates(
            user=resolved_user, candidates=resolved_candidates, limit=limit
        )
