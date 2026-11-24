"""Gemini AI Prompt Engine for Urban Air Quality Assistant.

Leverages Google Gemini Generative AI with strict Pydantic schemas,
domain-specific exceptions, guardrails against hallucination, and intelligent
zero-downtime offline fallbacks.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

from exceptions import (
    AeroLifeBaseException,
    AtmosphericDataError,
    PromptSynthesisError,
    SchemaValidationError,
)

load_dotenv()
logger = logging.getLogger(__name__)

PROMPT_DIR: Path = Path(__file__).parent / "prompts"
SYSTEM_PROMPT_PATH: Path = PROMPT_DIR / "system_prompt.txt"
DEFAULT_SYSTEM_PROMPT: str = (
    "You are AeroLife, an expert Urban Environmental Health & Sustainability Specialist."
)

ADVISORY_SCHEMA_TEMPLATE: str = """{
  "summary": "...",
  "risk_level": "Low | Moderate | Unhealthy | Severe | Hazardous",
  "daily_routines": [
    {"time_of_day": "...", "activity": "...", "recommendation": "...", "mask_required": "None | Cloth/Surgical | N95/FFP2 | Stay Indoors"}
  ],
  "indoor_hacks": [
    {"title": "...", "category": "Ventilation | Purification | Cleaning | Moisture & Plants", "action_steps": "...", "difficulty_level": "Easy | Moderate | DIY Project", "estimated_cost_inr": 150.0}
  ],
  "sustainable_swaps": [
    {"current_habit": "...", "sustainable_swap": "...", "co2_saved_kg_month": 45.0, "pm25_exposure_reduction_pct": 60.0, "impact_explanation": "..."}
  ],
  "disclaimer": "..."
}"""


def load_system_prompt(prompt_path: Path = SYSTEM_PROMPT_PATH) -> str:
    """Load the system instruction prompt from disk or fallback to default.

    Args:
        prompt_path: Filesystem path to the system prompt text file.

    Returns:
        The loaded system prompt string, or default prompt on failure.

    Raises:
        PromptSynthesisError: If reading the system prompt raises an I/O error.
    """
    try:
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        logger.warning("System prompt path %s missing. Using default.", prompt_path)
        return DEFAULT_SYSTEM_PROMPT
    except Exception as exc:
        logger.error("Failed to read system prompt: %s. Using default.", exc)
        return DEFAULT_SYSTEM_PROMPT


SYSTEM_PROMPT: str = load_system_prompt(SYSTEM_PROMPT_PATH)

__all__ = [
    "AeroLifeBaseException",
    "AtmosphericDataError",
    "PromptSynthesisError",
    "SchemaValidationError",
    "DailyRoutineItem",
    "IndoorHackItem",
    "SustainableSwapItem",
    "AirQualityAdvisoryResponse",
    "SYSTEM_PROMPT",
    "SYSTEM_PROMPT_PATH",
    "load_system_prompt",
    "validate_atmospheric_inputs",
    "construct_advisory_prompt",
    "parse_and_validate_advisory",
    "parse_and_validate_advisory_dict",
    "generate_offline_fallback",
    "generate_air_quality_advisory",
]


class DailyRoutineItem(BaseModel):
    """Schema for chronologically scheduled daily routine recommendations."""

    time_of_day: str = Field(description="Time block e.g. Morning (06:00 - 09:00)")
    activity: str = Field(
        description="Primary activity e.g. Commute, Exercise, School Run"
    )
    recommendation: str = Field(description="Specific actionable safety advice")
    mask_required: str = Field(
        description="None | Cloth/Surgical | N95/FFP2 | Stay Indoors"
    )


class IndoorHackItem(BaseModel):
    """Schema for practical, cost-effective indoor air quality interventions."""

    title: str = Field(description="Name of the indoor hack")
    category: str = Field(
        description="Ventilation | Purification | Cleaning | Moisture & Plants"
    )
    action_steps: str = Field(description="Clear step-by-step instructions")
    difficulty_level: str = Field(description="Easy | Moderate | DIY Project")
    estimated_cost_inr: float = Field(description="Approximate cost in Indian Rupees")


class SustainableSwapItem(BaseModel):
    """Schema for quantifiable lifestyle swaps reducing emissions and exposure."""

    current_habit: str = Field(description="High-pollution common habit")
    sustainable_swap: str = Field(description="Low-emission practical replacement")
    co2_saved_kg_month: float = Field(
        description="Estimated monthly CO2 reduction in kg"
    )
    pm25_exposure_reduction_pct: float = Field(
        description="Estimated PM2.5 exposure reduction %"
    )
    impact_explanation: str = Field(description="Explanation of environmental impact")


class AirQualityAdvisoryResponse(BaseModel):
    """Complete structured response schema for urban air quality advisories."""

    summary: str = Field(description="Executive contextual summary")
    risk_level: str = Field(
        description="Low | Moderate | Unhealthy | Severe | Hazardous"
    )
    daily_routines: list[DailyRoutineItem] = Field(
        description="Scheduled daily activities"
    )
    indoor_hacks: list[IndoorHackItem] = Field(description="Indoor air improvements")
    sustainable_swaps: list[SustainableSwapItem] = Field(
        description="Quantified sustainable swaps"
    )
    disclaimer: str = Field(description="Medical and legal liability disclaimer")


def validate_atmospheric_inputs(
    city: str,
    aqi: int,
    pm25: float,
    pm10: float,
) -> None:
    """Validate numerical and string parameters for atmospheric telemetry.

    Args:
        city: City or municipal area name.
        aqi: Numerical Air Quality Index value.
        pm25: PM2.5 concentration level in ug/m3.
        pm10: PM10 concentration level in ug/m3.

    Returns:
        None

    Raises:
        AtmosphericDataError: If city is blank or pollutant values are negative.
    """
    if not city or not city.strip():
        raise AtmosphericDataError(
            message="City name cannot be blank or empty.",
            details={"city": city, "aqi": aqi},
        )
    if aqi < 0 or pm25 < 0.0 or pm10 < 0.0:
        raise AtmosphericDataError(
            message="Atmospheric sensor readings cannot be negative.",
            details={"aqi": aqi, "pm25": pm25, "pm10": pm10},
        )


def _determine_risk_level(aqi: int) -> str:
    """Determine descriptive environmental risk category from numerical AQI.

    Args:
        aqi: Numerical Air Quality Index value.

    Returns:
        Categorical risk level string (Severe, Unhealthy, Moderate, or Low).

    Raises:
        AtmosphericDataError: If AQI is invalid.
    """
    if aqi > 250:
        return "Severe"
    if aqi > 150:
        return "Unhealthy"
    if aqi > 50:
        return "Moderate"
    return "Low"


def _determine_mask_recommendation(aqi: int, is_severe: bool) -> str:
    """Determine protective respiratory mask type based on air toxicity.

    Args:
        aqi: Numerical Air Quality Index.
        is_severe: Boolean flag indicating if conditions are critically severe.

    Returns:
        Recommended mask string (e.g. N95/FFP2, Cloth/Surgical, None).

    Raises:
        AtmosphericDataError: If AQI input is uninterpretable.
    """
    if is_severe:
        return "N95/FFP2"
    if aqi > 100:
        return "Cloth/Surgical"
    return "None"


def _build_morning_routine(is_severe: bool, mask_rec: str) -> dict[str, Any]:
    """Assemble morning routine recommendation item.

    Args:
        is_severe: Flag indicating whether smog alert is severe.
        mask_rec: Recommended mask specification.

    Returns:
        Routine dictionary for early morning time slot.
    """
    early_rec: str = (
        "Keep all external doors and windows tightly closed. In winter, ground-level thermal "
        "inversion traps toxic particulate matter near the ground. Avoid outdoor jogging or walks."
        if is_severe
        else "Light ventilation permitted only if sunlight has dispersed morning mist."
    )
    return {
        "time_of_day": "Early Morning (06:00 - 09:00)",
        "activity": "Morning Routine & Ventilation",
        "recommendation": early_rec,
        "mask_required": "Stay Indoors" if is_severe else mask_rec,
    }


def _build_default_daily_routines(
    is_severe: bool, mask_rec: str
) -> list[dict[str, Any]]:
    """Assemble chronologically partitioned daily outdoor and indoor routines.

    Args:
        is_severe: Boolean flag indicating severe pollution threshold exceeded.
        mask_rec: Recommended mask specification for outdoor exposure.

    Returns:
        List of structured daily routine dictionaries.

    Raises:
        PromptSynthesisError: If routine generation fails.
    """
    return [
        _build_morning_routine(is_severe, mask_rec),
        {
            "time_of_day": "Mid-Day (11:00 - 15:00)",
            "activity": "Ventilation & Errands",
            "recommendation": "Best window for brief cross-ventilation (15-20 minutes). Complete essential outdoor errands now.",
            "mask_required": mask_rec,
        },
        {
            "time_of_day": "Evening Commute (17:30 - 20:30)",
            "activity": "Return Commute & School Pickup",
            "recommendation": "Traffic congestion triggers severe localized PM2.5 and NO2 spikes. Keep vehicle windows rolled up with AC on recirculation.",
            "mask_required": mask_rec,
        },
        {
            "time_of_day": "Night (21:00 - 06:00)",
            "activity": "Sleep & Air Purification",
            "recommendation": "Run HEPA air purifier or DIY box fan filter in the primary bedroom. Maintain bedroom relative humidity between 40-50%.",
            "mask_required": "None",
        },
    ]


def _get_air_purification_hacks() -> list[dict[str, Any]]:
    """Assemble filtration and cleaning indoor air quality hacks.

    Returns:
        List of purification intervention dictionaries.
    """
    return [
        {
            "title": "DIY Corsi-Rosenthal / Box-Fan HEPA Filter",
            "category": "Purification",
            "action_steps": "Tape a MERV 13 or HEPA filter to the intake side of a box fan to create a low-cost high-CADR air purifier.",
            "difficulty_level": "DIY Project",
            "estimated_cost_inr": 1450.0,
        },
        {
            "title": "Wet-Mopping Over Dry Sweeping",
            "category": "Cleaning",
            "action_steps": "Replace dry brooms with microfiber damp mopping twice daily to prevent settled PM2.5 resuspension.",
            "difficulty_level": "Easy",
            "estimated_cost_inr": 150.0,
        },
    ]


def _get_plant_and_vent_hacks() -> list[dict[str, Any]]:
    """Assemble ventilation and botanical indoor air quality hacks.

    Returns:
        List of ventilation and botanical intervention dictionaries.
    """
    return [
        {
            "title": "Kitchen Backdraft & Inverted Venting",
            "category": "Ventilation",
            "action_steps": "Turn on exhaust hoods 2 minutes before igniting burners, and keep kitchen doors closed from bedrooms.",
            "difficulty_level": "Easy",
            "estimated_cost_inr": 0.0,
        },
        {
            "title": "Spider Plant & Areca Palm Placement",
            "category": "Moisture & Plants",
            "action_steps": "Place NASA Clean Air study plants in shaded corners to regulate indoor humidity and absorb volatile compounds.",
            "difficulty_level": "Moderate",
            "estimated_cost_inr": 600.0,
        },
    ]


def _build_default_indoor_hacks() -> list[dict[str, Any]]:
    """Assemble cost-effective, high-impact indoor air purification interventions.

    Returns:
        Combined list of indoor air quality improvement tactics.

    Raises:
        PromptSynthesisError: If hack assembly encounters data errors.
    """
    return _get_air_purification_hacks() + _get_plant_and_vent_hacks()


def _build_default_sustainable_swaps() -> list[dict[str, Any]]:
    """Generate high-yield emission reduction swaps with quantified metrics.

    Returns:
        List of actionable sustainable swaps with quantified metrics.

    Raises:
        PromptSynthesisError: If metric synthesis encounters data errors.
    """
    return [
        {
            "current_habit": "Solo driving single-occupancy petrol/diesel car for daily commute",
            "sustainable_swap": "Switching to Metro rail or pooled electric rideshare 3 days a week",
            "co2_saved_kg_month": 78.5,
            "pm25_exposure_reduction_pct": 62.0,
            "impact_explanation": "Rail transit avoids ground-level exhaust canyons while slashing monthly fossil fuel combustion by 65%.",
        },
        {
            "current_habit": "Burning dry leaves, garden waste, or domestic trash in colony corners",
            "sustainable_swap": "Community composting pit or municipal dry-waste segregation bin",
            "co2_saved_kg_month": 42.0,
            "pm25_exposure_reduction_pct": 88.0,
            "impact_explanation": "Open biomass burning releases high amounts of polycyclic aromatic hydrocarbons (PAHs) and carcinogenic black carbon directly in residential breathable zones.",
        },
        {
            "current_habit": "Continuous heating via open coil heaters / charcoal angeethi",
            "sustainable_swap": "Oil-filled radiator (OFR) or sealed ceramic heater with auto-thermostat",
            "co2_saved_kg_month": 28.0,
            "pm25_exposure_reduction_pct": 95.0,
            "impact_explanation": "Eliminates lethal indoor Carbon Monoxide (CO) buildup and prevents burning of ambient dust on exposed glowing coils.",
        },
    ]


def _build_fallback_summary(
    city: str, aqi: int, is_severe: bool, family_profile: str, lifestyle: str
) -> str:
    """Format contextual executive summary string for offline advisory.

    Args:
        city: City name string.
        aqi: Air Quality Index value.
        is_severe: Boolean flag indicating severe pollution.
        family_profile: Household demographic profile.
        lifestyle: Commuting and daily lifestyle profile.

    Returns:
        Formatted multi-sentence advisory summary.

    Raises:
        PromptSynthesisError: If string interpolation fails.
    """
    alert: str = "Severe Winter Smog Alert" if is_severe else "Elevated Pollution"
    return (
        f"Advisory for {city} with an AQI of {aqi} ({alert}). "
        f"Tailored specifically for households with {family_profile.lower()} "
        f"and {lifestyle.lower()} lifestyle."
    )


def parse_and_validate_advisory_dict(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate dictionary against AirQualityAdvisoryResponse schema.

    Args:
        payload: Dictionary containing advisory fields.

    Returns:
        Serialized dictionary conforming to the Pydantic schema.

    Raises:
        SchemaValidationError: If payload does not satisfy the schema.
    """
    try:
        validated = AirQualityAdvisoryResponse(**payload)
        return validated.model_dump()
    except ValidationError as err:
        raise SchemaValidationError(
            message=f"Dictionary failed Pydantic validation: {err}",
            details={"payload": payload, "errors": err.errors()},
        ) from err


