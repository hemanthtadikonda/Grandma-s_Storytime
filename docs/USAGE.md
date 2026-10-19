# Usage guide (one place)

Stack running → API on port **8000**.

| You are on | Base URL |
|------------|----------|
| VM (SSH) | `http://localhost:8000` |
| Your laptop | `http://<VM_PUBLIC_IP>:8000` |

**Health:** `GET /health` → `{"status":"ok"}`  
**Browser UI:** `/docs` (Swagger)

**Always send JSON** to `POST /jobs` — not plain story text (see [Fix 422 error](#fix-422-error) below).

Copy this body and change only `prompt`:

```json
{
  "prompt": "Your story idea in one or more sentences.",
  "template_id": "kids_moral_v1",
  "duration_target_sec": 60,
  "content_source": "original"
}
```

**Flow:** `POST /jobs` → copy `id` → `GET /jobs/{id}` until `status` is `done` → open `download_url` for the MP4.

---

<details>
<summary><strong>Swagger UI (/docs)</strong> — best for first video</summary>

1. Open `http://<host>:8000/docs`
2. **GET /health** → Try it out → Execute
3. **POST /jobs** → Try it out
4. Under Request body, paste the **full JSON** block from the top of this page (with your `prompt`)
5. Execute → expect **202** and an `id`
6. **GET /jobs/{job_id}** → paste `id` → Execute
7. Repeat step 6 every few seconds until `status` is `done`
8. Open `download_url` in a new browser tab

</details>

<details>
<summary><strong>curl</strong> — EC2 SSH or laptop</summary>

```bash
API=http://localhost:8000   # or http://<VM_PUBLIC_IP>:8000

JOB=$(curl -s -X POST "$API/jobs" -H "Content-Type: application/json" -d '{
  "prompt": "Mia learns to share her red ball at the park.",
  "template_id": "kids_moral_v1",
  "duration_target_sec": 60,
  "content_source": "original"
}')
echo "$JOB"
JOB_ID=$(echo "$JOB" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

while true; do
  curl -s "$API/jobs/$JOB_ID" | python3 -m json.tool
  STATUS=$(curl -s "$API/jobs/$JOB_ID" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  [ "$STATUS" = "done" ] || [ "$STATUS" = "failed" ] && break
  sleep 5
done

URL=$(curl -s "$API/jobs/$JOB_ID" | python3 -c "import sys,json; print(json.load(sys.stdin).get('download_url',''))")
curl -L -o my_short.mp4 "$URL"
```

</details>

<details>
<summary><strong>PowerShell</strong> — Windows</summary>

```powershell
$base = "http://<VM_PUBLIC_IP>:8000"   # or localhost

.\scripts\submit_job.ps1 -Prompt "Your story idea" -ApiBase $base
.\scripts\poll_job.ps1 -JobId "<job-id-from-output>" -ApiBase $base
```

Or without scripts:

```powershell
$body = @{
  prompt = "Your story idea"
  template_id = "kids_moral_v1"
  duration_target_sec = 60
  content_source = "original"
} | ConvertTo-Json

$job = Invoke-RestMethod -Method Post -Uri "$base/jobs" -ContentType "application/json" -Body $body
Invoke-RestMethod -Uri "$base/jobs/$($job.id)"
```

Open `download_url` when `status` is `done`.

</details>

<details>
<summary><strong>Postman / other tools</strong></summary>

Import OpenAPI: `http://<host>:8000/openapi.json`  
POST `/jobs` with the same JSON body as above.

`GET /artifacts/{id}` — same download as job id (for now `artifact_id` = `job_id`).

</details>

<details>
<summary><strong>Request fields</strong></summary>

| Field | Required | Notes |
|-------|----------|--------|
| `prompt` | Yes | Story idea; English works best with current voice |
| `template_id` | Yes | `kids_moral_v1` |
| `duration_target_sec` | No | Default `60` (15–180) |
| `content_source` | No | `original` or `public_domain` |
| `idempotency_key` | No | Optional; else server hashes prompt + template |

</details>

<details>
<summary><strong>Job statuses</strong></summary>

| `status` | Meaning |
|----------|---------|
| `queued` | Waiting for worker |
| `scripting` | Story text |
| `tts` | Voice (Edge TTS) |
| `rendering` | Video (FFmpeg) |
| `uploading` | Saving MP4 |
| `done` | Use `download_url` |
| `failed` | See `error`; run `docker compose logs worker` |

Usually **1–3 minutes** per video. Same prompt again may return `cached: true` with an existing file.

</details>

<details>
<summary><strong>Example prompt (Saraswati / learning)</strong></summary>

```json
{
  "prompt": "A gentle story for children and families: we pray to Goddess Saraswati for wisdom before learning. A child named Ananya is nervous about reading aloud; after a quiet prayer she tries again with patience. Moral: begin learning with gratitude and kindness.",
  "template_id": "kids_moral_v1",
  "duration_target_sec": 60,
  "content_source": "original"
}
```

Review the MP4 before YouTube upload.

</details>

<details>
<summary><strong>Fix 422 error</strong></summary>

Error: `json_invalid` / `JSON decode error`

**Cause:** Request body was only the story sentence, not JSON.

**Fix:** Body must be:

```json
{ "prompt": "...", "template_id": "kids_moral_v1", "duration_target_sec": 60, "content_source": "original" }
```

In Swagger, use **Edit Value** under POST /jobs, not a single line of text.

</details>

<details>
<summary><strong>Troubleshooting</strong></summary>

| Issue | Action |
|-------|--------|
| Connection refused | `docker compose ps`; open port 8000 in firewall |
| Stuck `queued` | `docker compose logs worker --tail 50` |
| `failed` at `tts` | VM needs internet (Edge TTS) |
| `failed` at `uploading` | S3 bucket + IAM role — [deploy/aws-s3-iam-role.md](deploy/aws-s3-iam-role.md) |
| 422 on POST | Use JSON body (see above) |

Restrict port **8000** to your IP so others cannot submit jobs.

</details>
