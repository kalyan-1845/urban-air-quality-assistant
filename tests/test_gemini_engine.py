"""Unit tests for Gemini AI Engine and Prompt Validation."""

import pytest
from pathlib import Path
from gemini_engine import (
    generate_offline_fallback,
    AirQualityAdvisoryResponse,
    SYSTEM_PROMPT_PATH,
)


def test_system_prompt_file_exists():
    """Verify system prompt file is present and not empty."""
    assert SYSTEM_PROMPT_PATH.exists()
    content = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    assert len(content) > 100
    assert "AeroLife" in content
    assert "LOW-EMISSION DAILY ROUTINES" in content


def test_offline_fallback_schema_compliance():
    """Verify that fallback data adheres strictly to the Pydantic schema."""
    fallback_data = generate_offline_fallback(
        city="Hyderabad",
        aqi=185,
        family_profile="Family with Infants",
        lifestyle="Two-Wheeler Daily Commuter",
    )

    # Validate against Pydantic model
    validated = AirQualityAdvisoryResponse(**fallback_data)
    assert validated.risk_level in ["Moderate", "Unhealthy", "Severe", "Hazardous"]
    assert len(validated.daily_routines) >= 3
    assert len(validated.indoor_hacks) >= 3
    assert len(validated.sustainable_swaps) >= 2
    assert len(validated.disclaimer) > 10


def test_sustainable_swaps_quantified_metrics():
    """Ensure every swap has quantified CO2 and PM2.5 metrics."""
    data = generate_offline_fallback("Delhi", 380, "Asthmatic Patients", "Car Commuter")
    for swap in data["sustainable_swaps"]:
        assert swap["co2_saved_kg_month"] > 0
        assert 0 <= swap["pm25_exposure_reduction_pct"] <= 100
        assert len(swap["impact_explanation"]) > 20