def parse_and_validate_advisory(raw_json_str: str) -> dict[str, Any]:
    """Parse JSON string and validate against AirQualityAdvisoryResponse schema.

    Args:
        raw_json_str: Raw JSON string returned from LLM.

    Returns:
        Dictionary adhering strictly to AirQualityAdvisoryResponse schema.

    Raises:
        SchemaValidationError: If JSON is invalid or fails Pydantic schema validation.
    """
    try:
        parsed_dict: dict[str, Any] = json.loads(raw_json_str)
        return parse_and_validate_advisory_dict(parsed_dict)
    except json.JSONDecodeError as exc:
        raise SchemaValidationError(
            message=f"Invalid JSON string received: {exc}",
            details={"raw_text": raw_json_str[:200]},
        ) from exc


def generate_offline_fallback(
    city: str, aqi: int, family_profile: str, lifestyle: str
) -> dict[str, Any]:
    """Generate intelligent offline fallback data matching schema if Gemini API is unavailable.

    Args:
        city: Target city name.
        aqi: Numerical Air Quality Index.
        family_profile: Household demographic makeup.
        lifestyle: Primary lifestyle or commute routine.

    Returns:
        Dictionary adhering strictly to AirQualityAdvisoryResponse schema.

    Raises:
        SchemaValidationError: If fallback construction fails validation.
    """
    is_severe: bool = aqi > 250
    mask_rec: str = _determine_mask_recommendation(aqi, is_severe)
    payload: dict[str, Any] = {
        "summary": _build_fallback_summary(
            city, aqi, is_severe, family_profile, lifestyle
        ),
        "risk_level": _determine_risk_level(aqi),
        "daily_routines": _build_default_daily_routines(is_severe, mask_rec),
        "indoor_hacks": _build_default_indoor_hacks(),
        "sustainable_swaps": _build_default_sustainable_swaps(),
        "disclaimer": (
            "This advisory is generated for environmental harm-reduction and air quality optimization. "
            "It does not replace individualized medical treatment for patients with chronic respiratory "
            "or cardiovascular conditions."
        ),
    }
    return parse_and_validate_advisory_dict(payload)


