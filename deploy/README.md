# CI/CD & Deployment Guide (VPS + Caddy + GitHub Actions)

This guide walks you through setting up automated CI/CD for **Construction RAG** on your VPS (`46.224.86.196`) under `citerag.naimulworks.me`.

---

## 1. Architecture Overview

- **Server IP:** `46.224.86.196`
- **Domain:** `citerag.naimulworks.me`
- **Reverse Proxy:** Host Caddy (handles automatic SSL/TLS via Let's Encrypt / ZeroSSL)
- **Deployment Path:** `~/citation-rag` (under `root`)
- **Docker Services:**
  - `postgres` (pgvector on internal port 5432, host `127.0.0.1:5433`)
  - `backend` (FastAPI on host `127.0.0.1:8000`)
  - `frontend` (Next.js on host `127.0.0.1:3001`)
- **CI/CD:** GitHub Actions (`.github/workflows/deploy.yml`)
  - Auto-triggers on push to `bugfix-guardrailing`
  - Manual trigger via **"Run workflow"** with branch dropdown (`bugfix-guardrailing`, `main`, or `custom`)

---

## 2. Server Preparation (One-Time Setup)

### Step 2.1: Ensure SSH Access for GitHub Actions

If you don't already have a dedicated SSH key pair for deployment, generate one on your local machine:
```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ./deploy_key
```

Add the public key (`deploy_key.pub`) to your VPS `root` authorized keys:
```bash
cat deploy_key.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

Keep the **private key** (`deploy_key` content) for GitHub Secrets in Step 3.

---

### Step 2.2: Initial Project Setup & `.env` on VPS

SSH into your VPS and create the project directory and production `.env`:

```bash
mkdir -p ~/citation-rag
cd ~/citation-rag
```

Create or paste your `.env` file (`nano ~/citation-rag/.env`):
```dotenv
# LLM Provider Configuration
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash
GOOGLE_API_KEY=your_gemini_api_key_here

# Embedding Configuration
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_strong_postgres_password
POSTGRES_DB=construction_rag
DATABASE_URL=postgresql://postgres:your_strong_postgres_password@postgres:5432/construction_rag

# Host Port Bindings (Proxy targets for Caddy)
FRONTEND_PORT=127.0.0.1:3001
BACKEND_PORT=127.0.0.1:8000
POSTGRES_PORT=127.0.0.1:5433

# Domain & CORS Settings
CORS_ORIGINS=https://citerag.naimulworks.me,http://localhost:3001,http://127.0.0.1:3001
NEXT_PUBLIC_API_URL=

# Better Auth & Google OAuth
BETTER_AUTH_SECRET=generate_a_random_32_character_string_here
BETTER_AUTH_URL=https://citerag.naimulworks.me
NEXT_PUBLIC_BETTER_AUTH_URL=https://citerag.naimulworks.me
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

---

### Step 2.3: Configure Caddy on VPS

Open your Caddyfile on the VPS:
```bash
nano /etc/caddy/Caddyfile
```

Add the configuration for `citerag.naimulworks.me` (from `deploy/Caddyfile`):
```caddyfile
citerag.naimulworks.me {
    # Request body limit for PDF document uploads (50MB)
    request_body {
        max_size 50MB
    }

    # Compression
    encode zstd gzip

    # 1. FastAPI Backend API & Documentation
    handle /api/v1/* {
        reverse_proxy 127.0.0.1:8000 {
            header_up Host {upstream_hostport}
            header_up X-Real-IP {remote_host}
            header_up X-Forwarded-For {remote_host}
            header_up X-Forwarded-Proto {scheme}
        }
    }

    handle /docs* {
        reverse_proxy 127.0.0.1:8000
    }

    handle /openapi.json {
        reverse_proxy 127.0.0.1:8000
    }

    # 2. Next.js Frontend Application & Better-Auth (/api/auth/*)
    handle {
        reverse_proxy 127.0.0.1:3001 {
            header_up Host {upstream_hostport}
            header_up X-Real-IP {remote_host}
            header_up X-Forwarded-For {remote_host}
            header_up X-Forwarded-Proto {scheme}
        }
    }

    # Logging
    log {
        output file /var/log/caddy/citerag.access.log
    }
}
```

Reload Caddy to apply changes:
```bash
sudo systemctl reload caddy
```
*(Make sure your DNS A record for `citerag.naimulworks.me` points to `46.224.86.196` so Caddy can automatically obtain the Let's Encrypt SSL certificate).*

---

## 3. GitHub Repository Secrets Setup

In your GitHub repository:
1. Go to **Settings** > **Secrets and variables** > **Actions**.
2. Click **New repository secret** and add:

| Secret Name | Required | Value |
|---|---|---|
| `VPS_SSH_KEY` | **Yes** | Your private SSH key (entire contents starting with `-----BEGIN ...`) |
| `VPS_HOST` | Optional | `46.224.86.196` (defaults to `46.224.86.196` if not set) |
| `VPS_USER` | Optional | `root` (defaults to `root` if not set) |
| `VPS_PORT` | Optional | `22` (defaults to `22` if not set) |

---

## 4. Triggering Deployments

### A. Automatic Deployment
Pushing commits to the `bugfix-guardrailing` branch will automatically trigger the workflow and deploy the latest code to `46.224.86.196`.

### B. Manual Deployment (Switching Branches via GitHub Webpage)
1. Go to the **Actions** tab on GitHub:
   `https://github.com/SudinsHub/multimodal-rag-with-citation/actions`
2. Click on **Deploy to VPS** on the left sidebar.
3. Click the **"Run workflow"** button on the right.
4. Select the branch you want to deploy from the dropdown:
   - `bugfix-guardrailing`
   - `main`
   - `custom` (enter custom branch in the input box)
5. Click **"Run workflow"**.
