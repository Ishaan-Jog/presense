"""
guardian/crisis_engine.py
--------------------------
Keyword-heuristic crisis parser.  Given a free-text scenario description,
detects crisis categories (flood, heat, power, accident) and mutates the
digital twin state accordingly, returning updated state, telemetry log
entries, and KPI metrics.

Public API
----------
update_city_state(scenario_text: str) -> tuple[dict, list[str], dict]
    Returns (mutated_state, html_log_entries, metrics_dict).
"""

import datetime
from guardian.data_layer import get_initial_city_state


# Keyword banks per crisis category
_FLOOD_KEYS    = {"flood", "rain", "storm", "water", "river", "sluice",
                  "gate", "overflow", "monsoon", "drown", "inundat"}
_HEAT_KEYS     = {"heat", "hot", "heatwave", "temperature", "summer",
                  "sun", "drought", "degrees", "48"}
_POWER_KEYS    = {"power", "blackout", "outage", "grid", "electricity",
                  "substation", "generator", "load", "offline"}
_ACCIDENT_KEYS = {"accident", "fire", "blast", "explosion", "leak",
                  "chemical", "industrial", "earthquake", "quake"}


def _detect(text: str, keywords: set[str]) -> bool:
    return any(k in text for k in keywords)


def _log(level: str, timestamp: str, message: str) -> str:
    """Build a styled HTML log entry string."""
    css_class = f"log-level-{level}"
    label = level.upper()
    return (
        f"<div class='log-entry {css_class}'>"
        f"<span class='log-time'>[{timestamp}]</span> "
        f"[{label}] {message}"
        f"</div>"
    )


def _log_info(timestamp: str, message: str) -> str:
    return (
        f"<div class='log-entry'>"
        f"<span class='log-time'>[{timestamp}]</span> "
        f"<span class='log-level-info'>[SYSTEM]</span> {message}"
        f"</div>"
    )


# Mutation helpers – each receives the mutable state dict and appends logs
def _apply_flood(state: dict, logs: list, ts: str, metrics: dict) -> None:
    state["drainage_gates"][0].update({
        "water_level_percentage": 95,
        "status": "CRITICAL OVERFLOW RISK", 
        "status_indicator": "CRITICAL",
    })
    state["drainage_gates"][1].update({
        "water_level_percentage": 98,
        "status": "CRITICAL OVERFLOW RISK",
        "status_indicator": "CRITICAL",
    })
    state["power_substations"][0].update({
        "load_percentage": 88,
        "status": "High Risk (Basement Flooding Imminent)",
        "status_indicator": "CRITICAL",
    })
    state["emergency_hubs"][0]["available_units"] = 4
    state["emergency_hubs"][1]["available_units"] = 5

    metrics["grid_load"]        = max(metrics["grid_load"], 79.0)
    metrics["flood_risk"]       = "CRITICAL"
    metrics["system_security"]  = "COMPROMISED"
    metrics["dispatch_available"] = min(metrics["dispatch_available"], 9)

    logs += [
        _log("alert",   ts, "High water volume detected in Pavana River drainage basin. Sluice Gate sensors warning."),
        _log("warning", ts, "Pavana River Flood Gate 1 at 95%. Automated pumps engaged."),
        _log("warning", ts, "Pavana River Flood Gate 2 at 98%. Backflow prevention active."),
        _log("alert",   ts, "Pimpri MSEDCL Substation Alpha reports basement water logging. Defenses required."),
    ]


def _apply_heat(state: dict, logs: list, ts: str, metrics: dict) -> None:
    state["power_substations"][0].update({
        "load_percentage": 98,
        "status": "Critical Load // Thermal Throttle",
        "status_indicator": "CRITICAL",
    })
    state["power_substations"][1].update({
        "load_percentage": 95,
        "status": "Grid Overload // Heat Stressed",
        "status_indicator": "CRITICAL",
    })
    state["hospitals"][0].update({"capacity": "95% (Heatstroke Admissions)", "status_indicator": "CRITICAL"})
    state["hospitals"][1].update({"capacity": "92% (Cooling Load Spike)",    "status_indicator": "CRITICAL"})

    metrics["grid_load"] = max(metrics["grid_load"], 96.5)
    if metrics["system_security"] != "COMPROMISED":
        metrics["system_security"] = "STRESSED"

    logs += [
        _log("alert",   ts, "High thermal load: Urban heat island effect spikes substation loads."),
        _log("warning", ts, "Pimpri MSEDCL Substation Alpha at 98% capacity. Active fan arrays engaged."),
        _log("warning", ts, "Chinchwad Substation Beta at 95% capacity. Transformer cooling initiated."),
        _log("alert",   ts, "YCM Hospital ER capacity spikes to 95% due to dehydration & thermal exhaustion cases."),
    ]


