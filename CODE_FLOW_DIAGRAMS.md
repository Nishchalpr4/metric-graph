# CODE FLOW DIAGRAMS & SEQUENCE DIAGRAMS

## 1. SYSTEM INITIALIZATION FLOW

```
                        APPLICATION START
                              |
                              v
                    ┌─────────────────────┐
                    │  python -m uvicorn  │
                    │  backend.app.main   │
                    └──────────┬──────────┘
                               |
                               v
                    ┌─────────────────────────────────────┐
                    │  FastAPI lifespan context manager   │
                    │  Startup event triggered            │
                    └──────────┬──────────────────────────┘
                               |
                               v
         ┌─────────────────────────────────────────────────────────┐
         │  STARTUP SEQUENCE (runs once when server starts)         │
         └──────────┬──────────────────────────────────────────────┘
                    |
      ┌─────────────┼─────────────┬──────────────────┬──────────────┐
      |             |             |                  |              |
      v             v             v                  v              v
   Step 1        Step 2        Step 3             Step 4          Step 5
   ─────         ─────         ─────              ─────            ─────
  Connect      Create        Query DB            Compile        Build Graph
   To DB       Tables        Metrics             Formulas       Structure
   |             |             |                  |              |
   v             v             v                  v              v
┌────────┐  ┌──────────┐  ┌────────────┐  ┌──────────────┐  ┌────────────┐
│DB      │  │metrics   │  │SELECT *    │  │compile_fn   │  │topological │
│Ready   │  │relation  │  │FROM metrics│  │for each     │  │sort        │
│        │  │ships     │  │(18 rows)   │  │formula      │  │metrics by  │
│        │  │tables    │  │            │  │(7 formulas) │  │dependency  │
│        │  │created   │  │            │  │             │  │            │
└────────┘  └──────────┘  └────────────┘  └──────────────┘  └────────────┘
   |             |             |                  |              |
   └─────────────┴─────────────┴──────────────────┴──────────────┘
                               |
                               v
         ┌─────────────────────────────────────────────────────────┐
         │        MEMORY CACHES POPULATED (In-Memory)              │
         │                                                         │
         │  _METRIC_REGISTRY = {                                  │
         │    "orders": {...},                                    │
         │    "revenue": {...},                                   │
         │    ... (all 18 metrics)                                │
         │  }                                                      │
         │                                                         │
         │  _FORMULA_FUNCTIONS = {                                │
         │    "gmv": lambda v: v["orders"] * v["aov"] / 1000,    │
         │    "revenue": lambda v: ...,                           │
         │    ... (7 compiled formulas)                           │
         │  }                                                      │
         │                                                         │
         │  _RELATIONSHIP_DEFINITIONS = [                         │
         │    {"metric": "orders", "driver": "marketing", ...},   │
         │    ... (24 relationships)                              │
         │  ]                                                      │
         │                                                         │
         │  _ALL_PERIODS = ["Q1 2023", "Q2 2023", ...]           │
         └──────────┬──────────────────────────────────────────────┘
                    |
                    v
         ┌─────────────────────────────────────┐
         │  Print startup confirmation:        │
         │  "✓ Metrics loaded from database"   │
         │  "✓ Application startup complete"   │
         └──────────┬──────────────────────────┘
                    |
                    v
         ┌─────────────────────────────────────┐
         │  app.include_router(routes)         │
         │  Server listens on :8000            │
         │  Ready to accept requests!          │
         └─────────────────────────────────────┘
```

---

## 2. REQUEST PROCESSING FLOW (Detailed)

