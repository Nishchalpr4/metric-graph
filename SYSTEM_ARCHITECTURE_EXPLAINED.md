# Complete System Architecture & Code Flow Explanation

## 🏗️ SYSTEM OVERVIEW

```
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND (Browser)                          │
│                   (app.js, index.html, styles.css)              │
│  - User interface with metric graph visualization               │
│  - Natural language query input                                 │
│  - Interactive causal analysis display                          │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP Requests (JSON)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND API LAYER                            │
│                  (FastAPI on port 8000)                         │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  API Routes (app/api/routes.py)                      │      │
│  │  - /api/health         (server health check)         │      │
│  │  - /api/seed           (initialize database)         │      │
│  │  - /api/metrics        (list all metrics)            │      │
│  │  - /api/periods        (available time periods)      │      │
│  │  - /api/segments       (data segments)               │      │
│  │  - /api/graph          (metric dependency graph)     │      │
│  │  - /api/suggestions    (example queries)             │      │
│  │  - /api/metric/{name}  (metric details + data)       │      │
│  │  - /api/import-csv     (data import)                 │      │
│  │  - /api/analyse        (synchronous analysis)        │      │
│  │  - /api/query          (NL query processor)          │      │
│  └──────────────────────────────────────────────────────┘      │
│                         │                                       │
│  ┌──────────────────────┴──────────────────────────────┐       │
│  │  Core Processing Modules                           │       │
│  │                                                    │       │
│  │  1. Query Parser (app/query/parser.py)            │       │
│  │     - Converts natural language to structured      │       │
│  │                                                    │       │
│  │  2. Metrics Engine (app/metrics/engine.py)        │       │
│  │     - Computes derived metrics from base values    │       │
│  │     - Performs formula evaluation                  │       │
│  │                                                    │       │
│  │  3. Query Handler (app/query/handler.py)          │       │
│  │     - Orchestrates analysis pipeline               │       │
│  │     - Trend analysis, segment breakdown            │       │
│  │                                                    │       │
│  │  4. Graph Inference (app/graph/inference.py)      │       │
│  │     - Causal decomposition                         │       │
│  │     - Finds root causes of metric changes          │       │
│  │                                                    │       │
│  │  5. Metrics Loader (app/metrics/loader.py)        │       │
│  │     - Loads all metrics/formulas from DB           │       │
│  │     - Compiles formulas safely                     │       │
│  │     - Manages in-memory caches                     │       │
│  └────────────────────────────────────────────────────┘       │
│                         │                                       │
└─────────────────────────┼───────────────────────────────────────┘
                         │ SQL Queries (via SQLAlchemy ORM)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              DATA PERSISTENCE LAYER                             │
│           (PostgreSQL Database via Neon)                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  TABLE: metrics                                      │      │
│  │  Columns: id, name, display_name, formula,          │      │
│  │           formula_inputs, unit, category, is_base   │      │
│  │  Records: 18 metrics (11 base + 7 derived)          │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  TABLE: metric_relationships                         │      │
│  │  Columns: metric_id, driver_id, relationship_type,  │      │
│  │           strength, description                     │      │
│  │  Records: 24 relationships (formula + causal)       │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  TABLE: time_series_data                             │      │
│  │  Columns: metric_id, period, segment, value,        │      │
│  │           is_computed                               │      │
│  │  Records: 44+ (imported metrics data)               │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  TABLE: causal_events (audit trail)                 │      │
│  │  TABLE: query_log (query history)                   │      │
│  └──────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 REQUEST FLOW EXAMPLE: "Why did orders grow from Q1 to Q4 2023?"

### STEP 1️⃣: USER SUBMITS QUERY (Frontend)

**File:** `frontend/index.html` & `frontend/app.js`

```javascript
// When user clicks "Analyse" button:
const query = "Why did orders grow from Q1 to Q4 2023?";

