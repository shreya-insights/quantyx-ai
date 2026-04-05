<div align="center">

# Quantyx AI
### Financial Intelligence & Analytics SaaS Platform

**"Turn raw financial data into real-time intelligence — fraud alerts, AI-driven insights, and enterprise analytics at production scale."**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-Strict-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://mysql.com)
[![Redis](https://img.shields.io/badge/Redis-7.0-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![Celery](https://img.shields.io/badge/Celery-5.4-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev)

---

**Built by [Shreya Tiwari](https://www.linkedin.com/in/shreya-tiwari-738a43214) · VIT MCA Alumni · Fintech & Data Analytics**

[View Live Demo](#quick-start) · [API Docs](http://localhost:8000/docs) · [Setup Guide](./SETUP.md) · [Reach Out](mailto:tiwashreyaa@gmail.com)

</div>

---

## About This Project

**Quantyx AI** is a full-stack, production-grade multi-tenant SaaS platform designed for fintech companies and banks to analyze transaction data, detect fraud in real time, and leverage AI to answer business questions in plain English.

This is not a tutorial project. Every architectural decision — from sliding-window Redis rate limiting to XGBoost fraud scoring with SHAP explainability — mirrors decisions made by engineering teams at financial institutions and data-driven SaaS companies.

**What makes this stand out:**
- **50+ REST API endpoints** with role-based access control and full tenant isolation
- **Hybrid fraud detection** — 5 deterministic rules + XGBoost ML model with SHAP explanations (EU AI Act compliant)
- **Analytics data warehouse** — nightly ETL pipeline populating pre-aggregated tables for cohort retention, LTV segmentation, RFM scoring
- **AI Analyst** — natural language querying of financial data using LLM tool-use chains (Groq/Gemini/OpenRouter)
- **Production observability** — Prometheus metrics, structured JSON logging, Grafana dashboards
- **Background task processing** — Celery workers with Redis broker for fraud scoring, email delivery, analytics cache rebuilding

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      React 19 + TypeScript (Port 3000)                   │
│  TanStack Query · Zustand · Framer Motion · Recharts · Monaco Editor     │
│  Pages: Dashboard · Analytics · Fraud · Query Lab · AI Analyst           │
└─────────────────────────────┬───────────────────────────────────────────┘
                               │  REST + WebSocket  (Vite proxy → :8000)
┌─────────────────────────────▼───────────────────────────────────────────┐
│                    FastAPI (Python 3.11) — Port 8000                      │
│                                                                           │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ Auth + RBAC  │  │  Analytics    │  │   Fraud      │  │ AI Analyst │ │
│  │ JWT + bcrypt │  │  Engine       │  │   Engine     │  │ LLM Chain  │ │
│  └──────────────┘  └───────────────┘  └──────────────┘  └────────────┘ │
│                                                                           │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │  Invitations │  │  Query Lab    │  │  Reports     │  │Subscriptions│ │
│  │  + Email     │  │  SQL Sandbox  │  │  CSV + PDF   │  │  + Metering│ │
│  └──────────────┘  └───────────────┘  └──────────────┘  └────────────┘ │
└──────────┬────────────────┬──────────────────────┬──────────────────────┘
           │                │                       │
┌──────────▼──────┐  ┌─────▼──────┐  ┌─────────────▼──────────────────────┐
│   MySQL 8.0     │  │  Redis 7   │  │         Celery Workers              │
│  22 Tables      │  │ Cache +    │  │  ┌────────────┐  ┌───────────────┐  │
│  Feature Store  │  │ Pub/Sub +  │  │  │ Fraud Queue│  │ Email Queue   │  │
│  Data Warehouse │  │ Rate Limit │  │  ├────────────┤  ├───────────────┤  │
│  Analytics Cache│  │ + Broker   │  │  │Analytics Q │  │ Features Q    │  │
└─────────────────┘  └────────────┘  │  └────────────┘  └───────────────┘  │
                                      │           (Beat: scheduled ETL)      │
                                      └─────────────────────────────────────┘
```

---

## Core Features

### 1. Real-Time Fraud Detection Engine
A **hybrid scoring system** that runs on every transaction — both via API and bulk CSV upload.

**5 Deterministic Rules:**
| Rule | Signal | Severity |
|---|---|---|
| Velocity Check | >5 transactions in 30 min from same account | HIGH |
| Amount Spike | Amount > 3× user's 30-day average | MEDIUM |
| Location Anomaly | >200 km from last transaction in short time | HIGH |
| Duplicate Detection | Same amount + merchant + account within 5 min | CRITICAL |
| Flagged Merchant | Merchant manually marked suspicious by analyst | MEDIUM |

**XGBoost ML Layer:**
- Trained on user/merchant feature vectors (velocity, spend ratios, fraud history)
- `scale_pos_weight` handles class imbalance without SMOTE
- **SHAP values** explain every ML decision (EU AI Act compliance)
- Model versioning with `feature_columns.json` — eliminates training/serving skew
- Weekly automated health check via Celery Beat: F1, Precision, AUC-PR, PSI drift

### 2. Analytics & Data Warehouse
Built to handle large-scale financial data without blocking the HTTP request path.

**Two-tier caching architecture:**
- **Redis** (5 min – 1 hour TTL) for hot analytics responses
- **Pre-aggregated DB tables** populated by nightly ETL (2:00 AM UTC)

**Analytics modules:**
- **Revenue Trends** — daily time series with window functions (`LAG`, `SUM OVER`)
- **RFM Segmentation** — multi-CTE + `NTILE(5)` to classify customers (Champions, Loyal, At Risk, Lost)
- **Cohort Retention Matrix** — first-transaction month → retention % grid
- **LTV Segments** — lifetime value distribution from warehouse table
- **Transaction Heatmap** — hour × day frequency grid showing peak activity
- **KPI Summary** — total revenue, transaction count, fraud rate, active accounts

### 3. AI Analyst (Natural Language → Data)
Ask questions like *"Which customer segment had the highest fraud rate last month?"* — get data-backed answers.

**LLM Provider Chain** (all free tier, no paid APIs):
1. **Groq** — `llama-3.3-70b-versatile` (primary, fastest)
2. **Gemini** — `gemini-1.5-flash` (fallback)
3. **OpenRouter** — `llama-3.1-8b-instruct:free` (last resort)

Auto-fallback on error. Per-user rate limiting (20 calls/hour) via Redis sliding window.

### 4. Multi-Tenant SaaS Architecture
Company isolation enforced at **every layer** — not just a flag in a WHERE clause.

- `company_id` embedded in JWT — cannot be spoofed without `SECRET_KEY`
- Repositories always filter by `company_id` from `TokenData` (never from request body)
- Redis keys namespaced: `quantyx:events:{company_id}`, `quantyx:rate:{company_id}:...`
- WebSocket channels per company: `quantyx:events:{company_id}`
- Three-layer rate limiting: IP → per-plan (60/300/1000 req/min) → monthly quota

### 5. Team Invitations with Secure Email Flow
Admin sends an invite → Celery sends email via Gmail SMTP → Invitee sets password → Joins automatically.

- Raw token **never** stored in DB — only SHA-256 hash
- Token validation endpoint is public but IP rate-limited
- Resend revokes old token before issuing new one
- Jinja2 HTML templates with `autoescape=True` (XSS-safe)
- Table-based email layout (Outlook compatible)

### 6. SQL Query Lab
A safe, sandboxed SQL editor for analysts to write custom queries.

- Monaco Editor with SQL syntax highlighting
- Read-only enforcement — DDL/DML blocked at query parser level
- `company_id` auto-injected as bound parameter (tenant isolation cannot be bypassed)
- Save, share, and track execution count of queries
- Pre-built templates for common fintech analytics

### 7. Real-Time WebSocket Events
Live updates pushed to browser clients via Redis pub/sub.

- Fraud alerts pushed instantly to connected analyst dashboards
- Transaction status updates streamed as they process
- Server heartbeat every 30 seconds
- Auto-reconnect with exponential backoff on disconnect
- Graceful fallback to polling if WebSocket unavailable

---

## Tech Stack

### Backend
| Category | Technology | Version |
|---|---|---|
| Web Framework | FastAPI (async) | 0.111 |
| ORM | SQLAlchemy 2.0 (async) | 2.0.31 |
| Database | MySQL 8.0 | 8.x |
| Cache / Broker | Redis | 7.x |
| Task Queue | Celery + RedBeat | 5.4 |
| Auth | python-jose (JWT HS256) | 3.3 |
| Password | passlib/bcrypt | 1.7 |
| ML | XGBoost + scikit-learn | 2.0+ |
| Explainability | SHAP | 0.45+ |
| Email | fastapi-mail + Jinja2 | 1.4+ |
| Logging | structlog (JSON) | 24.4 |
| Metrics | prometheus-client | 0.20+ |
| LLM Clients | groq + google-genai | latest |
| PDF | reportlab | 4.2 |
| Migrations | Alembic | 1.13 |

### Frontend
| Category | Technology | Version |
|---|---|---|
| Build Tool | Vite | 8.x |
| UI Library | React | 19.x |
| Language | TypeScript (strict) | 5.x |
| CSS Framework | Tailwind CSS | 3.x |
| Server State | TanStack Query | 5.x |
| Global State | Zustand + immer | 5.x |
| Routing | React Router | 7.x |
| Charts | Recharts | latest |
| Animations | Framer Motion | latest |
| Forms | React Hook Form + Zod | latest |
| SQL Editor | Monaco Editor | latest |
| HTTP Client | Axios | latest |

---

## Database Schema (22 Tables)

```
companies ─────────────── (multi-tenant root)
│
├── users              (admin / analyst / viewer)
├── subscriptions      (starter / growth / enterprise + metering)
├── invitations        (SHA-256 token hash, not raw token)
├── transactions       (core financial events + fraud job tracking)
├── accounts           (checking / savings / credit / wallet)
├── merchants          (MCC codes, flagged status)
├── categories         (hierarchical, self-FK)
├── fraud_alerts       (rule triggers + ML scores + SHAP metadata)
├── saved_queries      (Query Lab persistence)
├── kpi_reports        (JSON snapshots)
├── audit_logs         (append-only, no FK constraints — immutable)
├── admin_notifications
│
├── [Feature Store]
│   ├── user_features        (rolling 7d/30d spend, fraud rate)
│   ├── merchant_features    (avg amount, fraud rate, unique users)
│   └── velocity_features    (1h/24h transaction counts)
│
├── [Analytics Cache]
│   ├── daily_revenue_summaries
│   ├── monthly_category_summaries
│   ├── merchant_ranking_caches
│   └── kpi_summary_caches
│
├── [Data Warehouse]
│   ├── cohort_retention_metrics
│   ├── lifetime_value_metrics
│   └── hourly_transaction_heatmaps
│
└── [Model Monitoring]
    ├── model_performance_metrics  (F1, Precision, AUC-PR)
    └── feature_distribution_snapshots  (PSI drift detection)
```

---

## API Endpoints (50+ total)

```
Auth              POST /api/v1/auth/register · /login · /refresh
                  GET  /api/v1/auth/me

Invitations       POST /api/v1/invitations/send · /send-bulk
                  GET  /api/v1/invitations
                  POST /api/v1/invitations/{id}/resend
                  GET  /api/v1/invitations/validate?token=
                  POST /api/v1/invitations/accept

Transactions      GET  /api/v1/transactions  (paginated, filtered)
                  POST /api/v1/transactions  (+ enqueues fraud task)
                  POST /api/v1/transactions/bulk-upload  (CSV)
                  GET  /api/v1/transactions/{id}/fraud-status  (poll)

Analytics         GET  /api/v1/analytics/kpi-summary
                  GET  /api/v1/analytics/revenue-trends
                  GET  /api/v1/analytics/customer-segmentation
                  GET  /api/v1/analytics/cohort-retention
                  GET  /api/v1/analytics/ltv-segments
                  GET  /api/v1/analytics/transaction-heatmap
                  GET  /api/v1/analytics/top-merchants
                  GET  /api/v1/analytics/spending-by-category

Fraud             GET  /api/v1/fraud/alerts  (paginated)
                  GET  /api/v1/fraud/alerts/{id}  (+ SHAP data)
                  POST /api/v1/fraud/alerts/{id}/resolve
                  GET  /api/v1/fraud/stats

Query Lab         POST /api/v1/query-lab/execute
                  GET  /api/v1/query-lab/templates
                  POST /api/v1/query-lab/saved
                  GET  /api/v1/query-lab/saved

AI Analyst        POST /api/v1/analyst/ask
                  GET  /api/v1/analyst/suggested-questions
                  GET  /api/v1/analyst/provider-status

Reports           GET  /api/v1/reports/generate/csv
                  GET  /api/v1/reports/generate/pdf

Subscriptions     GET  /api/v1/subscriptions/plans · /current · /usage
                  POST /api/v1/subscriptions/subscribe · /upgrade

System            GET  /health  ·  /metrics  ·  /docs
WebSocket         WS   /api/v1/ws/company/{company_id}?token=
```

---

## SQL Analytics Examples

### RFM Customer Segmentation (Multi-CTE + NTILE)
```sql
WITH rfm_base AS (
    SELECT account_id,
        DATEDIFF(NOW(), MAX(transaction_date)) AS recency_days,
        COUNT(*)                               AS frequency,
        SUM(amount)                            AS monetary
    FROM transactions
    WHERE company_id = :company_id
    GROUP BY account_id
),
rfm_scored AS (
    SELECT *,
        NTILE(5) OVER (ORDER BY recency_days ASC)  AS r_score,
        NTILE(5) OVER (ORDER BY frequency    DESC) AS f_score,
        NTILE(5) OVER (ORDER BY monetary     DESC) AS m_score
    FROM rfm_base
)
SELECT *,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
        WHEN f_score >= 3                  THEN 'Loyal Customers'
        WHEN r_score <= 2 AND f_score >= 2 THEN 'At Risk'
        WHEN r_score <= 2                  THEN 'Lost'
        ELSE 'Potential Loyalists'
    END AS segment
FROM rfm_scored;
```

### Revenue Trend with Month-over-Month Growth
```sql
WITH monthly AS (
    SELECT
        DATE_FORMAT(transaction_date, '%Y-%m') AS month,
        SUM(amount) AS revenue
    FROM transactions
    WHERE company_id = :company_id
      AND status = 'completed'
    GROUP BY DATE_FORMAT(transaction_date, '%Y-%m')
)
SELECT
    month,
    revenue,
    LAG(revenue) OVER (ORDER BY month)                          AS prev_month,
    ROUND(
        (revenue - LAG(revenue) OVER (ORDER BY month))
        / NULLIF(LAG(revenue) OVER (ORDER BY month), 0) * 100
    , 2)                                                        AS mom_growth_pct
FROM monthly
ORDER BY month;
```

---

## Background Jobs (Celery)

| Task | Queue | Schedule | Purpose |
|---|---|---|---|
| `quantyx.fraud.analyze_transaction` | fraud | On transaction create | Run 5 rules + XGBoost + SHAP |
| `quantyx.email.send_invitation` | email | On invite send | Gmail SMTP via fastapi-mail |
| `quantyx.analytics.refresh_all_analytics_caches` | analytics | Every hour | Rebuild Redis + DB caches |
| `quantyx.warehouse.run_nightly_etl` | analytics | 2:00 AM UTC daily | Cohort, LTV, heatmap tables |
| `quantyx.features.recompute_all_features` | features | Every 6 hours | Update ML feature store |
| `quantyx.monitoring.run_model_health_check` | features | Weekly Monday | F1, PSI drift, admin alert |

---

## Project Structure

```
quantyx-ai/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/     # 13 router modules (50+ endpoints)
│   │   ├── core/                 # config, JWT auth, rate limiter, middleware
│   │   ├── models/               # 22 SQLAlchemy models
│   │   ├── schemas/              # Pydantic v2 request/response schemas
│   │   ├── services/             # Business logic (15+ services)
│   │   ├── repositories/         # Tenant-scoped data access layer
│   │   ├── worker/               # Celery app + 6 task modules
│   │   ├── utils/                # Redis cache, audit, masking, metrics
│   │   └── templates/emails/     # Jinja2 HTML email templates
│   ├── ml/                       # XGBoost training script + feature manifest
│   ├── alembic/versions/         # 11 migration files
│   └── tests/
├── frontend/
│   └── src/
│       ├── features/             # 10 feature modules (pages + hooks)
│       ├── components/           # Layout, common UI, design system
│       ├── stores/               # 5 Zustand stores (auth, filter, ui, theme, notify)
│       ├── services/             # Axios API clients (per feature)
│       ├── lib/                  # axios instance, queryClient, apiBase
│       └── router/               # React Router v7 with lazy code-splitting
├── monitoring/                   # Prometheus scrape config + Grafana dashboards
├── .github/workflows/            # CI (lint + typecheck + test) + CD
├── docker-compose.yml
├── docker-compose.prod.yml
├── SETUP.md                      # Complete local setup guide (non-technical friendly)
└── Updated_Project_Summary.md    # Deep-dive architecture documentation
```

---

## Quick Start

> For a full step-by-step guide including Gmail setup, Groq API key, and Windows instructions, see **[SETUP.md](./SETUP.md)**.

### Prerequisites
- Python 3.11+, Node.js 20+, MySQL 8, Redis 7, Git

### 1. Clone & configure
```bash
git clone https://github.com/shreya-insights/quantyx-ai.git "Quantyx AI"
cd "Quantyx AI"
cp .env.example backend/.env
# Edit backend/.env — add DB credentials, GROQ_API_KEY, Gmail App Password
```

### 2. Backend
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Celery Worker (new terminal)
```bash
cd backend && source .venv/bin/activate
celery -A app.worker.celery_app worker --loglevel=info \
  --queues=fraud,email,analytics,features --concurrency=4
```

### 4. Frontend (new terminal)
```bash
cd frontend
cp .env.example .env
npm install && npm run dev
```

Open **http://localhost:3000** — register your company and start exploring.

---

## Subscription Tiers

| Feature | Starter (Free) | Growth | Enterprise |
|---|---|---|---|
| API calls/month | 10,000 | 100,000 | Unlimited |
| Transactions/month | 5,000 | 100,000 | Unlimited |
| API rate limit | 60 req/min | 300 req/min | 1,000 req/min |
| Team members | 3 | 15 | Unlimited |
| AI Analyst | — | ✅ | ✅ |
| Query Lab | — | ✅ | ✅ |
| PDF Reports | — | ✅ | ✅ |
| Model Health Dashboard | — | — | ✅ |

---

## Engineering Standards Applied

This project was built following FAANG Staff/Principal Engineer coding standards:

- **Security:** `company_id` always from JWT (never request body) · bcrypt passwords · SHA-256 invite tokens · append-only audit logs · parameterized SQL (zero injection surface)
- **Resilience:** Redis failure never blocks requests (fail-open) · Celery task idempotency checks · WebSocket graceful degradation to polling · ML model unavailability falls back to rules-only
- **Performance:** Sliding-window rate limiting (ZADD, not fixed-window) · two-tier analytics caching · pre-aggregated warehouse tables · async SQLAlchemy throughout
- **Observability:** structlog JSON logs with correlation IDs · Prometheus metrics on every endpoint · Grafana dashboards pre-provisioned · Celery queue depth monitoring
- **Code quality:** mypy strict mode · ruff linting · Google-style docstrings · max 40-line functions · no magic numbers · absolute imports only

---

## About the Builder

<div align="center">

### Shreya Tiwari
**MCA · VIT University Alumni**

Data Analytics | Fintech | Full-Stack Engineering

I built Quantyx AI to demonstrate production-level thinking in financial data systems — combining data engineering, ML, backend architecture, and frontend development into a single cohesive product.

My core interest is in **Data Analyst roles within fintech** — where SQL, Python, and a deep understanding of financial data intersect. This project is a direct expression of how I think about data pipelines, analytical query design, fraud pattern recognition, and turning raw data into business intelligence.

**What I bring:**
- Advanced SQL (window functions, CTEs, RFM, cohort analysis, partitioning)
- Python data stack (pandas, numpy, scikit-learn, XGBoost, SHAP)
- End-to-end data pipeline design (ingestion → transformation → visualization)
- Strong fintech domain understanding (transactions, fraud, LTV, KPIs)
- Full-stack capability to own a feature from DB schema to UI

---

**Open to opportunities in Data Analytics, Fintech, and Business Intelligence.**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/shreya-tiwari-738a43214?utm_source=share&utm_campaign=share_via&utm_content=profile&utm_medium=android_app)
[![Email](https://img.shields.io/badge/Email-tiwashreyaa@gmail.com-EA4335?style=for-the-badge&logo=gmail&logoColor=white)](mailto:tiwashreyaa@gmail.com)

*Suggestions, feedback, or collaboration ideas? Reach out at **tiwashreyaa@gmail.com***

</div>

---

<div align="center">

**Quantyx AI** — Production-grade fintech analytics, built from scratch.

*If this project resonates with the kind of engineering you're looking for on your team — let's talk.*

[![LinkedIn](https://img.shields.io/badge/Shreya_Tiwari-LinkedIn-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/shreya-tiwari-738a43214?utm_source=share&utm_campaign=share_via&utm_content=profile&utm_medium=android_app)
[![Email](https://img.shields.io/badge/Email-tiwashreyaa@gmail.com-EA4335?style=flat-square&logo=gmail)](mailto:tiwashreyaa@gmail.com)

</div>