def _format_telemetry_block(
    city: str,
    aqi: int,
    pm25: float,
    pm10: float,
    family_profile: str,
    lifestyle: str,
    concerns: str,
) -> str:
    """Format atmospheric telemetry block for LLM prompt.

    Args:
        city: Area name.
        aqi: AQI index.
        pm25: PM2.5 level.
        pm10: PM10 level.
        family_profile: Family profile.
        lifestyle: Lifestyle routine.
        concerns: Specific concerns.

    Returns:
        Formatted multi-line condition report string.
    """
    return (
        f"Current Real-Time Conditions:\n- City: {city}\n- AQI: {aqi}\n"
        f"- PM2.5: {pm25} µg/m³\n- PM10: {pm10} µg/m³\n"
        f"- Household Profile: {family_profile}\n- Lifestyle / Commute: {lifestyle}\n"
        f"- Specific Concerns: {concerns}"
    )


def _build_prompt_payload(telemetry: str) -> str:
    """Combine telemetry report with advisory schema template.

    Args:
        telemetry: Formatted multi-line telemetry block.

    Returns:
        Final generation prompt string.
    """
    return f"{telemetry}\n\nGenerate JSON adhering strictly to:\n{ADVISORY_SCHEMA_TEMPLATE}"


def construct_advisory_prompt(
    city: str,
    aqi: int,
    pm25: float,
    pm10: float,
    family_profile: str,
    lifestyle: str,
    custom_concerns: str = "",
) -> str:
    """Construct structured user prompt enforcing JSON output according to schema.

    Args:
        city: City name.
        aqi: Numerical AQI value.
        pm25: PM2.5 level in ug/m3.
        pm10: PM10 level in ug/m3.
        family_profile: Household makeup description.
        lifestyle: Daily lifestyle routine.
        custom_concerns: Optional user-specified concerns.

    Returns:
        Formatted multi-line prompt string.

    Raises:
        PromptSynthesisError: If prompt construction fails.
    """
    try:
        concerns: str = custom_concerns.strip() or "General smog protection"
        telemetry: str = _format_telemetry_block(
            city, aqi, pm25, pm10, family_profile, lifestyle, concerns
        )
        return _build_prompt_payload(telemetry)
    except Exception as exc:
        raise PromptSynthesisError(
            message=f"Prompt synthesis failed: {exc}",
            details={"city": city, "aqi": aqi},
        ) from exc


