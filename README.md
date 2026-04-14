# Causal Financial Knowledge Graph

A comprehensive financial analytics platform that traces **causal chains behind business metric changes**. Built for food delivery businesses (like Swiggy), it supports natural language queries and provides multi-level decomposition of financial drivers with business context.

## Features

✅ **Natural Language Queries** — Ask "Why did revenue increase in Q3 2023?" without SQL  
✅ **Multi-Level Causal Decomposition** — Traces changes through 3 levels: formula deps → causal drivers → sub-drivers  
✅ **Hierarchical Graph Visualization** — See metric relationships left-to-right (base inputs → derived metrics → revenue)  
✅ **Business Event Enrichment** — Attach context (campaigns, expansions, policy changes) to metric changes  
✅ **Analyst Summary Generation** — Auto-generated narratives explaining changes  
✅ **Zero LLM Dependency** — Rule-based parsing + mathematical attribution (no API calls)  

## Tech Stack

**Backend:**
- FastAPI 0.104.1 (Python 3.13)
- SQLAlchemy 2.0.45 (ORM)
- PostgreSQL (Neon Cloud)
- NetworkX 3.6.1 (Graph algorithms)
- Gunicorn (Production server)

**Frontend:**
- HTML5 + CSS3 (dark mode)
- Vanilla JavaScript (no frameworks)
- SVG for graph visualization

## Project Structure

```
newmetric/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app
│   │   ├── config.py               # Configuration
│   │   ├── database.py             # SQLAlchemy setup
│   │   ├── models/
│   │   │   └── db_models.py        # ORM (5 tables)
│   │   ├── metrics/
│   │   │   ├── registry.py         # 17 metrics + 27 relationships + formulas
│   │   │   ├── engine.py           # Gradient-based attribution algorithm
│   │   │   └── seeder.py           # DB population
│   │   ├── graph/
│   │   │   ├── builder.py          # NetworkX graph from DB
│   │   │   └── inference.py        # Multi-level causal inference
│   │   ├── query/
│   │   │   ├── parser.py           # Regex + keyword NL parsing
│   │   │   └── handler.py          # Query orchestration
│   │   └── api/
│   │       └── routes.py           # 10 REST endpoints
│   ├── requirements.txt
│   ├── .env                        # DB_URL, DEBUG flag
│   └── wsgi.py                     # Gunicorn entry
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── vercel.json                     # Vercel deployment config
├── .gitignore
└── README.md
```

## Setup

### Local Development

**1. Prerequisites**
```bash
Python 3.13+
PostgreSQL (or use Neon Cloud for free)
Git
```

**2. Clone & Install**
```bash
git clone https://github.com/Nishchalpr4/metric-graph
cd newmetric
pip install -r backend/requirements.txt
```

**3. Configure Database**
```bash
# Create .env file
echo 'DATABASE_URL=postgresql://user:password@localhost:5432/metrics' > backend/.env
echo 'DEBUG=true' >> backend/.env
```

