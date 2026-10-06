"""
Geographic Distance Tests: validates Haversine great-circle distance
calculations across identical points, known geographic pairs, and poles.
"""

import math

import pytest

from app.utils.geo import haversine_distance


def test_haversine_identical_points() -> None:
    """Distance between identical coordinates should be exactly 0.0."""
    # Distance to oneself is zero by definition
    dist = haversine_distance(13.7563, 100.5018, 13.7563, 100.5018)
    assert dist == 0.0


def test_haversine_symmetry() -> None:
    """Distance from A to B must equal distance from B to A."""
    # Geographic distance is symmetric regardless of traversal direction
    lat1, lon1 = 13.7563, 100.5018
    lat2, lon2 = 18.7883, 98.9853
    dist_ab = haversine_distance(lat1, lon1, lat2, lon2)
    dist_ba = haversine_distance(lat2, lon2, lat1, lon1)
    assert pytest.approx(dist_ab, rel=1e-5) == dist_ba


def test_haversine_known_bangkok_to_chiang_mai() -> None:
    """Great circle distance between Bangkok and Chiang Mai is approx 586 km."""
    # Verifies real-world Thai coordinates for the dating app service area
    bkk_lat, bkk_lon = 13.7563, 100.5018
    cnx_lat, cnx_lon = 18.7883, 98.9853
    dist = haversine_distance(bkk_lat, bkk_lon, cnx_lat, cnx_lon)
    assert 580.0 <= dist <= 595.0


def test_haversine_known_london_to_paris() -> None:
    """Distance between London and Paris is approximately 343 km."""
    # Standard benchmark pair in geodesic literature
    lon_lat, lon_lon = 51.5074, -0.1278
    par_lat, par_lon = 48.8566, 2.3522
    dist = haversine_distance(lon_lat, lon_lon, par_lat, par_lon)
    assert 340.0 <= dist <= 350.0


def test_haversine_equator_one_degree() -> None:
    """One degree of longitude at the equator is approx 111.19 km."""
    # Earth circumference / 360 = ~40,030 km / 360 ~ 111.19 km per degree
    dist = haversine_distance(0.0, 0.0, 0.0, 1.0)
    assert pytest.approx(dist, rel=1e-2) == 111.19


def test_haversine_poles() -> None:
    """North to South Pole distance is half Earth circumference (~20,015 km)."""
    # From 90N to -90S along any meridian spans exactly pi * R
    dist = haversine_distance(90.0, 0.0, -90.0, 0.0)
    expected = math.pi * 6371.0
    assert pytest.approx(dist, rel=1e-3) == expected
