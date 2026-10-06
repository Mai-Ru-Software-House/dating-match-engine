"""
Response Models: defines outgoing payload schemas for recommendation,
search, error, and health status responses conforming to Mai Ru standards.
"""

from pydantic import BaseModel, ConfigDict, Field, computed_field
from pydantic.alias_generators import to_camel


class RecommendedCandidate(BaseModel):
    """Recommended candidate item containing user ID, match score, and distance.

    Attributes:
        user_id: Unique candidate identifier.
        match_score: Calculated mutual match compatibility score (0-100).
        distance_km: Geographic distance in km between user and candidate.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    user_id: str = Field(..., description="Candidate user identifier")
    match_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Mutual match score (0-100)",
    )
    distance_km: float = Field(
        ...,
        ge=0.0,
        description="Geographic distance in km between user and candidate",
    )

    @computed_field(alias="user_id")
    def snake_user_id(self) -> str:
        """Alias property for backward compatibility with snake_case consumers."""
        return self.user_id

    @computed_field(alias="match_score")
    def snake_match_score(self) -> float:
        """Alias property for backward compatibility with snake_case consumers."""
        return self.match_score

    @computed_field(alias="distance_km")
    def snake_distance_km(self) -> float:
        """Alias property for backward compatibility with snake_case consumers."""
        return self.distance_km


class RecommendationResponse(BaseModel):
    """Response schema for candidate recommendation endpoints.

    Attributes:
        candidates: Ranked list of mutually eligible candidates.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    candidates: list[RecommendedCandidate] = Field(
        default_factory=list,
        description="Ranked candidates sorted descending by match score",
    )


class SearchCandidate(BaseModel):
    """Candidate item returned from specification search.

    Attributes:
        user_id: Candidate user identifier.
        distance_km: Geographic distance from search center in kilometers.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    user_id: str = Field(..., description="Candidate user identifier")
    distance_km: float | None = Field(
        default=None,
        description="Geographic distance in km from search center",
    )

    @computed_field(alias="user_id")
    def snake_user_id(self) -> str:
        """Alias property for backward compatibility with snake_case consumers."""
        return self.user_id

    @computed_field(alias="distance_km")
    def snake_distance_km(self) -> float | None:
        """Alias property for backward compatibility with snake_case consumers."""
        return self.distance_km


class CandidateSearchResponse(BaseModel):
    """Response schema for candidate specification search endpoint.

    Attributes:
        candidates: Candidates satisfying the search specification.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    candidates: list[SearchCandidate] = Field(
        default_factory=list,
        description="Candidates satisfying the search specification",
    )


class HealthResponse(BaseModel):
    """Health check response model.

    Attributes:
        status: Service health status indicator.
        service: Service identifier name.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    status: str = "ok"
    service: str = "dating-match-engine"


class ErrorDetail(BaseModel):
    """Structured error payload required by Mai Ru Coding Standards (Rule 3).

    Attributes:
        code: Machine-readable error code.
        message: Human-readable error description.
    """

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error description")


class ErrorResponse(BaseModel):
    """Top-level error response envelope required by Mai Ru standards.

    Attributes:
        error: Detailed error information.
    """

    error: ErrorDetail = Field(..., description="Error information")