// Send to backend via HTTP POST
fetch('http://localhost:8000/api/query', {
  method: 'POST',
  body: JSON.stringify({ query: query }),
  headers: { 'Content-Type': 'application/json' }
})
.then(response => response.json())
.then(data => {
  // Display results: root causes, graph visualization, etc.
  displayResults(data);
});
```

---

### STEP 2️⃣: API RECEIVES REQUEST (Backend Entry Point)

**File:** `backend/app/api/routes.py`

```python
@app.post("/api/query")
async def query_endpoint(request: QueryRequest):
    """
    Receives natural language query from frontend
    Orchestrates entire analysis pipeline
    """
    query_text = request.query
    
    # Call the query handler to process
    result = handle_query(query_text)
    
    return result
```

---

### STEP 3️⃣: PARSE NATURAL LANGUAGE (Query Parser)

**File:** `backend/app/query/parser.py`

```python
def parse_query(query_text: str) -> ParsedQuery:
    """
    Converts "Why did orders grow from Q1 to Q4 2023?"
    Into structured format the system can process
    """
    
    # Step 3.1: Extract metric name
    metric_name = extract_metric_name(query_text)
    # Result: "orders"
    
    # Step 3.2: Extract time periods
    periods = extract_periods(query_text)
    # Result: {"compare_period": "Q1 2023", "period": "Q4 2023"}
    
    # Step 3.3: Extract segment (customer segment)
    segment = extract_segment(query_text)
    # Result: "Overall" (default if not specified)
    
    # Step 3.4: Determine intent (what user is asking)
    intent = determine_intent(query_text)
    # Result: "explain_change" (not "trend", not "compare")
    
    return ParsedQuery(
        metric="orders",
        period="Q4 2023",
        compare_period="Q1 2023",
        segment="Overall",
        intent="explain_change"
    )
```

**How it extracts metric name:**
```python
def extract_metric_name(query: str) -> str:
    """
    Use fuzzy matching to find metric in query
    """
    # Get all available metrics from database
    metrics = METRIC_REGISTRY()  # Function call returns cached metrics
    metric_names = [m["name"] for m in metrics.values()]
    
    # Example: available_metrics = ["orders", "revenue", "gmv", ...]
    
    # Fuzzy match query against metric names
    closest_match = difflib.get_close_matches(
        query.lower(), 
        metric_names, 
        n=1, 
        cutoff=0.6
    )[0]
    
    # "Why did orders grow" → matches "orders"
    return closest_match
```

---

### STEP 4️⃣: LOAD DATA FROM DATABASE (Query Handler)

**File:** `backend/app/query/handler.py`

```python
def handle_query(parsed_query: ParsedQuery) -> AnalysisResult:
    """
    Implements the analysis pipeline:
    1. Load metric definitions
    2. Fetch time-series data
    3. Compute metrics
    4. Perform causal analysis
    5. Return results
    """
    
    # Step 4.1: Get metric definition from database
    metric = METRIC_REGISTRY()[parsed_query.metric]
    # Returns:
    # {
    #   "name": "orders",
    #   "display_name": "Orders",
    #   "formula": None (base metric, no formula),
    #   "unit": "M",
    #   "category": "Operational"
    # }
    
    # Step 4.2: Fetch time-series data from database
    db = SessionLocal()
    current_data = db.query(TimeSeriesData).filter(
        TimeSeriesData.metric_id == metric.id,
        TimeSeriesData.period == parsed_query.period,
        TimeSeriesData.segment == parsed_query.segment
    ).first()
    # Returns: TimeSeriesData(value=115000.0, period="Q4 2023")
    
    previous_data = db.query(TimeSeriesData).filter(
        TimeSeriesData.metric_id == metric.id,
        TimeSeriesData.period == parsed_query.compare_period,
        TimeSeriesData.segment == parsed_query.segment
    ).first()
    # Returns: TimeSeriesData(value=100000.0, period="Q1 2023")
    
    # Step 4.3: Calculate change metrics
    absolute_change = current_data.value - previous_data.value
    # 115000.0 - 100000.0 = 15000.0
    
    percent_change = (absolute_change / previous_data.value) * 100
    # (15000.0 / 100000.0) * 100 = 15.0%
    
    return {
        "metric": metric,
        "period": "Q4 2023",
        "value": 115000.0,
        "previous_value": 100000.0,
        "change": 15000.0,
        "percent_change": 15.0
    }
