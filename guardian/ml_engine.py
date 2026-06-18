"""
City-specific Scikit-Learn risk engine backed by real Open-Meteo history.

For each selected city, the engine downloads one year of hourly historical
weather observations and trains a cached RandomForestClassifier. No synthetic
weather rows are generated.

Open-Meteo provides weather observations, not verified disaster outcomes.
Consequently, the target classes are transparent weather-risk archetypes
derived from each city's own historical percentiles:

0 -> Normal / lower-risk weather pattern
1 -> Flood / severe-storm weather pattern
2 -> Heatwave / wildfire weather pattern
"""

from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

from guardian.weather_service import (
    ARCHIVE_URL,
    WeatherServiceError,
    get_open_meteo_json,
)


_FEATURE_COLS = [
    "temperature",
    "humidity",
    "wind_speed",
    "pressure",
    "precipitation",
]
_LABEL_NAMES = {
    0: "Normal / Clear Weather",
    1: "Flash Flood / Severe Storm Risk",
    2: "Severe Heatwave / Wildfire Risk",
}


@dataclass
class _CityModel:
    model: RandomForestClassifier
    scaler: StandardScaler
    sample_count: int
    start_date: str
    end_date: str


# Returns a one-year window ending six days ago for archive availability
def _historical_dates() -> tuple[str, str]:
    end = date.today() - timedelta(days=6)
    start = end - timedelta(days=365)
    return start.isoformat(), end.isoformat()


def _fetch_historical_dataset(latitude: float, longitude: float) -> pd.DataFrame:
    start_date, end_date = _historical_dates()
    payload = get_open_meteo_json(
        ARCHIVE_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": (
                "temperature_2m,relative_humidity_2m,wind_speed_10m,"
                "surface_pressure,precipitation"
            ),
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
            "timezone": "auto",
        },
    )
    hourly = payload.get("hourly") or {}
    source_columns = {
        "temperature": "temperature_2m",
        "humidity": "relative_humidity_2m",
        "wind_speed": "wind_speed_10m",
        "pressure": "surface_pressure",
        "precipitation": "precipitation",
    }

    if not all(source in hourly for source in source_columns.values()):
        raise WeatherServiceError(
            "Open-Meteo returned incomplete historical weather data."
        )

    frame = pd.DataFrame(
        {
            target: hourly[source]
            for target, source in source_columns.items()
        }
    )
    frame = frame.apply(pd.to_numeric, errors="coerce").dropna()
    if len(frame) < 500:
        raise WeatherServiceError(
            "Not enough historical observations were available to train "
            "the city-specific model."
        )
    return frame


def _derive_risk_labels(frame: pd.DataFrame) -> pd.Series:
    """
    Derive relative weather-risk classes from real observations.

    Percentile ranks make the classifier adapt to the selected city's climate.
    """
    ranks = frame.rank(pct=True)
    flood_score = (
        0.45 * ranks["precipitation"]
        + 0.20 * ranks["humidity"]
        + 0.20 * ranks["wind_speed"]
        + 0.15 * (1.0 - ranks["pressure"])
    )
    heat_score = (
        0.55 * ranks["temperature"]
        + 0.30 * (1.0 - ranks["humidity"])
        + 0.15 * ranks["wind_speed"]
    )

    labels = pd.Series(0, index=frame.index, dtype=int)
    flood_mask = flood_score >= flood_score.quantile(0.90)
    heat_mask = (heat_score >= heat_score.quantile(0.90)) & ~flood_mask
    labels.loc[flood_mask] = 1
    labels.loc[heat_mask] = 2
    return labels


@lru_cache(maxsize=32)
def _train_city_model(latitude: float, longitude: float) -> _CityModel:
    """Train once per coordinate pair and reuse the model on Streamlit reruns."""
    frame = _fetch_historical_dataset(latitude, longitude)
    labels = _derive_risk_labels(frame)

    scaler = StandardScaler()
    features = scaler.fit_transform(frame[_FEATURE_COLS].values)
    model = RandomForestClassifier(
        n_estimators=160,
        max_depth=10,
        min_samples_leaf=3,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )
    model.fit(features, labels.values)
    start_date, end_date = _historical_dates()
    return _CityModel(model, scaler, len(frame), start_date, end_date)


def _coordinate_key(value: float) -> float:
    """Limit cache fragmentation while retaining roughly street-level precision."""
    return round(float(value), 4)


def predict_risk(
    temp: float,
    humidity: float,
    wind_speed: float,
    pressure: float,
    precipitation: float,
    latitude: float,
    longitude: float,
) -> tuple[int, list[float], str]:
    """Predict risk using a model trained from the selected city's history."""
    bundle = _train_city_model(
        _coordinate_key(latitude),
        _coordinate_key(longitude),
    )
    observation = np.array(
        [[temp, humidity, wind_speed, pressure, precipitation]],
        dtype=float,
    )
    scaled = bundle.scaler.transform(observation)
    label = int(bundle.model.predict(scaled)[0])

    # Keep the public probability contract fixed at labels [0, 1, 2].
    probabilities = [0.0, 0.0, 0.0]
    for model_class, probability in zip(
        bundle.model.classes_,
        bundle.model.predict_proba(scaled)[0],
    ):
        probabilities[int(model_class)] = float(probability)

    return label, probabilities, _LABEL_NAMES[label]


def get_feature_importances(
    latitude: float,
    longitude: float,
) -> dict[str, float]:
    """Return feature importances for the selected city's trained model."""
    bundle = _train_city_model(
        _coordinate_key(latitude),
        _coordinate_key(longitude),
    )
    return dict(zip(_FEATURE_COLS, bundle.model.feature_importances_.tolist()))


def get_model_summary(latitude: float, longitude: float) -> dict[str, object]:
    """Return provenance details for display in the dashboard."""
    bundle = _train_city_model(
        _coordinate_key(latitude),
        _coordinate_key(longitude),
    )
    return {
        "sample_count": bundle.sample_count,
        "start_date": bundle.start_date,
        "end_date": bundle.end_date,
    }