def _apply_power(state: dict, logs: list, ts: str, metrics: dict) -> None:
    state["power_substations"][0].update({
        "load_percentage": 100,
        "status": "GRID TRIPPED // Offline",
        "status_indicator": "CRITICAL",
    })
    for h in state["hospitals"]:
        h.update({"power_status": "Emergency Generator Active", "status_indicator": "CRITICAL"})

    metrics["grid_load"]       = max(metrics["grid_load"], 50.0)
    metrics["system_security"] = "COMPROMISED"

    logs += [
        _log("alert",    ts, "MSEDCL Power Substation Alpha reports complete grid separation. Tripped state."),
        _log("dispatch", ts, "YCM Hospital and Aditya Birla Hospital switched automatically to local backup diesel generators."),
    ]


def _apply_accident(state: dict, logs: list, ts: str, metrics: dict) -> None:
    state["emergency_hubs"][0]["available_units"] = 2
    state["emergency_hubs"][1]["available_units"] = 3
    state["hospitals"][0].update({"capacity": "90% (Casualty Influx)", "status_indicator": "CRITICAL"})

    metrics["dispatch_available"] = min(metrics["dispatch_available"], 5)
    if metrics["system_security"] == "OPTIMAL":
        metrics["system_security"] = "STRESSED"

    logs += [
        _log("alert",    ts, "Local emergency incident reported. Fire and rescue crews dispatched."),
        _log("dispatch", ts, "Pimpri Fire Depot deployed 16 units to incident zone."),
        _log("dispatch", ts, "YCM Hospital alerts emergency surgical wards."),
    ]


# Public entrypoint
def update_city_state(scenario_text: str) -> tuple[dict, list[str], dict]:
    """
    Parse *scenario_text* and return a mutated digital-twin state.

    Returns
    -------
    state   : dict         – mutated city infrastructure state
    logs    : list[str]    – list of HTML-formatted telemetry log entries
    metrics : dict         – KPI values for the metric cards
    """
    state     = get_initial_city_state()
    logs: list[str] = []
    ts        = datetime.datetime.now().strftime("%H:%M:%S")
    text      = scenario_text.lower()

    is_flood    = _detect(text, _FLOOD_KEYS)
    is_heat     = _detect(text, _HEAT_KEYS)
    is_power    = _detect(text, _POWER_KEYS)
    is_accident = _detect(text, _ACCIDENT_KEYS)

    logs.append(_log_info(ts, f"Initiating simulation for scenario: '{scenario_text[:60]}...'"))

    # Mutable metrics accumulator (uses floats internally; formatted on return)
    metrics = {
        "grid_load":          58.5,
        "flood_risk":         "LOW",
        "system_security":    "OPTIMAL",
        "dispatch_available": 43,
    }

    if is_flood:
        _apply_flood(state, logs, ts, metrics)
    if is_heat:
        _apply_heat(state, logs, ts, metrics)
    if is_power:
        _apply_power(state, logs, ts, metrics)
    if is_accident:
        _apply_accident(state, logs, ts, metrics)

    if not any([is_flood, is_heat, is_power, is_accident]):
        logs.append(_log_info(ts, "Standard monitoring active. Digital Twin running normal background loads."))

    # Format metrics for display
    disp_avail = metrics["dispatch_available"]
    formatted_metrics = {
        "grid_load":       f"{metrics['grid_load']}%",
        "flood_risk":      metrics["flood_risk"],
        "system_security": metrics["system_security"],
        "dispatch_status": (
            f"ACTIVE ({disp_avail})"
            if disp_avail < 43
            else f"STANDBY ({disp_avail})"
        ),
    }

    return state, logs, formatted_metrics
