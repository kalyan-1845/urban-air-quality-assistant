"""Efficiency and Caching Benchmark Tests for AeroLife."""

import time
import pytest
from air_quality_service import get_aqi_category, fetch_live_air_quality, resolve_city_coordinates


def test_aqi_category_caching_speed():
    """Verify that cached category lookups execute in sub-millisecond time."""
    # Warm up cache
    get_aqi_category(180)

    # Measure cached call latency
    start = time.perf_counter()
    for _ in range(100):
        res = get_aqi_category(180)
    duration = time.perf_counter() - start

    assert res["tier"] == "Moderate"
    # 100 cached lookups should finish in under 10 milliseconds
    assert duration < 0.01


def test_resolve_city_coordinates_caching():
    """Verify in-memory caching for known and resolved coordinates."""
    coords1 = resolve_city_coordinates("Delhi")
    coords2 = resolve_city_coordinates("Delhi")
    assert coords1 == coords2
    assert coords1 is not None


def test_cached_air_quality_speed():
    """Verify that repeated city queries complete quickly."""
    # First call
    data1 = fetch_live_air_quality("Hyderabad")
    assert data1["city"] == "Hyderabad"

    # Second call should be served from memory cache
    start = time.perf_counter()
    data2 = fetch_live_air_quality("Hyderabad")
    duration = time.perf_counter() - start

    assert data1["aqi"] == data2["aqi"]
    assert duration < 0.05  # sub-50ms cache response
