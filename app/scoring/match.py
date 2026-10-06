"""
Match Compatibility Scoring: computes bidirectional directional compatibility
and final geometric mean mutual match scores.
"""

import math

from app.config import get_settings
from app.scoring.age import calculate_age_score
from app.scoring.distance import calculate_distance_score


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


def compute_pair_match_score(
    age_a: int,
    age_min_a: int,
    age_max_a: int,
    radius_a: float,
    age_b: int,
    age_min_b: int,
    age_max_b: int,
    radius_b: float,
    distance_km: float,
    w_age: float | None = None,
    w_distance: float | None = None,
    round_decimals: int | None = None,
) -> float:
    """Calculate complete bidirectional mutual match score for a candidate pair.

    Args:
        age_a: Age of requesting user A.
        age_min_a: Minimum preferred age of user A.
        age_max_a: Maximum preferred age of user A.
        radius_a: Maximum search radius of user A in km.
        age_b: Age of candidate B.
        age_min_b: Minimum preferred age of candidate B.
        age_max_b: Maximum preferred age of candidate B.
        radius_b: Maximum search radius of candidate B in km.
        distance_km: Geographic distance between users in km.
        w_age: Optional custom age weight.
        w_distance: Optional custom distance weight.
        round_decimals: Optional custom rounding decimal places.

    Returns:
        Final mutual match score (0-100).
    """
    # Direction A -> B
    age_score_a_to_b = calculate_age_score(
        candidate_age=age_b,
        age_min=age_min_a,
        age_max=age_max_a,
    )
    dist_score_a_to_b = calculate_distance_score(
        distance_km=distance_km,
        radius_km=radius_a,
    )
    c_a_b = calculate_directional_score(
        age_score=age_score_a_to_b,
        distance_score=dist_score_a_to_b,
        w_age=w_age,
        w_distance=w_distance,
    )

    # Direction B -> A
    age_score_b_to_a = calculate_age_score(
        candidate_age=age_a,
        age_min=age_min_b,
        age_max=age_max_b,
    )
    dist_score_b_to_a = calculate_distance_score(
        distance_km=distance_km,
        radius_km=radius_b,
    )
    c_b_a = calculate_directional_score(
        age_score=age_score_b_to_a,
        distance_score=dist_score_b_to_a,
        w_age=w_age,
        w_distance=w_distance,
    )

    return calculate_mutual_match_score(
        c_a_b=c_a_b,
        c_b_a=c_b_a,
        round_decimals=round_decimals,
    )
