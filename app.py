"""
app.py
------
GuardianGrid – entry point.

This file is intentionally thin: it handles only Streamlit UI layout and
session-state orchestration.  All business logic lives in the `guardian`
package:

    guardian/config.py        – page config, CSS, API-key loading
    guardian/data_layer.py    – baseline digital-twin state
    guardian/crisis_engine.py – keyword heuristic parser + state mutator
    guardian/map_renderer.py  – Folium map builder
    guardian/ai_playbook.py   – OpenAI streaming generator
"""

import streamlit as st
from streamlit_folium import st_folium
from guardian.config import configure_page, load_api_key
from guardian.crisis_engine import update_city_state
from guardian.map_renderer import build_map
from guardian.ai_playbook import stream_playbook


# Page and API setup
configure_page()
openai_api_key, api_configured = load_api_key()


# Session-state bootstrap
if "current_scenario" not in st.session_state:
    st.session_state.current_scenario = "Clear/Normal Weather"
    (
        st.session_state.city_state,
        st.session_state.logs,
        st.session_state.metrics,
    ) = update_city_state("Clear/Normal Weather")


# Sidebar
st.sidebar.markdown("## ⚙️ Dashboard Controls")

model_name = st.sidebar.selectbox(
    "AI Inference Model",
    ["gpt-4o-mini", "gpt-4o"],
    index=0,
    help="Model used by the AI Autonomous Playbook engine.",
)

st.sidebar.markdown("---")

custom_scenario = st.sidebar.text_area(
    "Describe Environmental Simulation Scenario",
    value=st.session_state.current_scenario,
    help=(
        "Type any weather or crisis event description. "
        "GuardianGrid heuristics will immediately update the digital twin."
    ),
)

if st.sidebar.button("🔄 Reset Digital Twin"):
    st.session_state.current_scenario = "Clear/Normal Weather"
    (
        st.session_state.city_state,
        st.session_state.logs,
        st.session_state.metrics,
    ) = update_city_state("Clear/Normal Weather")
    st.session_state.pop("mitigation_playbook", None)
    st.rerun()


# Scenario change detection, re-run heuristic engine
if custom_scenario != st.session_state.current_scenario:
    st.session_state.current_scenario = custom_scenario
    (
        st.session_state.city_state,
        st.session_state.logs,
        st.session_state.metrics,
    ) = update_city_state(custom_scenario)
    st.session_state.pop("mitigation_playbook", None)


# Header banner
st.markdown("""
<div class="header-banner">
    <h1>🛡️ GuardianGrid | Smart AI-enabled Infrastructure Auto-Defender</h1>
    <p>Real-Time Digital Twin &amp; Civil Defense Orchestration System | Pimpri-Chinchwad (PCMC) Zone</p>
</div>
""", unsafe_allow_html=True)


# Row 1 – KPI metric cards
metrics = st.session_state.metrics
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    sec = metrics["system_security"]
    if sec == "OPTIMAL":
        val_display, delta_color = "🟢 OPTIMAL", "normal"
    elif sec == "STRESSED":
        val_display, delta_color = "🟡 STRESSED", "inverse"
    else:
        val_display, delta_color = "🔴 COMPROMISED", "inverse"
    st.metric("System Security Status", val_display,
              delta=f"State: {sec}", delta_color=delta_color)

with col_m2:
    st.metric("Global Grid Load", metrics["grid_load"])

with col_m3:
    st.metric("Flood Risk Level", metrics["flood_risk"])

with col_m4:
    st.metric("Emergency Services Dispatch", metrics["dispatch_status"])

st.markdown("<br>", unsafe_allow_html=True)


# Row 2 – Spatial map (left) + telemetry log (right)
col_left, col_right = st.columns([6, 4])

with col_left:
    st.markdown("### 🌐 Digital Twin Spatial Map")
    st.caption(
        "Hover over elements to see a status summary. "
        "Click markers to expand full telemetry parameters."
    )
    st_folium(build_map(st.session_state.city_state), height=400, use_container_width=True)

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
st.markdown("## 🤖 AI AUTONOMOUS CRITICAL MITIGATION PLAYBOOK")

if not api_configured:
    st.info(
        "🗝️ **OpenAI API Key Required**: Configure your key in "
        "`.streamlit/secrets.toml` to unlock the AI Playbook engine. "
        "The live telemetry simulation and interactive map remain fully "
        "operational using local heuristic parsers."
    )
else:
    is_normal = (
        any(k in st.session_state.current_scenario.lower()
            for k in ("clear", "normal", "good", "safe"))
        and len(st.session_state.current_scenario) < 30
    )

    if is_normal:
        st.success("☀️ **System Operational**: All systems normal. No emergency playbook required.")
    elif "mitigation_playbook" in st.session_state:
        # Already generated – show persisted result
        label = st.session_state.current_scenario[:40]
        st.markdown(
            f'<div class="playbook-container">'
            f'<div class="playbook-title">📋 ACTIVE MITIGATION PLAYBOOK ({label}...)</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(st.session_state.mitigation_playbook)
    else:
        st.warning(
            "⚠️ **Emergency Playbook Pending**: Critical event active. "
            "Trigger the AI Autonomous engine to generate emergency "
            "mitigation, dispatch commands, and civil warning broadcasts."
        )
        if st.button("⚡ Execute AI Auto-Defender Playbook", type="primary"):
            title_ph  = st.empty()
            output_ph = st.empty()

            title_ph.markdown(
                '<div class="playbook-container">'
                '<div class="playbook-title">⚡ AUTONOMOUS ENGINE COMPUTING MITIGATION CHANNELS...</div>'
                '</div>',
                unsafe_allow_html=True,
            )

            full_text = ""
            try:
                for chunk in stream_playbook(
                    api_key=openai_api_key,
                    city_state=st.session_state.city_state,
                    scenario=st.session_state.current_scenario,
                    model=model_name,
                ):
                    full_text += chunk
                    output_ph.markdown(full_text)

                st.session_state.mitigation_playbook = full_text
                label = st.session_state.current_scenario[:40]
                title_ph.markdown(
                    f'<div class="playbook-container">'
                    f'<div class="playbook-title">📋 ACTIVE MITIGATION PLAYBOOK ({label}...)</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.rerun()

            except Exception as exc:
                st.error(f"OpenAI API error: {exc}")