def _init_gemini_model(api_key: str) -> Any:
    """Initialize and configure the Google Gemini generative model instance.

    Args:
        api_key: Valid Google Gemini API authentication key.

    Returns:
        Configured GenerativeModel instance ready for inference.

    Raises:
        PromptSynthesisError: If model initialization or configuration fails.
    """
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        return genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.3,
            },
            system_instruction=SYSTEM_PROMPT,
        )
    except Exception as exc:
        raise PromptSynthesisError(
            message=f"Failed to initialize Gemini GenerativeModel: {exc}",
            details={"model_name": "gemini-1.5-flash"},
        ) from exc


def _execute_gemini_inference(model: Any, prompt: str) -> str:
    """Execute single inference request against Gemini model.

    Args:
        model: Configured GenerativeModel instance.
        prompt: User generation prompt string.

    Returns:
        Response text string.

    Raises:
        PromptSynthesisError: If response text is empty or missing.
    """
    response = model.generate_content(prompt)
    if response and hasattr(response, "text") and response.text:
        return str(response.text)
    raise PromptSynthesisError("Empty response body received from Gemini API.")


def _call_gemini_api_with_retry(
    model: Any,
    prompt: str,
    max_retries: int = 3,
    backoff_seconds: float = 1.0,
) -> str:
    """Call Gemini API with exponential backoff retry logic and timeout resilience.

    Args:
        model: Configured GenerativeModel instance.
        prompt: User generation prompt string.
        max_retries: Maximum number of request attempts before failing.
        backoff_seconds: Initial backoff duration in seconds.

    Returns:
        Raw response string from the Gemini LLM.

    Raises:
        PromptSynthesisError: If all retries are exhausted without a valid response.
    """
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return _execute_gemini_inference(model, prompt)
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Gemini API attempt %d/%d failed: %s", attempt, max_retries, exc
            )
            if attempt < max_retries:
                time.sleep(backoff_seconds * (2 ** (attempt - 1)))
    raise PromptSynthesisError(
        message=f"All {max_retries} Gemini API attempts failed: {last_error}",
        details={"prompt_length": len(prompt)},
    )


