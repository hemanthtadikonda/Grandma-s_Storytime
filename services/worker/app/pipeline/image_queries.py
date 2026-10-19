"""Build per-scene image search queries from prompt keywords (works for any topic)."""

from app.pipeline.prompt_extract import search_keywords, strip_markdown


def build_scene_image_queries(prompt: str, title: str) -> list[str]:
    terms = search_keywords(prompt, title, limit=8)
    t0, t1, t2 = terms[0], terms[1] if len(terms) > 1 else "children", terms[2] if len(terms) > 2 else "happy"

    snippet = " ".join(terms[:4])[:60] or "children story"
    clean_title = strip_markdown(title)[:40]

    queries = [
        f"children {clean_title} illustration" if len(clean_title) > 3 else f"children {t0} {t1}",
        f"kids {t1} {t2} colorful",
        f"child learning {t0} school",
        f"happy children {t2} friends outdoor",
    ]

    # If prompt is very keyword-rich, rotate terms into later scenes
    if len(terms) > 4:
        queries[2] = f"children {terms[3]} {terms[4] if len(terms) > 4 else 'play'}"

    return queries[:4]