```

---

### STEP 5️⃣: COMPUTE DERIVED METRICS (Metrics Engine)

**File:** `backend/app/metrics/engine.py`

```python
def compute_all_metrics(base_values: dict) -> dict:
    """
    Takes base metric values (orders, aov, etc.)
    Computes all derived metrics using formulas
    
    Example input:
    {
        "orders": 115000,
        "aov": 330,
        "commission_rate": 26,
        "delivery_charges": 5600000,
        "discounts": 2300000
    }
    """
    
    # Step 5.1: Get computation order (topologically sorted)
    computation_order = COMPUTATION_ORDER()
    # Result: ['orders', 'aov', 'commission_rate', 'delivery_charges', 
    #          'discounts', 'gmv', 'revenue', 'take_rate', ...]
    # (base metrics first, then derived in dependency order)
    
    # Step 5.2: Get formula functions
    formula_functions = FORMULA_FUNCTIONS()
    # Result: {
    #   "gmv": lambda v: v["orders"] * v["aov"] / 1000,
    #   "revenue": lambda v: v["gmv"] * v["commission_rate"] / 100 + ...,
    #   ...
    # }
    
    # Step 5.3: Compute in order
    computed_values = base_values.copy()
    
    for metric_name in computation_order:
        if metric_name not in computed_values:
            # This is a derived metric
            formula_fn = formula_functions[metric_name]
            
            # Call the compiled formula function
            computed_values[metric_name] = formula_fn(computed_values)
    
    # Example computation:
    # gmv = orders * aov / 1000 = 115000 * 330 / 1000 = 37950
    # revenue = gmv * commission_rate/100 + delivery_charges - discounts
    #         = 37950 * 26/100 + 5600000 - 2300000
    #         = 9867 + 5600000 - 2300000 = 3309867
    
    return computed_values
```

**How formulas are compiled (at startup, in `loader.py`):**

```python
def _compile_formula(formula_str: str, inputs: List[str]) -> Callable:
    """
    Converts database formula string to safe Python lambda
    
    Input: formula_str = "gmv * commission_rate / 100 + delivery_charges - discounts"
           inputs = ["gmv", "commission_rate", "delivery_charges", "discounts"]
    """
    
    # Step 1: Replace metric names with safe variable access
    sanitized = formula_str
    for metric_name in sorted(inputs, key=len, reverse=True):
        # Use regex to replace whole words only
        pattern = r'\b' + re.escape(metric_name) + r'\b'
        sanitized = re.sub(pattern, f"v['{metric_name}']", sanitized)
    
    # Result after substitution:
    # "v['gmv'] * v['commission_rate'] / 100 + v['delivery_charges'] - v['discounts']"
    
    # Step 2: Create lambda with restricted namespace (SAFE!)
    safe_namespace = {
        'sqrt': math.sqrt,
        'log': math.log,
        'exp': math.exp,
        'abs': abs,
        'min': min,
        'max': max,
        'pow': pow,
        '__builtins__': {}  # ← This prevents eval/exec/import!
    }
    
    code = f"lambda v: ({sanitized})"
    # Result: "lambda v: (v['gmv'] * v['commission_rate'] / 100 + ...)"
    
    # Step 3: Compile and return
    formula_fn = eval(code, {"__builtins__": {}}, safe_namespace)
    
    return formula_fn
    
    # Now can be called safely:
    # formula_fn({"gmv": 37950, "commission_rate": 26, ...}) → 3309867