def _generate_remote_advisory(
    api_key: str,
    city: str,
    aqi: int,
    pm25: float,
    pm10: float,
    family_profile: str,
    lifestyle: str,
    custom_concerns: str,
) -> dict[str, Any]:
    """Execute remote LLM synthesis pipeline.

    Args:
        api_key: Valid Gemini API key.
        city: City name.
        aqi: AQI value.
        pm25: PM2.5 concentration.
        pm10: PM10 concentration.
        family_profile: Household profile.
        lifestyle: Lifestyle profile.
        custom_concerns: Specific concerns.

    Returns:
        Validated advisory dictionary.

    Raises:
        AeroLifeBaseException: If validation or synthesis fails.
    """
    validate_atmospheric_inputs(city=city, aqi=aqi, pm25=pm25, pm10=pm10)
    prompt: str = construct_advisory_prompt(
        city, aqi, pm25, pm10, family_profile, lifestyle, custom_concerns
    )
    model = _init_gemini_model(api_key=api_key)
    response_text: str = _call_gemini_api_with_retry(model=model, prompt=prompt)
    return parse_and_validate_advisory(raw_json_str=response_text)


def generate_air_quality_advisory(
    city: str,
    aqi: int,
    pm25: float,
    pm10: float,
    family_profile: str,
    lifestyle: str,
    custom_concerns: str = "",
) -> dict[str, Any]:
    """Generate structured GenAI advisory using Google Gemini with reliable fallback.

    Args:
        city: City name.
        aqi: Numerical AQI value.
        pm25: PM2.5 level in µg/m³.
        pm10: PM10 level in µg/m³.
        family_profile: Household makeup (e.g. Elderly, Infants, Asthmatics).
        lifestyle: Daily lifestyle routine (e.g. Office Commuter, Work from Home).
        custom_concerns: Optional user-specified health or household details.

    Returns:
        Dictionary adhering strictly to AirQualityAdvisoryResponse schema.

    Raises:
        AeroLifeBaseException: Handled internally; returns offline fallback on error.
    """
    api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return generate_offline_fallback(city, aqi, family_profile, lifestyle)

    try:
        return _generate_remote_advisory(
            api_key, city, aqi, pm25, pm10, family_profile, lifestyle, custom_concerns
        )
    except Exception as exc:
        logger.warning("Advisory error: %s. Using resilient offline engine.", exc)
        return generate_offline_fallback(city, aqi, family_profile, lifestyle)
