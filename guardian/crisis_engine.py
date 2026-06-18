"""
guardian/crisis_engine.py
--------------------------
ML-driven crisis state controller. Takes the Scikit-Learn prediction
label (0-4) and probability scores, then mutates the digital-twin
state dictionary accordingly, returning updated state, telemetry HTML
log entries, and KPI metrics.

Public API
----------
update_city_state_from_ml(ml_label: int, ml_probs: list[float])
    -> tuple[dict, list[str], dict]
    Returns (mutated_state, html_log_entries, metrics_dict).
"""

import datetime
from guardian.data_layer import get_initial_city_state, relocate_city_state


# ── Log helpers ──────────────────────────────────────────────────────────────

def _log(level: str, timestamp: str, message: str) -> str:
    """Build a styled HTML log entry string."""
    css_class = f"log-level-{level}"
    label     = level.upper()
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


# ── Crisis mutation helpers ───────────────────────────────────────────────────

def _apply_flood(state: dict, logs: list, ts: str, metrics: dict) -> None:
    """
    Label 1 – Flash Flood Risk.
    Sets drainage gates to critical (95 / 98 %), marks substations at risk.
    """
    state["drainage_gates"][0].update({
        "water_level_percentage": 95,
        "status": "CRITICAL OVERFLOW RISK — Automated Pumps Engaged",
        "status_indicator": "CRITICAL",
    })
    state["drainage_gates"][1].update({
        "water_level_percentage": 98,
        "status": "CRITICAL OVERFLOW RISK — Backflow Prevention Active",
        "status_indicator": "CRITICAL",
    })
    state["power_substations"][0].update({
        "load_percentage": 88,
        "status": "High Risk — Basement Water Logging Imminent",
        "status_indicator": "CRITICAL",
    })
    state["emergency_hubs"][0]["available_units"] = 4
    state["emergency_hubs"][1]["available_units"] = 5

    metrics["grid_load"]          = max(metrics["grid_load"], 79.0)
    metrics["flood_risk"]         = "CRITICAL"
    metrics["system_security"]    = "COMPROMISED"
    metrics["dispatch_available"] = min(metrics["dispatch_available"], 9)

    gate_1 = state["drainage_gates"][0]["id"]
    gate_2 = state["drainage_gates"][1]["id"]
    substation = state["power_substations"][0]["name"]
    fire_hub = state["emergency_hubs"][0]["name"]
    ambulance_hub = state["emergency_hubs"][1]["name"]

    logs += [
        _log("alert", ts, "⚠️ High water volume detected in the local drainage network. Flood-gate sensors are at threshold."),
        _log("warning", ts, f"{gate_1} → 95%. Automated pump arrays engaged at full capacity."),
        _log("warning", ts, f"{gate_2} → 98%. Backflow prevention valves activated. Gate auto-lock in progress."),
        _log("alert", ts, f"{substation} reports rising water ingress. Emergency isolation protocols initiated."),
        _log("dispatch", ts, f"{fire_hub} and {ambulance_hub} placed on IMMEDIATE PRE-DEPLOYMENT status."),
    ]


