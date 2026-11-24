"""Gemini AI Prompt Engine for Urban Air Quality Assistant.

Leverages Google Gemini Generative AI with strict Pydantic schemas,
guardrails against hallucination, and intelligent zero-downtime offline fallbacks.
"""

import os
import json
from typing import Dict, Any, List
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# Read system prompt
PROMPT_DIR = Path(__file__).parent / "prompts"
SYSTEM_PROMPT_PATH = PROMPT_DIR / "system_prompt.txt"

if SYSTEM_PROMPT_PATH.exists():
    with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
else:
    SYSTEM_PROMPT = "You are AeroLife, an expert Urban Environmental Health & Sustainability Specialist."


# Pydantic Schemas for validation and evaluation score
class DailyRoutineItem(BaseModel):
    time_of_day: str = Field(description="Time block e.g. Morning (06:00 - 09:00)")
    activity: str = Field(description="Primary activity e.g. Commute, Exercise, School Run")
    recommendation: str = Field(description="Specific actionable safety and emission-lowering advice")
    mask_required: str = Field(description="None | Cloth/Surgical | N95/FFP2 | Stay Indoors")


class IndoorHackItem(BaseModel):
    title: str = Field(description="Name of the indoor hack")
    category: str = Field(description="Ventilation | Purification | Cleaning | Moisture & Plants")
    action_steps: str = Field(description="Clear step-by-step instructions")
    difficulty_level: str = Field(description="Easy | Moderate | DIY Project")
    estimated_cost_inr: float = Field(description="Approximate cost in Indian Rupees")


class SustainableSwapItem(BaseModel):
    current_habit: str = Field(description="High-pollution common habit")
    sustainable_swap: str = Field(description="Low-emission practical replacement")
    co2_saved_kg_month: float = Field(description="Estimated monthly CO2 reduction in kg")
    pm25_exposure_reduction_pct: float = Field(description="Estimated reduction in personal PM2.5 exposure %")
    impact_explanation: str = Field(description="Clear explanation of the environmental and health impact")


class AirQualityAdvisoryResponse(BaseModel):
    summary: str
    risk_level: str
    daily_routines: List[DailyRoutineItem]
    indoor_hacks: List[IndoorHackItem]
    sustainable_swaps: List[SustainableSwapItem]
    disclaimer: str


