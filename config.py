"""Application Configuration and Constants for AeroLife."""

from typing import Dict, Any

APP_NAME = "AeroLife"
APP_VERSION = "2.1.0"
CACHE_TTL_SECONDS = 600  # 10 minutes cache for real-time sensor and advisory calls

# Open-Meteo API Endpoints
OPEN_METEO_AQI_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
OPEN_METEO_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"

# CPCB & WHO Standard AQI Thresholds
AQI_THRESHOLDS = {
    "GOOD": 50,
    "SATISFACTORY": 100,
    "MODERATE": 200,
    "POOR": 300,
    "VERY_POOR": 400,
}

# Default City Geocodes and Winter Benchmarks
DEFAULT_CITIES: Dict[str, Dict[str, Any]] = {
    "Delhi": {
        "lat": 28.6139,
        "lon": 77.2090,
        "base_aqi": 385,
        "pm25": 240.5,
        "pm10": 390.0,
        "primary_pollutant": "PM2.5",
        "condition": "Severe Winter Smog",
    },
    "Hyderabad": {
        "lat": 17.3850,
        "lon": 78.4867,
        "base_aqi": 142,
        "pm25": 58.2,
        "pm10": 115.0,
        "primary_pollutant": "PM2.5",
        "condition": "Moderate Haze",
    },
    "Mumbai": {
        "lat": 19.0760,
        "lon": 72.8777,
        "base_aqi": 168,
        "pm25": 82.4,
        "pm10": 145.0,
        "primary_pollutant": "PM10",
        "condition": "Unhealthy for Sensitive Groups",
    },
    "Bengaluru": {
        "lat": 12.9716,
        "lon": 77.5946,
        "base_aqi": 75,
        "pm25": 24.1,
        "pm10": 62.0,
        "primary_pollutant": "PM10",
        "condition": "Moderate",
    },
    "Kolkata": {
        "lat": 22.5726,
        "lon": 88.3639,
        "base_aqi": 265,
        "pm25": 165.0,
        "pm10": 240.0,
        "primary_pollutant": "PM2.5",
        "condition": "Very Poor",
    },
    "Chennai": {
        "lat": 13.0827,
        "lon": 80.2707,
        "base_aqi": 95,
        "pm25": 33.0,
        "pm10": 74.0,
        "primary_pollutant": "PM2.5",
        "condition": "Satisfactory",
    },
}
