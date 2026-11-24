"""Comprehensive Test Suite for Exceptions, Edge Cases, and Resilient Recovery.

Covers:
- AeroLife custom exception hierarchy and error code formatting.
- Numerical AQI edge cases (negative AQI, extreme AQI > 1000).
- Locality input edge cases (empty strings, whitespace-only, special characters).
- Geocoding and atmospheric API network fault tolerance.
- Gemini GenAI prompt engine fallback recovery under quota and network errors.
- Schema validation under various payload anomalies.
- Full branch coverage of fallback generation and prompt synthesis.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest
import requests

from exceptions import (
    AeroLifeBaseException,
    AirQualityServiceException,
    AtmosphericDataError,
    CityNotFoundException,
    InvalidAQIValueException,
    GeminiEngineException,
    PromptSynthesisError,
    GeminiQuotaExceededException,
    GeminiNetworkException,
    DataValidationException,
    SchemaValidationError,
    validate_aqi_bounds,
    validate_city_name,
)
from air_quality_service import (
    get_aqi_category,
    resolve_city_coordinates,
    fetch_live_air_quality,
)
import gemini_engine
from gemini_engine import (
    generate_offline_fallback,
    generate_air_quality_advisory,
    AirQualityAdvisoryResponse,
    load_system_prompt,
    validate_atmospheric_inputs,
    _determine_risk_level,
    parse_and_validate_advisory_dict,
    construct_advisory_prompt,
    _init_gemini_model,
    _call_gemini_api_with_retry,
)


# =====================================================================
# 1. CUSTOM EXCEPTION HIERARCHY TESTS
# =====================================================================

def test_aerolife_base_exception():
    """Verify base exception attributes and string formatting."""
    exc_default = AeroLifeBaseException()
    assert isinstance(exc_default, Exception)
    assert exc_default.error_code == "AEROLIFE_GENERAL_ERROR"
    assert "AEROLIFE_GENERAL_ERROR" in str(exc_default)

    exc_custom = AeroLifeBaseException(
        "Custom failure occurred",
        "CUSTOM_CODE_123",
        details={"hint": "check logs"},
    )
    assert exc_custom.message == "Custom failure occurred"
    assert exc_custom.error_code == "CUSTOM_CODE_123"
    assert "Details:" in str(exc_custom)
    assert "CUSTOM_CODE_123" in str(exc_custom)


def test_air_quality_service_exceptions():
    """Verify atmospheric service exceptions and error codes."""
    aq_exc = AirQualityServiceException("Sensor station unreachable")
    assert isinstance(aq_exc, AeroLifeBaseException)
    assert aq_exc.error_code == "AQ_SERVICE_ERROR"
    assert "Sensor station unreachable" in str(aq_exc)

    atm_exc = AtmosphericDataError("Out of bounds pollutant")
    assert isinstance(atm_exc, AirQualityServiceException)
    assert atm_exc.error_code == "ATMOSPHERIC_DATA_ERROR"

    city_exc = CityNotFoundException("Atlantis")
    assert isinstance(city_exc, AirQualityServiceException)
    assert city_exc.city == "Atlantis"
    assert city_exc.error_code == "CITY_NOT_FOUND"
    assert "Atlantis" in str(city_exc)

    aqi_exc = InvalidAQIValueException(-25)
    assert isinstance(aqi_exc, AtmosphericDataError)
    assert aqi_exc.aqi == -25
    assert aqi_exc.error_code == "INVALID_AQI_VALUE"
    assert "-25" in str(aqi_exc)


def test_gemini_engine_exceptions():
    """Verify GenAI engine exception hierarchy and specific failure modes."""
    gemini_base = GeminiEngineException("LLM model timeout")
    assert isinstance(gemini_base, AeroLifeBaseException)
    assert gemini_base.error_code == "GEMINI_ENGINE_ERROR"

    prompt_exc = PromptSynthesisError("Failed prompt assembly")
    assert isinstance(prompt_exc, GeminiEngineException)
    assert prompt_exc.error_code == "PROMPT_SYNTHESIS_ERROR"

    quota_exc = GeminiQuotaExceededException()
    assert isinstance(quota_exc, PromptSynthesisError)
    assert quota_exc.error_code == "GEMINI_QUOTA_EXCEEDED"
    assert "quota" in str(quota_exc).lower()

    net_exc = GeminiNetworkException()
    assert isinstance(net_exc, PromptSynthesisError)
    assert net_exc.error_code == "GEMINI_NETWORK_ERROR"
    assert "network" in str(net_exc).lower()

    val_exc = DataValidationException("Missing required schema field 'summary'")
    assert isinstance(val_exc, AeroLifeBaseException)
    assert val_exc.error_code == "DATA_VALIDATION_ERROR"

    schema_exc = SchemaValidationError("Field constraint violated")
    assert isinstance(schema_exc, DataValidationException)
    assert schema_exc.error_code == "SCHEMA_VALIDATION_ERROR"


def test_exception_helper_validators():
    """Verify input validation helper functions and boundary enforcement."""
    # Valid AQI bounds
    assert validate_aqi_bounds(120) == 120
    assert validate_aqi_bounds(0) == 0

    # Negative AQI with non-strict clamping
    assert validate_aqi_bounds(-15, strict=False) == 0

    # Negative AQI with strict enforcement
    with pytest.raises(InvalidAQIValueException) as exc_info:
        validate_aqi_bounds(-50, strict=True)
    assert exc_info.value.aqi == -50

    # City name normalization
    assert validate_city_name("  new delhi  ") == "New Delhi"
    assert validate_city_name("hyderabad") == "Hyderabad"

    # Empty city with fallback
    assert validate_city_name("", strict=False) == "Delhi"
    assert validate_city_name("   ", strict=False) == "Delhi"

    # Empty city with strict enforcement
    with pytest.raises(CityNotFoundException) as exc_info:
        validate_city_name("", strict=True)
    assert exc_info.value.city == ""


# =====================================================================
# 2. EDGE CASES: AQI VALUES AND LOCALITY STRINGS
# =====================================================================

def test_negative_aqi_handling():
    """Verify graceful categorization when sensors report negative AQI."""
    result = get_aqi_category(-1)
    assert result["tier"] == "Unknown / Calibrating"
    assert result["color"] == "#6B7280"
    assert "Unknown" in result["badge"]
    assert "calibrating" in result["action"].lower() or "station" in result["action"].lower()

    result_extreme_neg = get_aqi_category(-999)
    assert result_extreme_neg["tier"] == "Unknown / Calibrating"

    # Verify strict mode raises exception
    with pytest.raises(InvalidAQIValueException) as exc_info:
        get_aqi_category(-10, strict=True)
    assert exc_info.value.aqi == -10


def test_extreme_aqi_over_1000():
    """Verify emergency advisory categorization when AQI exceeds 1000."""
    result_1001 = get_aqi_category(1001)
    assert "Hazardous" in result_1001["tier"] or "Severe" in result_1001["tier"]
    assert "Catastrophic" in result_1001["tier"]
    assert result_1001["color"] == "#450A0A"
    assert "Extreme" in result_1001["badge"] or "Hazardous" in result_1001["badge"]
    assert "1000 AQI" in result_1001["action"] or "catastrophic" in result_1001["action"].lower()

    result_2500 = get_aqi_category(2500)
    assert "Catastrophic" in result_2500["tier"]
    assert result_2500["color"] == "#450A0A"


def test_empty_and_whitespace_city_strings():
    """Verify that empty, None, and whitespace strings do not raise exceptions."""
    # Coordinate resolution handles empty strings gracefully
    assert resolve_city_coordinates("") is None
    assert resolve_city_coordinates("   ") is None

    # Air quality fetch falls back to reliable default (Delhi)
    res_empty = fetch_live_air_quality("")
    assert res_empty["city"] == "Delhi"
    assert res_empty["aqi"] > 0
    assert "pm25" in res_empty

    res_spaces = fetch_live_air_quality("     ")
    assert res_spaces["city"] == "Delhi"
    assert res_spaces["aqi"] > 0


def test_special_characters_in_locality():
    """Verify robustness against arbitrary special characters and injection strings."""
    special_queries = [
        "New Delhi @#!$%^&*()",
        "Mumbai <script>alert('xss')</script>",
        "City'; DROP TABLE air_quality;--",
        "../../etc/passwd",
        "Bengaluru 🚀✨🍃",
    ]

    for query in special_queries:
        res = fetch_live_air_quality(query)
        assert isinstance(res, dict)
        assert "aqi" in res
        assert res["aqi"] > 0
        assert "category" in res
        assert "tier" in res["category"]


def test_explicit_lat_lon_coordinates():
    """Verify explicit geographical coordinates override city geocoding lookup."""
    res = fetch_live_air_quality("CustomStationPoint", lat=28.6139, lon=77.2090)
    assert res["city"] == "Customstationpoint"
    assert res["aqi"] > 0
    assert "category" in res


def test_geocoding_api_success_and_mock(monkeypatch):
    """Verify geocoding resolution when Open-Meteo API returns valid coordinate results."""
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [{"latitude": 26.8467, "longitude": 80.9462, "name": "Lucknow"}]
    }
    mock_session.get.return_value = mock_resp

    monkeypatch.setattr("air_quality_service.get_http_session", lambda: mock_session)

    # Use unique city name to bypass previous cache
    coords = resolve_city_coordinates("Lucknow-Custom-Test")
    assert coords == (26.8467, 80.9462)


def test_resolve_city_coordinates_network_exception(monkeypatch):
    """Verify geocoding gracefully returns None when Open-Meteo network raises an error."""
    mock_session = MagicMock()
    mock_session.get.side_effect = requests.exceptions.RequestException("DNS lookup failed")
    monkeypatch.setattr("air_quality_service.get_http_session", lambda: mock_session)

    coords = resolve_city_coordinates("ErrorCityUnresolvable")
    assert coords is None


def test_air_quality_service_network_failure_resilience(monkeypatch):
    """Verify service falls back to regional benchmark if remote API network times out."""
    mock_session = MagicMock()
    mock_session.get.side_effect = requests.exceptions.ConnectTimeout("Remote host unreachable")
    monkeypatch.setattr("air_quality_service.get_http_session", lambda: mock_session)

    # Calling with explicit coordinates triggers API call which then fails and falls back
    res = fetch_live_air_quality("Varanasi-NetworkFail", lat=25.3176, lon=82.9739)
    assert res["city"] == "Varanasi-Networkfail"
    assert res["aqi"] > 0
    assert "Regional Model Benchmark" in res["source"] or "Offline" in res["source"]


# =====================================================================
# 3. GEMINI AI FALLBACK & RECOVERY TESTS
# =====================================================================

def test_gemini_advisory_without_api_key(monkeypatch):
    """Verify seamless offline engine activation when GEMINI_API_KEY is not set."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    advisory = generate_air_quality_advisory(
        city="Pune",
        aqi=165,
        pm25=72.0,
        pm10=130.0,
        family_profile="Family with Toddlers",
        lifestyle="Working from Home",
    )

    validated = AirQualityAdvisoryResponse(**advisory)
    assert validated.risk_level in ["Moderate", "Unhealthy", "Severe", "Hazardous"]
    assert len(validated.daily_routines) >= 3
    assert len(validated.indoor_hacks) >= 3
    assert len(validated.sustainable_swaps) >= 2


