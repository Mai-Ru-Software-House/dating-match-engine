"""
Mock Elysia Backend Server: provides local test endpoints simulating
the Elysia Prisma DAL (/internal/v1/...) for testing the Match Engine.
"""

import os
from typing import Annotated

import uvicorn
from fastapi import FastAPI, HTTPException, Query, status

app = FastAPI(
    title="Mock Elysia Backend API",
    description=(
        "Simulates Elysia Prisma DAL internal REST endpoints "
        "for local Match Engine testing."
    ),
    version="1.0.0",
)

# In-memory mock database records
MOCK_USERS: dict[str, dict] = {
    "usr_001": {
        "userId": "usr_001",
        "age": 25,
        "dateOfBirth": "2001-05-14",
        "gender": "female",
        "latitude": 13.7563,
        "longitude": 100.5018,
        "targetPreference": {
            "ageMin": 23,
            "ageMax": 30,
            "gender": ["male", "non_binary"],
            "radiusKm": 25.0,
        },
    },
    "usr_002": {
        "userId": "usr_002",
        "age": 27,
        "dateOfBirth": "1999-09-22",
        "gender": "male",
        "latitude": 13.7800,
        "longitude": 100.5200,
        "targetPreference": {
            "ageMin": 22,
            "ageMax": 28,
            "gender": ["female"],
            "radiusKm": 30.0,
        },
    },
}

MOCK_CANDIDATES: list[dict] = [
    {
        "userId": "usr_002",
        "age": 27,
        "dateOfBirth": "1999-09-22",
        "gender": "male",
        "latitude": 13.7800,
        "longitude": 100.5200,
        "targetPreference": {
            "ageMin": 22,
            "ageMax": 28,
            "gender": ["female"],
            "radiusKm": 30.0,
        },
    },
    {
        "userId": "usr_003",
        "age": 26,
        "dateOfBirth": "2000-02-10",
        "gender": "non_binary",
        "latitude": 13.7650,
        "longitude": 100.5120,
        "targetPreference": {
            "ageMin": 24,
            "ageMax": 29,
            "gender": ["female", "male"],
            "radiusKm": 15.0,
        },
    },
    {
        "userId": "usr_004",
        "age": 29,
        "dateOfBirth": "1997-11-05",
        "gender": "male",
        "latitude": 13.8200,
        "longitude": 100.5500,
        "targetPreference": {
            "ageMin": 20,
            "ageMax": 30,
            "gender": ["female"],
            "radiusKm": 20.0,
        },
    },
    {
        "userId": "usr_005",
        "age": 35,
        "dateOfBirth": "1991-03-12",
        "gender": "male",
        "latitude": 13.7600,
        "longitude": 100.5050,
        "targetPreference": {
            "ageMin": 20,
            "ageMax": 30,
            "gender": ["female"],
            "radiusKm": 20.0,
        },
    },
]


@app.get("/health", summary="Health check endpoint")
async def health_check() -> dict[str, str]:
    """Return health status of mock backend service."""
    return {"status": "ok", "service": "mock-elysia-backend"}


@app.get(
    "/internal/v1/matching-pool",
    summary="Simulated unified matching pool endpoint",
)
async def get_matching_pool(
    user_id: Annotated[
        str | None, Query(alias="userId", description="User ID query parameter")
    ] = None,
    user_id_snake: Annotated[
        str | None, Query(alias="user_id", description="User ID snake_case alias")
    ] = None,
) -> dict:
    """Return requesting user profile and pre-filtered candidate pool.

    Args:
        user_id: Requesting user ID (camelCase).
        user_id_snake: Requesting user ID (snake_case).

    Returns:
        JSON payload containing user matching profile and candidate pool.

    Raises:
        HTTPException: If user ID is missing or not found in mock store.
    """
    effective_id = user_id or user_id_snake
    if not effective_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter 'userId' is required",
        )

    # If user is known, return their profile; otherwise generate default profile
    user_profile = MOCK_USERS.get(effective_id)
    if user_profile is None:
        user_profile = {
            "userId": effective_id,
            "age": 25,
            "dateOfBirth": "2001-05-14",
            "gender": "female",
            "latitude": 13.7563,
            "longitude": 100.5018,
            "targetPreference": {
                "ageMin": 22,
                "ageMax": 30,
                "gender": ["male", "non_binary"],
                "radiusKm": 25.0,
            },
        }

    # Filter out self
    eligible_candidates = [c for c in MOCK_CANDIDATES if c["userId"] != effective_id]

    return {
        "user": user_profile,
        "candidates": eligible_candidates,
    }


@app.get(
    "/internal/v1/candidates",
    summary="Simulated candidate pool for specification search",
)
async def get_candidates() -> dict:
    """Return general candidate pool for specification search.

    Returns:
        JSON payload containing list of candidates.
    """
    return {"candidates": MOCK_CANDIDATES}


def run() -> None:
    """Run the mock server using uvicorn."""
    port = int(os.getenv("PORT", "3000"))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("scripts.mock_backend:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    run()
