"""
Geographic Utilities: provides distance calculations between coordinates
using the spherical Haversine formula.
"""

import math

EARTH_RADIUS_KM: float = 6371.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on Earth.

    Uses the spherical Haversine formula with Earth mean radius of 6371.0 km.

    Args:
        lat1: Latitude of point 1 in degrees (-90.0 to 90.0).
        lon1: Longitude of point 1 in degrees (-180.0 to 180.0).
        lat2: Latitude of point 2 in degrees (-90.0 to 90.0).
        lon2: Longitude of point 2 in degrees (-180.0 to 180.0).

    Returns:
        Great-circle distance in kilometers.
    """
    if (lat1 == lat2) and (lon1 == lon2):
        return 0.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    haversine_term = (math.sin(delta_phi / 2.0) ** 2) + (
        math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )
    # Clamp to avoid domain errors from floating-point roundoff
    clamped_term = min(1.0, max(0.0, haversine_term))
    central_angle = 2.0 * math.atan2(
        math.sqrt(clamped_term), math.sqrt(1.0 - clamped_term)
    )

    return EARTH_RADIUS_KM * central_angle
