"""Build per-scene image search queries from the user prompt (keyword heuristics)."""

import re


def _has_any(text: str, words: tuple[str, ...]) -> bool:
    t = text.lower()
    return any(w in t for w in words)


def build_scene_image_queries(prompt: str, title: str, hero: str) -> list[str]:
    p = prompt.lower()
    queries: list[str] = []

    if _has_any(p, ("saraswati", "sarasvati", "saraswathi")):
        queries = [
            "Saraswati goddess education veena",
            "Saraswati Hindu goddess art",
            "children reading books school",
            "child learning writing classroom",
            "children happy friends school",
        ]
    elif _has_any(p, ("pray", "prayer", "god", "goddess", "temple", "devotion", "worship")):
        queries = [
            "children prayer family",
            "temple lamp peaceful",
            "children meditation calm",
            "family spiritual together",
            "sunrise hope children",
        ]
    elif _has_any(p, ("share", "sharing", "kind", "kindness")):
        queries = [
            "children sharing toys",
            "kids friends playground happy",
            "children helping each other",
            "happy children classroom",
            "family love children",
        ]
    else:
        # Generic kids story — mix prompt words into middle scenes
        snippet = re.sub(r"[^\w\s]", "", prompt)[:50].strip() or "children story"
        queries = [
            "grandmother reading story children illustration",
            f"children {snippet} colorful",
            "child learning school books",
            "happy children friends outdoor",
            "children bedtime stars peaceful",
        ]

    # Personalize scene 2 with title/hero when short enough
    if hero and hero != "our little friend":
        queries[1] = f"child {hero} learning happy"
    if len(title) < 40:
        queries[1] = f"children {title} illustration"

    return queries[:5]
