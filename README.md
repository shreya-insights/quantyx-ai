# Quantyx AI — Financial Intelligence & Analytics SaaS

> **"Turn financial data into real-time intelligence."**

A production-grade, multi-tenant Fintech Analytics SaaS built with **FastAPI · MySQL 8.0 · Next.js 14 · Redis**.
SQL-first architecture with advanced window functions, multi-level CTEs, and a 5-rule fraud detection engine.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Next.js 14 Frontend                        │
│   Dashboard · Analytics · Query Lab · Fraud Monitor          │
└─────────────────────┬───────────────────────────────────────┘
                       │ REST API
┌─────────────────────▼───────────────────────────────────────┐
│              FastAPI (Python 3.11)                           │
│  Auth ─ Transactions ─ Analytics ─ Fraud ─ Query Lab         │
├───────────────┬──────────────────┬──────────────────────────┤
│ Service Layer │  Repository Layer │  Redis Cache             │
│   (Business   │  (Raw SQL + ORM)  │  (TTL: 5m–1h)           │
│    Logic)     │                   │                          │
└───────────────┴──────────┬────────┴──────────────────────────┘
                            │
          ┌─────────────────▼─────────────────┐
          │       MySQL 8.0                    │
          │  Partitioned · Indexed · 10 tables │
          └────────────────────────────────────┘
```

---

## USP Features

| # | Feature | Tech Used |
|---|---------|-----------|
| 1 | **SQL Analytics Engine** | Window functions, LAG, NTILE, RANK, DENSE_RANK |
| 2 | **RFM Customer Segmentation** | Multi-level CTEs + NTILE(5) scoring |
| 3 | **Cohort Retention Matrix** | PERIOD_DIFF + pivot aggregations |
| 4 | **Fraud Detection Engine** | 5 rules: velocity, spike, location, duplicate, night |
| 5 | **Live SQL Query Lab** | Monaco editor + safe SELECT sandbox |
| 6 | **Multi-Tenant SaaS** | JWT + company_id isolation + RBAC |
| 7 | **KPI Auto-Generation** | One-shot summary query with aggregations |
| 8 | **PDF/CSV Reports** | ReportLab + pandas export |
| 9 | **Redis Caching** | TTL-based with tenant-aware invalidation |
| 10 | **Subscription Tiers** | Starter/Growth/Enterprise with API metering |

---

## Tech Stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2
- **Database:** MySQL 8.0 — RANGE partitioned, covering indexes, read replicas ready
- **Cache:** Redis 7 — sliding window rate limiting, query result caching
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS, Recharts, Monaco Editor
- **Auth:** JWT (python-jose) + bcrypt + RBAC (admin/analyst/viewer)
- **DevOps:** Docker, Docker Compose, GitHub Actions CI/CD

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local frontend dev)
- Python 3.11+ (for local backend dev)

### 1. Clone and configure

```bash
git clone https://github.com/your-org/quantyx-ai.git
cd quantyx-ai
cp .env.example .env
# Edit .env with your secrets
```

### 2. Start with Docker Compose

```bash
docker compose up -d
```

Services:
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Adminer (DB GUI):** http://localhost:8080

### 3. Run Database Migrations

```bash
docker compose exec backend alembic upgrade head
```

### 4. Local Development (Backend)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 5. Local Development (Frontend)

```bash
cd frontend
npm install
npm run dev
```

---

## API Documentation

Full interactive API docs at `http://localhost:8000/docs`

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register company + admin user |
| POST | `/api/v1/auth/login` | Get JWT tokens |
| GET | `/api/v1/analytics/revenue-trends` | MoM revenue with LAG() |
| GET | `/api/v1/analytics/customer-segmentation` | RFM via NTILE(5) |
| GET | `/api/v1/analytics/cohort` | Cohort retention matrix |
| GET | `/api/v1/analytics/top-merchants` | RANK() per category |
| GET | `/api/v1/analytics/kpi-summary` | One-shot KPI aggregation |
| POST | `/api/v1/transactions/bulk-upload` | CSV ingestion (batch 500) |
| GET | `/api/v1/fraud/alerts` | Fraud alerts with JOIN context |
| POST | `/api/v1/query-lab/execute` | Safe SQL executor |
| GET | `/api/v1/reports/generate/pdf` | PDF via ReportLab |

