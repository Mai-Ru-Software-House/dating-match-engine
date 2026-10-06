"""
Age Compatibility Scoring: computes directional Gaussian decay score
based on candidate age and user preferred age interval.
"""

import math

from app.config import get_settings


def calculate_age_score(
    candidate_age: float,
    age_min: float,
    age_max: float,
    sigma: float | None = None,
) -> float:
    """Calculate directional age compatibility score using Gaussian decay.

    Formula:
        mu = (age_min + age_max) / 2
        age_score = exp(-((candidate_age - mu)^2) / (2 * sigma^2))

    Args:
        candidate_age: Age of the candidate being evaluated.
        age_min: User's minimum preferred age.
        age_max: User's maximum preferred age.
        sigma: Standard deviation spread; defaults to half-interval width.

    Returns:
        Directional age compatibility score in (0.0, 1.0].
    """
    midpoint_age = (age_min + age_max) / 2.0

    if sigma is None:
        half_width = (age_max - age_min) / 2.0
        settings = get_settings()
        sigma = half_width if half_width > 0.0 else settings.DEFAULT_AGE_SIGMA

    if sigma <= 0.0:
        sigma = 1.0

    deviation = candidate_age - midpoint_age
    exponent = -(deviation**2) / (2.0 * (sigma**2))
    return math.exp(exponent)
