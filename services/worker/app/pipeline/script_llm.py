"""Open-source LLM script generation via Ollama (local) or OpenAI-compatible /v1/chat/completions."""

import json
import logging
import re
from typing import Any

import requests

from storytime_common.settings import Settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You write scripts for "Grandma's Storytime", a gentle YouTube channel for children ages 5-10.

Return ONLY one JSON object. No markdown, no code fences, no commentary.

Schema:
{
  "title": "short video title, max 8 words",
  "moral": "one short sentence lesson",
  "scenes": [
    {
      "caption": "on-screen label, max 6 words",
      "narration_line": "grandma speaks warmly, max 22 words",
      "image_query": "3-6 English keywords for a kid-safe stock photo search"
    }
  ]
}

Rules:
- Exactly 4 objects in "scenes".
- Follow the user's topic and intent. If their brief is long, distill it — do not copy it verbatim.
- narration_line: simple English, spoken aloud; no bullet lists, no stage directions, no Sanskrit unless they asked for it.
- image_query: concrete visuals (people, places, objects), child-appropriate, no logos or text overlays.
- Keep all four scenes part of one coherent mini-story or lesson.
"""


def _truncate_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text.strip()
    return " ".join(words[:max_words]).strip() + "."


def _parse_json_object(text: str) -> dict[str, Any]:
    raw = text.strip()
    if m := re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL):
        raw = m.group(1)
    else:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            raw = raw[start : end + 1]
    return json.loads(raw)


def _normalize_llm_payload(data: dict[str, Any]) -> dict[str, Any]:
    title = _truncate_words(str(data.get("title") or "Today's Story"), 10)
    moral = str(data.get("moral") or "Be kind and keep learning.").strip()[:200]
    scenes_raw = data.get("scenes")
    if not isinstance(scenes_raw, list):
        raise ValueError("LLM JSON missing scenes array")

    scenes: list[dict[str, str]] = []
    for item in scenes_raw[:4]:
        if not isinstance(item, dict):
            continue
        scenes.append(
            {
                "caption": str(item.get("caption") or "Story time")[:48],
                "narration_line": _truncate_words(
                    str(item.get("narration_line") or "Grandma has a story for you."), 22
                ),
                "image_query": re.sub(
                    r"[^\w\s-]", "", str(item.get("image_query") or "children happy illustration")
                )[:80].strip()
                or "children illustration",
            }
        )

    while len(scenes) < 4:
        scenes.append(
            {
                "caption": "Remember",
                "narration_line": "Grandma loves you. See you next time!",
                "image_query": "children happy friends",
            }
        )

    return {"title": title, "moral": moral, "scenes": scenes}


def _ollama_chat(settings: Settings, user_prompt: str) -> str:
    url = settings.ollama_base_url.rstrip("/") + "/api/chat"
    body = {
        "model": settings.ollama_model,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "options": {"temperature": settings.llm_temperature, "num_predict": settings.llm_max_tokens},
    }
    resp = requests.post(url, json=body, timeout=settings.llm_timeout_sec)
    resp.raise_for_status()
    content = resp.json().get("message", {}).get("content", "")
    if not content:
        raise ValueError("Ollama returned empty message")
    return content


def _openai_compatible_chat(settings: Settings, user_prompt: str) -> str:
    base = settings.llm_openai_base_url.rstrip("/")
    url = f"{base}/v1/chat/completions"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"
    body = {
        "model": settings.ollama_model,
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }
    resp = requests.post(url, json=body, headers=headers, timeout=settings.llm_timeout_sec)
    resp.raise_for_status()
    choices = resp.json().get("choices") or []
    if not choices:
        raise ValueError("LLM returned no choices")
    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise ValueError("LLM returned empty content")
    return content


def generate_llm_content_blocks(prompt: str, duration_target_sec: int) -> dict[str, Any]:
    settings = Settings()
    user_prompt = (
        f"User idea (may be long — summarize for a {duration_target_sec}-second vertical kids short):\n\n"
        f"{prompt.strip()}"
    )

    if settings.script_provider == "ollama":
        raw = _ollama_chat(settings, user_prompt)
    elif settings.script_provider == "openai_compatible":
        raw = _openai_compatible_chat(settings, user_prompt)
    else:
        raise ValueError(f"script_llm does not support SCRIPT_PROVIDER={settings.script_provider}")

    data = _parse_json_object(raw)
    return _normalize_llm_payload(data)
