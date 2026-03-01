# 🏭 Manufacturing Workflow Automation System

> A production-grade backend system that simulates a factory floor — tracking work orders, station health, defects, downtime, and KPI analytics — with async automation rules that respond to real-time events.

[![CI](https://github.com/your-username/mfg-workflow/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/mfg-workflow/actions)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 What It Does

This system models a real manufacturing floor with four station types: **Cutting → Assembly → QA → Packaging**. Work orders flow through stations, generating events that drive:

- **Real-time KPI calculations**: throughput, avg cycle time, defect rate, downtime
- **Bottleneck detection**: identify slow stations and get actionable recommendations  
- **Async automation rules** (via Celery): automatically hold QA stations when defects spike, pause work orders when machines go down, flag bottlenecks when cycle times exceed thresholds

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client / Script                         │
│               curl | simulate_factory.py | /docs                │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP
┌─────────────────────────▼───────────────────────────────────────┐
│                      FastAPI (port 8000)                        │
│                                                                 │
│  /work-orders   /stations   /events   /kpis   /automation       │
│                                                                 │
│         Pydantic validation │ SQLAlchemy ORM                    │
└──────────┬──────────────────┼────────────────────────┬──────────┘
           │                  │                        │
    ┌──────▼──────┐   ┌───────▼──────┐       ┌────────▼────────┐
    │ PostgreSQL  │   │   KPI &      │       │  Celery Worker  │
    │             │   │ Automation   │       │                 │
    │ work_orders │   │  Services    │       │  - run_rules    │
    │ stations    │   └──────────────┘       │  - snapshot_kpi │
    │ events      │                          └────────┬────────┘
    │ kpi_history │◄─────────────────────────────────┘
    │ auto_rules  │          ▲
    └─────────────┘          │
                      ┌──────┴──────┐
                      │    Redis    │
                      │   (broker)  │
                      └─────────────┘
```

### Data Flow

```
Factory Event (e.g. MACHINE_DOWN)
    │
    ▼
POST /events ──► Validate + persist Event row
                │
                ├──► Sync side-effect: update Station.status = DOWN
                │
                └──► Celery Beat (every 2 min) ──► evaluate_all_rules()
                                                    │
                                                    ├── defect_rate_spike? → hold QA stations
                                                    ├── station_downtime?  → pause work orders
                                                    └── high_cycle_time?   → flag bottleneck
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI 0.111 + Uvicorn |
| Database | PostgreSQL 15 (SQLAlchemy 2.0 ORM) |
| Migrations | Alembic |
| Background jobs | Celery 5 + Redis 7 (broker + backend) |
| Validation | Pydantic v2 |
| Testing | Pytest + pytest-cov (SQLite in-memory) |
| CI | GitHub Actions |
| Containerization | Docker + Docker Compose |
| Linting | Ruff |

---

## 🚀 Quick Start (< 5 minutes)

### Prerequisites
- Docker & Docker Compose installed
- `git clone` this repo

```bash
# 1. Clone and enter
git clone https://github.com/your-username/mfg-workflow.git
cd mfg-workflow

# 2. Copy environment config
cp .env.example .env

# 3. Start all services (API + Postgres + Redis + Celery worker + beat)
docker compose up -d

# 4. Wait ~15 seconds for services to be ready, then check health
curl http://localhost:8000/health

# 5. Seed default stations + automation rules
docker compose exec api python scripts/seed_db.py

# 6. Run the factory simulation (20 work orders)
python scripts/simulate_factory.py --work-orders 20

# 7. Open the interactive API docs
open http://localhost:8000/docs
```

---

## 📡 API Reference

### Health
```bash
GET /health
```

### Work Orders
```bash
# Create
curl -X POST http://localhost:8000/work-orders \
  -H "Content-Type: application/json" \
  -d '{"product_type": "Widget-A", "priority": 3}'

# List with filters
curl "http://localhost:8000/work-orders?status=IN_PROGRESS"
curl "http://localhost:8000/work-orders?from_date=2024-01-01T00:00:00Z"
```

### Stations
```bash
# Create
curl -X POST http://localhost:8000/stations \
  -H "Content-Type: application/json" \
  -d '{"name": "Assembly-03", "type": "ASSEMBLY"}'

# Update status
curl -X PATCH http://localhost:8000/stations/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "RUNNING"}'
```

### Events
```bash
# Work order started
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{"type": "WORK_ORDER_STARTED", "work_order_id": 1}'

# Machine down (auto-updates station status)
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{"type": "MACHINE_DOWN", "station_id": 2, "payload": {"reason": "jam", "duration_minutes": 12}}'

# Defect found
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{"type": "DEFECT_FOUND", "station_id": 3, "work_order_id": 1, "payload": {"severity": "major"}}'
```

### KPIs
```bash
# Summary (last 24 hours)
curl "http://localhost:8000/kpis/summary?window_hours=24"

# Bottleneck analysis
curl "http://localhost:8000/kpis/bottlenecks?window_hours=24"
```

### Automation Rules
```bash
# Create a defect-rate rule
curl -X POST http://localhost:8000/automation/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Defect Spike Response",
    "condition_json": {"type": "defect_rate_spike", "threshold": 0.15, "sample_size": 50},
    "action_json": {"type": "hold_qa_station"}
  }'

# Manually trigger rule evaluation
curl -X POST http://localhost:8000/automation/rules/run
```

---

## 📊 KPIs Explained

| KPI | Formula | Notes |
|---|---|---|
| **Throughput** | Completed WOs ÷ window hours | Higher = better factory flow |
| **Avg Cycle Time** | Avg (completed_at − started_at) per WO | Lower = faster production |
| **Defect Rate %** | DEFECT_FOUND events ÷ last 50 events × 100 | >15% triggers QA hold |
| **Downtime Minutes** | Sum of `duration_minutes` in MACHINE_DOWN payloads | Cumulative for window |

---

## 🤖 Automation Rules

Three built-in rules ship with `seed_db.py`:

| Rule | Condition | Action |
|---|---|---|
| **Defect Spike** | defect rate > 15% (last 50 events) | Set all QA stations → HOLD |
| **Station Downtime** | any station DOWN > 10 min | Pause all IN_PROGRESS work orders → ON_HOLD |
| **Cycle Time Bottleneck** | station avg step time > 30 min | Log bottleneck + emit recommendation |

Rules run every 2 minutes via Celery Beat. You can also trigger evaluation manually via `POST /automation/rules/run`.

---

## 🧪 Running Tests

```bash
# With Docker (recommended)
docker compose exec api pytest tests/ --cov=app --cov-report=term-missing -v

# Locally (uses SQLite in-memory)
pip install -r requirements.txt
pytest tests/ -v
```

Test coverage includes:
- API happy paths + error cases for all endpoints
- KPI calculation correctness (throughput, cycle time, defect rate, downtime)  
- Automation rule triggering (defect spike, downtime pause, disabled rule skip)

---

## 🏃 Simulation

The simulation script drives a realistic factory shift:

```bash
python scripts/simulate_factory.py --work-orders 30

# Output:
# ============================================================
#   📊  FACTORY SIMULATION KPI REPORT
# ============================================================
#   Completed Work Orders : 30
#   Throughput (WOs/hr)   : 1.250
#   Avg Cycle Time (min)  : 38.4
#   Defect Rate           : 6.0%
#   Total Downtime (min)  : 47.3
#   Active Stations       : 4
#   Stations DOWN         : 0
#
#   ⚠️  Bottlenecks (1):
#      • Assembly-02: 41.2 min avg
#        → Station 'Assembly-02' avg cycle time 41.2 min exceeds ...
# ============================================================
```

Realistic distributions:
- Cutting: 8–25 min per step
- Assembly: 15–45 min per step  
- QA: 5–20 min per step
- Packaging: 3–10 min per step
- Machine down: 5% chance per step, 5–20 min duration
- Defect: 8% at QA, 3% at other stations

---

## 📁 Project Structure

```
mfg-workflow/
├── app/
│   ├── api/                # FastAPI routers
│   │   ├── work_orders.py
│   │   ├── stations.py
│   │   ├── events.py
│   │   ├── kpis.py
│   │   ├── automation.py
│   │   └── health.py
│   ├── core/               # Config, DB, logging
│   │   ├── config.py
│   │   ├── database.py
│   │   └── logging.py
│   ├── models/             # SQLAlchemy ORM models
│   │   └── models.py
│   ├── schemas/            # Pydantic schemas
│   │   └── schemas.py
│   ├── services/           # Business logic
│   │   ├── kpi_service.py
│   │   └── automation_service.py
│   ├── tasks/              # Celery tasks
│   │   ├── celery_app.py
│   │   └── tasks.py
│   └── main.py
├── migrations/             # Alembic migrations
│   ├── env.py
│   └── versions/001_initial.py
├── scripts/
│   ├── seed_db.py          # Default data
│   ├── simulate_factory.py # Factory simulation
│   └── demo.sh             # One-command demo
├── tests/
│   ├── conftest.py         # Fixtures
│   ├── test_work_orders.py
│   ├── test_stations.py
│   ├── test_events.py
│   ├── test_kpis.py
│   ├── test_automation.py
│   └── test_health.py
├── docs/
│   ├── decision_log.md
│   └── data_model.md
├── .github/workflows/ci.yml
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── pyproject.toml          # Ruff + pytest config
├── requirements.txt
└── README.md
```

---

## 🔧 Common Commands (Makefile)

```bash
make up          # Start all Docker services
make down        # Stop all services
make migrate     # Run DB migrations
make seed        # Seed default data
make simulate    # Run factory simulation
make test        # Run pytest with coverage
make lint        # Lint with Ruff
make demo        # Run curl demo script
make clean       # Remove containers + volumes
make help        # Show all commands
```

---

## 💡 What I Learned

Building this project deepened my understanding of several production backend patterns:

**Event sourcing over mutable state** — Using an append-only events table gives both real-time state (via side effects) and a full audit log for analytics. This is how real MES (Manufacturing Execution Systems) like SAP ME work.

**Async task isolation with Celery** — Decoupling automation logic into background tasks prevents slow rule evaluation from blocking the API. The beat scheduler ensures rules run even with no incoming traffic.

**Database index strategy** — Composite indexes on `(type, timestamp)` and `(station_id, timestamp)` make KPI queries fast at scale. Without them, defect-rate and cycle-time queries would require full table scans.

**Schema-driven configuration** — Using JSON columns for `condition_json` and `action_json` lets operators add new automation rules without code changes — a pattern used in workflow engines like Temporal and Airflow.

**Test isolation with SQLite** — Using SQLite in-memory for tests gives millisecond-fast test runs without Docker, while the production app uses PostgreSQL. SQLAlchemy's abstraction makes this seamless.

---

## 📜 License

MIT — see [LICENSE](LICENSE)
