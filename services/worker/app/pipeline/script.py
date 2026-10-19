import json
from pathlib import Path
from typing import Any

from app.pipeline.image_queries import build_scene_image_queries
from app.pipeline.prompt_extract import caption_safe, idea_sentence, story_title
from storytime_common.settings import Settings

INTRO_SECONDS = 5
CONTENT_SCENE_COUNT = 4


def _template_manifest(template_id: str) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[4] / "templates" / template_id / "manifest.json"
    if not root.exists():
        root = Path("/app/templates") / template_id / "manifest.json"
    return json.loads(root.read_text(encoding="utf-8"))


def _content_slot_sec(duration_target_sec: int) -> float:
    remaining = max(duration_target_sec - INTRO_SECONDS, CONTENT_SCENE_COUNT * 8)
    return round(remaining / CONTENT_SCENE_COUNT, 2)


def _content_narration_and_captions(prompt: str, title: str) -> list[dict[str, str]]:
    """Four brief scenes — always derived from this job's prompt, never a fixed theme."""
    topic = caption_safe(title)
    idea = idea_sentence(prompt, max_words=18)
    if len(idea) < 12:
        idea = f"Grandma has a sweet tale about {topic.lower()}."

    return [
        {
            "caption": topic,
            "narration_line": f"Today, Grandma tells a short story about {topic}.",
        },
        {
            "caption": "Listen close",
            "narration_line": idea,
        },
        {
            "caption": "Something to learn",
            "narration_line": (
                "Our little friend learns that patience, honesty, and kindness help every day."
            ),
        },
        {
            "caption": "Remember",
            "narration_line": (
                "Carry this story in your heart. Grandma loves you. See you next time!"
            ),
        },
    ]


def generate_script(prompt: str, template_id: str, duration_target_sec: int, content_source: str) -> dict[str, Any]:
    """60s short: 5s channel intro + 4 image scenes; narration trimmed from the user's prompt."""
    settings = Settings()
    if settings.script_provider != "stub":
        raise NotImplementedError(f"SCRIPT_PROVIDER={settings.script_provider} not implemented yet")

    _template_manifest(template_id)
    title = story_title(prompt)
    slot = _content_slot_sec(duration_target_sec)
    image_queries = build_scene_image_queries(prompt, title)

    scenes: list[dict[str, Any]] = [
        {
            "id": "intro",
            "intro": True,
            "skip_image_search": True,
            "emoji": "📚",
            "caption": "Grandma's Storytime\nWelcome to our channel!",
            "narration_line": "Welcome to Grandma's Storytime!",
            "duration_sec": float(INTRO_SECONDS),
        },
    ]

    content = _content_narration_and_captions(prompt, title)
    for i, block in enumerate(content[:CONTENT_SCENE_COUNT]):
        scenes.append(
            {
                "id": f"s{i + 1}",
                "emoji": "✨",
                "caption": block["caption"],
                "image_query": image_queries[i] if i < len(image_queries) else "children illustration",
                "narration_line": block["narration_line"],
                "duration_sec": slot,
            }
        )

    narration = " ".join(s["narration_line"] for s in scenes)
    return {
        "schema_version": "1",
        "title": title,
        "moral": "Be kind, be honest, and keep learning.",
        "template_id": template_id,
        "duration_target_sec": duration_target_sec,
        "content_source": content_source,
        "scenes": scenes,
        "narration": narration,
    }
