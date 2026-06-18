"""
app.py
------
GuardianGrid – Real-Time ML Disaster Predictor & AI-based Civil Defense Orchestration System

Entry point: handles Streamlit UI layout and session-state orchestration.
Business logic lives in the `guardian` package:

    guardian/config.py      – page config, CSS, API-key loading
    guardian/data_layer.py  – baseline digital-twin state
    guardian/ml_engine.py   – city-specific RandomForest trained on Open-Meteo history
    guardian/crisis_engine.py – ML-label-driven state mutator
    guardian/map_renderer.py  – Folium map builder
    guardian/ai_playbook.py   – OpenAI streaming generator
"""

import datetime
import re
from io import BytesIO
from html import escape
from pathlib import Path

import streamlit as st
from streamlit_folium import st_folium
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from guardian.config      import configure_page, load_api_key
from guardian.ml_engine import (
    predict_risk,
    get_feature_importances,
    get_model_summary,
)
from guardian.crisis_engine import update_city_state_from_ml
from guardian.map_renderer  import build_map
from guardian.ai_playbook   import stream_playbook
from guardian.weather_service import fetch_live_weather, WeatherServiceError


_PDF_FONT_REGISTRY_READY = False


def _register_pdf_fonts() -> tuple[str, str]:
    """Register a Unicode-capable Windows font for PDF exports."""
    global _PDF_FONT_REGISTRY_READY
    if not _PDF_FONT_REGISTRY_READY:
        font_dir = Path(r"C:\Windows\Fonts")
        body_font_path = font_dir / "mangal.ttf"
        bold_font_path = font_dir / "mangalb.ttf"
        if body_font_path.exists():
            pdfmetrics.registerFont(TTFont("Mangal", str(body_font_path)))
        if bold_font_path.exists():
            pdfmetrics.registerFont(TTFont("Mangal-Bold", str(bold_font_path)))
        _PDF_FONT_REGISTRY_READY = True
    registered_fonts = set(pdfmetrics.getRegisteredFontNames())
    body_font = "Mangal" if "Mangal" in registered_fonts else "Helvetica"
    bold_font = "Mangal-Bold" if "Mangal-Bold" in registered_fonts else "Helvetica-Bold"
    return body_font, bold_font


# Page and API setup
configure_page()
openai_api_key, api_configured = load_api_key()


# Session-state bootstrap
def _default_session():
    """Initialise all session-state keys to clean defaults."""
    st.session_state.ml_label      = 0
    st.session_state.ml_probs      = [1.0, 0.0, 0.0, 0.0, 0.0]
    st.session_state.ml_label_name = "Normal / Clear Weather"
    st.session_state.weather_params = {
        "temp": 28.0, "humidity": 55.0,
        "wind_speed": 15.0, "pressure": 1013.0,
        "precipitation": 0.0,
        "snowfall": 0.0, "snow_depth": 0.0,
        "soil_moisture": 0.25,
    }
    st.session_state.city_name = "Pune"
    st.session_state.latitude = 18.5204
    st.session_state.longitude = 73.8567
    st.session_state.safety_reason = ""
    st.session_state.weather_error = ""
    st.session_state.city_state, st.session_state.logs, st.session_state.metrics = \
        update_city_state_from_ml(
            0, [1.0, 0.0, 0.0, 0.0, 0.0],
            st.session_state.latitude, st.session_state.longitude,
            city_name=st.session_state.city_name,
        )
    st.session_state.assessment_ran   = False
    st.session_state.mitigation_playbook = None


def _normalize_probs(probs: list[float]) -> list[float]:
    """Return a fixed five-class probability vector for the dashboard."""
    normalized = list(probs[:5])
    if len(normalized) < 5:
        normalized.extend([0.0] * (5 - len(normalized)))
    return normalized


def _markdown_line_to_reportlab(line: str) -> str:
    line = escape(line)
    line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
    line = re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", line)
    return line