def _apply_heat(state: dict, logs: list, ts: str, metrics: dict) -> None:
    """
    Label 2 – Severe Heatwave / Wildfire Risk.
    Sets power substations to critical load (98 / 95 %), hospitals under surge.
    """
    state["power_substations"][0].update({
        "load_percentage": 98,
        "status": "Critical Load — Thermal Throttle Active",
        "status_indicator": "CRITICAL",
    })
    state["power_substations"][1].update({
        "load_percentage": 95,
        "status": "Grid Overload — Heat Stressed / Transformer Cooling On",
        "status_indicator": "CRITICAL",
    })
    state["hospitals"][0].update({
        "capacity": "95% (Heatstroke Admissions Surge)",
        "status_indicator": "CRITICAL",
    })
    state["hospitals"][1].update({
        "capacity": "92% (Cooling Load Spike — Dehydration Cases)",
        "status_indicator": "CRITICAL",
    })

    metrics["grid_load"]       = max(metrics["grid_load"], 96.5)
    metrics["flood_risk"]      = "LOW"
    if metrics["system_security"] != "COMPROMISED":
        metrics["system_security"] = "STRESSED"

    substation_1 = state["power_substations"][0]["name"]
    substation_2 = state["power_substations"][1]["name"]
    hospital_1 = state["hospitals"][0]["name"]
    hospital_2 = state["hospitals"][1]["name"]

    logs += [
        _log("alert",    ts, "🌡️ Urban heat island effect confirmed. Substation thermal load spike detected."),
        _log("warning", ts, f"{substation_1} → 98% capacity. Active cooling fan arrays at maximum RPM."),
        _log("warning", ts, f"{substation_2} → 95% capacity. Automatic transformer oil circulation initiated."),
        _log("alert", ts, f"{hospital_1} ER surge: 95% capacity — dehydration and thermal-exhaustion admissions rising."),
        _log("dispatch", ts, f"{hospital_2} activates heatstroke protocol. External cooling tents deployed."),
        _log("warning", ts, "The local grid operator is issuing a voluntary load-reduction appeal to industrial nodes."),
    ]


def _apply_drought(state: dict, logs: list, ts: str, metrics: dict) -> None:
    """Label 3 – Drought / water scarcity risk."""
    state["drainage_gates"][0].update({
        "water_level_percentage": 9,
        "status": "CRITICAL LOW FLOW — Water Conservation Protocol Active",
        "status_indicator": "CRITICAL",
    })
    state["drainage_gates"][1].update({
        "water_level_percentage": 12,
        "status": "LOW RESERVE — Controlled Retention Active",
        "status_indicator": "CRITICAL",
    })
    state["power_substations"][0].update({
        "load_percentage": 84,
        "status": "Elevated Cooling Demand — Conservation Mode",
        "status_indicator": "CRITICAL",
    })
    state["hospitals"][0].update({
        "capacity": "82% (Dehydration Response Active)",
        "status_indicator": "CRITICAL",
    })

    metrics["grid_load"] = 84.0
    metrics["flood_risk"] = "DROUGHT"
    metrics["system_security"] = "STRESSED"
    metrics["dispatch_available"] = 28

    gate_1 = state["drainage_gates"][0]["id"]
    gate_2 = state["drainage_gates"][1]["id"]
    hospital = state["hospitals"][0]["name"]
    logs += [
        _log("alert", ts, "🏜️ Critical soil-moisture deficit and prolonged dry-weather pattern detected."),
        _log("warning", ts, f"{gate_1} and {gate_2} switched to controlled water-retention mode."),
        _log("warning", ts, "Non-essential municipal water demand reduction protocol activated."),
        _log("dispatch", ts, f"{hospital} begins dehydration surge readiness and potable-water reserve checks."),
    ]


def _apply_snow(state: dict, logs: list, ts: str, metrics: dict) -> None:
    """Label 4 – Heavy snow / blizzard risk."""
    for substation in state["power_substations"]:
        substation.update({
            "load_percentage": 91,
            "status": "Ice Load Risk — Cold Weather Protection Active",
            "status_indicator": "CRITICAL",
        })
    for hospital in state["hospitals"]:
        hospital.update({
            "power_status": "Backup Generation Armed — Snow Access Risk",
            "status_indicator": "CRITICAL",
        })
    state["emergency_hubs"][0]["available_units"] = 7
    state["emergency_hubs"][1]["available_units"] = 9

    metrics["grid_load"] = 91.0
    metrics["flood_risk"] = "SNOW/ICE"
    metrics["system_security"] = "COMPROMISED"
    metrics["dispatch_available"] = 16

    substation_1 = state["power_substations"][0]["name"]
    substation_2 = state["power_substations"][1]["name"]
    fire_hub = state["emergency_hubs"][0]["name"]
    logs += [
        _log("alert", ts, "❄️ Heavy snow or blizzard pattern detected. Road and utility icing risk is critical."),
        _log("warning", ts, f"{substation_1} and {substation_2} activate ice-load and cold-start protection."),
        _log("dispatch", ts, f"{fire_hub} deploys snow-capable rescue units and road-clearance support."),
        _log("warning", ts, "Hospitals arm backup power and restrict non-critical transport movements."),
    ]


