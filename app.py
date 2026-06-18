"""
app.py
------
GuardianGrid – Hybrid AI Smart City Disaster Predictor & Infrastructure
Auto-Defender.

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

import streamlit as st
from streamlit_folium import st_folium

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


# ── 0. Page setup (must be first Streamlit call) ────────────────────────────
configure_page()
openai_api_key, api_configured = load_api_key()


# ── 1. Session-state bootstrap ───────────────────────────────────────────────
def _default_session():
    """Initialise all session-state keys to clean defaults."""
    st.session_state.ml_label      = 0
    st.session_state.ml_probs      = [1.0, 0.0, 0.0]
    st.session_state.ml_label_name = "Normal / Clear Weather"
    st.session_state.weather_params = {
        "temp": 28.0, "humidity": 55.0,
        "wind_speed": 15.0, "pressure": 1013.0,
        "precipitation": 0.0,
    }
    st.session_state.city_name = "New York"
    st.session_state.latitude = 40.7128
    st.session_state.longitude = -74.0060
    st.session_state.safety_reason = ""
    st.session_state.weather_error = ""
    st.session_state.city_state, st.session_state.logs, st.session_state.metrics = \
        update_city_state_from_ml(
            0, [1.0, 0.0, 0.0],
            st.session_state.latitude, st.session_state.longitude,
            city_name=st.session_state.city_name,
        )
    st.session_state.assessment_ran   = False
    st.session_state.mitigation_playbook = None

if "ml_label" not in st.session_state:
    _default_session()


# ── 2. Sidebar ───────────────────────────────────────────────────────────────
# (API key section rendered by load_api_key() above)
st.sidebar.markdown(
    "<div class='sidebar-section-title'>📡 Open-Meteo Live Weather Input</div>",
    unsafe_allow_html=True,
)

city_query = st.sidebar.text_input("Enter City Name", value="New York")

st.sidebar.markdown("<br>", unsafe_allow_html=True)

run_btn   = st.sidebar.button("🔮 Run Assessment", type="primary", use_container_width=True)
reset_btn = st.sidebar.button("🔄 Reset Digital Twin",             use_container_width=True)

st.sidebar.markdown("---")
model_name = st.sidebar.selectbox(
    "🤖 AI Inference Model",
    ["gpt-4o-mini", "gpt-4o"],
    index=0,
    help="OpenAI model used by the Autonomous Playbook engine.",
)

# ── Feature importance expander (educational / debug) ───────────────────────
with st.sidebar.expander("📊 ML Model · Feature Importances", expanded=False):
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


# ── 3. Button actions ─────────────────────────────────────────────────────────
if reset_btn:
    _default_session()
    st.rerun()

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
                live.latitude,
                live.longitude,
            )

        safety_reasons = []
        if live.wind_speed >= 75:
            safety_reasons.append(
                f"wind speed {live.wind_speed:.1f} km/h exceeds 75 km/h"
            )
        if live.precipitation >= 15:
            safety_reasons.append(
                f"precipitation {live.precipitation:.1f} mm exceeds 15 mm"
            )

        safety_reason = "; ".join(safety_reasons)
        if safety_reason and label == 0:
            # The model has three classes only. Route severe storm telemetry
            # into its flood/storm crisis branch as a conservative fail-safe.
            label = 1
            label_name = "Flash Flood / Severe Storm Risk (Safety Override)"
            probs = [min(probs[0], 0.10), max(probs[1], 0.80), probs[2]]
            total = sum(probs)
            probs = [prob / total for prob in probs]

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
        }
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


# ── 4. Header ────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="header-banner">'
    f'<div class="header-tag">{st.session_state.city_name.upper()} · DIGITAL TWIN · v2.0</div>'
    '<h1>🛡️ GUARDIANGRID // Hybrid Smart Infrastructure AI</h1>'
    '<p>Real-Time ML Disaster Predictor &amp; Civil Defense Orchestration System</p>'
    '</div>',
    unsafe_allow_html=True,
)


# ── 5. Row 1 – KPI Metric Cards ──────────────────────────────────────────────
label      = st.session_state.ml_label
probs      = st.session_state.ml_probs
label_name = st.session_state.ml_label_name
metrics    = st.session_state.metrics

# Determine badge class
if label == 0:
    badge_cls   = "risk-badge-normal"
    alert_state = "✅ ALL CLEAR"
    alert_delta_color = "normal"
elif label == 1:
    badge_cls   = "risk-badge-flood"
    alert_state = "🚨 CRITICAL FLASH FLOOD WARNING"
    alert_delta_color = "inverse"
else:
    badge_cls   = "risk-badge-heat"
    alert_state = "🚨 CRITICAL GRID OVERLOAD WARNING"
    alert_delta_color = "inverse"

col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    flood_pct = f"{probs[1] * 100:.1f}%"
    st.metric(
        "Flood Probability",
        flood_pct,
        delta=f"P(FloodRisk) = {probs[1]:.3f}",
        delta_color="inverse" if probs[1] > 0.4 else "normal",
    )

with col_m2:
    heat_pct = f"{probs[2] * 100:.1f}%"
    st.metric(
        "Heatwave / Wildfire Risk",
        heat_pct,
        delta=f"P(HeatRisk) = {probs[2]:.3f}",
        delta_color="inverse" if probs[2] > 0.4 else "normal",
    )

with col_m3:
    st.metric(
        "System Alert State",
        alert_state if label != 0 else "🟢 OPTIMAL",
        delta=metrics["system_security"],
        delta_color=alert_delta_color,
    )

with col_m4:
    st.metric("Global Grid Load", metrics["grid_load"])

st.markdown("<br>", unsafe_allow_html=True)

# ── 6. Live Weather Metrics ──────────────────────────────────────────────────
weather = st.session_state.weather_params
if st.session_state.assessment_ran:
    st.markdown(
        f"### 🌦️ Live Open-Meteo Telemetry · {st.session_state.city_name}"
    )
    st.caption(
        f"Resolved coordinates: {st.session_state.latitude:.4f}, "
        f"{st.session_state.longitude:.4f} · "
        f"Current precipitation: {weather['precipitation']:.1f} mm"
    )
    col_w1, col_w2, col_w3, col_w4 = st.columns(4)
    col_w1.metric("Temperature", f"{weather['temp']:.1f} °C")
    col_w2.metric("Relative Humidity", f"{weather['humidity']:.0f}%")
    col_w3.metric("Wind Speed", f"{weather['wind_speed']:.1f} km/h")
    col_w4.metric("Surface Pressure", f"{weather['pressure']:.1f} hPa")
else:
    st.info(
        "🌦️ Enter a city and run an assessment to load current Open-Meteo "
        "temperature, humidity, wind, pressure, and precipitation."
    )

if st.session_state.safety_reason:
    st.error(
        "⚠️ **Rule-based safety override active:** "
        f"{st.session_state.safety_reason}."
    )

st.markdown("<br>", unsafe_allow_html=True)


# ── 7. ML Prediction Result Banner ───────────────────────────────────────────
if st.session_state.assessment_ran:
    ts_now = datetime.datetime.now().strftime("%H:%M:%S  %d %b %Y")
    if label == 0:
        st.success(
            f"☀️ **ML Prediction [Label 0]:** {label_name}  |  "
            f"Confidence: {probs[0]*100:.1f}%  |  Assessed at {ts_now}"
        )
    elif label == 1:
        st.error(
            f"🌊 **ML Prediction [Label 1]:** {label_name}  |  "
            f"Flash Flood Probability: {probs[1]*100:.1f}%  |  Assessed at {ts_now}"
        )
    else:
        st.error(
            f"🔥 **ML Prediction [Label 2]:** {label_name}  |  "
            f"Heatwave/Wildfire Probability: {probs[2]*100:.1f}%  |  Assessed at {ts_now}"
        )

    # Probability bar chart (inline HTML for precise styling)
    bar_data = [
        ("Normal / Clear Weather",          probs[0], "#10b981"),
        ("Flash Flood Risk",                probs[1], "#38bdf8"),
        ("Heatwave / Wildfire Risk",        probs[2], "#f87171"),
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
        f"<div class='ml-section-header'>RandomForest · Probability Distribution</div>"
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


# ── 8. Row 2 – Map (left) + Telemetry Log (right) ────────────────────────────
col_left, col_right = st.columns([6, 4])

with col_left:
    st.markdown(
        f"### 🌐 Digital Twin Spatial Map · {st.session_state.city_name}"
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


# ── 9. Row 3 – AI Autonomous Mitigation Playbook ─────────────────────────────
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
    # label == 1 or 2 → crisis active
    if st.session_state.mitigation_playbook:
        # Persisted result – redisplay without re-calling API
        risk_tag = "FLASH FLOOD" if label == 1 else "HEATWAVE / WILDFIRE"
        st.markdown(
            f'<div class="playbook-container">'
            f'<div class="playbook-title">'
            f'📋 ACTIVE MITIGATION PLAYBOOK — {risk_tag} RESPONSE</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(st.session_state.mitigation_playbook)

    else:
        risk_tag = "FLASH FLOOD" if label == 1 else "HEATWAVE / WILDFIRE"
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
                '⚙️ AUTONOMOUS ENGINE COMPUTING MITIGATION CHANNELS...</div>'
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
                title_ph.markdown(
                    f'<div class="playbook-container">'
                    f'<div class="playbook-title">'
                    f'📋 ACTIVE MITIGATION PLAYBOOK — {risk_tag} RESPONSE</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.rerun()

            except Exception as exc:
                st.error(f"❌ OpenAI API error: {exc}")
