import json
import re
from pathlib import Path
from typing import Any

from app.pipeline.image_queries import build_scene_image_queries
from storytime_common.settings import Settings

INTRO_SECONDS = 5
CONTENT_SCENE_COUNT = 4


def _template_manifest(template_id: str) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[4] / "templates" / template_id / "manifest.json"
    if not root.exists():
        root = Path("/app/templates") / template_id / "manifest.json"
    return json.loads(root.read_text(encoding="utf-8"))


def _strip_markdown(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"^[-*]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _story_title(prompt: str) -> str:
    clean = _strip_markdown(prompt)
    if m := re.search(r"[\"'“]([^\"'”]{4,72})[\"'”]", clean):
        return m.group(1).strip()
    if m := re.search(r"based on (?:the )?(?:Sanskrit prayer )?[\"'“]?([^\"'”.]{4,60})", clean, re.I):
        return m.group(1).strip().title()
    first = re.split(r"[.\n]", clean)[0].strip()
    if re.match(r"create a ", first, re.I) and len(clean) > 80:
        if "saraswati" in clean.lower():
            return "Saraswati Namastubhyam"
        return "A Story for You"
    if len(first) < 8:
        return "A Special Story for You"
    return first[:72]


def _content_slot_sec(duration_target_sec: int) -> float:
    remaining = max(duration_target_sec - INTRO_SECONDS, CONTENT_SCENE_COUNT * 8)
    return round(remaining / CONTENT_SCENE_COUNT, 2)


def _content_narration_and_captions(prompt: str, title: str) -> list[dict[str, str]]:
    p = prompt.lower()
    if _has_any(p, ("saraswati", "sarasvati", "namastubhyam", "vidyarambham")):
        return [
            {
                "caption": title,
                "narration_line": "We bow to Goddess Saraswati, who brings wisdom, music, and learning.",
            },
            {
                "caption": "Prayer",
                "narration_line": (
                    "Saraswati Namastubhyam. We ask her blessing as we begin our studies."
                ),
            },
            {
                "caption": "Learn with joy",
                "narration_line": (
                    "Read, write, and sing with a peaceful heart. Respect your teachers and stay curious."
                ),
            },
            {
                "caption": "Jai Maa Saraswati",
                "narration_line": "Learn with joy. Grow with wisdom. Grandma loves you. Jai Maa Saraswati!",
            },
        ]
    if _has_any(p, ("pray", "prayer", "temple", "devotion", "worship", "god", "goddess")):
        return [
            {
                "caption": title,
                "narration_line": "Grandma shares a gentle prayer story for children everywhere.",
            },
            {
                "caption": "Quiet heart",
                "narration_line": "We pause, breathe, and thank the good in our lives.",
            },
            {
                "caption": "Kindness",
                "narration_line": "Be kind to family and friends. Small good deeds matter.",
            },
            {
                "caption": "Remember",
                "narration_line": "Carry peace in your heart. Grandma is always cheering for you.",
            },
        ]
    topic = title.rstrip(".")
    if len(topic) > 48:
        topic = topic[:45] + "..."
    return [
        {
            "caption": topic,
            "narration_line": f"Today Grandma tells a short story about {topic}.",
        },
        {
            "caption": "Listen close",
            "narration_line": "Our friend learns that patience and honesty help every day.",
        },
        {
            "caption": "Choose kindness",
            "narration_line": "When we share and help others, everyone feels happier.",
        },
        {
            "caption": "Sweet dreams",
            "narration_line": "Be kind, be brave, and keep learning. See you next time!",
        },
    ]


def _has_any(text: str, words: tuple[str, ...]) -> bool:
    return any(w in text for w in words)


def generate_script(prompt: str, template_id: str, duration_target_sec: int, content_source: str) -> dict[str, Any]:
    """60s short: 5s channel intro + 4 image scenes with brief grandma narration."""
    settings = Settings()
    if settings.script_provider != "stub":
        raise NotImplementedError(f"SCRIPT_PROVIDER={settings.script_provider} not implemented yet")

    _template_manifest(template_id)
    idea = _strip_markdown(prompt)
    title = _story_title(prompt)
    slot = _content_slot_sec(duration_target_sec)
    image_queries = build_scene_image_queries(idea, title, "child")

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

    content = _content_narration_and_captions(idea, title)
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