def _apply_normal(state: dict, logs: list, ts: str, metrics: dict) -> None:
    """Label 0 – Normal / Clear Weather. No mutations needed."""
    gates = " and ".join(gate["id"] for gate in state["drainage_gates"])
    logs += [
        _log_info(ts, "All systems within normal parameters. Digital Twin running standard background monitoring cycles."),
        _log_info(ts, f"{gates}: Normal discharge. Power substations: Nominal load. Hospitals: Standard occupancy."),
        _log_info(ts, "Emergency dispatch depots: Full fleet readiness. No alerts active."),
    ]


# Public entrypoint
def update_city_state_from_ml(
    ml_label: int,
    ml_probs: list,
    latitude: float = 18.6200,
    longitude: float = 73.7950,
    safety_reason: str = "",
    city_name: str = "Selected City",
) -> tuple[dict, list[str], dict]:
    """
    Apply crisis mutations to the digital twin based on the Scikit-Learn
    RandomForestClassifier prediction.

    Parameters
    ----------
    ml_label : int – 0 Normal, 1 Flood, 2 Heat, 3 Drought, 4 Snow
    ml_probs : list[float] – probabilities in class order 0 through 4

    Returns
    -------
    state   : dict         – mutated Pimpri-Chinchwad infrastructure state
    logs    : list[str]    – HTML-formatted telemetry log entries
    metrics : dict         – KPI values for the metric cards
    """
    state = relocate_city_state(
        get_initial_city_state(),
        latitude,
        longitude,
        city_name,
    )
    logs: list[str] = []
    ts   = datetime.datetime.now().strftime("%H:%M:%S")

    # Base metrics accumulator
    metrics = {
        "grid_load":          58.5,
        "flood_risk":         "LOW",
        "system_security":    "OPTIMAL",
        "dispatch_available": 43,
    }

    # Dispatch classification header log
    label_names = {
        0: "Normal/Clear",
        1: "Flash Flood/Severe Storm Risk",
        2: "Heatwave/Wildfire Risk",
        3: "Drought/Water Scarcity Risk",
        4: "Heavy Snow/Blizzard Risk",
    }
    probability_text = " | ".join(
        f"P{index}={probability:.2f}"
        for index, probability in enumerate(ml_probs)
    )
    logs.append(_log_info(
        ts,
        f"Scikit-Learn RandomForest prediction received → Label {ml_label}: "
        f"{label_names[ml_label]} "
        f"[{probability_text}]"
    ))
    if safety_reason:
        logs.append(_log(
            "alert",
            ts,
            f"Live-weather safety override activated: {safety_reason}",
        ))

    if ml_label == 1:
        _apply_flood(state, logs, ts, metrics)
    elif ml_label == 2:
        _apply_heat(state, logs, ts, metrics)
    elif ml_label == 3:
        _apply_drought(state, logs, ts, metrics)
    elif ml_label == 4:
        _apply_snow(state, logs, ts, metrics)
    else:
        _apply_normal(state, logs, ts, metrics)

    # Format metrics for display widgets
    disp_avail = metrics["dispatch_available"]
    formatted_metrics = {
        "grid_load":       f"{metrics['grid_load']:.1f}%",
        "flood_risk":      metrics["flood_risk"],
        "system_security": metrics["system_security"],
        "dispatch_status": (
            f"ACTIVE ({disp_avail})"
            if disp_avail < 43
            else f"STANDBY ({disp_avail})"
        ),
    }

    return state, logs, formatted_metrics
