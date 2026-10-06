"""
Eligibility Services: checks mutual eligibility for recommendation
and matches candidates against explicit search specifications.
"""

from app.models.profile import CandidateProfile, UserMatchingProfile
from app.models.request import CandidateSearchRequest
from app.utils.geo import haversine_distance


def is_mutually_eligible(
    user_a: UserMatchingProfile,
    user_b: CandidateProfile,
    distance_km: float | None = None,
) -> tuple[bool, float]:
    """Check if two profiles are mutually eligible for candidate recommendation.

    Both profiles must mutually satisfy:
    1. Gender: B.gender in A.target_preference.gender AND
       A.gender in B.target_preference.gender
    2. Age: A.age_min <= B.age <= A.age_max AND B.age_min <= A.age <= B.age_max
    3. Distance: distance <= A.radius_km AND distance <= B.radius_km

    Args:
        user_a: The primary requesting user.
        user_b: The candidate profile.
        distance_km: Precalculated distance, or None to compute via Haversine.

    Returns:
        Tuple of (is_eligible: bool, distance_km: float).
    """
    if user_a.user_id == user_b.user_id:
        return False, 0.0

    if user_b.target_preference is None:
        return False, 0.0

    pref_a = user_a.target_preference
    pref_b = user_b.target_preference

    # 1. Gender mutual compatibility
    if (user_b.gender not in pref_a.gender) or (user_a.gender not in pref_b.gender):
        return False, 0.0

    # 2. Age mutual compatibility
    assert user_a.age is not None
    assert user_b.age is not None
    if not (pref_a.age_min <= user_b.age <= pref_a.age_max):
        return False, 0.0
    if not (pref_b.age_min <= user_a.age <= pref_b.age_max):
        return False, 0.0

    # 3. Distance mutual compatibility
    computed_distance = distance_km
    if computed_distance is None:
        computed_distance = haversine_distance(
            user_a.latitude,
            user_a.longitude,
            user_b.latitude,
            user_b.longitude,
        )

    if (computed_distance > pref_a.radius_km) or (computed_distance > pref_b.radius_km):
        return False, computed_distance

    return True, computed_distance


def matches_search_specification(
    candidate: CandidateProfile,
    spec: CandidateSearchRequest,
    distance_km: float | None = None,
) -> tuple[bool, float | None]:
    """Check if a candidate meets explicit search filter criteria.

    Args:
        candidate: The candidate profile.
        spec: The search specification criteria.
        distance_km: Precalculated distance or None to compute via Haversine.

    Returns:
        Tuple of (matches: bool, distance_km: float | None).
    """
    assert candidate.age is not None

    if spec.age_min is not None and (candidate.age < spec.age_min):
        return False, distance_km
    if spec.age_max is not None and (candidate.age > spec.age_max):
        return False, distance_km

    if spec.gender is not None and (candidate.gender not in spec.gender):
        return False, distance_km

    computed_distance = distance_km
    if spec.location is not None:
        if computed_distance is None:
            computed_distance = haversine_distance(
                spec.location.lat,
                spec.location.lng,
                candidate.latitude,
                candidate.longitude,
            )
        if spec.radius_km is not None and (computed_distance > spec.radius_km):
            return False, computed_distance

    return True, computed_distance
