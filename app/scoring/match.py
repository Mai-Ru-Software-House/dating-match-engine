"""
Match Compatibility Scoring: computes bidirectional directional compatibility
and final geometric mean mutual match scores.
"""

import math
from dataclasses import dataclass

from app.config import get_settings
from app.scoring.age import calculate_age_score
from app.scoring.distance import calculate_distance_score


@dataclass(frozen=True)
class PairParticipant:
    """Age and search preferences of one side of a candidate pair.

    Attributes:
        age: Age of the participant.
        age_min: Minimum preferred age of the participant.
        age_max: Maximum preferred age of the participant.
        radius_km: Maximum search radius of the participant in km.
    """

    age: int
    age_min: int
    age_max: int
    radius_km: float


@dataclass(frozen=True)
class ScoringOptions:
    """Optional overrides for pair scoring; None falls back to settings.

    Attributes:
        w_age: Optional custom age weight.
        w_distance: Optional custom distance weight.
        round_decimals: Optional custom rounding decimal places.
    """

    w_age: float | None = None
    w_distance: float | None = None
    round_decimals: int | None = None


def calculate_directional_score(
    age_score: float,
    distance_score: float,
    w_age: float | None = None,
    w_distance: float | None = None,
) -> float:
    """Calculate directional compatibility score C_A_B.

    Formula:
        C_A_B = w_age * age_score + w_distance * distance_score

    Args:
        age_score: Directional age compatibility score.
        distance_score: Directional distance compatibility score.
        w_age: Weight for age score (defaults to settings.WEIGHT_AGE = 0.7).
        w_distance: Weight for distance (defaults to settings.WEIGHT_DISTANCE = 0.3).

    Returns:
        Weighted directional compatibility score.
    """
    settings = get_settings()
    weight_age = w_age if w_age is not None else settings.WEIGHT_AGE
    weight_dist = w_distance if w_distance is not None else settings.WEIGHT_DISTANCE

    return (weight_age * age_score) + (weight_dist * distance_score)


def calculate_mutual_match_score(
    c_a_b: float,
    c_b_a: float,
    round_decimals: int | None = None,
) -> float:
    """Calculate mutual match score using geometric mean.

    Formula:
        match_score = 100 * sqrt(C_A_B * C_B_A)

    Args:
        c_a_b: Directional compatibility from user A to candidate B.
        c_b_a: Directional compatibility from candidate B to user A.
        round_decimals: Decimal places to round output score.

    Returns:
        Mutual match score bounded between 0.0 and 100.0.
    """
    # Guard against float rounding anomalies
    clamped_a_to_b = max(0.0, min(1.0, c_a_b))
    clamped_b_to_a = max(0.0, min(1.0, c_b_a))

    score = 100.0 * math.sqrt(clamped_a_to_b * clamped_b_to_a)

    settings = get_settings()
    decimals = round_decimals if round_decimals is not None else settings.SCORE_DECIMALS
    return round(score, decimals)


def _score_direction(
    viewer: PairParticipant,
    candidate: PairParticipant,
    distance_km: float,
    options: ScoringOptions,
) -> float:
    """Calculate directional compatibility of a candidate as seen by a viewer.

    Args:
        viewer: Participant whose age range and radius are being applied.
        candidate: Participant being evaluated by the viewer.
        distance_km: Geographic distance between the two participants in km.
        options: Weight overrides for the directional score.

    Returns:
        Weighted directional compatibility score from viewer to candidate.
    """
    age_score = calculate_age_score(
        candidate_age=candidate.age,
        age_min=viewer.age_min,
        age_max=viewer.age_max,
    )
    distance_score = calculate_distance_score(
        distance_km=distance_km,
        radius_km=viewer.radius_km,
    )
    return calculate_directional_score(
        age_score=age_score,
        distance_score=distance_score,
        w_age=options.w_age,
        w_distance=options.w_distance,
    )


def compute_pair_match_score(
    user_a: PairParticipant,
    user_b: PairParticipant,
    distance_km: float,
    options: ScoringOptions | None = None,
) -> float:
    """Calculate complete bidirectional mutual match score for a candidate pair.

    Args:
        user_a: Requesting user A.
        user_b: Candidate B.
        distance_km: Geographic distance between users in km.
        options: Optional weight and rounding overrides.

    Returns:
        Final mutual match score (0-100).
    """
    options = options or ScoringOptions()

    c_a_b = _score_direction(user_a, user_b, distance_km, options)
    c_b_a = _score_direction(user_b, user_a, distance_km, options)

    return calculate_mutual_match_score(
        c_a_b=c_a_b,
        c_b_a=c_b_a,
        round_decimals=options.round_decimals,
    )