**4. Initialize Database**
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```
Then open http://localhost:8001 and click "Seed DB" button.

**5. Open Frontend**
Navigate to `frontend/index.html` in your browser (or serve via Python)
```bash
python -m http.server 8000 --directory frontend
```

### Sample Queries

After seeding, try these questions:
- "Why did revenue increase in Q3 2023?"
- "What caused AOV to rise in Q3 2023?"
- "What drove GMV growth in Q3 2023 vs Q2 2023?"
- "Show revenue trends for Food Delivery"
- "Why did discounts increase in Q3 2023?"

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Health check |
| `/api/seed` | POST | Reset & populate database |
| `/api/periods` | GET | List all periods |
| `/api/segments` | GET | List all segments |
| `/api/metrics` | GET | List all metrics with formulas |
| `/api/metric/{name}` | GET | Single metric definition + time-series |
| `/api/graph` | GET | Full relationship graph (JSON) |
| `/api/suggestions` | GET | Sample queries for UI |
| `/api/query` | POST | Natural language query handler |
| `/api/analyse` | POST | Structured analysis (programmatic) |

## Analysis Algorithm

When you query "Why did Revenue increase in Q3 2023?"

**1. Parse** → Extract metric, period, direction  
**2. Fetch Data** → Get Q3 2023 vs Q2 2023 values  
**3. Decompose** → Use formula: `Revenue = GMV × Commission − Discounts + Delivery`  
**4. Attribute** → Gradient-based contribution of each input
**5. Recurse** → For each major driver (GMV), find its drivers (Orders, AOV)  
**6. Enrich** → Attach business events from that period  
**7. Summarize** → Generate analyst narrative  
**8. Visualize** → Render hierarchical graph  

**Output:** Complete causal chain with all 3 levels visible

## Deployment to Vercel

### ⚠️ Important: Vercel Python Support

Vercel has **limited native Python support**. For FastAPI applications, we recommend:

**Option A: Deploy with Docker (Recommended for Vercel)**
**Option B: Use Railway, Render, or Heroku (Better for Python)**

---

### Option A: Docker Deployment to Vercel

**Prerequisites:**
- Vercel account: https://vercel.com
- Docker installed locally

**Steps:**

1. **Push to GitHub**
```bash
git add .
git commit -m "Vercel deployment with Docker"
git push origin main
```

2. **Connect to Vercel**
   - Go to https://vercel.com/new
   - Import your GitHub repo
   - Select "Docker" as the framework
   - Add environment variables:
     - `DATABASE_URL`: Your PostgreSQL connection string
     - `DEBUG`: `false`
   - Click Deploy

3. **Get Database (Neon Cloud - Free)**
   - Sign up: https://neon.tech
   - Create project → Copy connection string
   - Paste into Vercel env vars

---

### Option B: Deploy to Railway (Easier for Python)

**Recommended: Railway is optimized for Python apps**

1. **Sign up**: https://railway.app
2. **Connect GitHub repo**
3. **Set environment variable**: `DATABASE_URL`
4. **Deploy**

Railway auto-detects FastAPI and starts the server automatically (~3 minutes).

---

### Option C: Deploy to Render

**Also Python-friendly:**

1. **Sign up**: https://render.com
2. **Create new Web Service**
3. **Connect GitHub**
4. **Build command**: `pip install -r backend/requirements.txt`
5. **Start command**: `cd backend && gunicorn -w 4 -b 0.0.0.0:$PORT -k uvicorn.workers.UvicornWorker app.main:app`
6. **Set `DATABASE_URL` env var**
7. **Deploy**

---

### Option D: Deploy to Heroku

**If you have Heroku account:**

```bash
heroku login
heroku create your-app-name
heroku config:set DATABASE_URL="postgresql://..."
git push heroku main
```

---

### Database Configuration

All deployment options need a PostgreSQL database.

**Best options:**
1. **Neon Cloud** (Free, 3GB) - https://neon.tech
2. **Supabase** (Free PostgreSQL) - https://supabase.com
3. **AWS RDS** (Paid, scalable)

**Steps for Neon:**
1. Create account → Create project
2. Copy connection string ending with `?sslmode=require`
3. Add to deployment platform env vars as `DATABASE_URL`

---

### First Deployment Checklist

- [ ] Database created & connection string saved
- [ ] Environment variables configured (`DATABASE_URL`, `DEBUG=false`)
- [ ] `.env` file NOT committed to GitHub (check `.gitignore`)
- [ ] Code pushed to GitHub main branch
- [ ] Deployment platform connected & deployed
- [ ] Check logs for errors: `DATABASE_URL connected successfully`
- [ ] Open deployed app → Click "Seed DB" to initialize database
- [ ] Test with sample query in UI

---

### Local Testing Before Deployment

```bash
# Test with Docker locally
docker build -t metric-graph .
docker run -e DATABASE_URL="your-connection-string" -p 8000:8000 metric-graph

# Or test directly
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# Visit http://localhost:8000
```

## Configuration

Edit `backend/metrics/registry.py` to:
- Add/remove metrics
- Define formulas
- Create new causal relationships
- Seed custom time-series data

## Performance

- **Query latency:** ~200ms (parsing + DB + inference)
- **Graph rendering:** ~500ms (SVG generation)
- **Inference depth:** Max 3 levels to prevent explosion
- **DB queries:** Single-threaded but optimized with indexes

## Future Enhancements

- [ ] ML-based causal discovery (to auto-detect relationships)
- [ ] Time-series forecasting (what-if scenarios)
- [ ] Segment-level attribution (break down by geo, user cohort)
- [ ] Custom metric definitions (UI builder)
- [ ] PDF report generation
- [ ] Team collaboration (comments, annotations)
- [ ] Real-time data ingestion (webhook API)

## License

MIT

## Support

For issues, open a GitHub issue or contact the maintainers.