def test_gemini_recovery_on_quota_error(monkeypatch):
    """Verify graceful fallback recovery when Gemini API throws 429 ResourceExhausted."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock_quota_exceeded_key")

    mock_genai = MagicMock()
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = Exception(
        "429 ResourceExhausted: Quota exceeded for quota metric 'GenerateContent Requests'"
    )
    mock_genai.GenerativeModel.return_value = mock_model

    monkeypatch.setattr("gemini_engine.genai", mock_genai, raising=False)
    monkeypatch.setitem(
        __import__("sys").modules,
        "google.generativeai",
        mock_genai,
    )

    advisory = generate_air_quality_advisory(
        city="Delhi",
        aqi=390,
        pm25=250.0,
        pm10=400.0,
        family_profile="Elderly Parents (>65 yrs)",
        lifestyle="Public Transit",
        custom_concerns="Chronic wheezing",
    )

    # Should not crash; must return offline fallback data matching schema
    validated = AirQualityAdvisoryResponse(**advisory)
    assert validated.risk_level == "Severe"
    assert "Delhi" in validated.summary
    assert len(validated.daily_routines) > 0


def test_gemini_recovery_on_network_transport_error(monkeypatch):
    """Verify graceful recovery when network drops during Gemini API request."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock_network_fail_key")

    mock_genai = MagicMock()
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = requests.exceptions.ConnectionError(
        "Failed to establish connection to generativelanguage.googleapis.com"
    )
    mock_genai.GenerativeModel.return_value = mock_model

    monkeypatch.setitem(
        __import__("sys").modules,
        "google.generativeai",
        mock_genai,
    )

    advisory = generate_air_quality_advisory(
        city="Mumbai",
        aqi=175,
        pm25=85.0,
        pm10=145.0,
        family_profile="Active Outdoor Athletes",
        lifestyle="Car Commuter",
    )

    validated = AirQualityAdvisoryResponse(**advisory)
    assert validated.risk_level in ["Moderate", "Unhealthy", "Severe"]
    assert "Mumbai" in validated.summary


