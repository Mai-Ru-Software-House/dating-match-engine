"""
Models: exports domain schemas, request envelopes, and response models.
"""

from app.models.profile import (
    CandidateProfile,
    TargetPreference,
    UserMatchingProfile,
    calculate_age_from_dob,
)
from app.models.request import (
    CandidateSearchRequest,
    LocationSpec,
    RecommendationRequest,
)
from app.models.response import (
    CandidateSearchResponse,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    RecommendationResponse,
    RecommendedCandidate,
    SearchCandidate,
)

__all__ = [
    "CandidateProfile",
    "CandidateSearchRequest",
    "CandidateSearchResponse",
    "ErrorDetail",
    "ErrorResponse",
    "HealthResponse",
    "LocationSpec",
    "RecommendationRequest",
    "RecommendationResponse",
    "RecommendedCandidate",
    "SearchCandidate",
    "TargetPreference",
    "UserMatchingProfile",
    "calculate_age_from_dob",
]
