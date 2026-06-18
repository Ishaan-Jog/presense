"""
guardian/config.py
------------------
Handles page configuration, global CSS injection, and OpenAI API-key
resolution (secrets.toml first, sidebar text_input fallback).

Nothing here has Streamlit widget side-effects beyond the one-time
page_config + markdown CSS call and the sidebar API-key input.
"""

import streamlit as st


# ── CSS ─────────────────────────────────────────────────────────────────────
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Outfit:wght@300;400;600;800&display=swap');

body, .stApp {
    background-color: #05080f;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Outfit', sans-serif !important;
}

div[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700;
    font-size: 1.4rem;
}

/* ── Header Banner ── */
.header-banner {
    background: linear-gradient(135deg, #090d16 0%, #1e1b4b 60%, #311042 100%);
    border: 1px solid #312e81;
    border-radius: 14px;
    padding: 26px 32px;
    margin-bottom: 22px;
    box-shadow: 0 0 40px rgba(99, 102, 241, 0.18), 0 0 80px rgba(99,102,241,0.06);
    position: relative;
    overflow: hidden;
}
.header-banner::before {
    content: '';
    position: absolute;
    top: -40%;
    right: -10%;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%);
    pointer-events: none;
}
.header-banner h1 {
    color: #ffffff;
    font-weight: 800;
    letter-spacing: 1.8px;
    margin: 0;
    font-size: 2rem;
    text-shadow: 0 0 14px rgba(99, 102, 241, 0.55);
}
.header-banner p {
    color: #a5b4fc;
    margin: 6px 0 0 0;
    font-size: 0.88rem;
    text-transform: uppercase;
    letter-spacing: 2.5px;
    font-family: 'JetBrains Mono', monospace;
}
.header-tag {
    display: inline-block;
    background: rgba(99,102,241,0.15);
    border: 1px solid rgba(99,102,241,0.35);
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.7rem;
    color: #818cf8;
    letter-spacing: 1.5px;
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 10px;
}

