import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any


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


def render_short(script: dict[str, Any], scene_wavs: list[Path], out_mp4: Path) -> Path:
    manifest = _manifest(script["template_id"])
    w = manifest["video"]["width"]
    h = manifest["video"]["height"]
    fps = manifest["video"]["fps"]
    font_size = manifest["style"]["font_size"]
    caption_color = manifest["style"].get("caption_color", "#FFF8E7").lstrip("#")
    scene_colors = manifest["style"].get(
        "scene_colors",
        ["#5B4BB4", "#E85D9A", "#3AAFB9", "#F4A261", "#6C63FF"],
    )
    font_file = _font_path(manifest)

    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    scene_clips: list[Path] = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i, scene in enumerate(script["scenes"]):
            caption = _escape_drawtext(scene["caption"])
            dur = float(scene["duration_sec"])
            bg = scene_colors[i % len(scene_colors)].lstrip("#")
            scene_mp4 = tmp_path / f"scene_{i}.mp4"
            audio = scene_wavs[i]

            # Gentle zoom + fade for a soft "animated" feel (kid-friendly, not flashy).
            vf = (
                f"color=c=0x{bg}:s={w}x{h}:d={dur},"
                f"zoompan=z='min(1.0+0.0008*on,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={int(dur * fps)}:s={w}x{h}:fps={fps},"
                f"fade=t=in:st=0:d=0.45,fade=t=out:st={max(dur - 0.45, 0.1):.2f}:d=0.45,"
                f"drawtext=fontfile={font_file}:"
                f"text='{caption}':fontcolor=0x{caption_color}:fontsize={font_size}:"
                f"borderw=4:bordercolor=0x00000066:"
                f"x=(w-text_w)/2:y=h*0.72-text_h/2"
            )
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    vf,
                    "-i",
                    str(audio),
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
