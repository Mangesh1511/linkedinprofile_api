# 🚢 Production Deployment Guide (Public REST API)

This guide details how to deploy the **Reverse-Engineered LinkedIn Profile REST API** to production cloud platforms as a high-performance public web service.

---

## Option 1: Google Cloud Run (Recommended for Public APIs)

Google Cloud Run scales to zero when idle and provides HTTPS domain endpoints automatically.

### 1-Command CLI Deployment:
```bash
gcloud run deploy linkedin-profile-api \
  --source . \
  --platform managed \
  --region asia-south1 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 512Mi \
  --cpu 1 \
  --no-cpu-throttling \
  --timeout 300s \
  --set-env-vars LI_AT="your_li_at_cookie",JSESSIONID="ajax:your_jsessionid"
```

---

## Option 2: Docker Compose (VPS / AWS EC2 / DigitalOcean)

Run 24/7 on a Linux server:

```bash
docker-compose up -d --build
```

---

## Option 3: Render.com / Railway / Fly.io

1. Connect your GitHub repository to Render / Railway.
2. Choose **Docker** environment.
3. Set environment variables (`LI_AT`, `JSESSIONID`).
4. Deploy!
