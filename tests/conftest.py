"""
Shared Test Fixtures: provides reusable profile models and HTTP clients
for testing the Match Engine matching logic, scoring, and internal API routes.
"""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.profile import CandidateProfile, TargetPreference, UserMatchingProfile


@pytest.fixture
def sample_user_a() -> UserMatchingProfile:
    """Fixture providing a baseline requesting female user located in central Bangkok.

    User attributes:
        Age: 25 (born in 2001)
        Location: Bangkok (lat 13.7563, lng 100.5018)
        Preference: Ages 24-30 (midpoint 27), male/non-binary, within 15 km.
    """
    return UserMatchingProfile(
        user_id="user_a",
        age=25,
        gender="female",
        latitude=13.7563,
        longitude=100.5018,
        target_preference=TargetPreference(
            age_min=24,
            age_max=30,
            gender=["male", "non_binary"],
            radius_km=15.0,
        ),
    )


@pytest.fixture
def sample_candidate_b() -> CandidateProfile:
    """Fixture providing a mutually eligible candidate close to user A's midpoint.

    Candidate attributes:
        Age: 27 (exact midpoint of user A's 24-30 range)
        Distance: ~3.4 km from user A (well within both 15 km and 20 km radii)
        Mutual preference: Wants female, 22-28 (user A is 25, within range).
    """
    return CandidateProfile(
        user_id="user_b",
        age=27,
        gender="male",
        latitude=13.7800,
        longitude=100.5200,
        target_preference=TargetPreference(
            age_min=22,
            age_max=28,
            gender=["female"],
            radius_km=20.0,
        ),
    )


@pytest.fixture
def sample_candidate_c() -> CandidateProfile:
    """Fixture providing an eligible candidate farther away and older than candidate B.

    Candidate attributes:
        Age: 29 (farther from user A's midpoint 27 than candidate B)
        Distance: ~8.8 km from user A (eligible, but yields lower distance score than B)
        Mutual preference: Wants female, 20-30 (user A is 25, within range).
    """
    return CandidateProfile(
        user_id="user_c",
        age=29,
        gender="male",
        latitude=13.8200,
        longitude=100.5500,
        target_preference=TargetPreference(
            age_min=20,
            age_max=30,
            gender=["female"],
            radius_km=15.0,
        ),
    )


@pytest.fixture
def sample_candidate_ineligible_gender() -> CandidateProfile:
    """Fixture providing a candidate ineligible due to gender incompatibility.

    Candidate attributes:
        Gender: female (satisfies user A only if user A sought females,
            but user A seeks male/non-binary).
        Preference: wants male (fails because user A is female).
    """
    return CandidateProfile(
        user_id="user_ineligible_gender",
        age=26,
        gender="female",
        latitude=13.7600,
        longitude=100.5050,
        target_preference=TargetPreference(
            age_min=24,
            age_max=30,
            gender=["male"],
            radius_km=20.0,
        ),
    )


@pytest.fixture
def sample_candidate_ineligible_age() -> CandidateProfile:
    """Fixture providing candidate ineligible because age exceeds user A range.

    Candidate attributes:
        Age: 35 (user A specifies age_max=30, violating mutual age constraint).
    """
    return CandidateProfile(
        user_id="user_ineligible_age",
        age=35,
        gender="male",
        latitude=13.7600,
        longitude=100.5050,
        target_preference=TargetPreference(
            age_min=20,
            age_max=30,
            gender=["female"],
            radius_km=20.0,
        ),
    )


@pytest.fixture
def sample_candidate_ineligible_distance() -> CandidateProfile:
    """Fixture providing candidate in Chiang Mai, far exceeding user A radius.

    Candidate attributes:
        Coordinates: Chiang Mai (~586 km away, exceeding 15 km radius).
    """
    return CandidateProfile(
        user_id="user_ineligible_distance",
        age=26,
        gender="male",
        latitude=18.7883,
        longitude=98.9853,
        target_preference=TargetPreference(
            age_min=20,
            age_max=30,
            gender=["female"],
            radius_km=20.0,
        ),
    )


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Fixture providing an async HTTP client bound to the FastAPI ASGI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
