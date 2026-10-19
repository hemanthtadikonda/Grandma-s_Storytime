# Deploy on Ubuntu VM (Docker Compose)

Run the video pipeline on any **Ubuntu Server VM** with Docker — API, worker, Redis, MinIO, grandma voice (Edge TTS), MP4 download.

Works the same on **AWS EC2**, **Hetzner**, **DigitalOcean**, **Linode**, **Azure VM**, or any provider that gives you Ubuntu + SSH.

**Time:** ~30–45 minutes first time  
**Cost:** depends on provider; e.g. AWS `t3.large` ~$60/mo if 24/7 — **stop the VM** when not rendering.

---

## What you will have at the end

| Item | URL / access |
|------|----------------|
| API + OpenAPI docs | `http://<VM_PUBLIC_IP>:8000/docs` |
| Submit jobs | `POST http://<VM_PUBLIC_IP>:8000/jobs` |
| MP4 artifacts | Presigned `download_url` on `GET /jobs/{id}` when `status` is `done` |
| MinIO console (optional, admin) | `http://<VM_PUBLIC_IP>:9001` — keep restricted |

The **worker must reach the internet** for Edge TTS (Microsoft speech). A VM with outbound HTTPS is required.

---

## 1. Provision an Ubuntu VM

Minimum: **2 vCPU, 8 GB RAM**, **30–40 GB** disk. Recommended: **4 vCPU, 8 GB** for faster FFmpeg builds.

**Firewall / security rules** (names differ by cloud; idea is the same):

| Port | Source | Purpose |
|------|--------|---------|
| 22 | **Your IP only** | SSH |
| 8000 | **Your IP only** | API (submit/poll jobs) |
| 9001 | **Your IP only** (optional) | MinIO web console |

**Do not** expose `6379` (Redis) or `9000` (MinIO API) to the whole internet.

### Example: AWS EC2

1. **EC2** → **Launch instance**.
2. **AMI:** Ubuntu Server **24.04 LTS** (or 22.04).
3. **Instance type:** `t3.large` (recommended). Minimum: `t3.medium` (slower).
4. **Key pair:** `.pem` for SSH.
5. **Public IP:** enabled.
6. **Security group:** rules in the table above.
7. Launch; note **Public IPv4** → use as `<VM_PUBLIC_IP>` below.

### Other providers

Create an **Ubuntu 24.04** server with the same ports, attach your SSH key, note the public IP. Continue from **§2 Connect with SSH** — the rest of this guide is identical.

---

## 2. Connect with SSH

Default user on Ubuntu cloud images is usually `ubuntu`:

```bash
chmod 400 /path/to/your-key.pem
ssh -i /path/to/your-key.pem ubuntu@<VM_PUBLIC_IP>
```

Windows PowerShell:

```powershell
ssh -i C:\path\to\your-key.pem ubuntu@<VM_PUBLIC_IP>
```

---

## 3. Install Docker on Ubuntu

Run on the VM:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git

sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${VERSION_CODENAME}") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo usermod -aG docker ubuntu
```

Log out and SSH back in:

```bash
exit
docker --version
docker compose version
```

---

## 4. Clone the project

```bash
cd ~
git clone https://github.com/YOUR_USER/Grandma-s_Storytime.git
cd Grandma-s_Storytime
```

If the repo is only on your laptop, push to GitHub first, or copy with `scp`/rsync.

---

## 5. Configure environment

```bash
cp .env.example .env
nano .env
```

**Important:** with Docker Compose, keep `redis` as hostname in `.env` — not `localhost`.

### Storage on EC2 (recommended): S3 + IAM role

Do **not** put access keys in `.env`. Attach an IAM role to the EC2 instance and use a real S3 bucket.

1. Follow **[aws-s3-iam-role.md](aws-s3-iam-role.md)** (bucket, policy, role, attach to instance).
2. On the VM:

   ```bash
   cp .env.aws.example .env
   nano .env   # set S3_BUCKET and S3_REGION only
   ```

3. Start stack **without** MinIO:

   ```bash
   docker compose up --build -d
   ```

### Storage for local dev: MinIO

```bash
cp .env.example .env
docker compose --profile minio up --build -d
```

Voice (both setups):

```env
TTS_PROVIDER=edge
TTS_VOICE=en-GB-SoniaNeural
```

US option: `en-US-JennyNeural`

### Scripts (recommended: Ollama on the host)

For prompts that are not turned into good stories by rules alone, use a **local open-source LLM**:

1. On the VM: install Ollama and `ollama pull llama3.2:3b` — full steps in **[ollama.md](ollama.md)**.
2. In `.env`:

   ```env
   SCRIPT_PROVIDER=ollama
   OLLAMA_BASE_URL=http://host.docker.internal:11434
   OLLAMA_MODEL=llama3.2:3b
   ```

3. Rebuild: `docker compose up --build -d worker`

Pipeline overview: **[IMPLEMENTATION.md](../IMPLEMENTATION.md)**.

---

## 6. Build and start the stack

```bash
cd ~/Grandma-s_Storytime
docker compose up --build -d
```

First build: **10–20 minutes**.

```bash
docker compose ps
docker compose logs -f worker
```

Health check on the VM:

```bash
curl -s http://localhost:8000/health
```

From your laptop (if firewall allows your IP on 8000):

```bash
curl -s http://<VM_PUBLIC_IP>:8000/health
```

Browser: `http://<VM_PUBLIC_IP>:8000/docs`

---

## 7. Create videos

See **[docs/USAGE.md](../USAGE.md)** — Swagger UI, curl, PowerShell, JSON body, 422 fix (expand sections in that file).

---

## 8. Operations

```bash
cd ~/Grandma-s_Storytime
docker compose logs -f api
docker compose logs -f worker
docker compose up --build -d   # after changes
docker compose down            # stop stack
docker compose up -d           # start again
```

**Save money:** stop or power off the VM when idle. Disk data usually persists; **public IP may change** on next start unless your provider gives a static IP (e.g. AWS Elastic IP).

---

## 9. Optional: run stack on boot

```bash
sudo nano /etc/systemd/system/grandma-storytime.service
```

```ini
[Unit]
Description=Grandma Storytime Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/Grandma-s_Storytime
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0
User=ubuntu
Group=ubuntu

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable grandma-storytime.service
sudo systemctl start grandma-storytime.service
```

---

## 10. Troubleshooting

| Problem | What to do |
|---------|------------|
| Cannot SSH | Firewall port 22, your IP, correct key, VM running |
| Cannot reach `:8000` | Open 8000 to your IP; test `curl localhost:8000/health` on VM first |
| Job stays `queued` | `docker compose logs worker`; `docker compose up -d worker` |
| `failed` at `tts` | Outbound HTTPS; `TTS_PROVIDER=edge` |
| `failed` at `rendering` | Logs + enough RAM (8 GB) |
| Out of disk | `df -h`; `docker system prune -a` |
| Same video for same prompt | Idempotency cache — change prompt slightly |

---

## 11. Security checklist

- [ ] SSH and **8000** limited to your IP
- [ ] EC2: S3 via **IAM role** (no keys in `.env`); local dev: MinIO not exposed publicly
- [ ] `.env` not in git
- [ ] Review MP4s before YouTube
- [ ] HTTPS (Caddy/nginx + domain) if API is exposed broadly

---

## 12. Channel workflow

1. **POST /jobs** with a moral prompt.  
2. Poll until `done`.  
3. Download MP4.  
4. Optional edit (e.g. CapCut + images).  
5. Upload to YouTube manually.  
6. Power off VM when done for the week.

---

## 13. Next upgrades

1. Voice / music (prayer lines, BGM).  
2. Custom illustrations per scene (beyond stock search).  
3. Static public IP / DNS for the API.  
4. Metrics and job duration dashboards.

LLM scripting and Ken Burns render are documented in **[IMPLEMENTATION.md](../IMPLEMENTATION.md)**.

---

## Quick reference

```bash
cd ~/Grandma-s_Storytime
docker compose up --build -d
curl -s http://localhost:8000/health
docker compose logs -f worker
docker compose down
```

**API:** `http://<VM_PUBLIC_IP>:8000`  
**Docs:** `http://<VM_PUBLIC_IP>:8000/docs`
