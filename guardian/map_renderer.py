"""
guardian/map_renderer.py
-------------------------
Builds and returns an interactive Folium map of the Pimpri-Chinchwad
digital twin.  Marker colours and transmission-line colours update
automatically to reflect crisis status.

Public API
----------
build_map(city_state: dict) -> folium.Map
    Returns a ready-to-embed Folium map object.
"""

import folium


# Colour helpers
def _status_color(status_indicator: str, default_ok: str = "#10b981") -> str:
    return "#ef4444" if status_indicator == "CRITICAL" else default_ok


def _line_dash(status_indicator: str) -> str | None:
    return "5, 10" if status_indicator == "CRITICAL" else None


# Popup HTML factory
def _make_popup_html(title: str, category: str, details: dict) -> str:
    rows = "".join(
        f"<tr>"
        f"<td style='color:#94a3b8;padding:4px 12px 4px 0;font-size:0.78rem;'>{k}</td>"
        f"<td style='color:#f8fafc;font-weight:bold;font-family:monospace;font-size:0.78rem;'>{v}</td>"
        f"</tr>"
        for k, v in details.items()
    )
    return f"""
    <div style="font-family:'Outfit',sans-serif;background-color:#0f172a;color:#f8fafc;
                border:1px solid #1e293b;border-radius:8px;padding:12px;min-width:210px;
                box-shadow:0 4px 6px rgba(0,0,0,0.2);">
        <span style="font-size:0.68rem;text-transform:uppercase;color:#818cf8;
                     font-weight:bold;letter-spacing:1px;">{category}</span>
        <h4 style="margin:3px 0 8px 0;font-size:0.95rem;color:#ffffff;
                   border-bottom:1px solid #334155;padding-bottom:5px;
                   font-weight:bold;">{title}</h4>
        <table style="width:100%;border-collapse:collapse;">{rows}</table>
    </div>
    """


# Layer builders
def _add_transmission_lines(m: folium.Map, city_state: dict) -> None:
    subs  = city_state["power_substations"]
    hosps = city_state["hospitals"]
    gates = city_state["drainage_gates"]

    # Substation Alpha → YCM Hospital
    alpha_crit = subs[0]["status_indicator"]
    folium.PolyLine(
        locations=[[subs[0]["lat"], subs[0]["lon"]], [hosps[0]["lat"], hosps[0]["lon"]]],
        color=_status_color(alpha_crit),
        weight=2.5, opacity=0.6,
        dash_array=_line_dash(alpha_crit),
        tooltip="Power line: Substation Alpha → YCM Hospital",
    ).add_to(m)

    # Substation Beta → Aditya Birla Hospital
    beta_crit = subs[1]["status_indicator"]
    folium.PolyLine(
        locations=[[subs[1]["lat"], subs[1]["lon"]], [hosps[1]["lat"], hosps[1]["lon"]]],
        color=_status_color(beta_crit),
        weight=2.5, opacity=0.6,
        dash_array=_line_dash(beta_crit),
        tooltip="Power line: Substation Beta → Aditya Birla Hospital",
    ).add_to(m)

    # Pavana sluice gate interconnect
    gate_crit = gates[0]["status_indicator"]
    folium.PolyLine(
        locations=[[gates[0]["lat"], gates[0]["lon"]], [gates[1]["lat"], gates[1]["lon"]]],
        color=_status_color(gate_crit, "#38bdf8"),
        weight=2, opacity=0.4, dash_array="10, 10",
        tooltip="Pavana River Sluice Automation Interceptor Line",
    ).add_to(m)


def _add_hospitals(m: folium.Map, hospitals: list) -> None:
    for h in hospitals:
        color  = _status_color(h["status_indicator"])
        radius = 12 if h["status_indicator"] == "CRITICAL" else 9
        popup  = _make_popup_html(h["name"], "🏥 Hospital & Clinical Vault", {
            "Power Status":    h["power_status"],
            "ICU/Cap Capacity": h["capacity"],
            "Node State":      h["status_indicator"],
        })
        folium.CircleMarker(
            location=[h["lat"], h["lon"]], radius=radius,
            color=color, fill=True, fill_color=color, fill_opacity=0.8,
            popup=folium.Popup(folium.Html(popup, script=True), max_width=300),
            tooltip=f"Hospital: {h['name']}",
        ).add_to(m)


def _add_substations(m: folium.Map, substations: list) -> None:
    for p in substations:
        color  = _status_color(p["status_indicator"])
        radius = 12 if p["status_indicator"] == "CRITICAL" else 9
        popup  = _make_popup_html(p["name"], "⚡ Power Substation Node", {
            "Load Percentage": f"{p['load_percentage']}%",
            "MSEDCL Status":   p["status"],
            "Node State":      p["status_indicator"],
        })
        folium.CircleMarker(
            location=[p["lat"], p["lon"]], radius=radius,
            color=color, fill=True, fill_color=color, fill_opacity=0.8,
            popup=folium.Popup(folium.Html(popup, script=True), max_width=300),
            tooltip=f"Substation: {p['name']}",
        ).add_to(m)


def _add_drainage_gates(m: folium.Map, gates: list) -> None:
    for d in gates:
        color  = _status_color(d["status_indicator"], "#38bdf8")
        radius = 12 if d["status_indicator"] == "CRITICAL" else 9
        popup  = _make_popup_html(d["id"], "💧 Sluice Gate Control", {
            "Water Level": f"{d['water_level_percentage']}%",
            "Gate Status": d["status"],
            "Node State":  d["status_indicator"],
        })
        folium.CircleMarker(
            location=[d["lat"], d["lon"]], radius=radius,
            color=color, fill=True, fill_color=color, fill_opacity=0.8,
            popup=folium.Popup(folium.Html(popup, script=True), max_width=300),
            tooltip=f"Sluice Gate: {d['id']}",
        ).add_to(m)


def _add_emergency_hubs(m: folium.Map, hubs: list) -> None:
    for e in hubs:
        popup = _make_popup_html(e["name"], "🚒 Emergency Dispatch Depot", {
            "Available Fleet Units": e["available_units"],
            "Node State":            e["status_indicator"],
        })
        folium.CircleMarker(
            location=[e["lat"], e["lon"]], radius=9,
            color="#3b82f6", fill=True, fill_color="#3b82f6", fill_opacity=0.8,
            popup=folium.Popup(folium.Html(popup, script=True), max_width=300),
            tooltip=f"Emergency Depot: {e['name']}",
        ).add_to(m)


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

def build_map(city_state: dict) -> folium.Map:
    """
    Build a Folium dark-map centred on Pimpri-Chinchwad and add all
    digital-twin asset layers drawn from *city_state*.
    """
    m = folium.Map(
        location=[18.6200, 73.7950],
        zoom_start=13,
        tiles="CartoDB dark_matter",
        attr="© CartoDB",
    )
    _add_transmission_lines(m, city_state)
    _add_hospitals(m,        city_state["hospitals"])
    _add_substations(m,      city_state["power_substations"])
    _add_drainage_gates(m,   city_state["drainage_gates"])
    _add_emergency_hubs(m,   city_state["emergency_hubs"])
    return m
