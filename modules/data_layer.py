"""
modules/data_layer.py
----------------------
Defines the baseline (normal-weather) state for a digital twin city.  Returns a fresh deep-copy each call so that crisis mutations
never bleed across simulation runs.

Assets modelled
---------------
- Hospitals          (name, lat, lon, power_status, capacity, status_indicator)
- Power substations  (name, lat, lon, load_percentage, status, status_indicator)
- Drainage/sluice gates (id, lat, lon, water_level_percentage, status, status_indicator)
- Emergency hubs     (name, lat, lon, available_units, status_indicator)
"""

import copy


_BASELINE_CENTER = (18.6200, 73.7950)


# Baseline city state – edit coordinates / names here to update the twin
_BASELINE: dict = {
    "hospitals": [
        {
            "name": "YCM Hospital (Yashwantrao Chavan Memorial)",
            "lat": 18.6218,
            "lon": 73.8184,
            "power_status": "Grid Power (Normal)",
            "capacity": "65%",
            "status_indicator": "NORMAL",
        },
        {
            "name": "Aditya Birla Memorial Hospital",
            "lat": 18.6249,
            "lon": 73.7715,
            "power_status": "Grid Power (Normal)",
            "capacity": "45%",
            "status_indicator": "NORMAL",
        },
    ],
    "power_substations": [
        {
            "name": "Pimpri MSEDCL Substation Alpha",
            "lat": 18.6180,
            "lon": 73.8010,
            "load_percentage": 62,
            "status": "Operational",
            "status_indicator": "NORMAL",
        },
        {
            "name": "Chinchwad Power Grid Zone Beta",
            "lat": 18.6405,
            "lon": 73.7959,
            "load_percentage": 55,
            "status": "Operational",
            "status_indicator": "NORMAL",
        },
    ],
    "drainage_gates": [
        {
            "id": "Pavana River Flood Gate 1",
            "lat": 18.6262,
            "lon": 73.7637,
            "water_level_percentage": 24,
            "status": "Open (Normal Discharge)",
            "status_indicator": "NORMAL",
        },
        {
            "id": "Pavana River Flood Gate 2",
            "lat": 18.6030,
            "lon": 73.8024,
            "water_level_percentage": 30,
            "status": "Closed (Retaining Flow)",
            "status_indicator": "NORMAL",
        },
    ],
    "emergency_hubs": [
        {
            "name": "Pimpri Fire Station & Rescue Depot",
            "lat": 18.6200,
            "lon": 73.8180,
            "available_units": 18,
            "status_indicator": "NORMAL",
        },
        {
            "name": "Thergaon Ambulance Depot",
            "lat": 18.6080,
            "lon": 73.7820,
            "available_units": 25,
            "status_indicator": "NORMAL",
        },
    ],
}


def get_initial_city_state() -> dict:
    """Return a deep copy of the baseline city state dictionary."""
    return copy.deepcopy(_BASELINE)


def relocate_city_state(
    city_state: dict,
    latitude: float,
    longitude: float,
    city_name: str = "Selected City",
) -> dict:
    """
    Move all mock infrastructure assets around a new city centre while
    preserving their original relative layout and applying selected-city
    names to the simulated infrastructure.
    """
    lat_offset = latitude - _BASELINE_CENTER[0]
    lon_offset = longitude - _BASELINE_CENTER[1]

    for asset_group in city_state.values():
        for asset in asset_group:
            asset["lat"] = float(asset["lat"]) + lat_offset
            asset["lon"] = float(asset["lon"]) + lon_offset

    locality = city_name.split(",", 1)[0].strip() or "City"
    city_state["hospitals"][0]["name"] = f"{locality} Central General Hospital"
    city_state["hospitals"][1]["name"] = f"{locality} North Medical Center"
    city_state["power_substations"][0]["name"] = f"{locality} Grid Substation Alpha"
    city_state["power_substations"][1]["name"] = f"{locality} Grid Substation Beta"
    city_state["drainage_gates"][0]["id"] = f"{locality} Flood Gate 1"
    city_state["drainage_gates"][1]["id"] = f"{locality} Flood Gate 2"
    city_state["emergency_hubs"][0]["name"] = f"{locality} Fire & Rescue Command"
    city_state["emergency_hubs"][1]["name"] = f"{locality} Ambulance Response Depot"

    return city_state