```
                    HTTP REQUEST ARRIVES
                    POST /api/query
                    {"query": "Why did orders grow from Q1 to Q4 2023?"}
                              |
                              v
        ┌─────────────────────────────────────────┐
        │  routes.py::query_endpoint()            │
        │  - Receives QueryRequest object         │
        │  - Calls handle_query(query_text)       │
        └────────────┬────────────────────────────┘
                     |
                     v
        ┌────────────────────────────────────┐
        │  parser.py::parse_query()          │
        │  Input: String                     │
        │  Output: ParsedQuery object        │
        └────────┬───────────────────────────┘
                 |
      ┌──────────┼──────────┬─────────────┬──────────────┐
      |          |          |             |              |
      v          v          v             v              v
   Extract    Extract    Extract      Extract         Determine
   Metric     Periods    Segment      Comparison      Intent
   Name                              Period
      |          |          |             |              |
      v          v          v             v              v
┌──────────┐ ┌───────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐
│"orders"  │ │"Q4    │ │"Overall" │ │"Q1 2023" │ │"explain_  │
│matched   │ │2023"  │ │detected  │ │inferred  │ │change"    │
│against   │ │found  │ │from data │ │from      │ │identified │
│metric    │ │in     │ │          │ │context   │ │           │
│names     │ │query  │ │          │ │          │ │           │
└──────────┘ └───────┘ └──────────┘ └──────────┘ └────────────┘
      |          |          |             |              |
      └──────────┴──────────┴─────────────┴──────────────┘
                     |
                     v
        ┌────────────────────────────────────────────┐
        │  ParsedQuery = {                           │
        │    metric: "orders",                       │
        │    period: "Q4 2023",                      │
        │    compare_period: "Q1 2023",              │
        │    segment: "Overall",                     │
        │    intent: "explain_change"                │
        │  }                                         │
        └────────┬─────────────────────────────────┘
                 |
                 v
        ┌─────────────────────────────────────────────┐
        │  handler.py::handle_query()                 │
        │  - Gets SessionLocal (DB connection)        │
        │  - Fetches time-series data                 │
        │  - Computes metric changes                  │
        └────────┬────────────────────────────────────┘
                 |
      ┌──────────┼───────────────┬────────────────┐
      |          |               |                |
      v          v               v                v
   Query DB   Query DB       Calculate         Get Previous
   Current    Previous       Change            Value
   Period     Period
      |          |               |                |
      v          v               v                v
   SELECT    SELECT         115000 -         100000
   WHERE     WHERE          100000 =
   period=   period=        15000
   Q4 2023   Q1 2023
      |          |               |                |
      └──────────┴───────────────┴────────────────┘
                     |
                     v
        ┌────────────────────────────────────────────┐
        │  Result = {                                │
        │    current_value: 115000.0,                │
        │    previous_value: 100000.0,               │
        │    absolute_change: 15000.0,               │
        │    percent_change: 15.0                    │
        │  }                                         │
        └────────┬─────────────────────────────────┘
                 |
                 v
        ┌────────────────────────────────────────────┐
        │  engine.py::compute_all_metrics()          │
        │  - Gets METRIC_REGISTRY() (from cache!)    │
        │  - Gets FORMULA_FUNCTIONS() (from cache!)  │
        │  - Gets COMPUTATION_ORDER()                │
        └────────┬─────────────────────────────────┘
                 |
      ┌──────────┴──────────────────────────────┐
      |                                         |
      v                                         v
   Base Metrics               Derived Metrics
   (already exist)            (computed in order)
      |                                  |
   orders                            gmv = orders * aov / 1000
   aov                               revenue = gmv * commission...
   commission_rate                   take_rate = revenue / gmv...
   delivery_charges                  arpu = revenue / active_users...
   discounts                         cac = marketing / new_users...
   marketing_spend                   ebitda = revenue - costs...
   new_users                         order_frequency = orders...
   active_users
   basket_size
   restaurant_partners
   pricing_index
      |
      └──────────┬──────────────────────────────┘
                 |
                 v
        ┌────────────────────────────────────────────┐
        │  computed_values = {                       │
        │    "orders": 115000.0,                     │
        │    "aov": 330.0,                           │
        │    ... (all 11 base metrics),              │
        │    "gmv": 37950.0,          (computed)     │
        │    "revenue": 3309867.0,    (computed)     │
        │    "take_rate": 8.71,       (computed)     │
        │    ... (all 7 derived)                     │
        │  }                                         │
        └────────┬─────────────────────────────────┘
                 |
                 v
        ┌────────────────────────────────────────────┐
        │  inference.py::infer_causal_drivers()      │
        │  - Gets relationships from database        │
        │  - For each driver:                        │
        │    1. Get current & previous values        │
        │    2. Calculate change %                   │
        │    3. Estimate impact × strength           │
        │  - Sort by impact (descending)             │
        └────────┬─────────────────────────────────┘
                 |
      ┌──────────┼──────────────┬─────────────┐
      |          |              |             |
      v          v              v             v
   Get Drivers  Check If       Calc         Estimate
   for        Changed         Change %      Impact
   "orders"
      |          |              |             |
      v          v              v             v
   [active_  active_users  4.5%         0.85 * 4.5% =
    users,   Q1→Q4 =      (500K→   3.8% impact
    market   525K)         525K)
    ing,
    discoun  marketing    8.3%         0.65 * 8.3% =
    ts,      Q1→Q4 =     (1.2B→    5.4% impact
    restaur  1.3B)        1.3B)
    ant]
             discounts   4.5%         0.55 * 4.5% =
             Q1→Q4 =     (2.2B→    2.5% impact
             2.3B)        2.3B)
      |
      └──────────┴──────────────────────┘
                 |
                 v
        ┌────────────────────────────────────────────┐
        │  causal_drivers = [                        │
        │    {name: "marketing_spend",               │
        │     change: 8.3, impact: 5.4, strength: 0.65},  │
        │    {name: "active_users",                  │
        │     change: 4.5, impact: 3.8, strength: 0.85},  │
        │    {name: "discounts",                     │
        │     change: 4.5, impact: 2.5, strength: 0.55},  │
        │    {name: "restaurant_partners",           │
        │     change: 3.7, impact: 1.8, strength: 0.50}   │
        │  ]  (sorted by impact)                     │
        └────────┬─────────────────────────────────┘
                 |
                 v
        ┌────────────────────────────────────────────┐
        │  routes.py::format_response()              │
        │  - Build JSON with all results             │
        │  - Include summary text                    │
        │  - Include graph structure                 │
        └────────┬─────────────────────────────────┘
                 |
                 v
        ┌────────────────────────────────────────────┐
        │  JSON Response sent to frontend:           │
        │  {                                         │
        │    "query": "Why did orders...",           │
        │    "metric": {...},                        │
        │    "change": {...},                        │
        │    "drivers": [{...}, {...}, ...],         │
        │    "summary": "Orders increased by 15%..." │
        │  }                                         │
        └────────┬─────────────────────────────────┘
                 |
                 v
                HTTP 200 OK
                Response body sent to browser
                |
                v
        Browser receives JSON
        app.js processes and displays results
        User sees causal analysis on screen!
```

