import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.pipeline.visuals import scene_image_path, write_scene_art


def _manifest(template_id: str) -> dict[str, Any]:
    for base in (
        Path(__file__).resolve().parents[4] / "templates",
        Path("/app/templates"),
    ):
        p = base / template_id / "manifest.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"template {template_id} not found")


def _escape_drawtext(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _font_path(manifest: dict[str, Any]) -> str:
    candidates = [
        manifest["style"].get("font_file"),
        "/usr/share/fonts/truetype/quicksand/Quicksand-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if path and Path(path).exists():
            return path
    return "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _scene_video_filter(
    dur: float,
    fps: int,
    w: int,
    h: int,
    font_file: str,
    caption: str,
    caption_color: str,
    font_size: int,
    from_image: bool,
) -> str:
    frames = max(int(dur * fps), 1)
    fade_out = max(dur - 0.4, 0.1)

    if from_image:
        motion = (
            f"scale=8000:-1,zoompan=z='min(1.08+0.0012*on,1.22)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s={w}x{h}:fps={fps}"
        )
    else:
        motion = f"scale={w}:{h},fps={fps}"

    # Caption card + gentle bounce (kids notice motion on text)
    caption_y = f"h-200+25*sin(2*PI*t/2.8)"
    return (
        f"{motion},"
        f"fade=t=in:st=0:d=0.35,fade=t=out:st={fade_out:.2f}:d=0.35,"
        f"drawbox=x=40:y=h-280:w=w-80:h=200:color=0x000000@0.42:t=fill,"
        f"drawbox=x=40:y=h-280:w=w-80:h=200:color=0xffffff@0.15:t=6,"
        f"drawtext=fontfile={font_file}:text='{caption}':fontcolor=0x{caption_color}:"
        f"fontsize={font_size}:borderw=3:bordercolor=0x00000099:"
        f"x=(w-text_w)/2:y={caption_y}"
    )


def render_short(
    script: dict[str, Any],
    scene_wavs: list[Path],
    out_mp4: Path,
    scene_images: list[Path | None] | None = None,
) -> Path:
    manifest = _manifest(script["template_id"])
    template_id = script["template_id"]
    w = manifest["video"]["width"]
    h = manifest["video"]["height"]
    fps = manifest["video"]["fps"]
    font_size = manifest["style"].get("caption_font_size", manifest["style"].get("font_size", 52))
    caption_color = manifest["style"].get("caption_color", "#FFF8E7").lstrip("#")
    scene_colors = manifest["style"].get(
        "scene_colors",
        ["#6C63FF", "#FF6B9D", "#4ECDC4", "#FFD166", "#9B5DE5"],
    )
    font_file = _font_path(manifest)

    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        scene_clips: list[Path] = []

        for i, scene in enumerate(script["scenes"]):
            caption = _escape_drawtext(scene["caption"])
            dur = float(scene["duration_sec"])
            scene_mp4 = tmp_path / f"scene_{i}.mp4"
            audio = scene_wavs[i]
            emoji = scene.get("emoji", "")
            bg = scene_colors[i % len(scene_colors)]

            fetched = scene_images[i] if scene_images and i < len(scene_images) else None
            custom = scene_image_path(template_id, i, scene.get("id", f"s{i}"))
            if fetched and fetched.is_file():
                image_input = fetched
                from_image = True
            elif custom:
                image_input = custom
                from_image = True
            else:
                image_input = write_scene_art(
                    tmp_path / f"art_{i}.png",
                    w,
                    h,
                    bg,
                    i,
                    emoji=emoji,
                )
                from_image = True

            vf = _scene_video_filter(dur, fps, w, h, font_file, caption, caption_color, font_size, from_image)

            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-loop",
                    "1",
                    "-i",
                    str(image_input),
                    "-i",
                    str(audio),
                    "-vf",
                    vf,
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-shortest",
                    str(scene_mp4),
                ],
                check=True,
                capture_output=True,
            )
            scene_clips.append(scene_mp4)

        list_file = tmp_path / "concat.txt"
        list_file.write_text("\n".join(f"file '{p}'" for p in scene_clips), encoding="utf-8")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c",
                "copy",
                str(out_mp4),
            ],
            check=True,
            capture_output=True,
        )

    return out_mp4