```

---

### STEP 6️⃣: CAUSAL ANALYSIS (Graph Inference)

**File:** `backend/app/graph/inference.py`

```python
def infer_causal_drivers(
    metric_name: str,
    current_value: float,
    previous_value: float,
    all_metrics: dict
) -> List[CausalDriver]:
    """
    When "orders" increased 15%, what caused it?
    
    Uses causal graph to find drivers
    """
    
    # Step 6.1: Get relationships from database
    relationships = RELATIONSHIP_DEFINITIONS()
    # Example relationships for "orders":
    # [
    #   {"metric": "orders", "driver": "active_users", "strength": 0.85},
    #   {"metric": "orders", "driver": "marketing_spend", "strength": 0.65},
    #   {"metric": "orders", "driver": "discounts", "strength": 0.55},
    # ]
    
    # Step 6.2: Get drivers for this metric
    drivers = [r for r in relationships if r["metric"] == metric_name]
    
    # Step 6.3: For each driver, check if it changed
    causal_drivers = []
    
    for driver in drivers:
        driver_name = driver["driver"]
        driver_strength = driver["strength"]
        
        # Get previous/current values of the driver
        driver_current = all_metrics[driver_name]
        driver_previous = get_previous_value(driver_name)
        
        # Calculate change in driver
        driver_change_pct = (driver_current - driver_previous) / driver_previous * 100
        
        # Estimate impact: change * strength
        # Example: active_users +4.5% * strength 0.85 = +3.8% impact on orders
        estimated_impact = driver_change_pct * driver_strength
        
        causal_drivers.append({
            "name": driver_name,
            "change": driver_change_pct,
            "impact": estimated_impact,
            "strength": driver_strength,
            "type": driver["type"]  # "causal" or "formula"
        })
    
    # Step 6.4: Sort by impact (highest first)
    causal_drivers.sort(key=lambda x: abs(x["impact"]), reverse=True)
    
    return causal_drivers
    
    # Returns:
    # [
    #   {"name": "active_users", "change": 4.5, "impact": 3.8, "strength": 0.85},
    #   {"name": "marketing_spend", "change": 8.3, "impact": 5.4, "strength": 0.65},
    #   {"name": "discounts", "change": 4.5, "impact": 2.5, "strength": 0.55},
    # ]
```

---

### STEP 7️⃣: BUILD RESPONSE (Format for Frontend)

**File:** `backend/app/api/routes.py`

```python
def format_response(
    parsed_query: ParsedQuery,
    computed_metrics: dict,
    causal_drivers: List[CausalDriver]
) -> dict:
    """
    Formats backend analysis into JSON for frontend display
    """
    
    metric = METRIC_REGISTRY()[parsed_query.metric]
    
    return {
        # The original question
        "query": "Why did orders grow from Q1 to Q4 2023?",
        
        # Structured interpretation
        "parsed": {
            "metric": "orders",
            "period": "Q4 2023",
            "compare_period": "Q1 2023",
            "segment": "Overall",
            "intent": "explain_change"
        },
        
        # The metric's values
        "metric": {
            "name": "orders",
            "display_name": "Orders",
            "value": 115000.0,
            "unit": "M",
            "period": "Q4 2023"
        },
        
        # Change metrics
        "change": {
            "absolute": 15000.0,
            "percent": 15.0,
            "previous": 100000.0,
            "current": 115000.0
        },
        
        # Root causes found
        "drivers": [
            {
                "name": "Active Users",
                "type": "causal",
                "change": 4.5,
                "impact": 3.8,
                "strength": 0.85
            },
            {
                "name": "Marketing Spend",
                "type": "causal",
                "change": 8.3,
                "impact": 5.4,
                "strength": 0.65
            },
            # ... more drivers
        ],
        
        # Summary for user display
        "summary": "Orders increased by 15% (100000.0M → 115000.0M) in Q4 2023 vs Q1 2023. " +
                   "Causal business drivers: Marketing Spend ↑ 8.3%, Active Users ↑ 4.5%, " +
                   "Platform Discounts ↑ 4.5%."
    }
