"""
guardian/data_layer.py
----------------------
Defines the baseline (normal-weather) state for the Pimpri-Chinchwad
digital twin.  Returns a fresh deep-copy each call so that crisis mutations
never bleed across simulation runs.

Assets modelled
---------------
- Hospitals          (name, lat, lon, power_status, capacity, status_indicator)
- Power substations  (name, lat, lon, load_percentage, status, status_indicator)
- Drainage/sluice gates (id, lat, lon, water_level_percentage, status, status_indicator)
- Emergency hubs     (name, lat, lon, available_units, status_indicator)
"""

import copy


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
