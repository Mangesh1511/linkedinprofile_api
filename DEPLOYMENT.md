# 🚢 Production Deployment Guide (Public REST API)

This guide details how to deploy the **Reverse-Engineered LinkedIn Profile REST API** to production cloud platforms as a secure public web service.

---

## 🔒 Securing Your Public API

When deploying to the public internet, you must protect your endpoint from unauthorized traffic and abuse:

1. **Set `API_KEY` in Environment**:
   In your `.env` or cloud console environment variables, set:
   ```env
   API_KEY=your_secret_random_api_key_12345
   ```
2. **Client Request Authentication**:
   Public clients must send the `X-API-Key` HTTP header or `apiKey` query parameter:
   ```http
   GET /api/profileinfo?profileUrl=https://www.linkedin.com/in/williamhgates/
   X-API-Key: your_secret_random_api_key_12345
   ```

---

## Option 1: Google Cloud Run (Recommended for Public APIs)

Google Cloud Run scales to zero when idle and provides HTTPS domain endpoints automatically.

### 1-Command CLI Deployment:
```bash
gcloud run deploy linkedin-profile-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 2GiB \
  --cpu 2 \
  --no-cpu-throttling \
  --timeout 300s \
  --set-env-vars LINKEDIN_EMAIL="your_email@gmail.com",LINKEDIN_PASSWORD="your_password",API_KEY="your_secret_api_key"
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
3. Set environment variables (`LINKEDIN_EMAIL`, `LINKEDIN_PASSWORD`, `API_KEY`).
4. Deploy!
