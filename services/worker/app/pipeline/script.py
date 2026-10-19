import json
import logging
from pathlib import Path
from typing import Any

from app.pipeline.image_queries import build_scene_image_queries
from app.pipeline.prompt_extract import caption_safe, idea_sentence, story_title
from app.pipeline.script_assemble import assemble_script
from app.pipeline.script_llm import generate_llm_content_blocks
from storytime_common.settings import Settings

logger = logging.getLogger(__name__)


def _template_manifest(template_id: str) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[4] / "templates" / template_id / "manifest.json"
    if not root.exists():
        root = Path("/app/templates") / template_id / "manifest.json"
    return json.loads(root.read_text(encoding="utf-8"))


def _stub_content_scenes(prompt: str, title: str) -> list[dict[str, str]]:
    topic = caption_safe(title)
    idea = idea_sentence(prompt, max_words=18)
    if len(idea) < 12:
        idea = f"Grandma has a sweet tale about {topic.lower()}."

    return [
        {
            "caption": topic,
            "narration_line": f"Today, Grandma tells a short story about {topic}.",
            "image_query": "",
        },
        {"caption": "Listen close", "narration_line": idea, "image_query": ""},
        {
            "caption": "Something to learn",
            "narration_line": (
                "Our little friend learns that patience, honesty, and kindness help every day."
            ),
            "image_query": "",
        },
        {
            "caption": "Remember",
            "narration_line": (
                "Carry this story in your heart. Grandma loves you. See you next time!"
            ),
            "image_query": "",
        },
    ]


def generate_script(prompt: str, template_id: str, duration_target_sec: int, content_source: str) -> dict[str, Any]:
    """60s short: 5s intro + 4 scenes. Uses Ollama/open LLM when configured, else rules-based stub."""
    settings = Settings()
    _template_manifest(template_id)
    image_queries = build_scene_image_queries(prompt, story_title(prompt))

    provider = settings.script_provider.lower().strip()
    if provider in ("ollama", "openai_compatible"):
        try:
            llm = generate_llm_content_blocks(prompt, duration_target_sec)
            return assemble_script(
                title=llm["title"],
                moral=llm["moral"],
                template_id=template_id,
                duration_target_sec=duration_target_sec,
                content_source=content_source,
                content_scenes=llm["scenes"],
                fallback_image_queries=image_queries,
            )
        except Exception as exc:  # noqa: BLE001 — fall back so jobs still complete
            logger.warning("LLM script failed (%s), using stub: %s", provider, exc)

    if provider != "stub":
        logger.warning("Unknown SCRIPT_PROVIDER=%s, using stub", settings.script_provider)

    title = story_title(prompt)
    scenes = _stub_content_scenes(prompt, title)
    for i, scene in enumerate(scenes):
        if not scene.get("image_query") and i < len(image_queries):
            scene["image_query"] = image_queries[i]

    return assemble_script(
        title=title,
        moral="Be kind, be honest, and keep learning.",
        template_id=template_id,
        duration_target_sec=duration_target_sec,
        content_source=content_source,
        content_scenes=scenes,
        fallback_image_queries=image_queries,
    )
