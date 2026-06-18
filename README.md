# 🛡️ GuardianGrid

GuardianGrid is a Streamlit dashboard for real-time smart-infrastructure risk monitoring. It combines live Open-Meteo weather data, a city-specific RandomForest model, a digital-twin map, telemetry logs, and an optional AI playbook to simulate how a municipal response system could react to changing conditions.

Built as part of the **Edunet IBM SkillsBuild Internship** program.

## Live Demo

Deployed link: [guardian-grid.streamlit.app](https://guardian-grid.streamlit.app/){target="_blank"}

## Features

- Live weather lookup by city name using Open-Meteo.
- City-specific machine learning predictions trained on historical weather observations.
- Probability dashboard for normal, flood, heatwave, drought, and snow risk.
- Digital-twin map with infrastructure assets and state changes.
- Telemetry and system logs that reflect the current assessment.
- Optional AI mitigation playbook powered by OpenAI.

## Project Structure

```text
project/
├── app.py
├── README.md
├── requirements.txt
└── guardian/
   ├── __init__.py
   ├── ai_playbook.py
   ├── config.py
   ├── crisis_engine.py
   ├── data_layer.py
   ├── map_renderer.py
   ├── ml_engine.py
   └── weather_service.py
```

## Requirements

- Python 3.11 or later
- Internet access for Open-Meteo data and model training
- OpenAI API key for the AI playbook section

## Setup

1. Clone the repository.

  ```bash
  git clone https://github.com/Ishaan-Jog/guardian-grid.git
  cd guardian-grid
  ```

2. Create a virtual environment.

  ```bash
  python -m venv .venv
  .venv\Scripts\activate
  ```

3. Install dependencies.

  ```bash
  pip install -r requirements.txt
  ```

4. Add your OpenAI API key for the AI playbook.

  Create `.streamlit/secrets.toml` with:

  ```toml
  OPENAI_API_KEY = "your-key-here"
  ```

## Run Locally

```bash
streamlit run app.py
```

Then open the local URL shown in the terminal, usually `http://localhost:8501`.

## How It Works

1. Enter a city name in the sidebar.
2. Click **Run Assessment**.
3. The app fetches live weather data and trains or reuses a city-specific model.
4. The dashboard updates the probabilities, map state, logs, and response metrics.
5. If an OpenAI key is configured, you can generate an AI mitigation playbook.

## Notes

- The app can still run without an OpenAI API key. However, you will not get to use the AI playbook feature.
- The ML model is trained from real historical weather data for the selected city.
- The probabilities shown in the UI are normalized to five risk classes.

## License

This project was developed for educational purposes during the **Edunet IBM SkillsBuild Internship** program.
