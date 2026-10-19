"""Build final script JSON: 5s intro + four content scenes."""

from typing import Any

INTRO_SECONDS = 5
CONTENT_SCENE_COUNT = 4


def content_slot_sec(duration_target_sec: int) -> float:
    remaining = max(duration_target_sec - INTRO_SECONDS, CONTENT_SCENE_COUNT * 8)
    return round(remaining / CONTENT_SCENE_COUNT, 2)


def assemble_script(
    *,
    title: str,
    moral: str,
    template_id: str,
    duration_target_sec: int,
    content_source: str,
    content_scenes: list[dict[str, str]],
    fallback_image_queries: list[str] | None = None,
) -> dict[str, Any]:
    slot = content_slot_sec(duration_target_sec)
    queries = fallback_image_queries or []

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

    for i, block in enumerate(content_scenes[:CONTENT_SCENE_COUNT]):
        image_q = block.get("image_query") or (queries[i] if i < len(queries) else "children illustration")
        scenes.append(
            {
                "id": f"s{i + 1}",
                "emoji": "✨",
                "caption": block["caption"],
                "image_query": image_q,
                "narration_line": block["narration_line"],
                "duration_sec": slot,
            }
        )

    narration = " ".join(s["narration_line"] for s in scenes)
    return {
        "schema_version": "1",
        "title": title,
        "moral": moral,
        "template_id": template_id,
        "duration_target_sec": duration_target_sec,
        "content_source": content_source,
        "scenes": scenes,
        "narration": narration,
    }
