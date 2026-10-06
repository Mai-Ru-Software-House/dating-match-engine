"""
Request Models: defines incoming request payloads for recommendation
and specification search endpoints with camelCase support.
"""

from typing import Self

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel

from app.models.profile import (
    CandidateProfile,
    UserMatchingProfile,
)

DEFAULT_PAGE_LIMIT: int = 20


class LocationSpec(BaseModel):
    """Search geographic coordinates supporting lat/lng and latitude/longitude.

    Attributes:
        lat: Latitude in decimal degrees (-90.0 to 90.0).
        lng: Longitude in decimal degrees (-180.0 to 180.0).
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    lat: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        validation_alias=AliasChoices("lat", "latitude"),
        description="Latitude (-90.0 to 90.0)",
    )
    lng: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        validation_alias=AliasChoices("lng", "longitude"),
        description="Longitude (-180.0 to 180.0)",
    )


class CandidateSearchRequest(BaseModel):
    """Candidate search specification criteria.

    Attributes:
        age_min: Minimum candidate age.
        age_max: Maximum candidate age.
        gender: Allowed candidate genders (e.g. ['G1', 'G3']).
        radius_km: Maximum radius in km from location.
        location: Search center location coordinates.
        limit: Maximum number of candidates to return.
        candidates: Optional pre-fetched candidate pool from backend DAL.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    age_min: int | None = Field(
        default=None,
        description="Minimum candidate age",
    )
    age_max: int | None = Field(
        default=None,
        description="Maximum candidate age",
    )
    gender: list[str] | None = Field(
        default=None,
        description="Allowed candidate genders (e.g. ['G1', 'G3'])",
    )
    radius_km: float | None = Field(
        default=None,
        gt=0.0,
        description="Maximum radius in km from location",
    )
    location: LocationSpec | None = Field(
        default=None,
        description="Search center location coordinates",
    )
    limit: int = Field(
        default=DEFAULT_PAGE_LIMIT,
        ge=1,
        description="Maximum number of candidates to return",
    )
    candidates: list[CandidateProfile] | None = Field(
        default=None,
        description="Optional pre-fetched candidate pool to search against",
    )

    @field_validator("gender", mode="before")
    @classmethod
    def normalize_gender(cls, value: str | list[str] | None) -> list[str] | None:
        """Allow a single string or list of strings for gender.

        Args:
            value: A single gender string, list of strings, or None.

        Returns:
            Normalized list of gender strings or None.
        """
        if isinstance(value, str):
            return [value]
        return value

    @model_validator(mode="after")
    def validate_search_spec(self) -> Self:
        """Validate consistency of age range and location constraints.

        Returns:
            The validated instance.

        Raises:
            ValueError: If constraints are violated.
        """
        if (
            self.age_min is not None
            and (self.age_max is not None)
            and (self.age_min > self.age_max)
        ):
            raise ValueError(
                f"age_min ({self.age_min}) cannot exceed age_max ({self.age_max})"
            )
        if self.radius_km is not None and (self.location is None):
            raise ValueError("radius_km requires location coordinates to be specified")
        return self


class RecommendationRequest(BaseModel):
    """Request model for POST /internal/v1/recommendations.

    Attributes:
        user_id: ID of requesting user.
        limit: Maximum number of recommendations to return.
        user: Optional user matching profile; if omitted, fetched from backend.
        candidates: Optional candidate pool; if omitted, fetched from backend.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    user_id: str = Field(..., min_length=1, description="ID of requesting user")
    limit: int = Field(
        default=DEFAULT_PAGE_LIMIT,
        ge=1,
        description="Maximum number of recommendations to return",
    )
    user: UserMatchingProfile | None = Field(
        default=None,
        description="User matching profile; if omitted, fetched from backend",
    )
    candidates: list[CandidateProfile] | None = Field(
        default=None,
        description="Optional candidate pool; if omitted, fetched from backend",
    )
