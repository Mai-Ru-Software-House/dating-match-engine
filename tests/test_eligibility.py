"""
Mutual Eligibility & Specification Filter Tests: verifies bidirectional
matching rules across age bounds, gender tokens, distance radii, and search specs.
"""

from app.models.profile import CandidateProfile, TargetPreference, UserMatchingProfile
from app.models.request import CandidateSearchRequest, LocationSpec
from app.services.eligibility import is_mutually_eligible, matches_search_specification


def test_self_matching_ineligible(sample_user_a: UserMatchingProfile) -> None:
    """A user must never be eligible to match with themselves."""
    # Defensively prevent users from matching with their own profile
    eligible, _ = is_mutually_eligible(sample_user_a, sample_user_a)
    assert eligible is False


def test_missing_target_preference_ineligible(
    sample_user_a: UserMatchingProfile,
) -> None:
    """Candidates without target preferences cannot be mutually recommended."""
    # Recommendation requires mutual preferences; without preference, check fails
    candidate = CandidateProfile(
        user_id="no_pref",
        age=26,
        gender="male",
        latitude=13.7600,
        longitude=100.5100,
        target_preference=None,
    )
    eligible, _ = is_mutually_eligible(sample_user_a, candidate)
    assert eligible is False


def test_mutual_eligibility_success(
    sample_user_a: UserMatchingProfile, sample_candidate_b: CandidateProfile
) -> None:
    """Mutually matching users pass eligibility."""
    # Both satisfy each other's age range, gender lists, and geographic radii
    eligible, dist = is_mutually_eligible(sample_user_a, sample_candidate_b)
    assert eligible is True
    assert dist > 0.0


def test_gender_one_way_ineligible(
    sample_user_a: UserMatchingProfile,
    sample_candidate_ineligible_gender: CandidateProfile,
) -> None:
    """If gender preference is not mutually satisfied, candidate is ineligible."""
    # One-sided gender match fails mutual requirement: B in A.pref and A in B.pref
    eligible, _ = is_mutually_eligible(
        sample_user_a, sample_candidate_ineligible_gender
    )
    assert eligible is False


def test_gender_configurable_non_binary_and_tokens() -> None:
    """Genders must not be restricted; custom tokens like G1, G3 are valid."""
    # Custom non-binary and generic tokens (e.g. G1, G3) must be accepted
    user_x = UserMatchingProfile(
        user_id="user_x",
        age=25,
        gender="G1",
        latitude=13.75,
        longitude=100.50,
        target_preference=TargetPreference(
            age_min=20,
            age_max=30,
            gender=["G2", "G3"],
            radius_km=10.0,
        ),
    )
    candidate_y = CandidateProfile(
        user_id="cand_y",
        age=24,
        gender="G3",
        latitude=13.76,
        longitude=100.51,
        target_preference=TargetPreference(
            age_min=20,
            age_max=30,
            gender=["G1"],
            radius_km=10.0,
        ),
    )
    eligible, _ = is_mutually_eligible(user_x, candidate_y)
    assert eligible is True


def test_age_one_way_ineligible(
    sample_user_a: UserMatchingProfile,
    sample_candidate_ineligible_age: CandidateProfile,
) -> None:
    """If candidate age fails requesting user's range, candidate is ineligible."""
    # Candidate age (35) exceeds user A's maximum allowed age (30)
    eligible, _ = is_mutually_eligible(sample_user_a, sample_candidate_ineligible_age)
    assert eligible is False


def test_age_reverse_ineligible(sample_user_a: UserMatchingProfile) -> None:
    """If user age fails candidate range, candidate is ineligible."""
    # User A is age 25. Candidate targets age 28-35. Fails reverse direction check.
    candidate = CandidateProfile(
        user_id="strict_older_seeker",
        age=26,
        gender="male",
        latitude=13.7600,
        longitude=100.5100,
        target_preference=TargetPreference(
            age_min=28,
            age_max=35,
            gender=["female"],
            radius_km=20.0,
        ),
    )
    eligible, _ = is_mutually_eligible(sample_user_a, candidate)
    assert eligible is False


def test_age_boundary_eligible() -> None:
    """Exact age boundaries (age_min and age_max) are eligible."""
    # Age constraints are inclusive (age_min <= age <= age_max)
    user_min = UserMatchingProfile(
        user_id="u1",
        age=20,
        gender="G1",
        latitude=13.75,
        longitude=100.50,
        target_preference=TargetPreference(
            age_min=20,
            age_max=30,
            gender=["G2"],
            radius_km=10.0,
        ),
    )
    cand_max = CandidateProfile(
        user_id="u2",
        age=30,
        gender="G2",
        latitude=13.75,
        longitude=100.50,
        target_preference=TargetPreference(
            age_min=20,
            age_max=30,
            gender=["G1"],
            radius_km=10.0,
        ),
    )
    eligible, _ = is_mutually_eligible(user_min, cand_max)
    assert eligible is True


def test_distance_asymmetric_radius_ineligible() -> None:
    """If user is within A's radius (20km) but outside B's radius (2km)."""
    user_a = UserMatchingProfile(
        user_id="u_a",
        age=25,
        gender="G1",
        latitude=13.7563,
        longitude=100.5018,
        target_preference=TargetPreference(
            age_min=20,
            age_max=30,
            gender=["G2"],
            radius_km=20.0,
        ),
    )
    # The pair is ~4.8 km apart. User A allows 20 km, but candidate B only allows 2 km.
    cand_b = CandidateProfile(
        user_id="u_b",
        age=25,
        gender="G2",
        latitude=13.8000,
        longitude=100.5018,
        target_preference=TargetPreference(
            age_min=20,
            age_max=30,
            gender=["G1"],
            radius_km=2.0,
        ),
    )
    eligible, dist = is_mutually_eligible(user_a, cand_b)
    assert dist > 2.0
    assert eligible is False


def test_search_specification_matching() -> None:
    """Specification search correctly filters on age, gender, and geographic radius."""
    spec = CandidateSearchRequest(
        age_min=20,
        age_max=25,
        gender=["G1", "G3"],
        radius_km=10.0,
        location=LocationSpec(lat=13.7563, lng=100.5018),
        limit=20,
    )

    # 1. Matching candidate: age 22, gender G1, within ~1.2 km
    matching_cand = CandidateProfile(
        user_id="match",
        age=22,
        gender="G1",
        latitude=13.76,
        longitude=100.51,
    )
    is_match, dist = matches_search_specification(matching_cand, spec)
    assert is_match is True
    assert dist is not None and dist < 10.0

    # 2. Ineligible: Wrong gender (G2 not in ["G1", "G3"])
    wrong_gender = CandidateProfile(
        user_id="wrong_gender",
        age=22,
        gender="G2",
        latitude=13.76,
        longitude=100.51,
    )
    is_match, _ = matches_search_specification(wrong_gender, spec)
    assert is_match is False

    # 3. Ineligible: Age 28 exceeds search spec age_max 25
    wrong_age = CandidateProfile(
        user_id="wrong_age",
        age=28,
        gender="G1",
        latitude=13.76,
        longitude=100.51,
    )
    is_match, _ = matches_search_specification(wrong_age, spec)
    assert is_match is False

    # 4. Ineligible: Chiang Mai coordinates (~586 km) exceed search radius of 10 km
    far_away = CandidateProfile(
        user_id="far_away",
        age=23,
        gender="G3",
        latitude=18.7883,
        longitude=98.9853,
    )
    is_match, _ = matches_search_specification(far_away, spec)
    assert is_match is False