---

## Database Schema

```
companies (multi-tenant root)
    └── users (admin/analyst/viewer)
    └── accounts (checking/savings/credit/investment)
    └── merchants (category_code, is_flagged)
    └── transactions ← RANGE PARTITIONED by YEAR
    └── fraud_alerts (velocity/spike/location/duplicate/night)
    └── kpi_reports (JSON metrics cache)
    └── subscriptions (starter/growth/enterprise)
    └── saved_queries (Query Lab persistence)

categories (hierarchical, self-FK)
```

### Critical Indexes
- `(company_id, transaction_date)` — primary analytics filter
- `(company_id, status, transaction_type)` — aggregation covering index
- `(account_id, transaction_date)` — per-account analytics

---

## SQL Analytics Examples

### Revenue Trend with MoM Growth (Window Function)
```sql
SELECT month,
    SUM(CASE WHEN transaction_type='credit' THEN amount ELSE 0 END) AS inflow,
    ROUND(
        (inflow - LAG(inflow) OVER (ORDER BY month))
        / NULLIF(LAG(inflow) OVER (ORDER BY month), 0) * 100, 2
    ) AS mom_growth_pct
FROM transactions WHERE company_id = :cid
GROUP BY month ORDER BY month;
```

### RFM Segmentation (Multi-CTE + NTILE)
```sql
WITH rfm_scored AS (
    SELECT account_id,
        NTILE(5) OVER (ORDER BY DATEDIFF(NOW(), MAX(transaction_date)) ASC) AS r,
        NTILE(5) OVER (ORDER BY COUNT(*) DESC) AS f,
        NTILE(5) OVER (ORDER BY SUM(amount) DESC) AS m
    FROM transactions WHERE company_id = :cid GROUP BY account_id
)
SELECT *, CASE WHEN r>=4 AND f>=4 AND m>=4 THEN 'Champions'
               WHEN r<=2 AND f>=3 THEN 'At Risk' ELSE 'Loyalists' END AS segment
FROM rfm_scored;
```

---

## Subscription Tiers

| Feature | Starter (Free) | Growth ($49/mo) | Enterprise ($199/mo) |
|---------|---------------|-----------------|---------------------|
| Users | 1 | 10 | Unlimited |
| Transactions/month | 10K | 500K | Unlimited |
| Analytics | Core | Full | Full + Custom |
| Fraud Detection | ✗ | ✓ | ✓ |
| Query Lab | ✗ | ✓ | ✓ |
| PDF Reports | ✗ | ✓ | ✓ |
| White-label | ✗ | ✗ | ✓ |

---

## Running Tests

```bash
cd backend
pytest tests/ -v --cov=app
```

---

## Project Structure

```
quantyx-ai/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/    # auth, transactions, analytics, fraud, query_lab, reports
│   │   ├── core/                # config, security, dependencies, middleware
│   │   ├── models/              # 10 SQLAlchemy models
│   │   ├── schemas/             # Pydantic v2 request/response
│   │   ├── services/            # Business logic (fraud, analytics, ingestion)
│   │   ├── repositories/        # SQL-first data access layer
│   │   ├── db/                  # AsyncSession, Base
│   │   └── utils/               # cache, pagination
│   ├── alembic/                 # DB migrations
│   └── tests/
├── frontend/
│   ├── app/                     # Next.js App Router pages
│   ├── components/              # Sidebar, charts, UI components
│   ├── lib/                     # API client, utils
│   └── store/                   # Zustand auth store
├── .github/workflows/           # CI + CD pipelines
├── docker-compose.yml
└── docker-compose.prod.yml
```

---

Built with ❤️ as a showcase of production-grade fintech engineering.
