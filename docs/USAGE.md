# Usage guide (one place)

Stack running → API on port **8000**.

| You are on | Base URL |
|------------|----------|
| VM (SSH) | `http://localhost:8000` |
| Your laptop | `http://<VM_PUBLIC_IP>:8000` |

**Health:** `GET /health`  
**Browser UI:** `/docs`

## You only need a prompt

Users send **plain text** — no JSON.

**Flow:** `POST /jobs` (paste prompt) → copy `id` → `GET /jobs/{id}` until `done` → open `download_url`.

The API turns your text into an internal job automatically (`kids_moral_v1`, ~60 seconds, etc.).

**Smarter scripts:** set `SCRIPT_PROVIDER=ollama` and run [Ollama](deploy/ollama.md). Without it, the worker uses rule-based `stub` only.

**How it works (developers):** [IMPLEMENTATION.md](IMPLEMENTATION.md) — 60 s layout, LLM, TTS, images, FFmpeg.

---

<details>
<summary><strong>Swagger UI (/docs)</strong></summary>

1. Open `http://<host>:8000/docs`
2. **POST /jobs** → **Try it out**
3. Under **Request body** → **Edit Value** (not the Curl block at the bottom), paste **only your story** — many lines OK
4. Do **not** paste the generated `curl -X POST ...` line into the box
5. **Execute** → **202** with an `id`
5. **GET /jobs/{job_id}** → poll until `status` is `done`
7. Open `download_url` for the MP4

**Poll every 5–10 seconds.** Status goes: `queued` → `scripting` → `tts` → `images` → `rendering` → `uploading` → **`done`**.  
While you saw `tts`, the job was still running — keep calling **GET /jobs/{id}** until `done` or `failed`.

Advanced options: **POST /jobs/json** (developers only).

</details>

<details>
<summary><strong>curl</strong></summary>

```bash
API=http://localhost:8000   # or your VM IP

JOB=$(curl -s -X POST "$API/jobs" \
  -H "Content-Type: text/plain; charset=utf-8" \
  --data-binary @- <<'EOF'
Mia learns to share her red ball with a shy new friend at the park.
EOF
)
echo "$JOB"
JOB_ID=$(echo "$JOB" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

while true; do
  curl -s "$API/jobs/$JOB_ID" | python3 -m json.tool
  STATUS=$(curl -s "$API/jobs/$JOB_ID" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  [ "$STATUS" = "done" ] || [ "$STATUS" = "failed" ] && break
  sleep 5
done
```

One line:

```bash
curl -s -X POST "$API/jobs" -H "Content-Type: text/plain" -d "Your story idea here."
```

</details>

<details>
<summary><strong>PowerShell</strong></summary>

```powershell
.\scripts\submit_job.ps1 -Prompt "Your story idea" -ApiBase "http://<VM_IP>:8000"
.\scripts\poll_job.ps1 -JobId "<job-id>" -ApiBase "http://<VM_IP>:8000"
```

</details>

<details>
<summary><strong>Advanced: POST /jobs/json</strong> (optional)</summary>

For scripts that need `idempotency_key`, `duration_target_sec`, etc.:

```json
{
  "prompt": "Your story",
  "template_id": "kids_moral_v1",
  "duration_target_sec": 60,
  "content_source": "original"
}
```

</details>

<details>
<summary><strong>Job statuses</strong></summary>

| `status` | Meaning |
|----------|---------|
| `queued` | Waiting for worker |
| `scripting` | Story JSON (Ollama or stub; may take up to ~90 s on CPU) |
| `tts` | Voice |
| `images` | Download scene pictures |
| `rendering` | Video |
| `uploading` | Saving MP4 |
| `done` | Use `download_url` |
| `failed` | See `error`; `docker compose logs worker` |

</details>

<details>
<summary><strong>Video shape (~60 seconds)</strong></summary>

- **5 seconds:** channel intro (“Grandma’s Storytime”, welcome) — branding card, no stock image.
- **~55 seconds:** **4 scenes** with images + grandma voice + on-screen captions.
- Long prompts are **summarized** for narration (never read word-for-word).

Default template: `kids_moral_v1` (1080×1920 vertical). Not 16:9 or full 3D.

</details>

<details>
<summary><strong>Scene images (auto)</strong></summary>

The script includes an `image_query` per content scene (from the LLM or keyword rules). The worker searches via `IMAGE_PROVIDER` (default Wikimedia). Temp files are deleted after the job. Override with PNGs in `templates/kids_moral_v1/assets/`.

</details>

<details>
<summary><strong>Environment (pipeline)</strong></summary>

| Variable | Purpose |
|----------|---------|
| `SCRIPT_PROVIDER` | `ollama` (recommended), `stub`, or `openai_compatible` |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | Local LLM — see [deploy/ollama.md](deploy/ollama.md) |
| `TTS_VOICE` | Edge TTS voice (default `en-GB-SoniaNeural`) |
| `IMAGE_PROVIDER` | `wikimedia`, `pexels`, `pixabay`, or `none` |

Full list: [IMPLEMENTATION.md](IMPLEMENTATION.md#environment-variables-pipeline).

</details>

<details>
<summary><strong>Troubleshooting</strong></summary>

| Issue | Action |
|-------|--------|
| 422 on `POST /jobs` | Use **text/plain** body, not JSON |
| Used JSON on `/jobs` by mistake | Use **POST /jobs/json** or switch to plain text |
| Stuck `queued` | `docker compose logs worker` |
| Same video again | Change prompt, `SCRIPT_PROVIDER`, or `idempotency_key` in `/jobs/json` |
| Dumb / generic story | Enable Ollama (`SCRIPT_PROVIDER=ollama`); check `docker compose logs worker` for LLM errors |
| `scripting` very slow | Normal with CPU Ollama; use a smaller model or more RAM |

</details>
