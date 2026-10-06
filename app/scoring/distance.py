"""
Distance Compatibility Scoring: computes directional exponential decay
score based on candidate distance and user preferred radius.
"""

import math


def calculate_distance_score(distance_km: float, radius_km: float) -> float:
    """Calculate directional distance compatibility score.

    Formula:
        distance_score = exp(-(distance / radius)^2)

    Args:
        distance_km: Geographic distance in kilometers.
        radius_km: User's maximum preferred radius in kilometers.

    Returns:
        Directional distance score in (0.0, 1.0]. Returns 0.0 if radius <= 0.
    """
    if radius_km <= 0.0:
        return 0.0

    non_negative_distance = max(0.0, distance_km)
    normalized_distance = non_negative_distance / radius_km
    return math.exp(-(normalized_distance**2))
