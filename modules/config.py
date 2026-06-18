"""
guardian/config.py
------------------
Handles page configuration, global CSS injection, and OpenAI API-key
resolution (secrets.toml first, sidebar text_input fallback).

Nothing here has Streamlit widget side-effects beyond the one-time
page_config + markdown CSS call and the sidebar API-key input.
"""

import streamlit as st


# CSS

_CSS = """
<style>
/* Theme-driven styling */
@import url('https://fonts.googleapis.com/css2?family=Pliant:ital,wght@0,100..900;1,100..900&display=swap');
:root {
    --guardian-sans: 'Pliant', sans-serif;
    --guardian-mono: 'JetBrains Mono', 'Consolas', 'Courier New', monospace;
    --guardian-bg: var(--background-color, #06111f);
    --guardian-surface: var(--secondary-background-color, #0b1626);
    --guardian-surface-strong: color-mix(in srgb, var(--secondary-background-color, #0b1626) 88%, white 12%);
    --guardian-border: color-mix(in srgb, var(--primary-color, #2563eb) 35%, transparent);
    --guardian-primary: var(--primary-color, #2563eb);
    --guardian-primary-soft: color-mix(in srgb, var(--primary-color, #2563eb) 14%, transparent);
    --guardian-text: var(--text-color, #e2e8f0);
    --guardian-muted: color-mix(in srgb, var(--text-color, #e2e8f0) 74%, transparent);
}

body, .stApp {
    background-color: var(--guardian-bg);
    font-family: var(--guardian-sans);
    color: var(--guardian-text);
}

html {
    scroll-behavior: smooth;
}

h1, h2, h3, h4, h5, h6 {
    font-family: var(--guardian-sans) !important;
    letter-spacing: 0;
}

div[data-testid="stMetricValue"] {
    font-family: var(--guardian-sans) !important;
    font-weight: 600;
    font-size: 1.4rem;
}

/* ── Header Banner ── */
.header-banner {
    background: var(--guardian-surface);
    border: 1px solid var(--guardian-border);
    border-radius: 14px;
    padding: 26px 32px;
    margin-bottom: 22px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.26);
    position: relative;
    overflow: hidden;
}
.header-banner::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, rgba(255,255,255,0.03) 0%, transparent 100%);
    pointer-events: none;
}
.header-banner h1 {
    color: #ffffff;
    font-weight: 700;
    letter-spacing: 0.2px;
    margin: 0;
    font-size: 2rem;
}
.header-banner p {
    color: var(--guardian-muted);
    margin: 6px 0 0 0;
    font-size: 0.88rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-family: var(--guardian-sans);
}
.header-tag {
    display: inline-block;
    background: var(--guardian-primary-soft);
    border: 1px solid color-mix(in srgb, var(--guardian-primary) 32%, transparent);
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.7rem;
    color: color-mix(in srgb, var(--guardian-primary) 70%, white 30%);
    letter-spacing: 0.8px;
    font-family: var(--guardian-sans);
    margin-bottom: 10px;
}

/* ── KPI Metric Cards ── */
div[data-testid="metric-container"] {
    background: linear-gradient(145deg, var(--guardian-surface) 0%, var(--guardian-surface-strong) 100%);
    border: 1px solid color-mix(in srgb, var(--guardian-border) 70%, #1e293b 30%);
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    transition: transform 0.2s ease, border-color 0.25s ease, box-shadow 0.25s ease;
}
div[data-testid="metric-container"]:hover {
    transform: translateY(-3px);
    border-color: var(--guardian-primary);
    box-shadow: 0 0 18px rgba(37, 99, 235, 0.16);
}
div[data-testid="stMetricLabel"] > div {
    font-family: var(--guardian-sans) !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: #94a3b8 !important;
}

/* ── ML Section divider ── */
.ml-section-header {
    background: linear-gradient(90deg, var(--guardian-primary-soft) 0%, transparent 100%);
    border-left: 4px solid var(--guardian-primary);
    border-radius: 0 8px 8px 0;
    padding: 10px 16px;
    margin: 18px 0 12px 0;
    font-family: var(--guardian-sans);
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: color-mix(in srgb, var(--guardian-primary) 65%, white 35%);
    font-weight: 600;
}

/* ── Risk Badge ── */
.risk-badge-normal   { color: #34d399; font-weight: 700; font-family: var(--guardian-sans); }
.risk-badge-flood    { color: #38bdf8; font-weight: 700; font-family: var(--guardian-sans); animation: pulse-blue 1.5s infinite; }
.risk-badge-heat     { color: #ef4444; font-weight: 700; font-family: var(--guardian-sans); animation: pulse-red 1.5s infinite; }

@keyframes pulse-blue {
    0%, 100% { text-shadow: 0 0 6px rgba(56,189,248,0.28); }
    50%       { text-shadow: 0 0 18px rgba(56,189,248,0.62); }
}
@keyframes pulse-red {
    0%, 100% { text-shadow: 0 0 6px rgba(239,68,68,0.28); }
    50%       { text-shadow: 0 0 18px rgba(239,68,68,0.62); }
}

/* ── Terminal Log ── */
.terminal-log-container {
    background-color: #030712;
    border: 1px solid #1f2937;
    border-radius: 10px;
    padding: 15px;
    height: 420px;
    overflow-y: auto;
    font-family: var(--guardian-mono);
    font-size: 0.80rem;
}
.log-entry {
    margin-bottom: 8px;
    line-height: 1.5;
    border-left: 3px solid #374151;
    padding-left: 10px;
    font-family: var(--guardian-mono);
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
    background: linear-gradient(145deg, var(--guardian-bg) 0%, var(--guardian-surface) 100%);
    border: 1px solid var(--guardian-border);
    border-left: 6px solid var(--guardian-primary);
    border-radius: 10px;
    padding: 18px 24px;
    margin-top: 12px;
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.35), 0 0 40px rgba(37, 99, 235, 0.05);
}
.playbook-title {
    font-family: var(--guardian-sans);
    font-size: 1.15rem;
    font-weight: bold;
    color: #e0e7ff;
    letter-spacing: 0.2px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.broadcast-canvas {
    background: linear-gradient(145deg, var(--guardian-bg) 0%, var(--guardian-surface) 100%);
    border: 1px solid color-mix(in srgb, var(--guardian-border) 80%, #334155 20%);
    border-left: 6px solid #22c55e;
    border-radius: 12px;
    padding: 18px 22px;
    margin-top: 16px;
    box-shadow: 0 4px 28px rgba(0, 0, 0, 0.28);
}
.broadcast-canvas-title {
    font-family: var(--guardian-sans);
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #86efac;
    margin-bottom: 10px;
}

.return-top-button {
    position: fixed;
    right: 22px;
    bottom: 22px;
    z-index: 9999;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    padding: 0;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--guardian-surface) 0%, var(--guardian-surface-strong) 100%);
    border: 1px solid var(--guardian-primary);
    color: color-mix(in srgb, var(--guardian-primary) 74%, white 26%) !important;
    text-decoration: none !important;
    font-family: var(--guardian-sans);
    font-size: 1rem;
    font-weight: 800;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.32);
}
.return-top-button:hover {
    transform: translateY(-2px);
    border-color: #60a5fa;
    box-shadow: 0 10px 28px rgba(37, 99, 235, 0.18);
}

/* ── Probability Bar ── */
.prob-bar-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 4px 0;
    font-family: var(--guardian-sans);
    font-size: 0.78rem;
}
.prob-label { color: #94a3b8; width: 200px; flex-shrink: 0; }
.prob-bar-bg {
    flex: 1;
    background: color-mix(in srgb, var(--guardian-surface) 70%, #1e293b 30%);
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
    font-family: var(--guardian-sans);
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: color-mix(in srgb, var(--guardian-primary) 60%, white 40%);
    font-weight: 600;
    margin: 16px 0 8px 0;
    padding-bottom: 4px;
    border-bottom: 1px solid color-mix(in srgb, var(--guardian-border) 70%, #1e293b 30%);
}
</style>
"""


def configure_page() -> None:
    """Set Streamlit page config and inject global CSS. Call once at startup."""
    st.set_page_config(
        page_title="PreSense | Real-Time ML Disaster Predictor & AI-based Civil Defense Orchestration System",
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

    # Tier 2: sidebar input
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