/* ── KPI Metric Cards ── */
div[data-testid="metric-container"] {
    background: linear-gradient(145deg, #0d1222 0%, #111827 100%);
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    transition: transform 0.2s ease, border-color 0.25s ease, box-shadow 0.25s ease;
}
div[data-testid="metric-container"]:hover {
    transform: translateY(-3px);
    border-color: #6366f1;
    box-shadow: 0 0 18px rgba(99, 102, 241, 0.22);
}
div[data-testid="stMetricLabel"] > div {
    font-family: 'Outfit', sans-serif !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: #94a3b8 !important;
}

/* ── ML Section divider ── */
.ml-section-header {
    background: linear-gradient(90deg, rgba(99,102,241,0.12) 0%, transparent 100%);
    border-left: 4px solid #6366f1;
    border-radius: 0 8px 8px 0;
    padding: 10px 16px;
    margin: 18px 0 12px 0;
    font-family: 'Outfit', sans-serif;
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #818cf8;
    font-weight: 600;
}

/* ── Risk Badge ── */
.risk-badge-normal   { color: #10b981; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
.risk-badge-flood    { color: #38bdf8; font-weight: 700; font-family: 'JetBrains Mono', monospace; animation: pulse-blue 1.5s infinite; }
.risk-badge-heat     { color: #f87171; font-weight: 700; font-family: 'JetBrains Mono', monospace; animation: pulse-red 1.5s infinite; }

@keyframes pulse-blue {
    0%, 100% { text-shadow: 0 0 6px rgba(56,189,248,0.4); }
    50%       { text-shadow: 0 0 18px rgba(56,189,248,0.85); }
}
@keyframes pulse-red {
    0%, 100% { text-shadow: 0 0 6px rgba(248,113,113,0.4); }
    50%       { text-shadow: 0 0 18px rgba(248,113,113,0.85); }
}

/* ── Terminal Log ── */
.terminal-log-container {
    background-color: #030712;
    border: 1px solid #1f2937;
    border-radius: 10px;
    padding: 15px;
    height: 420px;
    overflow-y: auto;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.80rem;
}
.log-entry {
    margin-bottom: 8px;
    line-height: 1.5;
    border-left: 3px solid #374151;
    padding-left: 10px;
}
.log-time           { color: #6b7280; font-weight: bold; }
.log-level-info     { color: #34d399; }
.log-level-warning  { color: #fbbf24; border-left-color: #fbbf24 !important; }
.log-level-alert    { color: #f87171; border-left-color: #f87171 !important; animation: flash 2s infinite; }
.log-level-dispatch { color: #60a5fa; border-left-color: #60a5fa !important; }

@keyframes flash {
    0%   { opacity: 1;   }
    50%  { opacity: 0.55; }
    100% { opacity: 1;   }
}

/* ── AI Playbook ── */
.playbook-container {
    background: linear-gradient(145deg, #0a0e1a 0%, #0f1626 100%);
    border: 1px solid #312e81;
    border-left: 6px solid #6366f1;
    border-radius: 10px;
    padding: 18px 24px;
    margin-top: 12px;
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.35), 0 0 40px rgba(99,102,241,0.07);
}
.playbook-title {
    font-family: 'Outfit', sans-serif;
    font-size: 1.15rem;
    font-weight: bold;
    color: #e0e7ff;
    letter-spacing: 1.2px;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* ── Probability Bar ── */
.prob-bar-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 4px 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
}
.prob-label { color: #94a3b8; width: 200px; flex-shrink: 0; }
.prob-bar-bg {
    flex: 1;
    background: #1e293b;
    border-radius: 4px;
    height: 8px;
    overflow: hidden;
}
.prob-bar-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.5s ease;
}
.prob-val { color: #f8fafc; width: 45px; text-align: right; flex-shrink: 0; }

/* ── Sidebar styling ── */
.sidebar-section-title {
    font-family: 'Outfit', sans-serif;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #6366f1;
    font-weight: 600;
    margin: 16px 0 8px 0;
    padding-bottom: 4px;
    border-bottom: 1px solid #1e293b;
}
</style>
"""


def configure_page() -> None:
    """Set Streamlit page config and inject global CSS. Call once at startup."""
    st.set_page_config(
        page_title="GuardianGrid | Hybrid AI Smart City Infrastructure Defender",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(_CSS, unsafe_allow_html=True)


def load_api_key() -> tuple[str, bool]:
    """
    Resolve the OpenAI API key with a two-tier strategy:

    Tier 1 (preferred): .streamlit/secrets.toml  →  OPENAI_API_KEY
    Tier 2 (fallback):  Sidebar st.text_input    (password masked)

    Returns
    -------
    (api_key, is_configured) : tuple[str, bool]
        api_key        – raw key string (empty if unavailable / placeholder)
        is_configured  – True only when a real key is present
    """
    # --- Tier 1: secrets.toml ------------------------------------------------
    _PLACEHOLDER = "YOUR_OPENAI_API_KEY_HERE"
    try:
        if "OPENAI_API_KEY" in st.secrets:
            key_val = st.secrets["OPENAI_API_KEY"]
            if key_val and key_val != _PLACEHOLDER:
                # Still render the sidebar section (read-only indication)
                st.sidebar.markdown(
                    "<div class='sidebar-section-title'>🔑 API Configuration</div>",
                    unsafe_allow_html=True,
                )
                st.sidebar.success("✅ OpenAI API Key loaded from secrets.toml")
                return key_val, True
    except Exception:
        pass

    # --- Tier 2: sidebar input -----------------------------------------------
    st.sidebar.markdown(
        "<div class='sidebar-section-title'>🔑 API Configuration</div>",
        unsafe_allow_html=True,
    )
    key_input = st.sidebar.text_input(
        "OpenAI API Key",
        type="password",
        placeholder="sk-proj-...",
        help="Enter your OpenAI API key to unlock the AI Playbook engine.",
    )
    if key_input and key_input != _PLACEHOLDER:
        return key_input, True

    return "", False
