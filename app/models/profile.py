"""
Profile Models: defines matching data schemas for users, candidates,
and target preferences, with support for Prisma DAL camelCase serialization.
"""

from datetime import date
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


def calculate_age_from_dob(dob: date) -> int:
    """Calculate age in whole years from a birth date.

    Args:
        dob: The date of birth.

    Returns:
        The calculated age in full years.
    """
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


class TargetPreference(BaseModel):
    """Target matching preferences of a user.

    Attributes:
        age_min: Minimum preferred age in years.
        age_max: Maximum preferred age in years.
        gender: List of acceptable candidate genders.
        radius_km: Maximum acceptable distance in kilometers.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    age_min: int = Field(
        ...,
        description="Minimum preferred age",
    )
    age_max: int = Field(
        ...,
        description="Maximum preferred age",
    )
    gender: list[str] = Field(
        ...,
        min_length=1,
        description="List of preferred genders (e.g. ['G1', 'G3'])",
    )
    radius_km: float = Field(
        ...,
        gt=0.0,
        description="Maximum matching radius in kilometers",
    )

    @model_validator(mode="after")
    def validate_age_range(self) -> Self:
        """Validate that minimum age does not exceed maximum age.

        Returns:
            The validated instance.

        Raises:
            ValueError: If age_min is greater than age_max.
        """
        if self.age_min > self.age_max:
            raise ValueError(
                f"age_min ({self.age_min}) cannot be "
                f"greater than age_max ({self.age_max})"
            )
        return self


class CandidateProfile(BaseModel):
    """Candidate profile containing attributes relevant to matching computation.

    Attributes:
        user_id: Unique candidate identifier.
        age: Candidate age in years.
        date_of_birth: Candidate date of birth in YYYY-MM-DD format.
        gender: Candidate gender string token.
        latitude: Geographic latitude coordinate.
        longitude: Geographic longitude coordinate.
        target_preference: Target matching preferences.
    """

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    user_id: str = Field(..., min_length=1, description="Unique candidate ID")
    age: int | None = Field(
        default=None,
        description="Candidate age in years",
    )
    date_of_birth: date | None = Field(
        default=None,
        description="Candidate date of birth (YYYY-MM-DD)",
    )
    gender: str = Field(..., min_length=1, description="Candidate gender identifier")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude coordinate")
    longitude: float = Field(
        ..., ge=-180.0, le=180.0, description="Longitude coordinate"
    )
    target_preference: TargetPreference | None = Field(
        default=None,
        description="Target preferences (required for mutual recommendation)",
    )

    @model_validator(mode="after")
    def resolve_age(self) -> Self:
        """Compute age from date_of_birth if age was not explicitly provided.

        Returns:
            The validated instance with age populated.

        Raises:
            ValueError: If neither age nor date_of_birth was provided.
        """
        if self.age is None:
            if self.date_of_birth is None:
                raise ValueError(
                    f"User '{self.user_id}' must provide either "
                    "'age' or 'date_of_birth'"
                )
            self.age = calculate_age_from_dob(self.date_of_birth)
        return self


class UserMatchingProfile(CandidateProfile):
    """Requesting user profile. Must contain target_preference for mutual matching."""

    target_preference: TargetPreference = Field(
        ...,
        description="Target preferences for mutual matching",
    )
