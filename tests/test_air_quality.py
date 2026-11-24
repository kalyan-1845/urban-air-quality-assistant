"""Unit tests for Air Quality Service."""

import pytest
from air_quality_service import get_aqi_category, fetch_live_air_quality, DEFAULT_CITIES


def test_aqi_category_ranges():
    """Verify standard CPCB/EPA AQI tiers categorize accurately."""
    good = get_aqi_category(35)
    assert good["tier"] == "Good"
    assert "Safe" in good["badge"]

    moderate = get_aqi_category(150)
    assert moderate["tier"] == "Moderate"

    poor = get_aqi_category(250)
    assert poor["tier"] == "Poor"

    severe = get_aqi_category(350)
    assert severe["tier"] == "Very Poor"

    hazard = get_aqi_category(450)
    assert "Hazardous" in hazard["tier"] or "Severe" in hazard["tier"]


def test_fetch_air_quality_known_city():
    """Test fetching air quality for standard preset cities."""
    res = fetch_live_air_quality("Delhi")
    assert res["city"] == "Delhi"
    assert res["aqi"] > 0
    assert "pm25" in res
    assert "pm10" in res
    assert "category" in res


def test_fetch_air_quality_fallback():
    """Test graceful handling of unknown or offline localities."""
    res = fetch_live_air_quality("NonExistentCityXYZ")
    assert "aqi" in res
    assert res["aqi"] > 0
