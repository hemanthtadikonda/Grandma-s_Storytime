"""Generate bright, kid-friendly scene art when no custom image is provided."""

import colorsys
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _lighter(rgb: tuple[int, int, int], factor: float = 0.35) -> tuple[int, int, int]:
    return tuple(min(255, int(c + (255 - c) * factor)) for c in rgb)


def _template_assets_dir(template_id: str) -> Path:
    for base in (
        Path(__file__).resolve().parents[4] / "templates",
        Path("/app/templates"),
    ):
        p = base / template_id / "assets"
        if p.exists():
            return p
    return Path("/app/templates") / template_id / "assets"


def scene_image_path(template_id: str, scene_index: int, scene_id: str) -> Path | None:
    """Optional hand-made art: assets/scene_00.png or assets/scene_s1.jpg"""
    assets = _template_assets_dir(template_id)
    candidates = [
        assets / f"scene_{scene_index:02d}.png",
        assets / f"scene_{scene_index:02d}.jpg",
        assets / f"{scene_id}.png",
        assets / f"{scene_id}.jpg",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def generate_scene_art(
    width: int,
    height: int,
    base_color: str,
    scene_index: int,
    emoji: str = "",
    seed: int | None = None,
) -> Image.Image:
    rng = random.Random((seed or 0) + scene_index * 9973)
    top = _hex_to_rgb(base_color)
    bottom = _lighter(top, 0.55)
    img = Image.new("RGBA", (width, height))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        t = y / max(height - 1, 1)
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # Soft bubbles (common in kids apps)
    for _ in range(14):
        cx = rng.randint(-80, width + 80)
        cy = rng.randint(-80, height + 80)
        radius = rng.randint(40, 180)
        hue = (rng.random() + scene_index * 0.11) % 1.0
        sat = 0.45 + rng.random() * 0.25
        val = 0.85 + rng.random() * 0.15
        r, g, b = [int(255 * x) for x in colorsys.hsv_to_rgb(hue, sat, val)]
        alpha = rng.randint(35, 90)
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            fill=(r, g, b, alpha),
        )

    # Simple stars
    for _ in range(18):
        cx = rng.randint(40, width - 40)
        cy = rng.randint(40, height // 2)
        size = rng.randint(8, 22)
        _draw_star(draw, cx, cy, size, (255, 255, 220, rng.randint(120, 220)))

    # Central “story picture” frame area
    frame_margin = 90
    frame_top = int(height * 0.12)
    frame_bottom = int(height * 0.58)
    draw.rounded_rectangle(
        (frame_margin, frame_top, width - frame_margin, frame_bottom),
        radius=48,
        fill=(255, 255, 255, 55),
        outline=(255, 255, 255, 140),
        width=6,
    )

    if emoji:
        _draw_centered_emoji(draw, emoji, width // 2, (frame_top + frame_bottom) // 2)

    return img


def _draw_star(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, fill: tuple[int, int, int, int]) -> None:
    points = []
    for i in range(10):
        angle = i * 3.14159 / 5 - 3.14159 / 2
        r = size if i % 2 == 0 else size // 2
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(points, fill=fill)


def _draw_centered_emoji(draw: ImageDraw.ImageDraw, emoji: str, cx: int, cy: int) -> None:
    font = None
    for path, size in (
        ("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 200),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 160),
    ):
        if Path(path).exists():
            try:
                font = ImageFont.truetype(path, size)
                break
            except OSError:
                continue
    font = font or ImageFont.load_default()
    bbox = draw.textbbox((0, 0), emoji, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw // 2, cy - th // 2), emoji, font=font, embedded_color=True)


def write_scene_art(
    out_path: Path,
    width: int,
    height: int,
    base_color: str,
    scene_index: int,
    emoji: str = "",
) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    art = generate_scene_art(width, height, base_color, scene_index, emoji=emoji)
    art.convert("RGB").save(out_path, "PNG")
    return out_path
