import asyncio
import subprocess
import wave
from pathlib import Path
from typing import Any

import edge_tts

from storytime_common.settings import Settings


def _audio_duration_sec(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


async def _edge_to_mp3(text: str, voice: str, out_mp3: Path) -> None:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_mp3))


def _mp3_to_wav(mp3: Path, wav: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(mp3), str(wav)],
        check=True,
        capture_output=True,
    )


def _silent_wav(out_path: Path, duration_sec: float) -> Path:
    sample_rate = 22050
    frames = int(sample_rate * max(duration_sec, 2))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * frames)
    return out_path


def synthesize_line(text: str, out_wav: Path) -> Path:
    settings = Settings()
    out_wav.parent.mkdir(parents=True, exist_ok=True)

    if settings.tts_provider == "stub":
        return _silent_wav(out_wav, max(len(text) / 12.0, 3.0))

    if settings.tts_provider == "edge":
        mp3 = out_wav.with_suffix(".mp3")
        asyncio.run(_edge_to_mp3(text, settings.tts_voice, mp3))
        _mp3_to_wav(mp3, out_wav)
        mp3.unlink(missing_ok=True)
        return out_wav

    raise NotImplementedError(f"TTS_PROVIDER={settings.tts_provider} not implemented yet")


def synthesize_scenes(scenes: list[dict[str, Any]], work_dir: Path) -> list[Path]:
    """One grandma voice clip per scene; scene duration is fixed by the script (60s layout)."""
    wavs: list[Path] = []
    for i, scene in enumerate(scenes):
        line = scene.get("narration_line") or scene.get("caption") or ""
        path = work_dir / f"scene_{i:02d}.wav"
        synthesize_line(line, path)
        planned = scene.get("duration_sec")
        if planned is None:
            scene["duration_sec"] = round(_audio_duration_sec(path) + 0.35, 2)
        wavs.append(path)
    return wavs
