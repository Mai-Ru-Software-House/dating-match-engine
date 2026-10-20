"""
Scoring: exports scoring functions for age, distance, and mutual compatibility.
"""

from app.scoring.age import calculate_age_score
from app.scoring.distance import calculate_distance_score
from app.scoring.match import (
    PairParticipant,
    ScoringOptions,
    calculate_directional_score,
    calculate_mutual_match_score,
    compute_pair_match_score,
)

__all__ = [
    "PairParticipant",
    "ScoringOptions",
    "calculate_age_score",
    "calculate_distance_score",
    "calculate_directional_score",
    "calculate_mutual_match_score",
    "compute_pair_match_score",
]
