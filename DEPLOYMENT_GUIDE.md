# Deployment Guide

## Current Status
✅ **Backend (FastAPI)** - Working perfectly locally with 209 companies, 44 periods, 15,010 filings
✅ **Database (Neon PostgreSQL)** - All data verified and accessible
✅ **Frontend (Vanilla JS)** - Ready to deploy to Vercel

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    VERCEL (Frontend)                     │
│              (HTML, CSS, JS Static Files)                │
│                   ↓ Fetch Requests ↓                     │
├─────────────────────────────────────────────────────────┤
│              RENDER/RAILWAY (Backend API)                │
│         (FastAPI + Python + Database Driver)             │
│                   ↓ Query ↓                              │
├─────────────────────────────────────────────────────────┤
│              NEON (PostgreSQL Database)                  │
│         (209 companies, 44 periods, 15,010 filings)      │
└─────────────────────────────────────────────────────────┘
```

## Option A: Local Development (Free, Quick Testing)

### Step 1: Start Backend Locally
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Step 2: Update Frontend API URL
Edit `frontend/app.js`:
```javascript
const API_BASE = 'http://127.0.0.1:8000';  // Local backend
```

### Step 3: Run Frontend
```bash
# Option 1: Simple HTTP server
cd frontend
python -m http.server 8001

# Option 2: Vercel CLI for testing
vercel dev
```

Then visit: `http://localhost:8001`

✅ All features work locally!

---

## Option B: Production Deployment (Recommended)

### Step 1: Deploy Backend to Render
1. Go to https://render.com (Sign up with GitHub)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && gunicorn -w 4 -b 0.0.0.0:$PORT app.main:app`
   - **Environment Variables**:
     - `DATABASE_URL=postgresql://neondb_owner:...` (from your .env)
5. Select Instance: **Starter ($7/month)** to prevent spin-down
6. Deploy → Copy the backend URL (e.g., `https://your-backend.onrender.com`)

**OR** Use Railway.app (often cheaper):
1. Go to https://railway.app
2. New Project → Deploy from GitHub
3. Add environment: `DATABASE_URL`
4. Costs approximately $5-10/month

### Step 2: Deploy Frontend to Vercel
1. Update `frontend/app.js`:
```javascript
const API_BASE = 'https://your-backend.onrender.com';  // Production backend
```

2. Create `vercel.json` in root:
```json
{
  "buildCommand": "echo 'Deploying frontend only'",
  "installCommand": "echo 'No install needed'",
  "outputDirectory": "frontend"
}
```

3. Push to GitHub
4. Go to https://vercel.com → Import Project → Select repo
5. Deploy

### Step 3: Test Production
Visit your Vercel domain → Click "Seed DB" → Should show:
```json
{
  "companies": 209,
  "periods": 44,
  "filings": 15010,
  "metrics_loaded": 10
}
```

---

## Quick Summary

| Setup | Cost | Uptime | Setup Time |
|-------|------|--------|-----------|
| **Local Dev** | $0 | While running | 2 min ✅ |
| **Render (Free)** | $0 | 15 min then sleeps ❌ | 10 min |
| **Render (Starter)** | $7/mo | 24/7 ✅ | 10 min |
| **Railway** | $5-10/mo | 24/7 ✅ | 10 min |
| **Fly.io** | $3-5/mo | 24/7 ✅ | 10 min |

---

## Files Ready to Deploy

✅ `backend/app/` - All Python FastAPI code
✅ `backend/requirements.txt` - Dependencies
✅ `frontend/` - All static files (HTML, CSS, JS)
✅ `.env` - Database credentials (don't commit!)
✅ `vercel.json` - Frontend deployment config

---

## Current API Status

```
POST /api/seed                 → Initialize database (209 companies ✅)
POST /api/query                → Natural language queries
GET  /api/debug/database-raw   → Raw SQL data verification
GET  /api/companies-with-data  → List all companies
GET  /api/available-data       → List available periods/metrics
```

All endpoints tested and working ✅