def test_gemini_recovery_on_malformed_json_response(monkeypatch):
    """Verify recovery when Gemini returns unparseable or corrupted response."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock_json_error_key")

    mock_genai = MagicMock()
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is not valid JSON at all: 404 error"
    mock_model.generate_content.return_value = mock_response
    mock_genai.GenerativeModel.return_value = mock_model

    monkeypatch.setitem(
        __import__("sys").modules,
        "google.generativeai",
        mock_genai,
    )

    advisory = generate_air_quality_advisory(
        city="Chennai",
        aqi=95,
        pm25=32.0,
        pm10=70.0,
        family_profile="General Urban Household",
        lifestyle="Two-Wheeler",
    )

    # Should fall back cleanly without raising JSONDecodeError
    validated = AirQualityAdvisoryResponse(**advisory)
    assert "Chennai" in validated.summary
    assert len(validated.sustainable_swaps) >= 2


def test_gemini_live_success_path_mocked(monkeypatch):
    """Verify the full success pipeline of Gemini AI parsing and Pydantic validation."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock_success_key")

    mock_data = {
        "summary": "Mocked successful Gemini advisory for Bengaluru with AQI 65.",
        "risk_level": "Low",
        "daily_routines": [
            {
                "time_of_day": "Morning (07:00 - 09:00)",
                "activity": "Outdoor Walking",
                "recommendation": "Air quality is favorable. Normal outdoor walks permitted.",
                "mask_required": "None",
            }
        ],
        "indoor_hacks": [
            {
                "title": "Natural Cross Ventilation",
                "category": "Ventilation",
                "action_steps": "Open windows on opposite walls for 30 minutes.",
                "difficulty_level": "Easy",
                "estimated_cost_inr": 0.0,
            }
        ],
        "sustainable_swaps": [
            {
                "current_habit": "Using petrol scooter for short grocery runs",
                "sustainable_swap": "Bicycle or walking for trips under 1 km",
                "co2_saved_kg_month": 12.0,
                "pm25_exposure_reduction_pct": 20.0,
                "impact_explanation": "Eliminates tailpipe exhaust from cold engine starts.",
            }
        ],
        "disclaimer": "Standard health advisory disclaimer for environmental awareness.",
    }

    mock_genai = MagicMock()
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(mock_data)
    mock_model.generate_content.return_value = mock_response
    mock_genai.GenerativeModel.return_value = mock_model

    monkeypatch.setitem(
        __import__("sys").modules,
        "google.generativeai",
        mock_genai,
    )

    advisory = generate_air_quality_advisory(
        city="Bengaluru",
        aqi=65,
        pm25=22.0,
        pm10=55.0,
        family_profile="General Urban Household",
        lifestyle="Public Transit",
    )

    assert advisory["summary"] == mock_data["summary"]
    assert advisory["risk_level"] == "Low"
    assert advisory["daily_routines"][0]["mask_required"] == "None"
    assert advisory["indoor_hacks"][0]["estimated_cost_inr"] == 0.0