```

---

### STEP 8️⃣: FRONTEND DISPLAYS RESULTS

**File:** `frontend/app.js`

```javascript
function displayResults(data) {
    // Display the summary
    document.getElementById('summary').textContent = data.summary;
    
    // Display the metric value
    document.getElementById('metric-value').textContent = 
        `${data.metric.value}${data.metric.unit}`;
    
    // Display the change
    document.getElementById('change').textContent = 
        `▲ +${data.change.absolute} (+${data.change.percent}%)`;
    
    // Display causal drivers as collapsible list
    for (let driver of data.drivers) {
        addDriverItem(driver);
    }
    
    // Build and display interactive graph
    drawMetricGraph(data.graph);
}
```

**Visual Result on Screen:**
```
╔══════════════════════════════════════════════════════════════╗
║  "Why did orders grow from Q1 to Q4 2023?"                  ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Orders       115000.0M                                      ║
║               ▲ +15000.0M (+15%)                             ║
║               Q1 2023 → Q4 2023 · Overall                    ║
║                                                              ║
║  Summary: Orders increased by 15% (100000.0M → 115000.0M)  ║
║  in Q4 2023 vs Q1 2023. Causal business drivers:            ║
║  Marketing Spend ↑ 8.3%, Active Users ↑ 4.5%               ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  Root Cause Analysis                                         ║
╠══════════════════════════════════════════════════════════════╣
║  ▶ Marketing Spend      [causal] ↑ 8.3%                     ║
║    ₹1200000.00B → ₹1300000.00B | +₹100000.00B              ║
║                                                              ║
║  ▶ Active Users         [causal] ↑ 4.5%                     ║
║    500000.0M → 525000.0M | +25000.0M                        ║
║                                                              ║
║  ▶ Platform Discounts   [causal] ↑ 4.5%                     ║
║    2200000.0B → 2300000.0B | +100000.0B                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

---

## 🗄️ DATABASE SCHEMA DETAILS

### Table 1: `metrics` (18 rows)

```sql
CREATE TABLE metrics (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE,           -- "orders", "revenue", etc.
    display_name VARCHAR(200),          -- "Orders", "Revenue", etc.
    description TEXT,                   -- Human explanation
    formula VARCHAR(500),               -- Formula string (NULL for base)
    formula_inputs TEXT[],              -- Input metric names (NULL for base)
    unit VARCHAR(50),                   -- "M", "₹B", "%", etc.
    category VARCHAR(100),              -- "Financial", "Operational", "User"
    is_base BOOLEAN DEFAULT TRUE        -- TRUE for base, FALSE for derived
);

-- Examples:
-- (1, "orders", "Orders", ..., NULL, NULL, "M", "Operational", TRUE)
-- (12, "gmv", "Gross Merchandise Value", ..., "orders * aov / 1000", 
--     ["orders", "aov"], "₹B", "Financial", FALSE)
-- (14, "revenue", "Revenue", ..., 
--     "gmv * commission_rate / 100 + delivery_charges - discounts",
--     ["gmv", "commission_rate", "delivery_charges", "discounts"],
--     "₹B", "Financial", FALSE)
```

### Table 2: `metric_relationships` (24 rows)

```sql
CREATE TABLE metric_relationships (
    id SERIAL PRIMARY KEY,
    metric_id INT REFERENCES metrics(id),    -- The metric being driven
    driver_id INT REFERENCES metrics(id),    -- The driver metric
    relationship_type VARCHAR(50),           -- "formula" or "causal"
    strength FLOAT,                          -- 0.0 to 1.0 (correlation strength)
    description VARCHAR(500)                 -- Human explanation
);

-- Examples (relationships driving "orders"):
-- (1, 1, 2, "causal", 0.85, "Marketing drives customer acquisition")
-- (2, 1, 17, "causal", 0.75, "Discounts increase order volume")
-- (3, 1, 18, "causal", 0.45, "More partners = more choices")

-- Examples (formula dependencies):
-- (25, 12, 1, "formula", 1.0, "GMV = Orders × AOV")  [gmv depends on orders]
-- (25, 12, 2, "formula", 1.0, "GMV = Orders × AOV")  [gmv depends on aov]
-- (26, 14, 12, "formula", 1.0, "Revenue uses GMV")   [revenue depends on gmv]
```

