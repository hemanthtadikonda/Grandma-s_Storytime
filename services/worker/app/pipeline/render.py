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


def _ffmpeg_path(path: Path) -> str:
    return str(path).replace("\\", "/").replace(":", "\\:")


def _run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "")[-2500:]
        raise RuntimeError(f"ffmpeg failed: {tail}")


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
    caption_file: str,
    caption_color: str,
    font_size: int,
    from_image: bool,
) -> str:
    frames = max(int(dur * fps), 1)
    fade_out = max(dur - 0.4, 0.1)

    if from_image:
        # Moderate upscale — scale=8000 can OOM on small VMs
        motion = (
            f"scale=3840:-1,zoompan=z='min(1.06+0.001*on,1.18)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s={w}x{h}:fps={fps}"
        )
    else:
        motion = f"scale={w}:{h},fps={fps}"

    return (
        f"{motion},"
        f"fade=t=in:st=0:d=0.35,fade=t=out:st={fade_out:.2f}:d=0.35,"
        f"drawbox=x=40:y=h-280:w=w-80:h=200:color=0x000000@0.42:t=fill,"
        f"drawbox=x=40:y=h-280:w=w-80:h=200:color=0xffffff@0.15:t=6,"
        f"drawtext=fontfile={font_file}:textfile='{caption_file}':expansion=none:"
        f"fontcolor=0x{caption_color}:fontsize={font_size}:borderw=3:bordercolor=0x00000099:"
        f"x=(w-text_w)/2:y='h-th-90'"
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
            caption_path = tmp_path / f"caption_{i}.txt"
            caption_path.write_text(scene["caption"], encoding="utf-8")
            caption_file = _ffmpeg_path(caption_path)
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

            vf = _scene_video_filter(
                dur, fps, w, h, font_file, caption_file, caption_color, font_size, from_image
            )

            _run_ffmpeg(
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
                ]
            )
            scene_clips.append(scene_mp4)

        list_file = tmp_path / "concat.txt"
        list_file.write_text("\n".join(f"file '{p}'" for p in scene_clips), encoding="utf-8")
        _run_ffmpeg(
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
            ]
        )

    return out_mp4
