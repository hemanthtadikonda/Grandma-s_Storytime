"""Derive short titles and phrases from any user prompt (no theme-specific branches)."""

import re

_STOPWORDS = frozenset(
    """
    a an the and or but for with from into about your you our their this that these those
    create make generate video second seconds minute child children friendly beautiful
    high quality suitable designed ages years main objective format visual style audio
    voice over background music text subtitles final requirements total duration must
    produce storyboard written script platform supports based on prayer devotional
    """.split()
)


def strip_markdown(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"^[-*]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _truncate_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text.rstrip(".")
    return " ".join(words[:max_words]).rstrip(".") + "."


def story_title(prompt: str, max_len: int = 56) -> str:
    """Short on-screen title from quotes, topic phrase, or first useful sentence."""
    clean = strip_markdown(prompt)
    if m := re.search(r"[\"'“]([^\"'”]{4,80})[\"'”]", clean):
        return _truncate_words(m.group(1).strip(), 8)[:max_len]

    if m := re.search(
        r"(?:based on|about|on the topic of)\s+[\"'“]?([^\"'”.:]{4,80})",
        clean,
        re.I,
    ):
        return _truncate_words(m.group(1).strip(), 8)[:max_len]

    for part in re.split(r"[.\n]", clean):
        part = part.strip()
        if len(part) < 10:
            continue
        if re.match(
            r"^(create|make|generate|use|show|include|begin|total|do not|video format|"
            r"main objective|visual style|audio|prayer to|final requirement)",
            part,
            re.I,
        ):
            continue
        part = re.sub(r"^(create a |make a |generate a )", "", part, flags=re.I)
        return _truncate_words(part, 10)[:max_len]

    return "Today's Story"


def idea_sentence(prompt: str, max_words: int = 20) -> str:
    """One brief line from the prompt for narration (never the full paste)."""
    clean = strip_markdown(prompt)
    for part in re.split(r"[.\n]", clean):
        part = part.strip()
        if len(part) < 15:
            continue
        if re.match(
            r"^(create|make|generate|visual style|audio and|text and|final requirement|"
            r"0–|0-|main objective|video format|\*\*)",
            part,
            re.I,
        ):
            continue
        if part.count(":") == 1 and len(part.split(":")[0]) < 25:
            continue
        return _truncate_words(part, max_words)
    return _truncate_words(clean, max_words)


def caption_safe(text: str, max_len: int = 42) -> str:
    line = strip_markdown(text).replace("\n", " ").strip()
    if len(line) <= max_len:
        return line
    return line[: max_len - 3].rstrip() + "..."


def search_keywords(prompt: str, title: str, limit: int = 6) -> list[str]:
    """Keywords from prompt + title for image search (generic)."""
    blob = f"{title} {strip_markdown(prompt)}".lower()
    words = re.findall(r"[a-z]{4,}", blob)
    seen: list[str] = []
    for w in words:
        if w in _STOPWORDS or w in seen:
            continue
        seen.append(w)
        if len(seen) >= limit:
            break
    return seen or ["story", "learning", "happy"]
