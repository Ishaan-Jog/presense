"""
guardian/ai_playbook.py
-----------------------
OpenAI streaming integration.  Sends the current digital-twin state and
scenario description to the chosen model and yields response chunks for
Streamlit's live-streaming display.

Public API
----------
stream_playbook(api_key, city_state, scenario, model) -> Generator[str, None, None]
    Yields text chunks from the OpenAI streaming response.
"""

import json
from openai import OpenAI


# Prompt templates
_SYSTEM_PROMPT = (
    "You are the central autonomous AI brain of a high-tech smart city "
    "(Pimpri-Chinchwad, Pune, Maharashtra). "
    "Your purpose is not to predict the weather, but to analyze live "
    "structural data of the city's digital twin during a disaster and "
    "instantly execute infrastructure mitigation, resource allocation, "
    "and civil defense automation strategies. "
    "Be structured, authoritative, action-oriented, and write in clear "
    "markdown formatting. Do not use legacy markdown that breaks Streamlit "
    "rendering. Keep responses concise and focused on high-impact steps."
)

_USER_PROMPT_TEMPLATE = """\
Live telemetry data for the Pimpri-Chinchwad Digital Twin:
Scenario: {scenario}
Current Infrastructure Status:
{state_json}

Provide a structured critical mitigation playbook including:
1. **Automated Infrastructure Changes** \
(e.g. shedding power, adjusting gate states, swapping power grids)
2. **Emergency Resource Dispatch** \
(commands targeting depots, routing, casualty support)
3. **Automated Civil Broadcast** \
(warning drafts/broadcast scripts using localized names: \
Pimpri-Chinchwad, Pavana River, PCMC, etc.)
"""


# Public streaming generator
def stream_playbook(
    api_key: str,
    city_state: dict,
    scenario: str,
    model: str = "gpt-4o-mini",
):
    """
    Stream the AI mitigation playbook as text chunks.

    Parameters
    ----------
    api_key    : OpenAI secret key
    city_state : mutated digital-twin dict from crisis_engine
    scenario   : user-supplied free-text scenario description
    model      : OpenAI model identifier (default: gpt-4o-mini)

    Yields
    ------
    str – successive text chunks from the streaming response
    """
    client = OpenAI(api_key=api_key)

    user_prompt = _USER_PROMPT_TEMPLATE.format(
        scenario=scenario,
        state_json=json.dumps(city_state, indent=2),
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        stream=True,
    )

    for chunk in response:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
