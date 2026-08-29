"""Opt-in LLM-assisted qualitative analysis. Not run by default."""
import json
import os

PROMPT = """You are a literary style analyst. Given a writing sample and its \
computed quantitative metrics, describe the author's qualitative style.

Respond with ONLY a JSON object with these keys:
- "tone_and_register": one paragraph
- "rhetorical_devices": list of {{"device": str, "example": str}}
- "cadence_and_rhythm": one paragraph
- "persuasion_style": one paragraph

Quantitative metrics (for context, do not just restate them):
{metrics}

Writing sample:
---
{sample}
---
"""


def compute(raw_text: str, quantitative_metrics: dict, provider: str) -> dict:
    sample = raw_text[:8000]
    prompt = PROMPT.format(metrics=json.dumps(quantitative_metrics, indent=2), sample=sample)

    if provider == "anthropic":
        content = _call_anthropic(prompt)
    elif provider == "openai":
        content = _call_openai(prompt)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"raw_response": content}


def _call_anthropic(prompt: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


def _call_openai(prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content
