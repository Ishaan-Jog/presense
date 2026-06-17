"""
guardian/config.py
------------------
Handles page configuration, global CSS injection, and secure API-key loading
from .streamlit/secrets.toml.  Nothing here has Streamlit widget side-effects
beyond the one-time page_config + markdown CSS call.
"""

import streamlit as st


# CSS source string – keeps the stylesheet out of app.py
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Outfit:wght@300;400;600;800&display=swap');

h1, h2, h3, h4, h5, h6 {
    font-family: 'Outfit', sans-serif !important;
}

div[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700;
    font-size: 1.5rem;
    
}

.header-banner {
    background: linear-gradient(135deg, #090d16 0%, #1e1b4b 60%, #311042 100%);
    border: 1px solid #312e81;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 25px;
    box-shadow: 0 0 20px rgba(99, 102, 241, 0.2);
}
.header-banner h1 {
    color: #ffffff;
    font-weight: 800;
    letter-spacing: 1.5px;
    margin: 0;
    font-size: 2.2rem;
    text-shadow: 0 0 10px rgba(99, 102, 241, 0.5);
}
.header-banner p {
    color: #a5b4fc;
    margin: 6px 0 0 0;
    font-size: 0.95rem;
    text-transform: uppercase;
    letter-spacing: 2px;
}

div[data-testid="metric-container"] {
    background-color: #0d1222;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 15px 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    transition: transform 0.2s, border-color 0.2s;
}
div[data-testid="metric-container"]:hover {
    transform: translateY(-2px);
    border-color: #6366f1;
    box-shadow: 0 0 15px rgba(99, 102, 241, 0.25);
}

.terminal-log-container {
    background-color: #030712;
    border: 1px solid #1f2937;
    border-radius: 10px;
    padding: 15px;
    height: 400px;
    overflow-y: auto;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
}
.log-entry {
    margin-bottom: 8px;
    line-height: 1.45;
    border-left: 3px solid #4b5563;
    padding-left: 10px;
}
.log-time  { color: #9ca3af; font-weight: bold; }
.log-level-info    { color: #34d399; }
.log-level-warning { color: #fbbf24; border-left-color: #fbbf24; }
.log-level-alert   { color: #f87171; border-left-color: #f87171; animation: flash 2s infinite; }
.log-level-dispatch{ color: #60a5fa; border-left-color: #60a5fa; }

@keyframes flash {
    0%   { opacity: 1;   }
    50%  { opacity: 0.6; }
    100% { opacity: 1;   }
}

.playbook-container {
    background-color: #0b0f19;
    border: 1px solid #312e81;
    border-left: 6px solid #6366f1;
    border-radius: 8px;
    padding: 15px 20px;
    margin-top: 15px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}
.playbook-title {
    font-family: 'Outfit', sans-serif;
    font-size: 1.25rem;
    font-weight: bold;
    color: #e0e7ff;
    letter-spacing: 1px;
    display: flex;
    align-items: center;
    gap: 8px;
}
</style>
"""


def configure_page() -> None:
    # Set Streamlit page config and inject global CSS.  Call once at startup.
    st.set_page_config(
        page_title="GuardianGrid | Smart Infrastructure Auto-Defender",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(_CSS, unsafe_allow_html=True)


def load_api_key() -> tuple[str, bool]:
    """
    Load the OpenAI API key from st.secrets (secrets.toml).

    Returns
    -------
    (api_key, is_configured) : tuple[str, bool]
        api_key        – the raw key string (empty string if not found / invalid)
        is_configured  – True only when a real, non-placeholder key is present
    """
    try:
        if "OPENAI_API_KEY" in st.secrets:
            key_val = st.secrets["OPENAI_API_KEY"]
            if key_val and key_val != "YOUR_OPENAI_API_KEY_HERE":
                return key_val, True
    except Exception:
        pass
    return "", False