---

## 3. DATABASE QUERY SEQUENCES

### Sequence A: Metric Data Retrieval

```
APP RUNTIME                         DATABASE
────────────────────────────────────────────────────────

 User asks question
        |
        v
 parse_query()
 Get metric name: "orders"
        |
        |  SELECT id FROM metrics WHERE name = 'orders'
        |─────────────────────────────────────────────>
        |
        |<────────────────── Return: id = 1
        |
 Get metric definition from METRIC_REGISTRY() [Memory Cache]
        |
        |  SELECT * FROM time_series_data 
        |    WHERE metric_id = 1 
        |    AND period = 'Q4 2023'
        |    AND segment = 'Overall'
        |─────────────────────────────────────────────>
        |
        |<────────────────── {value: 115000.0, is_computed: false}
        |
 Get previous period value
        |
        |  SELECT * FROM time_series_data 
        |    WHERE metric_id = 1 
        |    AND period = 'Q1 2023'
        |    AND segment = 'Overall'
        |─────────────────────────────────────────────>
        |
        |<────────────────── {value: 100000.0, is_computed: false}
        |
 Calculate change: 115000 - 100000 = 15000
```

### Sequence B: Formula Compilation at Startup

```
APP STARTUP                         DATABASE
────────────────────────────────────────────────────────

 lifespan startup()
        |
        v
 load_metrics_from_database()
        |
        |  SELECT * FROM metrics
        |─────────────────────────────────────────────>
        |
        |<────────────────── 18 rows returned
        |                   (11 base + 7 derived)
        |
 For each derived metric:
 
 Metric: gmv
 formula: "orders * aov / 1000"
 formula_inputs: ["orders", "aov"]
        |
        v
 _compile_formula(formula, inputs)
        |
        v
 Sanitize: Replace "orders" → "v['orders']"
           Replace "aov" → "v['aov']"
        |
        v
 Create lambda: "lambda v: (v['orders'] * v['aov'] / 1000)"
        |
        v
 eval() with restricted namespace
 (only math.sqrt, log, etc. allowed)
        |
        v
 formula_function = compiled lambda
        |
        v
 Store in _FORMULA_FUNCTIONS["gmv"] = formula_function
        
 (Repeat for all 7 derived metrics)
        |
        v
 All formulas compiled, cached in memory
 Ready for runtime use!
```

### Sequence C: Causal Driver Analysis

