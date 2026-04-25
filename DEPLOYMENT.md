# 🚀 Deployment Guide

**Best free hosting:** Cloudflare Pages (frontend) + Render.com or Google Cloud Run (backend)

---

## ⭐ Option 1: Cloudflare Pages (Frontend) + Render.com Free (Backend) 

**COMPLETELY FREE** ✨

### A. Deploy Frontend to Cloudflare Pages (FREE)

1. **Sign up** → https://dash.cloudflare.com
2. **Pages** → Create project → Connect Git → Select repo
3. **Build settings:**
   - Framework: None (static site)
   - Build command: `echo "No build needed"`
   - Build output directory: `frontend`
4. **Environment variables:**
   - Name: `API_URL`
   - Value: Your Render backend URL (from step B below)
5. **Deploy!** → Instantly live, CDN cached globally

### B. Deploy Backend to Render.com (FREE)

1. **Sign up** → https://render.com
2. **New Web Service** → Connect GitHub → Select repo
3. **Settings:**
   - **Name:** any name
   - **Region:** Oregon (closest/fastest)
   - **Build:** `pip install -r backend/requirements.txt`
   - **Start:** `cd backend && gunicorn -w 4 -b 0.0.0.0:$PORT -k uvicorn.workers.UvicornWorker app.main:app`
4. **Add environment variable:**
   - `DATABASE_URL` = your Neon connection string
5. **Deploy!** → ⚠️ **Note:** Free tier sleeps after 15 mins, wakes on request

### C. Update Frontend API URL

Edit `frontend/app.js` line 1:
```javascript
// OLD:
const API = 'http://127.0.0.1:8001';

// NEW (replace with your Render URL):
const API = 'https://your-backend-name.onrender.com';
```

---

## Option 2: Google Cloud Run (FREE, No Sleep!)

Better than Render free tier - **doesn't sleep**, first 2M requests/month FREE.

### Steps:

1. **Sign up** → https://cloud.google.com/run
2. **Create Service** → Deploy container
3. **Build from source:**
   ```bash
   gcloud run deploy metric-graph \
     --source . \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --memory 512Mi
   ```
4. **Set environment variable:**
   - `DATABASE_URL` = your Neon connection string
5. **Done!** → Your backend URL appears

**Frontend:** Still use Cloudflare Pages (same steps as Option 1A)

---

## Option 3: Railway (if trial renews)

Railway is **Python-friendly**, requires minimal config, has paid tier.

### Steps:

1. **Sign up** → https://railway.app
2. **Connect GitHub repo**
3. **Railway auto-detects FastAPI** from:
   - `requirements.txt`
   - `Procfile`
4. **Add environment variable:**
   - `DATABASE_URL` = your Neon connection string
5. **Deploy** → Automatic (~2 min)

**Cost:** Paid starting after trial ends (~$5-20/month depending on usage)

---

## Option 2: Render.com

Similar to Railway, very Python-friendly.

### Steps:

1. https://render.com → New Web Service
2. Connect GitHub repo
3. **Build command:** `pip install -r backend/requirements.txt`
4. **Start command:** `cd backend && gunicorn -w 4 -b 0.0.0.0:$PORT -k uvicorn.workers.UvicornWorker app.main:app`
5. Add `DATABASE_URL` env var
6. Deploy!

---

## Option 3: Docker Deployment (Any Cloud)

Works with Heroku, Railway, Render, or any Docker-compatible platform.

```bash
# Build locally to test
docker build -t metric-graph .
docker run -e DATABASE_URL="your-string" -p 8000:8000 metric-graph

# Then push to any cloud (Railway, Render, Heroku, AWS, GCP, etc.)
```

---

## Option 4: Heroku (Legacy but simple)

```bash
heroku login
heroku create your-app-name
heroku config:set DATABASE_URL="postgres://..."
git push heroku main
```

---

## ❌ Why NOT Vercel?

- ❌ Vercel is optimized for Node.js/JavaScript
- ❌ Python/FastAPI support requires serverless function restructuring
- ❌ Database connections in serverless functions are complex
- ❌ Limited to 10s request timeout on free tier

💡 **Recommendation:** Use **Railway** or **Render** for best experience with Python/FastAPI like this project.

---

## Get Database (FREE)

### Neon Cloud (Recommended)
- Free 3GB PostgreSQL
- Connection pooling included
- URL format: `postgresql://user:pwd@ep-xxx.neon.tech/db?sslmode=require`
- Sign up: https://neon.tech

### Supabase
- Free PostgreSQL + other features
- https://supabase.com

### AWS RDS (Paid)
- https://aws.amazon.com/rds/

---

## Final Checklist

- [ ] Database created (Neon/Supabase)
- [ ] Connection string copied to clipboard
- [ ] Code pushed to GitHub
- [ ] .env file NOT committed (check .gitignore)
- [ ] Railway/Render account created
- [ ] Repository connected
- [ ] DATABASE_URL env var set
- [ ] Deploy button clicked
- [ ] Check deployment logs
- [ ] Visit deployed app URL
- [ ] Click "Seed DB" to initialize

**Estimated time:** 5-10 minutes total
