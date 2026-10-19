# Amazon S3 with EC2 IAM role (no access keys)

Use a real **S3 bucket** on EC2 without putting `S3_ACCESS_KEY` / `S3_SECRET_KEY` in `.env`. Credentials come from the **IAM instance profile** attached to the VM.

---

## 1. Create an S3 bucket

1. AWS Console → **S3** → **Create bucket**.
2. Name: e.g. `grandma-storytime-artifacts` (globally unique).
3. Region: same as your EC2 instance (e.g. `us-east-1`).
4. Block public access: **on** (downloads use presigned URLs from the API).
5. Create the bucket.

---

## 2. Create an IAM policy

**IAM** → **Policies** → **Create policy** → JSON:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "StorytimeArtifacts",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME"
    },
    {
      "Sid": "StorytimeObjects",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:HeadObject"
      ],
      "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME/*"
    }
  ]
}
```

Replace `YOUR_BUCKET_NAME`. Name the policy e.g. `GrandmaStorytimeS3`.

---

## 3. Create an IAM role for EC2

1. **IAM** → **Roles** → **Create role**.
2. Trusted entity: **AWS service** → **EC2**.
3. Attach policy: `GrandmaStorytimeS3` (from step 2).
4. Role name: e.g. `GrandmaStorytimeEC2Role`.

---

## 4. Attach the role to your instance

**EC2** → select your Ubuntu instance → **Actions** → **Security** → **Modify IAM role** → choose `GrandmaStorytimeEC2Role`.

No access keys are created or stored on disk.

---

## 5. Allow Docker containers to use the instance role

Containers must reach the **instance metadata** service for temporary credentials.

On the EC2 instance (once per instance):

```bash
# IMDSv2 hop limit 2 so containers can assume the instance role
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
curl -s -H "X-aws-ec2-metadata-token: $TOKEN" \
  http://169.254.169.254/latest/meta-data/iam/security-credentials/
```

You should see your role name. If containers still fail S3 access, set hop limit:

```bash
aws ec2 modify-instance-metadata-options \
  --instance-id "$(ec2-metadata -i | cut -d ' ' -f 2)" \
  --http-put-response-hop-limit 2 \
  --http-endpoint enabled
```

(Install `awscli` on the VM if needed, or change hop limit in the EC2 console under **Instance metadata options**.)

---

## 6. Configure the app

On the VM:

```bash
cd ~/Grandma-s_Storytime
cp .env.aws.example .env
nano .env
```

Set at minimum:

```env
STORAGE_BACKEND=aws
S3_BUCKET=grandma-storytime-artifacts
S3_REGION=us-east-1
```

For **LLM scripts** on the same EC2 instance, add (after installing Ollama on the host — see [ollama.md](ollama.md)):

```env
SCRIPT_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2:3b
```

See [IMPLEMENTATION.md](../IMPLEMENTATION.md) for the full pipeline.

Leave **unset** (remove if present): `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`.

Start **without** the MinIO profile:

```bash
docker compose up --build -d
```

Local laptop with MinIO still uses:

```bash
docker compose --profile minio up --build -d
```

---

## 7. Verify

```bash
docker compose exec worker python3 -c "
import boto3
b = boto3.client('s3', region_name='us-east-1')
print(b.list_objects_v2(Bucket='YOUR_BUCKET_NAME', MaxKeys=1))
"
```

Submit a job; when `done`, `download_url` should be a presigned S3 URL.

---

## Troubleshooting

| Issue | Fix |
|--------|-----|
| `Unable to locate credentials` | IAM role not attached to EC2, or hop limit not 2 for Docker |
| `Access Denied` on PutObject | IAM policy bucket ARN or `/*` object ARN wrong |
| `Cannot access S3 bucket` | Bucket name/region mismatch; create bucket first |
| Still using MinIO | `STORAGE_BACKEND` must be `aws`; do not start `--profile minio` |

See also: [ubuntu-docker-vm.md](ubuntu-docker-vm.md).
