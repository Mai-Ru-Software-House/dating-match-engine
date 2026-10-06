"""
Match Score Algorithm Tests: tests Gaussian age decay, exponential distance decay,
directional linear combinations, and geometric mean mutual scoring.
"""

import math

import pytest

from app.scoring.age import calculate_age_score
from app.scoring.distance import calculate_distance_score
from app.scoring.match import (
    calculate_directional_score,
    calculate_mutual_match_score,
    compute_pair_match_score,
)


def test_age_scoring_exact_midpoint() -> None:
    """Score should be exactly 1.0 when candidate age equals the midpoint mu."""
    # When candidate age == mu, (age - mu)^2 == 0, exp(0) == 1.0
    score = calculate_age_score(candidate_age=25, age_min=20, age_max=30)
    assert pytest.approx(score, rel=1e-6) == 1.0


def test_age_scoring_symmetric() -> None:
    """Ages equally distant from the midpoint must yield the exact same score."""
    # Gaussian bell curve is symmetric around mu: |23 - 25| == |27 - 25| == 2
    score_younger = calculate_age_score(candidate_age=23, age_min=20, age_max=30)
    score_older = calculate_age_score(candidate_age=27, age_min=20, age_max=30)
    assert pytest.approx(score_younger, rel=1e-6) == score_older


def test_age_scoring_at_boundary() -> None:
    """At age boundary (1 sigma away when sigma = half-range), score is exp(-0.5)."""
    # For range [20, 30], sigma = 5; boundary delta is 5 => exp(-0.5)
    score_min = calculate_age_score(candidate_age=20, age_min=20, age_max=30)
    score_max = calculate_age_score(candidate_age=30, age_min=20, age_max=30)
    expected = math.exp(-0.5)
    assert pytest.approx(score_min, rel=1e-6) == expected
    assert pytest.approx(score_max, rel=1e-6) == expected


def test_age_scoring_monotonic_decay() -> None:
    """Scores must strictly decrease as age deviates further from the midpoint."""
    # Monotonic drop: 25 (midpoint) > 27 (delta 2) > 29 (delta 4) > 32 (delta 7)
    s25 = calculate_age_score(candidate_age=25, age_min=20, age_max=30)
    s27 = calculate_age_score(candidate_age=27, age_min=20, age_max=30)
    s29 = calculate_age_score(candidate_age=29, age_min=20, age_max=30)
    s32 = calculate_age_score(candidate_age=32, age_min=20, age_max=30)
    assert s25 > s27 > s29 > s32


def test_distance_scoring_zero_distance() -> None:
    """At 0 km distance, compatibility score should be 1.0."""
    # exp(-(0 / r)^2) == exp(0) == 1.0
    score = calculate_distance_score(distance_km=0.0, radius_km=10.0)
    assert pytest.approx(score, rel=1e-6) == 1.0


def test_distance_scoring_at_radius() -> None:
    """At exactly radius distance, score is exp(-1) ≈ 0.367879."""
    # exp(-(radius / radius)^2) == exp(-1)
    score = calculate_distance_score(distance_km=10.0, radius_km=10.0)
    assert pytest.approx(score, rel=1e-6) == math.exp(-1.0)


def test_distance_scoring_monotonic_decay() -> None:
    """Distance score decreases monotonically as distance increases."""
    # Monotonic drop: 0 km > 5 km > 10 km > 15 km
    s0 = calculate_distance_score(distance_km=0.0, radius_km=10.0)
    s5 = calculate_distance_score(distance_km=5.0, radius_km=10.0)
    s10 = calculate_distance_score(distance_km=10.0, radius_km=10.0)
    s15 = calculate_distance_score(distance_km=15.0, radius_km=10.0)
    assert s0 > s5 > s10 > s15


def test_distance_scoring_invalid_radius() -> None:
    """Zero or negative radius returns 0.0 safely without division by zero."""
    # Avoid zero division and mathematical domain errors
    assert calculate_distance_score(distance_km=5.0, radius_km=0.0) == 0.0
    assert calculate_distance_score(distance_km=5.0, radius_km=-1.0) == 0.0


def test_directional_score_weights() -> None:
    """Verify weighted linear combination C_A_B = 0.7 * age + 0.3 * distance."""
    # Per SEN-201 specification: w_age = 0.7, w_distance = 0.3
    age_s = 0.8
    dist_s = 0.6
    c = calculate_directional_score(
        age_score=age_s,
        distance_score=dist_s,
        w_age=0.7,
        w_distance=0.3,
    )
    expected = 0.7 * 0.8 + 0.3 * 0.6
    assert pytest.approx(c, rel=1e-6) == expected


def test_mutual_score_geometric_mean_penalizes_asymmetry() -> None:
    """Geometric mean severely penalizes asymmetric compatibility.

    If one user is 0.9 compatible and the other is only 0.1 compatible,
    arithmetic mean would be 50.0, but geometric mean is 30.0.
    """
    score = calculate_mutual_match_score(c_a_b=0.9, c_b_a=0.1, round_decimals=2)
    expected = round(100.0 * math.sqrt(0.9 * 0.1), 2)
    assert score == expected
    assert score == 30.0


def test_mutual_score_perfect_match() -> None:
    """Perfect compatibility in both directions produces 100.0."""
    score = calculate_mutual_match_score(c_a_b=1.0, c_b_a=1.0)
    assert score == 100.0


def test_mutual_score_zero_match() -> None:
    """Zero compatibility on either side produces 0.0."""
    # Geometric mean sqrt(0 * 1) == 0 ensures unreciprocated matches score 0
    assert calculate_mutual_match_score(c_a_b=0.0, c_b_a=1.0) == 0.0
    assert calculate_mutual_match_score(c_a_b=1.0, c_b_a=0.0) == 0.0


def test_compute_pair_match_score_bidirectional() -> None:
    """End-to-end pair scoring calculates both directions properly."""
    # When both users are identical in age midpoints and distance is 0 km
    score = compute_pair_match_score(
        age_a=25,
        age_min_a=20,
        age_max_a=30,
        radius_a=15.0,
        age_b=25,
        age_min_b=20,
        age_max_b=30,
        radius_b=15.0,
        distance_km=0.0,
    )
    assert score == 100.0
