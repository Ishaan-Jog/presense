# 🛡️ GuardianGrid — AI-Powered Smart City Infrastructure Auto-Defender

> A real-time **Digital Twin** simulation of Pimpri-Chinchwad (PCMC), Pune, that uses the OpenAI API to autonomously generate crisis mitigation playbooks while dynamically updating a live, map-based infrastructure dashboard.

Built as part of the **Edunet IBM SkillsBuild Internship** program.

---

## ✨ Features

- 🗺️ **Interactive Digital Twin Map** — Folium-powered dark map of Pimpri-Chinchwad, showing hospitals, power substations, Pavana River sluice gates, and emergency hubs as live colour-coded nodes (🟢 normal → 🔴 critical) with transmission-line overlays.
- 🧠 **Free-text Crisis Simulation** — Type any natural-language scenario (e.g. *"heavy monsoon flooding over the Pavana river basin"*) and the heuristic engine instantly mutates the digital twin's state.
- 📊 **Live KPI Dashboard** — Four metric cards update in real-time: System Security Status, Global Grid Load, Flood Risk Level, and Emergency Dispatch availability.
- 🖥️ **Telemetry Event Log** — A styled terminal panel streams colour-coded log events (INFO / WARNING / ALERT / DISPATCH) as the crisis state evolves.
- 🤖 **AI Autonomous Mitigation Playbook** — Powered by OpenAI (`gpt-4o-mini` or `gpt-4o`), the playbook is streamed live onto the dashboard, covering:
  1. Automated infrastructure changes
  2. Emergency resource dispatch commands
  3. Localized civil broadcast drafts (PCMC, Pavana River, etc.)
- 🔒 **Secure API Key Handling** — Key is read exclusively from `.streamlit/secrets.toml`; no credentials are ever exposed in the UI.
- 🌐 **Zero Hardware Dependencies** — Fully Python + Streamlit, deployable to [Streamlit Community Cloud](https://streamlit.io/cloud) with no additional infrastructure.

---

## 🏙️ City Modelled

**Pimpri-Chinchwad Municipal Corporation (PCMC)**, Pune, Maharashtra.

| Asset | Name |
|---|---|
| 🏥 Hospital | YCM Hospital (Yashwantrao Chavan Memorial) |
| 🏥 Hospital | Aditya Birla Memorial Hospital |
| ⚡ Substation | Pimpri MSEDCL Substation Alpha |
| ⚡ Substation | Chinchwad Power Grid Zone Beta |
| 💧 Sluice Gate | Pavana River Flood Gate 1 |
| 💧 Sluice Gate | Pavana River Flood Gate 2 |
| 🚒 Emergency Hub | Pimpri Fire Station & Rescue Depot |
| 🚑 Emergency Hub | Thergaon Ambulance Depot |

---

## 🗂️ Project Structure

```
project/
│
├── app.py                        # Streamlit entry point — UI layout & orchestration only
│
├── guardian/                     # Core business-logic package
│   ├── __init__.py
│   ├── config.py                 # Page config, CSS injection, API-key loading
│   ├── data_layer.py             # Baseline digital-twin city state (deep-copy safe)
│   ├── crisis_engine.py          # Keyword heuristic parser + per-crisis state mutators
│   ├── map_renderer.py           # Folium map builder — markers, lines, popups
│   └── ai_playbook.py            # OpenAI streaming generator + prompt templates
│
├── .streamlit/
│   └── secrets.toml              # 🔑 API key goes here (git-ignored)
│
├── requirements.txt
└── .gitignore
```

### Module responsibilities

| File | Responsibility |
|---|---|
| `app.py` | Thin orchestrator — wires Streamlit widgets to `guardian` modules; zero business logic |
| `guardian/config.py` | `configure_page()` sets page config & injects CSS; `load_api_key()` reads from secrets with placeholder detection |
| `guardian/data_layer.py` | Single source of truth for asset coordinates & baseline attributes; returns `copy.deepcopy()` to prevent cross-run mutation |
| `guardian/crisis_engine.py` | Detects crisis categories via keyword banks; composable `_apply_*()` helpers allow compound events (e.g. flood + power outage simultaneously) |
| `guardian/map_renderer.py` | Builds layered Folium map; `_status_color()` and `_line_dash()` helpers keep marker/line styling DRY |
| `guardian/ai_playbook.py` | Prompt strings as module-level constants; `stream_playbook()` is a generator that yields chunks for live streaming |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- An [OpenAI API key](https://platform.openai.com/api-keys)

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/guardian-grid.git
cd guardian-grid
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure your OpenAI API key

Create the secrets file (it is git-ignored):

```toml
# .streamlit/secrets.toml
OPENAI_API_KEY = "sk-..."
```

> **Note:** The app runs fully without an API key — the map, KPI cards, and telemetry log all work using the local heuristic engine. The AI Playbook section will display a configuration prompt until a valid key is detected.

### 5. Run the app

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## 🌩️ How the Crisis Engine Works

Type any free-text description of a crisis in the sidebar text area. The engine scans the description for keyword categories:

| Category | Trigger keywords |
|---|---|
| 🌊 **Flood** | `flood`, `rain`, `storm`, `water`, `river`, `overflow`, `monsoon` … |
| 🌡️ **Heatwave** | `heat`, `hot`, `heatwave`, `temperature`, `drought`, `degrees` … |
| ⚡ **Power Outage** | `power`, `blackout`, `outage`, `grid`, `electricity`, `offline` … |
| 🔥 **Accident / Emergency** | `accident`, `fire`, `blast`, `explosion`, `earthquake`, `chemical` … |

Multiple categories can be active simultaneously (e.g. a flood that also causes a power outage).

**Example inputs:**

```
Category 4 monsoon flooding over the Pavana River with substation waterlogging
Severe 48°C heatwave causing thermal overload across the city grid
Industrial fire at Chinchwad MIDC with chemical leak
```

---

## ☁️ Deploying to Streamlit Community Cloud

1. Push the repository to GitHub (ensure `.streamlit/secrets.toml` is in `.gitignore`).
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your repo.
3. In the Streamlit Cloud dashboard, navigate to **App settings → Secrets** and add:
   ```toml
   OPENAI_API_KEY = "sk-..."
   ```
4. Deploy — no additional configuration required.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend & Deployment | [Streamlit](https://streamlit.io) |
| Interactive Maps | [Folium](https://python-visualization.github.io/folium/) + [streamlit-folium](https://folium.streamlit.app/) |
| AI Reasoning | [OpenAI Python SDK](https://github.com/openai/openai-python) (`gpt-4o-mini` / `gpt-4o`) |
| Data Layer | Pure Python dicts / JSON (in-memory digital twin) |
| Styling | Vanilla CSS with JetBrains Mono + Outfit (Google Fonts) |

---

## 📄 License

This project was developed for the **Edunet IBM SkillsBuild Internship** program. Feel free to fork and adapt for educational or research purposes.
