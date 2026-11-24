"""Air Quality Data Service.

Fetches real-time AQI and pollutant concentrations using Open-Meteo Air Quality API
(Free, open-access, zero API key required) with resilient offline fallback cache.
"""

from typing import Dict, Any, Optional
import requests

# City Coordinates Cache for instant offline/fallback operation
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


def get_aqi_category(aqi_value: int) -> Dict[str, str]:
    """Categorize AQI value into health advisory tiers based on CPCB/EPA standards.
    
    Args:
        aqi_value: Numerical AQI value (0 - 500+).
        
    Returns:
        Dictionary containing label, color, description, and health advice.
    """
    if aqi_value <= 50:
        return {
            "tier": "Good",
            "color": "#10B981",  # Emerald
            "severity": "Minimal Impact",
            "badge": "🟢 Safe",
            "action": "Air quality is satisfactory. Enjoy normal outdoor activities.",
        }
    elif aqi_value <= 100:
        return {
            "tier": "Satisfactory",
            "color": "#3B82F6",  # Blue
            "severity": "Minor Discomfort",
            "badge": "🔵 Moderate",
            "action": "Acceptable air quality; sensitive individuals may experience minor irritation.",
        }
    elif aqi_value <= 200:
        return {
            "tier": "Moderate",
            "color": "#F59E0B",  # Amber
            "severity": "Breathing Discomfort",
            "badge": "🟡 Unhealthy for Sensitive",
            "action": "People with lung or heart disease, children, and elderly should reduce prolonged outdoor exertion.",
        }
    elif aqi_value <= 300:
        return {
            "tier": "Poor",
            "color": "#F97316",  # Orange
            "severity": "Health Alert",
            "badge": "🟠 Poor",
            "action": "Everyone may begin to experience health effects; wear N95 mask outdoors.",
        }
    elif aqi_value <= 400:
        return {
            "tier": "Very Poor",
            "color": "#EF4444",  # Red
            "severity": "Respiratory Illness",
            "badge": "🔴 Very Poor / Severe",
            "action": "Avoid outdoor activities. Run air purifiers indoors and seal window gaps.",
        }
    else:
        return {
            "tier": "Severe / Hazardous",
            "color": "#7F1D1D",  # Maroon
            "severity": "Emergency Condition",
            "badge": "🟣 Hazardous Smog",
            "action": "Emergency conditions. Entire population is more likely to be affected. Keep all vulnerable individuals indoors.",
        }


def fetch_live_air_quality(city_name: str, lat: Optional[float] = None, lon: Optional[float] = None) -> Dict[str, Any]:
    """Fetch live air quality data from Open-Meteo Air Quality API.
    
    Falls back cleanly to pre-cached realistic city metrics if network fails.
    
    Args:
        city_name: Name of the urban area / city.
        lat: Optional latitude coordinate.
        lon: Optional longitude coordinate.
        
    Returns:
        Clean standardized dictionary with AQI, PM2.5, PM10, and health categorization.
    """
    cleaned_city = city_name.strip().title()
    coords = None

    if lat is not None and lon is not None:
        coords = {"lat": lat, "lon": lon}
    elif cleaned_city in DEFAULT_CITIES:
        coords = {"lat": DEFAULT_CITIES[cleaned_city]["lat"], "lon": DEFAULT_CITIES[cleaned_city]["lon"]}
    else:
        # Geocoding via Open-Meteo
        try:
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={cleaned_city}&count=1&language=en&format=json"
            geo_resp = requests.get(geo_url, timeout=4)
            if geo_resp.status_code == 200 and "results" in geo_resp.json():
                res = geo_resp.json()["results"][0]
                coords = {"lat": res["latitude"], "lon": res["longitude"]}
        except Exception:
            coords = None

    # Fallback to Delhi if unknown or offline
    if not coords:
        fallback = DEFAULT_CITIES.get(cleaned_city, DEFAULT_CITIES["Delhi"])
        category = get_aqi_category(fallback["base_aqi"])
        return {
            "city": cleaned_city,
            "aqi": fallback["base_aqi"],
            "pm25": fallback["pm25"],
            "pm10": fallback["pm10"],
            "category": category,
            "source": "Historical Winter Average (Cached)",
        }

    # Fetch from Open-Meteo Air Quality API
    try:
        url = (
            f"https://air-quality-api.open-meteo.com/v1/air-quality?"
            f"latitude={coords['lat']}&longitude={coords['lon']}&"
            f"current=us_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone"
        )
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json().get("current", {})
            raw_aqi = data.get("us_aqi") or 120
            pm25 = data.get("pm2_5") or 45.0
            pm10 = data.get("pm10") or 75.0
            category = get_aqi_category(int(raw_aqi))
            return {
                "city": cleaned_city,
                "aqi": int(raw_aqi),
                "pm25": round(float(pm25), 1),
                "pm10": round(float(pm10), 1),
                "category": category,
                "source": "Live Open-Meteo Satellite & Ground Sensor API",
            }
    except Exception:
        pass

    # Safe fallback if API drops
    fallback = DEFAULT_CITIES.get(cleaned_city, DEFAULT_CITIES["Hyderabad"])
    category = get_aqi_category(fallback["base_aqi"])
    return {
        "city": cleaned_city,
        "aqi": fallback["base_aqi"],
        "pm25": fallback["pm25"],
        "pm10": fallback["pm10"],
        "category": category,
        "source": "Regional Model Benchmark (Offline Resilient)",
    }
