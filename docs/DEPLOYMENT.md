# 🚀 Soul Sense - Production Deployment Guide

This guide provides instructions for deploying the **Soul Sense** platform (Next.js 14 Frontend + FastAPI Backend) using GitHub.

---

## 🌟 Method 1: 1-Click Render Blueprint (Recommended for Full-Stack)

The repository includes a ready-to-use [`render.yaml`](../render.yaml) blueprint that automatically provisions and connects both the **FastAPI Backend** and **Next.js Frontend** web services.

### Steps:
1. Log in to [Render](https://render.com/) with your GitHub account.
2. Click **New +** > **Blueprint**.
3. Select your repository: `nupurmadaan04/SOUL_SENSE_EXAM`.
4. Render will automatically detect `render.yaml` and configure:
   - **`soulsense-backend`**: Python FastAPI Web Service running on port `8000`.
   - **`soulsense-frontend`**: Next.js Web Service running on port `3005`.
5. Set your secret environment variables:
   - `GEMINI_API_KEY`: Your Google Gemini API Key.
   - `SECRET_KEY`: Automatically generated secure string.
6. Click **Apply**. Both frontend and backend will build and deploy automatically on every `git push origin main`.

---

## ⚡ Method 2: Vercel (Frontend) + Render / Railway (Backend)

For ultra-fast global CDN delivery of the Next.js frontend:

### 1. Deploy Frontend on Vercel:
1. Go to [Vercel](https://vercel.com/) and sign in with GitHub.
2. Click **Add New Project** and import `nupurmadaan04/SOUL_SENSE_EXAM`.
3. In project settings:
   - **Root Directory**: Select `frontend-web`.
   - **Framework Preset**: Next.js.
4. Add Environment Variable:
   - `NEXT_PUBLIC_API_URL`: `https://soul-sense-exam.onrender.com/api/v1`
5. Click **Deploy**.


### 2. Deploy Backend on Render / Railway:
1. Create a **New Web Service** pointing to `nupurmadaan04/SOUL_SENSE_EXAM`.
2. Set **Root Directory** to `backend/fastapi`.
3. Set **Build Command**: `pip install -r requirements.txt`.
4. Set **Start Command**: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`.
5. Add Environment Variables:
   - `APP_ENV=production`
   - `SECRET_KEY=<your_random_32_char_key>`
   - `GEMINI_API_KEY=<your_gemini_api_key>`
   - `BACKEND_CORS_ORIGINS=https://your-vercel-app.vercel.app`

---

## 🐳 Method 3: Self-Hosted Docker Deployment

Deploy on any VPS, AWS EC2, GCP Compute Engine, or DigitalOcean Droplet using Docker Compose:

```bash
# 1. Clone the repository on your server
git clone https://github.com/nupurmadaan04/SOUL_SENSE_EXAM.git
cd SOUL_SENSE_EXAM

# 2. Configure production environment
cp .env.example .env
# Edit .env with your production credentials:
# nano .env

# 3. Build and launch containers
docker-compose up -d --build
```

---

## 🔄 Method 4: Automated GitHub Actions CI/CD

The repository includes [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) which automatically runs on every push to `main`:
- Validates FastAPI backend startup and migrations.
- Builds and compiles Next.js frontend modules.
- Builds Docker container images for both frontend and backend.

Whenever you push to `main`, GitHub Actions will verify your code and trigger deployment automatically.