# =====================================================================
# 4. DEEP COVERAGE FOR GEMINI ENGINE BRANCHES
# =====================================================================

def test_load_system_prompt_fallback_branches(tmp_path):
    """Verify system prompt loader fallback when file is missing or unreadable."""
    missing_file = tmp_path / "absent_system_prompt.txt"
    loaded = load_system_prompt(missing_file)
    assert "AeroLife" in loaded

    mock_path = MagicMock(spec=Path)
    mock_path.exists.side_effect = PermissionError("Access denied")
    loaded_on_err = load_system_prompt(mock_path)
    assert "AeroLife" in loaded_on_err


def test_validate_atmospheric_inputs_exceptions():
    """Verify input validation raises AtmosphericDataError on invalid input."""
    with pytest.raises(AtmosphericDataError) as exc1:
        validate_atmospheric_inputs("", 100, 45.0, 75.0)
    assert "blank" in str(exc1.value).lower()

    with pytest.raises(AtmosphericDataError) as exc2:
        validate_atmospheric_inputs("Delhi", -5, 45.0, 75.0)
    assert "negative" in str(exc2.value).lower()

    with pytest.raises(AtmosphericDataError) as exc3:
        validate_atmospheric_inputs("Delhi", 100, -10.0, 75.0)
    assert "negative" in str(exc3.value).lower()

    with pytest.raises(AtmosphericDataError) as exc4:
        validate_atmospheric_inputs("Delhi", 100, 45.0, -20.0)
    assert "negative" in str(exc4.value).lower()


