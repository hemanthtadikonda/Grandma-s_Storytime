import json
import re
from pathlib import Path
from typing import Any

from app.pipeline.image_queries import build_scene_image_queries
from storytime_common.settings import Settings


def _template_manifest(template_id: str) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[4] / "templates" / template_id / "manifest.json"
    if not root.exists():
        root = Path("/app/templates") / template_id / "manifest.json"
    return json.loads(root.read_text(encoding="utf-8"))


def _clean_prompt(prompt: str) -> str:
    text = prompt.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _story_title(prompt: str) -> str:
    first = _clean_prompt(prompt).split(".")[0].strip()
    if len(first) < 8:
        return "A Special Story for You"
    return first[:72]


def generate_script(prompt: str, template_id: str, duration_target_sec: int, content_source: str) -> dict[str, Any]:
    """Turn a short idea into a grandma-style English story (v1: template + your prompt woven in)."""
    settings = Settings()
    if settings.script_provider != "stub":
        raise NotImplementedError(f"SCRIPT_PROVIDER={settings.script_provider} not implemented yet")

    _template_manifest(template_id)
    idea = _clean_prompt(prompt)
    title = _story_title(idea)
    hero = "our little friend"
    if match := re.search(r"\b([A-Z][a-z]+)\b", idea):
        hero = match.group(1)

    image_queries = build_scene_image_queries(idea, title, hero)

    scenes = [
        {
            "id": "s1",
            "emoji": "✨",
            "caption": "Grandma's Storytime",
            "image_query": image_queries[0],
            "narration_line": (
                "Hello, my dears. Snuggle in close. "
                "Grandma has a warm little story just for you."
            ),
        },
        {
            "id": "s2",
            "emoji": "📖",
            "caption": title,
            "image_query": image_queries[1],
            "narration_line": (
                f"Today we visit {hero}. {idea} "
                "The sun was gentle, and the world felt full of wonder."
            ),
        },
        {
            "id": "s3",
            "emoji": "🌈",
            "caption": "Something to learn",
            "image_query": image_queries[2],
            "narration_line": (
                f"But oh my, {hero} had a big feeling in their heart. "
                "Sometimes the right thing feels hard, doesn't it? "
                "Grandma squeezes your hand — you are brave enough to try."
            ),
        },
        {
            "id": "s4",
            "emoji": "🌟",
            "caption": "Happy ending",
            "image_query": image_queries[3],
            "narration_line": (
                f"And do you know what happened? {hero} chose kindness. "
                "Friends smiled, hearts felt lighter, and everyone played together. "
                "That is how love grows."
            ),
        },
        {
            "id": "s5",
            "emoji": "💛",
            "caption": "Remember",
            "image_query": image_queries[4],
            "narration_line": (
                "So remember, my sunshine: be kind, be honest, and share what you can. "
                "Grandma loves you very much. Sweet dreams till our next story."
            ),
        },
    ]

    narration = " ".join(s["narration_line"] for s in scenes)
    return {
        "schema_version": "1",
        "title": title,
        "moral": "Be kind, be honest, and share what you can.",
        "template_id": template_id,
        "duration_target_sec": duration_target_sec,
        "content_source": content_source,
        "scenes": scenes,
        "narration": narration,
    }