```
DATA IN MEMORY              PROCESSING LOGIC
────────────────────────────────────────────────────────

 Current computable_values = {
   orders: 115000,
   active_users: 525000,
   marketing_spend: 1.3B,
   discounts: 2.3B,
   ... (all others)
 }
        |
        v
 Get RELATIONSHIP_DEFINITIONS() from cache
        |
        v
 relationships = [
   {metric: "orders", driver: "active_users", strength: 0.85},
   {metric: "orders", driver: "marketing_spend", strength: 0.65},
   {metric: "orders", driver: "discounts", strength: 0.55},
   {metric: "orders", driver: "restaurant_partners", strength: 0.50},
   ... (more for other metrics)
 ]
        |
        v
 Filter for "orders": get drivers list
        |
        v
 For driver: "active_users"
        |
        v
 current_val = 525000 (Q4 2023)
 previous_val = 500000 (Q1 2023)
 driver_change = (525000 - 500000) / 500000 = 5.0%
        |
        v
 impact = 5.0% * 0.85 (strength) = 4.25%
        |
        v
 For driver: "marketing_spend"
        |
        v
 current_val = 1.3B
 previous_val = 1.2B
 driver_change = 8.3%
        |
        v
 impact = 8.3% * 0.65 = 5.4%
        |
        v
 (Repeat for all drivers)
        |
        v
 Sort drivers by impact (descending):
 1. marketing_spend: 5.4%
 2. active_users: 4.25%
 3. discounts: 2.5%
 4. restaurant_partners: 1.9%
        |
        v
 Return ranked drivers to response formatter
```

---

## 4. MODULE INTERACTION DIAGRAM

```
                        MAIN.PY
                      (Entry Point)
                          |
            ┌─────────────┼─────────────┐
            |             |             |
            v             v             v
        STARTUP       ROUTES.PY      SHUTDOWN
            |          (API Layer)      |
            |             |             |
            |    ┌────────┼────────┐    |
            |    |        |        |    |
            v    v        v        v    v
        LOADER  /query  /metrics  /seed
                 |        |        |
        ┌────────┴────┐   |        |
        |             |   |        |
        v             v   v        v
     PARSER.PY    HANDLER.PY    DATA.PY
        |             |        (DB Models)
        |    ┌────────┼────────┐
        |    |        |        |
        v    v        v        v
     ENGINE.PY  INFERENCE.PY  DATABASE
     (Metrics)  (Causality)   (PostgreSQL)
     (Formulas)  (Root Cause)
        |             |
        └─────────────┴────> API RESPONSE
                              |
                              v
                         FRONTEND
                      (Browser/JS)
```

---

## 5. FORMULA COMPILATION DETAILS

```
Input: Database formula string
"gmv * commission_rate / 100 + delivery_charges - discounts"

                    |
                    v
            ┌──────────────────┐
            │ Metric Name List │
            │                  │
            │ inputs = [       │
            │  "gmv",          │
            │  "commission_rate",
            │  "delivery_charges",
            │  "discounts"     │
            │ ]                │
            └────────┬─────────┘
                     |
                     v
        ┌──────────────────────────┐
        │ Replace metric names      │
        │ with safe variable access│
        │                          │
        │ "gmv" → "v['gmv']"       │
        │ "commission_rate" →      │
        │  "v['commission_rate']"  │
        │ "delivery_charges" →     │
        │  "v['delivery_charges']" │
        │ "discounts" →            │
        │  "v['discounts']"        │
        └────────┬─────────────────┘
                 |
                 v
Result string:
"v['gmv'] * v['commission_rate'] / 100 + v['delivery_charges'] - v['discounts']"
                 |
                 v
        ┌──────────────────────────┐
        │ Wrap in lambda            │
        │                          │
        │ "lambda v: (...)        │
        │                          │
        │ where ... is result      │
        └────────┬─────────────────┘
                 |
                 v
Expression: "lambda v: (v['gmv'] * v['commission_rate'] / 100 + v['delivery_charges'] - v['discounts'])"
                 |
                 v
        ┌──────────────────────────────────┐
        │ Create safe namespace:           │
        │                                  │
        │ ALLOWED:                         │
        │  - sqrt, log, exp, abs           │
        │  - min, max, pow                 │
        │  - Standard operators            │
        │                                  │
        │ FORBIDDEN (not in namespace):    │
        │  - eval, exec, compile           │
        │  - __import__, open              │
        │  - __builtins__: {}              │
        └────────┬───────────────────────┘
                 |
                 v
        ┌──────────────────────────────────┐
        │ eval(expression,                 │
        │      {"__builtins__": {}},       │
        │      safe_namespace)             │
        │                                  │
        │ Returns: <function object>       │
        └────────┬───────────────────────┘
                 |
                 v
        Compiled Function Object:
        <lambda function>
                 |
                 v
        Store in cache:
        FORMULA_FUNCTIONS["revenue"] = <lambda function>
                 |
                 v
        Ready for runtime use:
        result = FORMULA_FUNCTIONS()["revenue"]({
          "gmv": 37950.0,
          "commission_rate": 26.0,
          "delivery_charges": 5600000.0,
          "discounts": 2300000.0
        })
        
        Returns: 3309867.0
```

