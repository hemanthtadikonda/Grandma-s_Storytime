import hashlib


def prompt_hash(
    prompt: str,
    template_id: str,
    duration_target_sec: int,
    script_provider: str = "stub",
) -> str:
    payload = f"{template_id}|{duration_target_sec}|{script_provider}|{prompt.strip()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