def _playbook_to_pdf_bytes(playbook_text: str) -> bytes:
    buffer = BytesIO()
    body_font, bold_font = _register_pdf_fonts()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=42,
        rightMargin=42,
        topMargin=42,
        bottomMargin=42,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="PlaybookTitle",
        parent=styles["Heading1"],
        fontName=bold_font,
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#111827"),
        alignment=TA_LEFT,
        spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name="PlaybookHeading2",
        parent=styles["Heading2"],
        fontName=bold_font,
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#1f2937"),
        spaceBefore=8,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="PlaybookHeading3",
        parent=styles["Heading3"],
        fontName=bold_font,
        fontSize=10.5,
        leading=13,
        textColor=colors.HexColor("#374151"),
        spaceBefore=6,
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="PlaybookBody",
        parent=styles["BodyText"],
        fontName=body_font,
        fontSize=9.4,
        leading=13,
        textColor=colors.HexColor("#111827"),
        spaceAfter=3,
    ))

    story = []
    for raw_line in playbook_text.splitlines():
        line = raw_line.strip()
        if not line:
            story.append(Spacer(1, 4))
            continue
        if line.startswith("## "):
            story.append(Paragraph(_markdown_line_to_reportlab(line[3:]), styles["PlaybookTitle"]))
        elif line.startswith("### "):
            story.append(Paragraph(_markdown_line_to_reportlab(line[4:]), styles["PlaybookHeading2"]))
        elif line.startswith("#### "):
            story.append(Paragraph(_markdown_line_to_reportlab(line[5:]), styles["PlaybookHeading3"]))
        elif line.startswith("- "):
            story.append(Paragraph(f"• {_markdown_line_to_reportlab(line[2:])}", styles["PlaybookBody"]))
        else:
            story.append(Paragraph(_markdown_line_to_reportlab(line), styles["PlaybookBody"]))

    document.build(story)
    return buffer.getvalue()


