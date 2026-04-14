# 🚀 Deployment Guide

**Note:** Vercel has limited support for FastAPI. We recommend **Railway** or **Render** instead.

---

## ⭐ Option 1: Railway (RECOMMENDED)

Railway is **Python-friendly**, requires minimal config, and has generous free tier.

### Steps:

1. **Sign up** → https://railway.app
2. **Connect GitHub repo**
3. **Railway auto-detects FastAPI** from:
   - `requirements.txt` (root or backend/)
   - `Procfile` (defines start command)
4. **Add environment variable:**
   - Go to Project Settings → Variables
   - Add: `DATABASE_URL` = your Neon connection string
5. **Deploy** → Railway automatically builds and deploys (~2 min)

**That's it!** No config files needed. Railway handles everything.

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