---

## 6. TOPOLOGICAL SORT (Metric Dependency Order)

```
Metrics with dependencies:
                    
    base_metric ─────────> depends on nothing
                    
    gmv ────────────────> depends on [orders, aov]
    
    revenue ────────────> depends on [gmv, commission_rate, 
                                      delivery_charges, discounts]
    
    take_rate ─────────> depends on [revenue, gmv]
    
    arpu ──────────────> depends on [revenue, active_users]
    
    ebitda ────────────> depends on [revenue, delivery_charges, 
                                      discounts]
    
    cac ───────────────> depends on [marketing_spend, new_users]
    
    order_frequency ──> depends on [orders, active_users]

Topological Order (can be computed, no forward dependencies):

 Level 0 (base metrics - no dependencies):
 ├─ orders
 ├─ aov
 ├─ commission_rate
 ├─ delivery_charges
 ├─ discounts
 ├─ marketing_spend
 ├─ new_users
 ├─ active_users
 ├─ basket_size
 ├─ restaurant_partners
 └─ pricing_index
 
 Level 1 (depends only on level 0):
 ├─ gmv (needs: orders, aov)
 ├─ cac (needs: marketing_spend, new_users)
 └─ order_frequency (needs: orders, active_users)
 
 Level 2 (depends on level 0-1):
 ├─ revenue (needs: gmv, commission_rate, delivery_charges, discounts)
 ├─ arpu (needs: revenue, active_users) — NO! revenue is level 2
 
 OPTIMAL ORDER:
 [orders, aov, commission_rate, delivery_charges, discounts, 
  marketing_spend, new_users, active_users, basket_size, 
  restaurant_partners, pricing_index, 
  gmv, cac, order_frequency,        ← now all level 0 available
  revenue, take_rate, arpu, ebitda] ← now all inputs available
```

---

## 7. COMPLETE RESPONSE JSON STRUCTURE

```javascript
{
  // 1. Original query and interpretation
  "query": "Why did orders grow from Q1 to Q4 2023?",
  "parsed": {
    "metric": "orders",
    "period": "Q4 2023",
    "compare_period": "Q1 2023",
    "segment": "Overall",
    "intent": "explain_change"
  },

  // 2. Metric details
  "metric": {
    "name": "orders",
    "display_name": "Orders",
    "description": "Total orders placed...",
    "formula": null,           // null = base metric
    "formula_inputs": [],      // empty = base metric
    "unit": "M",
    "category": "Operational",
    "is_base": true,
    "value": 115000.0,
    "period": "Q4 2023"
  },

  // 3. Change metrics
  "change": {
    "absolute": 15000.0,
    "percent": 15.0,
    "direction": "increase",
    "previous": 100000.0,
    "current": 115000.0,
    "time_range": "Q1 2023 → Q4 2023"
  },

  // 4. Root cause analysis
  "drivers": [
    {
      "name": "Marketing Spend",
      "display_name": "Marketing Spend",
      "type": "causal",
      "strength": 0.65,
      "change_percent": 8.3,
      "estimated_impact": 5.4,
      "direction": "increase",
      "previous_value": 1200000.0,
      "current_value": 1300000.0,
      "unit": "₹B",
      "description": "Platform marketing drives acquisition"
    },
    {
      "name": "active_users",
      "display_name": "Monthly Active Users (MAU)",
      "type": "causal",
      "strength": 0.85,
      "change_percent": 4.5,
      "estimated_impact": 3.8,
      "direction": "increase",
      "previous_value": 500000.0,
      "current_value": 525000.0,
      "unit": "M",
      "description": "More active users = more orders"
    },
    {
      "name": "discounts",
      "display_name": "Platform Discounts",
      "type": "causal",
      "strength": 0.55,
      "change_percent": 4.5,
      "estimated_impact": 2.5,
      "direction": "increase",
      "previous_value": 2200000.0,
      "current_value": 2300000.0,
      "unit": "₹B",
      "description": "Discounts increase order volume"
    },
    // ... more drivers
  ],

  // 5. Human-readable summary
  "summary": "Orders increased by 15.0% (100000.0M → 115000.0M) in Q4 2023 vs Q1 2023. " +
             "Causal business drivers: Marketing Spend ↑ 8.3%, Monthly Active Users (MAU) ↑ 4.5%, " +
             "Platform Discounts ↑ 4.5%.",

  // 6. Graph data for visualization
  "graph": {
    "nodes": [
      {"id": 0, "name": "orders", "type": "base", "category": "Operational"},
      {"id": 1, "name": "revenue", "type": "derived", "category": "Financial"},
      // ... 18 total nodes
    ],
    "edges": [
      {"source": 0, "target": 10, "type": "causal", "strength": 0.85},
      {"source": 0, "target": 1, "type": "formula", "strength": 1.0},
      // ... 24 total edges
    ]
  },

  // 7. Success status
  "success": true,
  "timestamp": "2026-04-19T15:45:23Z"
}
```