### Table 3: `time_series_data` (44+ rows)

```sql
CREATE TABLE time_series_data (
    id SERIAL PRIMARY KEY,
    metric_id INT REFERENCES metrics(id),
    period VARCHAR(50),                  -- "Q1 2023", "Q2 2023", etc.
    segment VARCHAR(100),                -- "Overall", "Food", "Grocery", etc.
    value FLOAT,                         -- The metric value
    is_computed BOOLEAN DEFAULT FALSE    -- TRUE if calculated from formula
);

-- Examples:
-- (1, 1, "Q1 2023", "Overall", 100000.0, FALSE)     -- orders Q1
-- (2, 1, "Q2 2023", "Overall", 105000.0, FALSE)     -- orders Q2
-- (3, 1, "Q3 2023", "Overall", 110000.0, FALSE)     -- orders Q3
-- (4, 1, "Q4 2023", "Overall", 115000.0, FALSE)     -- orders Q4
-- (45, 12, "Q1 2023", "Overall", 37000.0, TRUE)     -- gmv Q1 (computed)
-- (46, 14, "Q1 2023", "Overall", 3200000.0, TRUE)   -- revenue Q1 (computed)
```

---

## 🚀 APP STARTUP SEQUENCE (How Everything Gets Initialized)

**File:** `backend/app/main.py`

```python
# Step 1: Create FastAPI app
app = FastAPI(title="Causal Financial Knowledge Graph")

# Step 2: Setup database connection
from app.database import SessionLocal, engine, Base

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Step 3: Define startup handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP: Load all metrics from database into memory
    print("Starting up...")
    db = SessionLocal()
    
    # This is the magic: load everything from DB once at startup
    load_metrics_from_database(db)
    print("✓ Metrics loaded from database")
    
    db.close()
    yield
    
    # SHUTDOWN: Cleanup (if needed)
    print("Shutting down...")

# Attach lifespan to app
app = FastAPI(lifespan=lifespan)

# Step 4: Import and include API routes
from app.api.routes import router
app.include_router(router)

# Step 5: Ready to serve
# Run with: python -m uvicorn app.main:app --port 8000
```

**What happens during `load_metrics_from_database(db)`:**

```python
# In app/metrics/loader.py

def load_metrics_from_database(db):
    print("Loading metrics from database...")
    
    # Step A: Query all metrics from DB
    metrics_rows = db.query(Metric).all()
    
    metric_registry = {}
    formula_functions = {}
    
    for metric_row in metrics_rows:
        # Convert DB row to dictionary
        metric_dict = {
            "id": metric_row.id,
            "name": metric_row.name,
            "display_name": metric_row.display_name,
            "formula": metric_row.formula,
            "formula_inputs": metric_row.formula_inputs,
            "unit": metric_row.unit,
            "is_base": metric_row.is_base
        }
        
        # Store in registry (by name for quick lookup)
        metric_registry[metric_row.name] = metric_dict
        
        # If derived metric with formula, compile it
        if not metric_row.is_base and metric_row.formula:
            formula_fn = _compile_formula(
                metric_row.formula,
                metric_row.formula_inputs
            )
            formula_functions[metric_row.name] = formula_fn
    
    # Step B: Query all relationships
    relationship_rows = db.query(MetricRelationship).all()
    relationships = [
        {
            "metric": r.metric.name,
            "driver": r.driver.name,
            "type": r.relationship_type,
            "strength": r.strength
        }
        for r in relationship_rows
    ]
    
    # Step C: Load all periods from time series data
    periods_rows = db.query(
        distinct(TimeSeriesData.period)
    ).all()
    periods = [p[0] for p in periods_rows]
    
    # Step D: Store everything in global cache variables
    global _METRIC_REGISTRY
    global _FORMULA_FUNCTIONS
    global _RELATIONSHIP_DEFINITIONS
    global _ALL_PERIODS
    
    _METRIC_REGISTRY = metric_registry          # In memory!
    _FORMULA_FUNCTIONS = formula_functions      # In memory!
    _RELATIONSHIP_DEFINITIONS = relationships   # In memory!
    _ALL_PERIODS = periods                      # In memory!
    
    print(f"✓ Loaded {len(metric_registry)} metrics")
    print(f"✓ Compiled {len(formula_functions)} formulas")
    print(f"✓ Loaded {len(relationships)} relationships")
    print(f"✓ Detected periods: {periods}")
```