def test_determine_risk_level_branches():
    """Verify all risk level threshold branches."""
    assert _determine_risk_level(30) == "Low"
    assert _determine_risk_level(85) == "Moderate"
    assert _determine_risk_level(180) == "Unhealthy"
    assert _determine_risk_level(350) == "Severe"


def test_parse_and_validate_advisory_dict_failure():
    """Verify SchemaValidationError when dictionary fails Pydantic validation."""
    with pytest.raises(SchemaValidationError) as exc:
        parse_and_validate_advisory_dict({"incomplete_payload": True})
    assert "validation" in str(exc.value).lower()


def test_construct_advisory_prompt_failure(monkeypatch):
    """Verify PromptSynthesisError when prompt assembly raises an exception."""
    monkeypatch.setattr(
        "gemini_engine._format_telemetry_block",
        MagicMock(side_effect=RuntimeError("Formatting error")),
    )
    with pytest.raises(PromptSynthesisError):
        construct_advisory_prompt("Delhi", 200, 100.0, 150.0, "General", "Transit")


def test_init_gemini_model_failure(monkeypatch):
    """Verify PromptSynthesisError when Gemini model initialization fails."""
    mock_genai = MagicMock()
    mock_genai.GenerativeModel.side_effect = RuntimeError("Model config failure")
    monkeypatch.setitem(__import__("sys").modules, "google.generativeai", mock_genai)

    with pytest.raises(PromptSynthesisError):
        _init_gemini_model("bad_key")


def test_call_gemini_api_retry_exhaustion_and_empty():
    """Verify PromptSynthesisError when Gemini returns empty text across retries."""
    mock_model = MagicMock()
    mock_empty_resp = MagicMock()
    mock_empty_resp.text = ""
    mock_model.generate_content.return_value = mock_empty_resp

    with pytest.raises(PromptSynthesisError) as exc:
        _call_gemini_api_with_retry(mock_model, "test prompt", max_retries=1, backoff_seconds=0.01)
    assert "attempts failed" in str(exc.value).lower()
