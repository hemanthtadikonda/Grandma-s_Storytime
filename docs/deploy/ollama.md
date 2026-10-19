# Open-source LLM scripts (Ollama)

The worker can write scene narration, captions, and image search phrases with a **local LLM** instead of the rules-only `stub` provider.

**See also:** [IMPLEMENTATION.md](../IMPLEMENTATION.md) (full pipeline, env vars, code map).

## Providers

| `SCRIPT_PROVIDER` | Use case |
|-------------------|----------|
| `stub` | No LLM (fast, limited quality) |
| `ollama` | [Ollama](https://ollama.com) on the same VM or in Docker |
| `openai_compatible` | vLLM, LocalAI, etc. (`LLM_OPENAI_BASE_URL` + `/v1/chat/completions`) |

If the LLM call fails, the worker **falls back to stub** and logs a warning so jobs still finish.

## Option A — Ollama in Docker Compose

```bash
docker compose --profile llm up -d ollama
docker compose exec ollama ollama pull llama3.2:3b
```

In `.env`:

```env
SCRIPT_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2:3b
```

Rebuild the worker:

```bash
docker compose up --build -d worker api
```

## Option B — Ollama on the EC2 host (recommended for RAM)

On the VM (outside Docker):

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b
sudo systemctl enable ollama
```

In `.env` (worker container reaches the host via `host.docker.internal` — already set in `docker-compose.yml`):

```env
SCRIPT_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2:3b
```

## Hardware

- **Minimum:** ~8 GB RAM for `llama3.2:3b` (CPU inference is slower but works).
- Larger models (`llama3.1:8b`, etc.) need more RAM and time per job.

## Verify

```bash
curl -s http://localhost:11434/api/tags
docker compose logs worker --tail 30
```

Submit a **new** job after changing `SCRIPT_PROVIDER` (cache key includes the provider).

## TTS and video

The LLM only improves the **script**. Voice is still Edge TTS; video is still FFmpeg + stock images — not full 3D or Sanskrit chanting unless you add those later.
