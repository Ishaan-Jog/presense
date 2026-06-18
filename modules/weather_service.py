"""
modules/weather_service.py
----------------------
Open-Meteo integration for city geocoding and live weather telemetry.

Both endpoints are free and do not require an API key.
"""

from dataclasses import dataclass

import requests


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


class WeatherServiceError(RuntimeError):
    """Raised when a city or its current weather cannot be resolved."""


@dataclass(frozen=True)
class LiveWeather:
    city_name: str
    latitude: float
    longitude: float
    temperature: float
    humidity: float
    wind_speed: float
    pressure: float
    precipitation: float
    snowfall: float
    snow_depth: float
    soil_moisture: float


def get_open_meteo_json(url: str, params: dict) -> dict:
    """Request and decode an Open-Meteo JSON response."""
    try:
        response = requests.get(url, params=params, timeout=12)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise WeatherServiceError(
            "Unable to contact Open-Meteo. Check your internet connection and try again."
        ) from exc
    except ValueError as exc:
        raise WeatherServiceError("Open-Meteo returned an invalid response.") from exc


def fetch_live_weather(city_name: str) -> LiveWeather:
    """Resolve *city_name* and return its current Open-Meteo observations."""
    query = city_name.strip()
    if not query:
        raise WeatherServiceError("Please enter a city name.")

    geo_data = get_open_meteo_json(
        GEOCODING_URL,
        {
            "name": query,
            "count": 1,
            "language": "en",
            "format": "json",
        },
    )
    results = geo_data.get("results") or []
    if not results:
        raise WeatherServiceError(
            f'No city named "{query}" was found. Try adding the state or country.'
        )

    place = results[0]
    latitude = float(place["latitude"])
    longitude = float(place["longitude"])
    display_parts = [
        place.get("name"),
        place.get("admin1"),
        place.get("country"),
    ]
    resolved_name = ", ".join(part for part in display_parts if part)

    weather_data = get_open_meteo_json(
        FORECAST_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,relative_humidity_2m,wind_speed_10m,"
                "surface_pressure,precipitation,snowfall,snow_depth,"
                "soil_moisture_0_to_1cm"
            ),
            "wind_speed_unit": "kmh",
            "timezone": "auto",
        },
    )
    current = weather_data.get("current")
    if not current:
        raise WeatherServiceError(
            f"Current weather is unavailable for {resolved_name or query}."
        )

    required = {
        "temperature_2m",
        "relative_humidity_2m",
        "wind_speed_10m",
        "surface_pressure",
    }
    if not required.issubset(current):
        raise WeatherServiceError("Open-Meteo returned incomplete weather telemetry.")

    return LiveWeather(
        city_name=resolved_name or query,
        latitude=latitude,
        longitude=longitude,
        temperature=float(current["temperature_2m"]),
        humidity=float(current["relative_humidity_2m"]),
        wind_speed=float(current["wind_speed_10m"]),
        pressure=float(current["surface_pressure"]),
        precipitation=float(current.get("precipitation", 0.0) or 0.0),
        snowfall=float(current.get("snowfall", 0.0) or 0.0),
        snow_depth=float(current.get("snow_depth", 0.0) or 0.0),
        soil_moisture=float(
            current.get("soil_moisture_0_to_1cm", 0.0) or 0.0
        ),
    )