def _extract_broadcast_section(playbook_text: str) -> str:
    match = re.search(
        r"### 4\. Public Broadcast Canvas\s*(.*?)(?=\n### \d+\.|\Z)",
        playbook_text,
        flags=re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def _playbook_without_broadcast(playbook_text: str) -> str:
    return re.sub(
        r"\n### 4\. Public Broadcast Canvas\s*.*?(?=\n### \d+\.|\Z)",
        "",
        playbook_text,
        flags=re.DOTALL,
    ).strip()


def _safe_filename(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return value or "GuardianGrid_Playbook"


def _render_playbook_header(playbook_text: str, risk_tag: str) -> None:
    export_name = _safe_filename(f"GuardianGrid_{st.session_state.city_name}_{risk_tag}_Playbook")
    text_bytes = playbook_text.encode("utf-8")
    pdf_bytes = _playbook_to_pdf_bytes(playbook_text)

    title_col, text_col, pdf_col = st.columns([6, 1, 1])
    with title_col:
        st.markdown(
            f'<div class="playbook-container">'
            f'<div class="playbook-title">'
            f'📋 ACTIVE MITIGATION PLAYBOOK — {risk_tag} RESPONSE</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with text_col:
        st.download_button(
            "⬇ TXT",
            data=text_bytes,
            file_name=f"{export_name}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with pdf_col:
        st.download_button(
            "⬇ PDF",
            data=pdf_bytes,
            file_name=f"{export_name}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )


def _render_broadcast_canvas(playbook_text: str) -> None:
    broadcast_section = _extract_broadcast_section(playbook_text)
    if not broadcast_section:
        return
    with st.container(border=True):
        st.markdown(
            '<div class="broadcast-canvas-title">📡 Public Broadcast Canvas</div>',
            unsafe_allow_html=True,
        )
        st.markdown(broadcast_section)

if "ml_label" not in st.session_state:
    _default_session()

st.markdown('<div id="page-top"></div>', unsafe_allow_html=True)
st.markdown(
    '<a class="return-top-button" href="#page-top" title="Go to top" aria-label="Go to top">↑</a>',
    unsafe_allow_html=True,
)


# Sidebar
# (API key section rendered by load_api_key() above)
st.sidebar.markdown(
    "<div class='sidebar-section-title'>📡 Live Weather Input</div>",
    unsafe_allow_html=True,
)

city_query = st.sidebar.text_input("Enter City Name", value="Pune")

st.sidebar.markdown("<br>", unsafe_allow_html=True)

run_btn   = st.sidebar.button("🔮 Run Assessment", type="primary", use_container_width=True)
st.sidebar.markdown("---")
model_name = st.sidebar.selectbox(
    "⚙️ AI Inference Model",
    ["gpt-5-nano", "gpt-4.1-nano"],
    index=0,
    help="OpenAI model used by the Autonomous Playbook engine.",
)

# Feature importance expander (educational / debug)
with st.sidebar.expander("📊 ML Model • Feature Importances", expanded=False):
    if not st.session_state.assessment_ran:
        st.caption("Run an assessment to train the selected city's model.")
    else:
        fi = get_feature_importances(
            st.session_state.latitude,
            st.session_state.longitude,
        )
        summary = get_model_summary(
            st.session_state.latitude,
            st.session_state.longitude,
        )
        st.caption(
            f"Trained on {summary['sample_count']:,} real hourly Open-Meteo "
            f"records from {summary['start_date']} to {summary['end_date']}."
        )
        label_map = {
            "temperature": "Temperature",
            "humidity":    "Humidity",
            "wind_speed":  "Wind Speed",
            "pressure":    "Pressure",
            "precipitation": "Precipitation",
            "snowfall": "Snowfall",
            "snow_depth": "Snow Depth",
            "soil_moisture": "Soil Moisture",
        }
        for feat, score in sorted(fi.items(), key=lambda x: -x[1]):
            bar_w = int(score * 100)
            st.markdown(
                f"<div style='font-family:monospace;font-size:0.78rem;margin-bottom:4px;'>"
                f"<span style='color:#94a3b8;width:90px;display:inline-block;'>"
                f"{label_map.get(feat, feat)}</span>"
                f"<span style='display:inline-block;background:#6366f1;height:8px;"
                f"width:{bar_w}px;border-radius:3px;vertical-align:middle;margin:0 6px;'></span>"
                f"<span style='color:#e0e7ff;'>{score:.3f}</span></div>",
                unsafe_allow_html=True,
            )


if run_btn:
    try:
        live = fetch_live_weather(city_query)
        with st.spinner(
            f"Training the city-specific model from real historical weather "
            f"for {live.city_name}..."
        ):
            label, probs, label_name = predict_risk(
                live.temperature,
                live.humidity,
                live.wind_speed,
                live.pressure,
                live.precipitation,
                live.snowfall,
                live.snow_depth,
                live.soil_moisture,
                live.latitude,
                live.longitude,
            )
            probs = _normalize_probs(probs)

        safety_reasons = []
        safety_label = None
        if live.wind_speed >= 75:
            safety_reasons.append(
                f"wind speed {live.wind_speed:.1f} km/h exceeds 75 km/h"
            )
            safety_label = 1
        if live.precipitation >= 15:
            safety_reasons.append(
                f"precipitation {live.precipitation:.1f} mm exceeds 15 mm"
            )
            safety_label = 1
        if live.snowfall >= 1.0 or (
            live.snow_depth >= 0.10 and live.wind_speed >= 40
        ):
            safety_reasons.append(
                f"snowfall {live.snowfall:.1f} cm and snow depth "
                f"{live.snow_depth:.2f} m indicate hazardous snow conditions"
            )
            safety_label = 4
        if (
            live.soil_moisture <= 0.08
            and live.humidity <= 30
            and live.precipitation == 0
            and live.temperature >= 30
        ):
            safety_reasons.append(
                f"soil moisture {live.soil_moisture:.3f} m³/m³ with hot, "
                "dry conditions indicates acute drought stress"
            )
            safety_label = 3

        safety_reason = "; ".join(safety_reasons)
        if safety_label is not None and label != safety_label:
            label = safety_label
            override_names = {
                1: "Flash Flood / Severe Storm Risk",
                3: "Drought / Water Scarcity Risk",
                4: "Heavy Snow / Blizzard Risk",
            }
            label_name = f"{override_names[label]} (Safety Override)"
            remaining = sum(
                probability
                for index, probability in enumerate(probs)
                if index != label
            )
            if remaining:
                probs = [
                    probability / remaining * 0.20
                    if index != label else 0.80
                    for index, probability in enumerate(probs)
                ]
            else:
                probs = [0.0] * 5
                probs[label] = 1.0

        st.session_state.ml_label       = label
        st.session_state.ml_probs       = probs
        st.session_state.ml_label_name  = label_name
        st.session_state.city_name      = live.city_name
        st.session_state.latitude       = live.latitude
        st.session_state.longitude      = live.longitude
        st.session_state.safety_reason  = safety_reason
        st.session_state.weather_error  = ""
        st.session_state.weather_params = {
            "temp": live.temperature,
            "humidity": live.humidity,
            "wind_speed": live.wind_speed,
            "pressure": live.pressure,
            "precipitation": live.precipitation,
            "snowfall": live.snowfall,
            "snow_depth": live.snow_depth,
            "soil_moisture": live.soil_moisture,
        }
        st.session_state.ml_probs = probs
        st.session_state.city_state, st.session_state.logs, st.session_state.metrics = \
            update_city_state_from_ml(
                label,
                probs,
                live.latitude,
                live.longitude,
                safety_reason,
                live.city_name,
            )
        st.session_state.assessment_ran = True
        st.session_state.mitigation_playbook = None
    except WeatherServiceError as exc:
        st.session_state.weather_error = str(exc)

if st.session_state.weather_error:
    st.error(f"🌐 Live weather lookup failed: {st.session_state.weather_error}")


# Header
st.markdown(
    '<div class="header-banner">'
    f'<div class="header-tag">{st.session_state.city_name.upper()} • DIGITAL TWIN</div>'
    '<h1>🛡️ GuardianGrid</h1>'
    '<p>Real-Time ML Disaster Predictor &amp; AI-based Civil Defense Orchestration System</p>'
    '</div>',
    unsafe_allow_html=True,
)


# Row 1 – KPI Metric Cards
label      = st.session_state.ml_label
probs      = _normalize_probs(st.session_state.ml_probs)
st.session_state.ml_probs = probs
label_name = st.session_state.ml_label_name
metrics    = st.session_state.metrics

alert_states = {
    0: "🟢 OPTIMAL",
    1: "🚨 FLASH FLOOD / STORM",
    2: "🚨 HEATWAVE / WILDFIRE",
    3: "🚨 DROUGHT / WATER SCARCITY",
    4: "🚨 HEAVY SNOW / BLIZZARD",
}
alert_state = alert_states[label]
alert_delta_color = "normal" if label == 0 else "inverse"

col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.metric(
        "Flood Probability",
        f"{probs[1] * 100:.1f}%",
        delta_color="inverse" if probs[1] > 0.4 else "normal",
    )

with col_m2:
    st.metric(
        "Heatwave / Wildfire Risk",
        f"{probs[2] * 100:.1f}%",
        delta_color="inverse" if probs[2] > 0.4 else "normal",
    )

with col_m3:
    st.metric(
        "Drought Risk",
        f"{probs[3] * 100:.1f}%",
        delta_color="inverse" if probs[3] > 0.4 else "normal",
    )

with col_m4:
    st.metric(
        "Snow / Blizzard Risk",
        f"{probs[4] * 100:.1f}%",
        delta_color="inverse" if probs[4] > 0.4 else "normal",
    )

col_status, col_grid = st.columns(2)
col_status.metric(
    "System Alert State",
    alert_state,
    delta=metrics["system_security"],
    delta_color=alert_delta_color,
)
col_grid.metric("Global Grid Load", metrics["grid_load"])

st.markdown("<br>", unsafe_allow_html=True)

# Live Weather Metrics
weather = st.session_state.weather_params
if st.session_state.assessment_ran:
    st.markdown(
        f"### 🌦️ Live Weather Telemetry • {st.session_state.city_name}"
    )
    st.caption(
        f"Resolved coordinates: {st.session_state.latitude:.4f}, "
        f"{st.session_state.longitude:.4f} • "
        f"Current precipitation: {weather['precipitation']:.1f} mm"
    )
    col_w1, col_w2, col_w3, col_w4 = st.columns(4)
    col_w1.metric("Temperature", f"{weather['temp']:.1f} °C")
    col_w2.metric("Relative Humidity", f"{weather['humidity']:.0f}%")
    col_w3.metric("Wind Speed", f"{weather['wind_speed']:.1f} km/h")
    col_w4.metric("Surface Pressure", f"{weather['pressure']:.1f} hPa")
    col_e1, col_e2, col_e3 = st.columns(3)
    col_e1.metric("Snowfall", f"{weather['snowfall']:.2f} cm")
    col_e2.metric("Snow Depth", f"{weather['snow_depth']:.3f} m")
    col_e3.metric(
        "Surface Soil Moisture",
        f"{weather['soil_moisture']:.3f} m³/m³",
    )
else:
    st.info(
        "🌦️ Enter a city and run an assessment to load current Open-Meteo "
        "temperature, humidity, wind, pressure, precipitation, snow, and "
        "soil moisture."
    )

if st.session_state.safety_reason:
    st.error(
        "⚠️ **Rule-based safety override active:** "
        f"{st.session_state.safety_reason}."
    )

st.markdown("<br>", unsafe_allow_html=True)


# ML Prediction Result Banner
if st.session_state.assessment_ran:
    ts_now = datetime.datetime.now().strftime("%H:%M:%S  %d %b %Y")
    prediction_icons = {0: "☀️", 1: "🌊", 2: "🔥", 3: "🏜️", 4: "❄️"}
    if label == 0:
        st.success(
            f"☀️ **ML Prediction [Label 0]:** {label_name}  |  "
            f"Confidence: {probs[0]*100:.1f}%  |  Assessed at {ts_now}"
        )
    else:
        st.error(
            f"{prediction_icons[label]} **ML Prediction [Label {label}]:** "
            f"{label_name}  |  Confidence: {probs[label]*100:.1f}%  |  "
            f"Assessed at {ts_now}"
        )

    # Probability bar chart (inline HTML for precise styling)
    bar_data = [
        ("Normal / Clear Weather",          probs[0], "#10b981"),
        ("Flash Flood Risk",                probs[1], "#38bdf8"),
        ("Heatwave / Wildfire Risk",        probs[2], "#f87171"),
        ("Drought / Water Scarcity Risk",   probs[3], "#f59e0b"),
        ("Heavy Snow / Blizzard Risk",      probs[4], "#c4b5fd"),
    ]
    bars_html = "".join(
        f"<div class='prob-bar-wrap'>"
        f"<span class='prob-label'>{lbl}</span>"
        f"<div class='prob-bar-bg'>"
        f"<div class='prob-bar-fill' style='width:{p*100:.1f}%;background:{col};'></div>"
        f"</div>"
        f"<span class='prob-val'>{p*100:.0f}%</span>"
        f"</div>"
        for lbl, p, col in bar_data
    )
    st.markdown(
        f"<div style='background:#0d1222;border:1px solid #1e293b;border-radius:10px;"
        f"padding:14px 18px;margin-bottom:10px;'>"
        f"<div class='ml-section-header'>RandomForest • Probability Distribution</div>"
        f"{bars_html}"
        f"</div>",
        unsafe_allow_html=True,
    )
else:
    st.info(
        "🔮 **Enter a city in the sidebar and click "
        "'Run Assessment'** to fetch live Open-Meteo observations, activate "
        "the Scikit-Learn model, and trigger the digital-twin controller."
    )

st.markdown("<br>", unsafe_allow_html=True)


# Row 2 – Map (left) + Telemetry Log (right)
col_left, col_right = st.columns([6, 4])

with col_left:
    st.markdown(
        f"### 🌐 Digital Twin Spatial Map • {st.session_state.city_name}"
    )
    st.caption(
        "Green markers = healthy assets.  Red markers = crisis/critical state.  "
        "Click any marker to expand live telemetry parameters."
    )
    st_folium(
        build_map(
            st.session_state.city_state,
            st.session_state.latitude,
            st.session_state.longitude,
        ),
        height=430,
        use_container_width=True,
    )

with col_right:
    st.markdown("### 🖥️ Telemetry & System Event Logs")
    st.caption("Live event telemetry from infrastructure node automation micro-agents.")
    log_html = "".join(st.session_state.logs)
    st.markdown(
        f'<div class="terminal-log-container">{log_html}</div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)


# Row 3 – AI Autonomous Mitigation Playbook
st.markdown("---")
st.markdown("## 🤖 AI AUTONOMOUS PRELIMINARY PRECAUTION & MITIGATION PLAYBOOK")

if not api_configured:
    st.info(
        "🗝️ **OpenAI API Key Required**: Enter your key in the sidebar (or configure "
        "`.streamlit/secrets.toml`) to unlock the AI Playbook engine.  \n"
        "The live Scikit-Learn ML predictions and the interactive map remain "
        "fully operational without an API key."
    )

elif label == 0 and st.session_state.assessment_ran:
    st.success(
        "☀️ **System Operational — No Emergency Playbook Required.**  \n"
        "All infrastructure nodes are green. The Scikit-Learn model reports "
        "normal weather conditions. No autonomous mitigation actions needed."
    )

elif not st.session_state.assessment_ran:
    st.warning(
        "⚠️ Run the Predictive Risk Assessment first to determine whether the "
        "AI Playbook engine should be invoked."
    )

else:
    risk_tags = {
        1: "FLASH FLOOD / SEVERE STORM",
        2: "HEATWAVE / WILDFIRE",
        3: "DROUGHT / WATER SCARCITY",
        4: "HEAVY SNOW / BLIZZARD",
    }
    risk_tag = risk_tags[label]
    if st.session_state.mitigation_playbook:
        _render_playbook_header(st.session_state.mitigation_playbook, risk_tag)
        st.markdown(_playbook_without_broadcast(st.session_state.mitigation_playbook))
        _render_broadcast_canvas(st.session_state.mitigation_playbook)

    else:
        st.warning(
            f"⚡ **{risk_tag} RISK DETECTED** — AI Autonomous Engine on standby.  \n"
            "Click below to generate the real-time emergency mitigation playbook."
        )

        if st.button("⚡ Execute AI Auto-Defender Playbook", type="primary"):
            title_ph  = st.empty()
            output_ph = st.empty()

            title_ph.markdown(
                '<div class="playbook-container">'
                '<div class="playbook-title">'
                '⚙️ COMPUTING MITIGATION CHANNELS...</div>'
                '</div>',
                unsafe_allow_html=True,
            )

            full_text = ""
            try:
                for chunk in stream_playbook(
                    api_key       = openai_api_key,
                    city_state    = st.session_state.city_state,
                    weather_params= st.session_state.weather_params,
                    ml_label      = st.session_state.ml_label,
                    ml_probs      = st.session_state.ml_probs,
                    ml_label_name = st.session_state.ml_label_name,
                    city_name     = st.session_state.city_name,
                    model         = model_name,
                ):
                    full_text += chunk
                    output_ph.markdown(full_text)

                st.session_state.mitigation_playbook = full_text
                st.rerun()

            except Exception as exc:
                st.error(f"❌ OpenAI API error: {exc}")
