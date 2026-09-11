"""Optional LLM layer. Works with Azure OpenAI or OpenAI if credentials are in
the environment; otherwise the agent runs fully deterministically and this
module reports itself unavailable.

Env (either set):
  Azure : AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT
  OpenAI: OPENAI_API_KEY [, OPENAI_MODEL]
"""
from __future__ import annotations
import json
import os


def _client():
    try:
        if os.environ.get("AZURE_OPENAI_API_KEY") and os.environ.get("AZURE_OPENAI_ENDPOINT"):
            from openai import AzureOpenAI
            client = AzureOpenAI(
                api_key=os.environ["AZURE_OPENAI_API_KEY"],
                azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"))
            model = os.environ["AZURE_OPENAI_DEPLOYMENT"]
            return client, model
        if os.environ.get("OPENAI_API_KEY"):
            from openai import OpenAI
            return OpenAI(), os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    except Exception:
        return None, None
    return None, None


def available() -> bool:
    client, _ = _client()
    return client is not None


def narrate(diagnosis: dict, plan: dict) -> str | None:
    """Produce an executive narrative from the structured findings + plan.
    Returns None if no LLM is configured (caller falls back to a template)."""
    client, model = _client()
    if client is None:
        return None
    system = ("You are a manufacturing operations analyst for a coffee-capsule plant. "
              "Write a concise, decision-ready executive brief (max ~250 words) from the "
              "provided JSON diagnosis and production plan. Use plain business language, "
              "cite the biggest euro impacts, and end with 3 prioritised actions.")
    user = json.dumps({"diagnosis": diagnosis, "plan": plan}, default=str)[:12000]
    try:
        resp = client.chat.completions.create(
            model=model, temperature=0.2,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}])
        return resp.choices[0].message.content.strip()
    except Exception as exc:  # noqa: BLE001
        return f"_(LLM narrative unavailable: {exc})_"
