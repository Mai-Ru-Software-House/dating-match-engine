"""
Profile Models Tests: tests Pydantic validation, bounds, and age resolution from DOB.
"""

from datetime import date

import pytest
from pydantic import ValidationError

from app.models.profile import (
    CandidateProfile,
    TargetPreference,
    calculate_age_from_dob,
)


def test_calculate_age_from_dob() -> None:
    """Test age calculation from date of birth."""
    # Verify age is computed based on current calendar date
    today = date.today()
    dob_25 = date(today.year - 25, today.month, today.day)
    assert calculate_age_from_dob(dob_25) == 25


def test_candidate_profile_resolves_age_from_dob() -> None:
    """Test automatic age resolution when DOB is provided without age."""
    # Backend may send date_of_birth instead of age; engine derives it
    dob = date(2000, 1, 1)
    cand = CandidateProfile(
        user_id="u_dob",
        date_of_birth=dob,
        gender="female",
        latitude=13.75,
        longitude=100.50,
    )
    assert cand.age is not None
    assert cand.age >= 24


def test_candidate_profile_missing_both_age_and_dob_raises() -> None:
    """Missing both age and date_of_birth must raise ValidationError."""
    # At least one age representation must be present for matching computation
    with pytest.raises(ValidationError) as exc:
        CandidateProfile(
            user_id="u_none",
            gender="female",
            latitude=13.75,
            longitude=100.50,
        )
    assert "either 'age' or 'date_of_birth'" in str(exc.value)


def test_target_preference_invalid_range() -> None:
    """age_min greater than age_max must raise ValidationError."""
    # Inverted range [30, 20] is logically invalid
    with pytest.raises(ValidationError) as exc:
        TargetPreference(
            age_min=30,
            age_max=20,
            gender=["male"],
            radius_km=10.0,
        )
    assert "cannot be greater than age_max" in str(exc.value)


def test_target_preference_invalid_radius() -> None:
    """radius_km <= 0 must raise ValidationError."""
    # Radius must be strictly positive float
    with pytest.raises(ValidationError):
        TargetPreference(
            age_min=20,
            age_max=30,
            gender=["male"],
            radius_km=0.0,
        )


def test_target_preference_empty_gender() -> None:
    """Empty gender list must raise ValidationError."""
    # Candidate search requires at least one target gender token
    with pytest.raises(ValidationError):
        TargetPreference(
            age_min=20,
            age_max=30,
            gender=[],
            radius_km=10.0,
        )


def test_invalid_coordinates() -> None:
    """Out-of-range latitude/longitude coordinates must raise ValidationError."""
    # Latitude must be within [-90.0, 90.0]
    with pytest.raises(ValidationError):
        CandidateProfile(
            user_id="u_bad_lat",
            age=25,
            gender="male",
            latitude=95.0,
            longitude=100.5,
        )

    # Longitude must be within [-180.0, 180.0]
    with pytest.raises(ValidationError):
        CandidateProfile(
            user_id="u_bad_lng",
            age=25,
            gender="male",
            latitude=13.75,
            longitude=190.0,
        )


def test_unrestricted_age_bounds() -> None:
    """Engine does not artificially reject ages since Prisma DAL owns age rules."""
    # Non-standard ages (under 18 or above 120) are permitted by compute engine
    profile_young = CandidateProfile(
        user_id="young_user",
        age=16,
        gender="male",
        latitude=13.75,
        longitude=100.5,
    )
    assert profile_young.age == 16

    pref = TargetPreference(
        age_min=15,
        age_max=130,
        gender=["female"],
        radius_km=10.0,
    )
    assert pref.age_min == 15
    assert pref.age_max == 130