Now the caches are ready, and runtime code can call:
```python
METRIC_REGISTRY()              # Returns cached metrics
FORMULA_FUNCTIONS()            # Returns cached compiled functions
RELATIONSHIP_DEFINITIONS()     # Returns cached relationships
ALL_PERIODS()                  # Returns cached periods
```

---

## 📱 COMPLETE REQUEST → RESPONSE CYCLE

```
1. USER SUBMITS QUERY
   └─> Frontend sends: POST /api/query
                      {"query": "Why did orders grow from Q1 to Q4 2023?"}

2. BACKEND RECEIVES REQUEST
   └─> routes.py query_endpoint() called

3. PARSE QUERY
   └─> parser.py extracts:
       - metric: "orders"
       - period: "Q4 2023"
       - compare_period: "Q1 2023"
       - intent: "explain_change"

4. LOAD DATA
   └─> handler.py queries database:
       - current orders = 115000.0
       - previous orders = 100000.0
       - change = 15000.0 (+15%)

5. COMPUTE METRICS
   └─> engine.py computes derived metrics:
       - gmv = orders * aov / 1000
       - revenue = gmv * commission_rate / 100 + ...
       - take_rate = revenue / gmv * 100
       - ... (all 18 metrics)

6. CAUSAL ANALYSIS
   └─> inference.py finds root causes:
       - Active Users changed +4.5% → impacts Orders +3.8%
       - Marketing changed +8.3% → impacts Orders +5.4%
       - Discounts changed +4.5% → impacts Orders +2.5%

7. FORMAT RESPONSE
   └─> routes.py builds JSON:
       {
         "query": "Why did orders grow...",
         "metric": {...},
         "change": {...},
         "drivers": [...]
       }

8. SEND TO FRONTEND
   └─> Frontend receives JSON

9. DISPLAY RESULTS
   └─> app.js renders:
       - Metric value + change
       - Root causes as expandable list
       - Interactive graph visualization
```

---

## 🔐 SECURITY FEATURES

### Formula Sandboxing (Safe Evaluation)

```python
# UNSAFE way (don't do this):
# eval("orders * aov / 1000")  # Could execute ANY Python code!

# SAFE way (what we do):
safe_namespace = {
    'sqrt': math.sqrt,
    'log': math.log,
    'exp': math.exp,
    'abs': abs,
    'min': min,
    'max': max,
    '__builtins__': {}  # ← This is the KEY: blocks eval/exec/import!
}

formula_fn = eval(
    "lambda v: (v['orders'] * v['aov'] / 1000)",
    {"__builtins__": {}},  # Empty builtins
    safe_namespace       # Only math functions allowed
)

# Now formula_fn can't do anything dangerous:
formula_fn({"orders": 115000, "aov": 330})  # ✓ Works (returns 37950)
formula_fn({"orders": 115000, "aov": 330}).__import__('os')  # ✗ Fails (no __import__)
```

### Database Access Control