---

## 8. CACHING STRATEGY

```
TIME AXIS
──────────────────────────────────────────────────────────────

APP STARTUP
    |
    v
 load_metrics_from_database()
    |
    ├─> Query: SELECT * FROM metrics (18 rows)
    │   Result: _METRIC_REGISTRY = {items cached in RAM}
    │   Size: ~10KB
    │   Access time: <1ms
    │
    ├─> Query: SELECT * FROM metric_relationships (24 rows)
    │   Result: _RELATIONSHIP_DEFINITIONS = [cached in RAM]
    │   Size: ~5KB
    │   Access time: <1ms
    │
    ├─> Compile: All formula strings to Python functions
    │   Result: _FORMULA_FUNCTIONS = {cached in RAM}
    │   Size: ~8KB
    │   Access time: <1ms
    │
    └─> Query: SELECT DISTINCT period (from time_series_data)
        Result: _ALL_PERIODS = [cached in RAM]
        Size: ~1KB
        Access time: <1ms

RUNNING STATE (Multiple Requests)
    |
    ├─> Request 1: GET /api/metrics
    │   └─> METRIC_REGISTRY()  ← Returns from cache (instant)
    │
    ├─> Request 2: POST /api/query
    │   ├─> METRIC_REGISTRY()  ← From cache
    │   ├─> ALL_PERIODS()      ← From cache
    │   ├─> FORMULA_FUNCTIONS()← From cache
    │   ├─> SQL: SELECT FROM time_series_data (DB query)
    │   └─> Response built
    │
    ├─> Request 3: GET /api/graph
    │   └─> METRIC_REGISTRY(), RELATIONSHIP_DEFINITIONS()
    │       Both from cache
    │
    └─> Request N: ...
        All use caches, database only hit for time-series data!

PERFORMANCE BENEFIT:
    
    Startup cost:  ~500ms (load DB, compile formulas)
    Per request:   <50ms (cache lookup + formula eval)
    
    vs old approach:
    
    Per request:   ~500ms (query DB every time)
```

---

## 9. ERROR HANDLING FLOW

```
REQUEST COMES IN
        |
        v
TRY:
├─> Parse query
│   └─> EXCEPT: ParsingError → Return 400 "Invalid query"
│
├─> Get metric from METRIC_REGISTRY()
│   └─> EXCEPT: KeyError → Return 404 "Metric not found"
│
├─> Query database
│   └─> EXCEPT: DBConnectionError → Return 500 "DB unavailable"
│
├─> Compute metrics
│   └─> EXCEPT: FormulaError (divide by zero, NaN) 
│       → Return 400 "Cannot compute metric"
│
├─> Perform analysis
│   └─> EXCEPT: NoDataError → Return 200 "No data found"
│       (This is success response, just no results)
│
└─> Format response
    └─> EXCEPT: SerializationError → Return 500 "Internal error"

FINALLY:
    Log request/response
    Clean up database connection
    Return to caller
```

This comprehensive guide shows every layer of the system!