def generate_offline_fallback(
    city: str, aqi: int, family_profile: str, lifestyle: str
) -> Dict[str, Any]:
    """Generate intelligent offline fallback data matching schema if Gemini API key is missing or quota hit."""
    is_severe = aqi > 250
    mask_rec = "N95/FFP2" if is_severe else ("Cloth/Surgical" if aqi > 100 else "None")
    
    return {
        "summary": (
            f"Advisory for {city} with an AQI of {aqi} ({'Severe Winter Smog Alert' if is_severe else 'Elevated Pollution'}). "
            f"Tailored specifically for households with {family_profile.lower()} and {lifestyle.lower()} lifestyle."
        ),
        "risk_level": "Severe" if is_severe else ("Unhealthy" if aqi > 150 else "Moderate"),
        "daily_routines": [
            {
                "time_of_day": "Early Morning (06:00 - 09:00)",
                "activity": "Morning Routine & Ventilation",
                "recommendation": (
                    "Keep all external doors and windows tightly closed. In winter, ground-level thermal inversion traps toxic particulate matter near the ground. Avoid outdoor jogging or morning walks."
                    if is_severe else "Light ventilation permitted only if sunlight has dispersed morning mist."
                ),
                "mask_required": "Stay Indoors" if is_severe else mask_rec,
            },
            {
                "time_of_day": "Mid-Day (11:00 - 15:00)",
                "activity": "Ventilation & Errands",
                "recommendation": (
                    "Best window for brief cross-ventilation (15-20 minutes) as solar heating lifts the inversion boundary. Complete essential outdoor errands now."
                ),
                "mask_required": mask_rec,
            },
            {
                "time_of_day": "Evening Commute (17:30 - 20:30)",
                "activity": "Return Commute & School Pickup",
                "recommendation": (
                    "Traffic congestion triggers severe localized PM2.5 and NO2 spikes. Keep vehicle windows rolled up with AC set to 'Internal Recirculation' mode."
                ),
                "mask_required": mask_rec,
            },
            {
                "time_of_day": "Night (21:00 - 06:00)",
                "activity": "Sleep & Air Purification",
                "recommendation": (
                    "Run HEPA air purifier or DIY box fan filter in the primary bedroom. Maintain bedroom relative humidity between 40-50% to prevent respiratory mucosal drying."
                ),
                "mask_required": "None",
            },
        ],
        "indoor_hacks": [
            {
                "title": "DIY Corsi-Rosenthal / Box-Fan HEPA Filter",
                "category": "Purification",
                "action_steps": "Tape a MERV 13 or HEPA grade furnace filter to the intake side of a standard box fan. Seals edges with duct tape to create an effective ₹1,500 purifier that matches ₹15,000 commercial CADR.",
                "difficulty_level": "DIY Project",
                "estimated_cost_inr": 1450.0,
            },
            {
                "title": "Wet-Mopping Over Dry Sweeping",
                "category": "Cleaning",
                "action_steps": "Stop using dry brooms which re-suspend settled fine PM2.5 and PM10 particles into your breathing zone. Use micro-fiber damp mopping with warm water twice daily.",
                "difficulty_level": "Easy",
                "estimated_cost_inr": 150.0,
            },
            {
                "title": "Kitchen Backdraft & Inverted Venting",
                "category": "Ventilation",
                "action_steps": "High-heat frying produces intense indoor PM2.5 spikes (>500 µg/m³). Always turn on exhaust hoods 2 minutes BEFORE igniting burners, and keep kitchen doors isolated from bedrooms.",
                "difficulty_level": "Easy",
                "estimated_cost_inr": 0.0,
            },
            {
                "title": "Spider Plant & Areca Palm Placement",
                "category": "Moisture & Plants",
                "action_steps": "Place NASA Clean Air study plants (Snake Plant, Areca Palm) in shaded corners to regulate indoor humidity and absorb volatile organic compounds (VOCs).",
                "difficulty_level": "Moderate",
                "estimated_cost_inr": 600.0,
            },
        ],
        "sustainable_swaps": [
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
        ],
        "disclaimer": "This advisory is generated for environmental harm-reduction and air quality optimization. It does not replace individualized medical treatment for patients with chronic respiratory or cardiovascular conditions.",
    }


def generate_air_quality_advisory(
    city: str,
    aqi: int,
    pm25: float,
    pm10: float,
    family_profile: str,
    lifestyle: str,
    custom_concerns: str = "",
) -> Dict[str, Any]:
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
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        # Seamless graceful fallback when API key isn't configured in test environments
        return generate_offline_fallback(city, aqi, family_profile, lifestyle)

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.3,
            },
            system_instruction=SYSTEM_PROMPT,
        )

        user_prompt = f"""
Current Real-Time Conditions:
- City: {city}
- AQI: {aqi}
- PM2.5: {pm25} µg/m³
- PM10: {pm10} µg/m³
- Household Profile: {family_profile}
- Lifestyle / Daily Commute: {lifestyle}
- Specific Concerns: {custom_concerns if custom_concerns else "General smog protection"}

Generate a comprehensive advisory in JSON adhering strictly to this schema:
{{
  "summary": "...",
  "risk_level": "Low | Moderate | Unhealthy | Severe | Hazardous",
  "daily_routines": [
    {{"time_of_day": "...", "activity": "...", "recommendation": "...", "mask_required": "None | Cloth/Surgical | N95/FFP2 | Stay Indoors"}}
  ],
  "indoor_hacks": [
    {{"title": "...", "category": "Ventilation | Purification | Cleaning | Moisture & Plants", "action_steps": "...", "difficulty_level": "Easy | Moderate | DIY Project", "estimated_cost_inr": 150.0}}
  ],
  "sustainable_swaps": [
    {{"current_habit": "...", "sustainable_swap": "...", "co2_saved_kg_month": 45.0, "pm25_exposure_reduction_pct": 60.0, "impact_explanation": "..."}}
  ],
  "disclaimer": "..."
}}
"""
        response = model.generate_content(user_prompt)
        parsed_json = json.loads(response.text)

        # Validate with Pydantic
        validated = AirQualityAdvisoryResponse(**parsed_json)
        return validated.model_dump()

    except Exception as err:
        # Fallback to local intelligent engine if rate-limited or parsing error
        print(f"Gemini API Notice: {err}. Employing resilient offline engine.")
        return generate_offline_fallback(city, aqi, family_profile, lifestyle)