- Only SELECT queries from API
- Only INSERT for CSV import (time_series_data table)
- No DELETE/UPDATE/ALTER operations from API
- `/api/seed` is the only write endpoint (creates tables)

---

## 🎯 KEY DESIGN PATTERNS

### 1. **Factory Pattern (Loader)**
The loader loads everything once at startup and caches it, so all code calls functions:
```python
# Not: METRIC_REGISTRY (constant)
# But: METRIC_REGISTRY() (function returning cached data)
```

### 2. **Strategy Pattern (Query Intent)**
Different analysis strategies based on query intent:
```python
if intent == "explain_change":
    perform_causal_analysis()
elif intent == "trend":
    perform_trend_analysis()
elif intent == "compare":
    perform_segment_comparison()
```

### 3. **Dependency Injection**
Database session passed to functions:
```python
def load_metrics(db):  # db is injected parameter
    metrics = db.query(Metric).all()
```

### 4. **Topological Sorting**
Metrics computed in dependency order:
```python
# Orders → GMV → Revenue (dependencies)
# So compute: orders first, then gmv, then revenue
```

---

## 📈 DATA FLOW THROUGH SYSTEM

```
Database              Memory Cache          Runtime Processing
──────────────────────────────────────────────────────────────

metrics table    ──>  METRIC_REGISTRY()   ──>  api/query_endpoint
  (18 rows)          (in-memory dict)        ↓
                                             parser.py
                                             ↓
metric_relat... ──>  RELATIONSHIP_DEF()   ──>  handler.py
  (24 rows)          (in-memory list)        ↓
                                             inference.py
                                             ↓
time_series_... ──>  SQL Query (live)     ──>  engine.py
  (44+ rows)         (fetched each call)      ↓
                                             Response JSON
                                             ↓
                                             Frontend Display
```

---

## ⚡ WHY THIS ARCHITECTURE IS SMART

### 1. **Zero Hardcoding**
- Add new metric? Just insert into DB
- Change relationship? Update row in relationships table
- No code changes needed!

### 2. **Fast Startup**
- Load metrics once at startup (~500ms)
- Every subsequent query: instant cache access (<1ms)
- Database queries only for time-series data (not definitions)

### 3. **Scalable**
- Works with any database structure
- Change `.env` → restart → works with new company data
- No code modifications for multiple companies

### 4. **Safe**
- Formula sandboxing prevents code injection
- Database constraints prevent bad data
- Type checking with SQLAlchemy ORM

### 5. **Testable**
- Each module has single responsibility
- Dependency injection allows mocking
- Clear interfaces between modules

---

## 🔄 SUMMARY: The Complete Loop

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  1. User asks: "Why did orders grow from Q1 to Q4 2023?"        │
│                                                                  │
│  2. Frontend sends query to /api/query endpoint                 │
│                                                                  │
│  3. Backend parses query → extracts metric, periods, intent     │
│                                                                  │
│  4. Load data from database:                                    │
│     - Metric definitions from cache (METRIC_REGISTRY())         │
│     - Time-series values via SQL query                          │
│     - Relationships from cache (RELATIONSHIP_DEFINITIONS())     │
│                                                                  │
│  5. Compute derived metrics using formulas (engine.py)          │
│                                                                  │
│  6. Perform causal analysis (inference.py):                     │
│     - What changed? Which drivers contributed?                  │
│     - Estimate impact of each driver                            │
│     - Rank by importance                                        │
│                                                                  │
│  7. Format as JSON response                                     │
│                                                                  │
│  8. Frontend receives JSON and displays results:                │
│     - Metric value and change                                   │
│     - Root causes ranked by impact                              │
│     - Interactive graph showing relationships                   │
│                                                                  │
│  9. User explores:                                              │
│     - Click "Marketing Spend" → see marketing changes           │
│     - Click "Active Users" → see user acquisition changes       │
│     - Drag graph nodes → interactive visualization              │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Every step is automated, generic, and database-driven. The system works for ANY company's metrics!** 🚀
