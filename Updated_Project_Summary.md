# Quantyx AI — Complete Project Documentation
### Full Architecture, Feature Breakdown, Data Flows, and Implementation Details

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Technology Stack](#2-technology-stack)
3. [Repository Structure](#3-repository-structure)
4. [Backend Architecture](#4-backend-architecture)
5. [Database Schema — All Models & Fields](#5-database-schema--all-models--fields)
6. [All API Endpoints (Detailed)](#6-all-api-endpoints-detailed)
7. [Authentication & Authorization System](#7-authentication--authorization-system)
8. [Multi-Tenancy Architecture](#8-multi-tenancy-architecture)
9. [Rate Limiting & Subscription Metering](#9-rate-limiting--subscription-metering)
10. [Fraud Detection System](#10-fraud-detection-system)
11. [Analytics Engine](#11-analytics-engine)
12. [AI Analyst Feature](#12-ai-analyst-feature)
13. [Team Invitations & Email System](#13-team-invitations--email-system)
14. [Celery Workers & Background Tasks](#14-celery-workers--background-tasks)
15. [Real-Time WebSocket System](#15-real-time-websocket-system)
16. [ML Model — Training, Serving, Monitoring](#16-ml-model--training-serving-monitoring)
17. [Query Lab Feature](#17-query-lab-feature)
18. [Reports & Exports](#18-reports--exports)
19. [Subscriptions & Plan Management](#19-subscriptions--plan-management)
20. [Audit Logging](#20-audit-logging)
21. [Observability — Prometheus, Grafana, Structlog](#21-observability--prometheus-grafana-structlog)
22. [Frontend Architecture](#22-frontend-architecture)
23. [Frontend Routing & Pages](#23-frontend-routing--pages)
24. [Frontend State Management](#24-frontend-state-management)
25. [Frontend Features — Component-Level Detail](#25-frontend-features--component-level-detail)
26. [Onboarding Wizard](#26-onboarding-wizard)
27. [End-to-End Data Flows](#27-end-to-end-data-flows)
28. [Environment Variables Reference](#28-environment-variables-reference)
29. [CI/CD Pipeline](#29-cicd-pipeline)
30. [Docker & Infrastructure Setup](#30-docker--infrastructure-setup)
31. [Alembic Migrations](#31-alembic-migrations)
32. [Security Model](#32-security-model)
33. [Dependencies Reference](#33-dependencies-reference)

---

## 1. Project Overview

**Quantyx AI** is a production-grade, multi-tenant fintech SaaS (Software-as-a-Service) platform that provides financial analytics, real-time fraud detection, customer intelligence, and an AI-powered natural language analyst to fintech companies and banks.

**What problem it solves:**
Financial institutions and fintech startups need to analyze transaction data, detect fraud in real time, understand customer lifetime value, and query raw data — all without building their own data infrastructure. Quantyx AI provides all of this as a hosted, multi-tenant service behind a subscription model.

**Who uses it:**
- **Admin** (company owner): full access, manages team, billing, settings
- **Analyst**: can view and query data, use AI Analyst, access analytics
- **Viewer**: read-only access with PII masking on sensitive transaction fields

**Core product capabilities:**
1. Transaction ingestion (single + bulk CSV)
2. Real-time fraud detection with ML scoring + rule engine
3. Revenue trend analysis, RFM customer segmentation, cohort retention
4. AI-powered natural language querying of financial data
5. SQL Query Lab with saved queries and templates
6. CSV/PDF export of reports
7. Team management with email-based invitations
8. Role-based access control (RBAC) with JWT
9. Subscription tier management (Starter / Growth / Enterprise)
10. Prometheus metrics + Grafana dashboards

---

## 2. Technology Stack

### Backend
| Layer | Technology | Version | Why Chosen |
|---|---|---|---|
| Web Framework | FastAPI | latest | Async-first, Pydantic integration, auto OpenAPI docs |
| ORM | SQLAlchemy 2.0 | async | Type-safe, supports async sessions with aiomysql |
| Database | MySQL 8.0 | 8.x | Window functions, JSON columns, battle-tested for fintech |
| Cache / Broker | Redis 7 | 7.x | Fast, pub/sub for WebSocket, Celery broker, rate-limit ZADD |
| Task Queue | Celery + RedBeat | latest | Async fraud scoring, email, ETL, beat scheduling |
| Auth | python-jose | latest | JWT HS256 sign/verify |
| Password | passlib/bcrypt | latest | Industry-standard password hashing |
| Validation | Pydantic v2 | 2.x | Schema validation, settings management |
| ML | scikit-learn + XGBoost | latest | Fraud scoring model |
| Explainability | SHAP | latest | EU AI Act compliance for ML decisions |
| Email | fastapi-mail + Jinja2 | latest | Template-based transactional email |
| Logging | structlog | latest | Structured JSON logs, ELK-compatible |
| Metrics | prometheus-client | latest | Prometheus scrape endpoint |
| HTTP Client | httpx | latest | Async HTTP for OpenRouter LLM calls |
| Data | pandas + numpy | latest | Feature engineering, CSV ingestion |
| PDF | reportlab | latest | PDF report generation |
| Excel | openpyxl | latest | CSV/Excel export |

### Frontend
| Layer | Technology | Version | Why Chosen |
|---|---|---|---|
| Build Tool | Vite | 8.x | Instant HMR, ESM-native, fast builds |
| UI Library | React | 19.x | Component model, hooks, concurrent features |
| Language | TypeScript (strict) | 5.x | Type safety, noImplicitAny, strictNullChecks |
| CSS | Tailwind CSS | 3.x | Utility-first, consistent design tokens |
| Data Fetching | TanStack Query v5 | 5.x | Server state management, cache, background refetch |
| Global State | Zustand v5 | 5.x | Minimal boilerplate, immer middleware |
| Routing | React Router v7 | 7.x | Nested routes, lazy code-splitting |
| Forms | React Hook Form + Zod | latest | Performant forms with schema validation |
| Charts | Recharts | latest | React-native SVG charts |
| Animations | Framer Motion | latest | Transform/opacity animations only |
| Lottie | lottie-react | latest | JSON animation playback |
| Code Editor | Monaco Editor | latest | SQL editor in Query Lab |
| HTTP Client | Axios | latest | Interceptors for token injection/refresh |
| Icons | Lucide React | latest | Consistent icon system |

### Infrastructure
| Component | Technology |
|---|---|
| Container | Docker + Docker Compose |
| Monitoring | Prometheus + Grafana |
| CI/CD | GitHub Actions |

---

## 3. Repository Structure

```
/Quantyx AI/
├── .cursor/rules/                     # Cursor AI coding rules (FAANG standards)
│   ├── Quantyx-AI-FAANG-Engineering-Standards.mdc
│   ├── Cloud-Only-Free-LLM-Setup.mdc
│   ├── email-statement-wizard.mdc
│   └── quantyx_git_identity.mdc
├── .github/
│   └── workflows/
│       ├── ci.yml                     # CI: lint, typecheck, test
│       └── cd.yml                     # CD: build and deploy
├── monitoring/
│   ├── prometheus.yml                 # Prometheus scrape config
│   └── grafana/
│       └── provisioning/              # Grafana dashboards + datasources
├── backend/
│   ├── alembic/
│   │   ├── env.py                     # Alembic async migration runner
│   │   └── versions/
│   │       ├── 0001_initial_schema.py
│   │       ├── 0002_*.py
│   │       ├── ...
│   │       └── 0011_invitations.py    # Latest: invitations table
│   ├── app/
│   │   ├── main.py                    # FastAPI app factory + lifespan
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── router.py          # Aggregates all endpoint routers
│   │   │       └── endpoints/
│   │   │           ├── auth.py
│   │   │           ├── invitations.py
│   │   │           ├── transactions.py
│   │   │           ├── analytics.py
│   │   │           ├── fraud.py
│   │   │           ├── query_lab.py
│   │   │           ├── reports.py
│   │   │           ├── subscriptions.py
│   │   │           ├── analyst.py
│   │   │           ├── audit.py
│   │   │           ├── accounts_merchants.py
│   │   │           ├── model_health.py
│   │   │           └── websocket.py
│   │   ├── core/
│   │   │   ├── config.py              # All settings via pydantic-settings
│   │   │   ├── dependencies.py        # JWT auth, rate limiter, DB session
│   │   │   ├── exceptions.py          # QuantyxException base class
│   │   │   ├── middleware.py          # RequestLoggingMiddleware + TenantUsageMiddleware
│   │   │   └── security.py            # bcrypt + JWT create/decode
│   │   ├── db/
│   │   │   ├── base.py                # DeclarativeBase
│   │   │   ├── session.py             # Async engine + sessionmaker
│   │   │   └── types.py               # Custom column types
│   │   ├── models/                    # SQLAlchemy ORM models (14 modules)
│   │   ├── schemas/                   # Pydantic request/response schemas
│   │   ├── repositories/              # Data access layer (7 repos)
│   │   ├── services/                  # Business logic (15+ services)
│   │   ├── worker/
│   │   │   ├── celery_app.py          # Celery + RedBeat config
│   │   │   └── tasks/
│   │   │       ├── fraud_tasks.py
│   │   │       ├── email_tasks.py
│   │   │       ├── analytics_tasks.py
│   │   │       ├── feature_tasks.py
│   │   │       ├── warehouse_tasks.py
│   │   │       └── monitoring_tasks.py
│   │   ├── utils/
│   │   │   ├── audit.py               # Audit log helper
│   │   │   ├── cache.py               # Redis client + get/set helpers
│   │   │   ├── masking.py             # PII masking for viewer role
│   │   │   ├── metrics.py             # Prometheus counter/histogram definitions
│   │   │   ├── pagination.py          # Offset pagination helper
│   │   │   └── ws_connection_manager.py # WebSocket connection registry
│   │   └── templates/
│   │       └── emails/
│   │           ├── base.html          # Email base layout (table-based)
│   │           ├── invitation.html    # Invite email template (Jinja2)
│   │           └── invitation_text.txt # Plain text fallback
│   ├── ml/
│   │   ├── train_fraud_model.py       # XGBoost model training script
│   │   ├── feature_columns.json       # Canonical feature list (training = serving)
│   │   └── __init__.py
│   ├── tests/                         # pytest test suite
│   ├── requirements.txt               # Pinned Python dependencies
│   └── run_dev.sh                     # Dev startup script
└── frontend/
    ├── index.html                     # SPA entry point
    ├── vite.config.ts                 # Vite config + dev proxy
    ├── tsconfig.json                  # TypeScript base config
    ├── tsconfig.app.json              # App-specific TS config (strict mode)
    ├── package.json                   # Node dependencies
    ├── .env                           # Local env (gitignored)
    ├── .env.example                   # Env template
    └── src/
        ├── main.tsx                   # React root mount
        ├── App.tsx                    # QueryClientProvider + RouterProvider
        ├── index.css                  # Global styles + Tailwind directives
        ├── vite-env.d.ts
        ├── router/
        │   └── index.tsx              # All routes (lazy-loaded)
        ├── components/
        │   ├── layout/
        │   │   ├── AppShell.tsx       # Sidebar + Topbar + Outlet
        │   │   ├── Sidebar.tsx        # Nav links, role-based visibility
        │   │   └── Topbar.tsx         # User avatar, theme toggle, notifications
        │   ├── common/
        │   │   ├── ProtectedRoute.tsx # JWT check + redirect to login
        │   │   ├── PageHeader.tsx     # Page title + subtitle component
        │   │   ├── ErrorBoundary.tsx  # React error boundary for pages
        │   │   └── EmptyState.tsx     # Zero-data placeholder
        │   └── ui/
        │       ├── Button.tsx
        │       ├── Card.tsx
        │       ├── Input.tsx
        │       ├── Modal.tsx
        │       ├── Badge.tsx
        │       ├── Spinner.tsx
        │       ├── Skeleton.tsx
        │       └── index.ts           # Barrel export
        ├── features/
        │   ├── auth/                  # Login, Register, Accept Invite, Landing
        │   ├── wizard/                # Onboarding wizard (5 steps)
        │   ├── dashboard/             # KPI dashboard + live feed
        │   ├── analytics/             # Revenue, RFM, cohort, heatmap, LTV
        │   ├── transactions/          # Transaction list + fraud status
        │   ├── fraud/                 # Fraud alerts + explanations
        │   ├── query-lab/             # SQL editor + saved queries
        │   ├── reports/               # CSV/PDF export
        │   ├── settings/              # Profile + team settings
        │   ├── ai-analyst/            # Natural language AI analyst chat
        │   └── [each feature]/
        │       ├── pages/             # Page-level components
        │       ├── components/        # Feature-specific UI
        │       └── hooks/             # Feature-specific TanStack Query hooks
        ├── hooks/                     # Shared hooks (pagination, websocket, etc.)
        ├── services/                  # Axios API client modules (per feature)
        ├── stores/                    # Zustand stores (auth, ui, filter, theme, etc.)
        ├── types/                     # TypeScript type definitions
        ├── lib/                       # axios instance, queryClient, apiBase
        ├── utils/                     # constants, format, cn, jwtExpiry
        └── assets/
            └── animations/            # Lottie JSON files
```

---

## 4. Backend Architecture

### Application Startup (`main.py` lifespan)

When FastAPI starts, the `lifespan` context manager runs:
1. Calls `init_metrics_at_startup()` — registers all Prometheus counters/histograms
2. Calls `MLFraudService.load()` in a thread — loads the XGBoost model and `feature_columns.json` from `backend/ml/` into memory. If the model file is not found, the app continues with rules-only fraud detection (graceful degradation)
3. Logs startup with structlog (version, debug mode)

On shutdown:
1. Closes the Redis async client cleanly

### Middleware Stack (request processing order)
1. **CORSMiddleware** — allows `localhost:3000` (dev) or configured origins
2. **RequestLoggingMiddleware** — assigns a correlation ID (`X-Correlation-ID`) to every request, logs request/response details via structlog, records Prometheus HTTP metrics (method, path, status, latency)
3. **TenantUsageMiddleware** — exists for tenant usage tracking (quota increment is a Redis-backed operation; actual quota enforcement is in `check_rate_limit`)
4. **QuantyxException handler** — converts all `QuantyxException` subclasses into structured JSON `{"error_code": "...", "detail": "..."}` responses

### API Routing
All endpoints live under `/api/v1` prefix, defined in `app/api/v1/router.py`. The router aggregates 13 separate endpoint modules. Each module is a FastAPI `APIRouter` with its own prefix and tags.

### Service Layer Architecture
The backend follows strict layering:
```
HTTP Endpoint (router)
    ↓ calls
Service (business logic, validation, orchestration)
    ↓ calls
Repository (SQL queries, always tenant-scoped)
    ↓ calls
SQLAlchemy async session → MySQL
```
Redis is accessed directly from services/rate-limiter via `app/utils/cache.py` helper.

---

## 5. Database Schema — All Models & Fields

### `companies`
Represents a tenant organization. Every piece of data in the system is owned by a company.

| Column | Type | Description |
|---|---|---|
| `id` | UUID / PK | Company unique identifier |
| `name` | VARCHAR | Company display name |
| `slug` | VARCHAR (unique) | URL-safe identifier (e.g. "acme-bank") |
| `subscription_tier` | ENUM | starter / growth / enterprise |
| `api_key` | VARCHAR | API key for programmatic access |
| `is_active` | BOOLEAN | Soft-delete flag |
| `created_at` | DATETIME | Creation timestamp |
| `updated_at` | DATETIME | Last update timestamp |

### `users`
People who log into Quantyx AI. Always belong to one company.

| Column | Type | Description |
|---|---|---|
| `id` | UUID / PK | User unique identifier |
| `company_id` | FK → companies | Tenant ownership |
| `email` | VARCHAR (unique) | Login email |
| `hashed_password` | VARCHAR | bcrypt hash |
| `full_name` | VARCHAR | Display name |
| `role` | ENUM | admin / analyst / viewer |
| `is_active` | BOOLEAN | Account active flag |
| `last_login` | DATETIME | Last successful login |
| `created_at` | DATETIME | |
| `updated_at` | DATETIME | |

### `subscriptions`
Subscription state per company. Controls plan limits and billing.

| Column | Type | Description |
|---|---|---|
| `id` | UUID / PK | |
| `company_id` | FK → companies | |
| `plan_name` | VARCHAR | starter / growth / enterprise |
| `status` | ENUM | active / cancelled / expired |
| `billing_cycle` | ENUM | monthly / annual |
| `amount` | DECIMAL | Billing amount |
| `currency` | VARCHAR | USD / etc. |
| `starts_at` | DATETIME | Plan start |
| `ends_at` | DATETIME | Plan end / renewal |
| `api_calls_limit` | INT | Monthly API call quota |
| `api_calls_used` | INT | Calls used this period |
| `transaction_limit` | INT | Max transactions per month |
| `created_at` | DATETIME | |

### `transactions`
The core financial event. Every fraud detection, analytics computation, and report is based on this table.

| Column | Type | Description |
|---|---|---|
| `id` | UUID / PK | |
| `company_id` | FK → companies | Tenant isolation |
| `account_id` | FK → accounts | Source account |
| `merchant_id` | FK → merchants | Destination merchant |
| `category_id` | FK → categories | Spend category |
| `transaction_ref` | VARCHAR (unique) | External reference ID |
| `amount` | DECIMAL | Transaction amount |
| `currency` | VARCHAR | ISO currency code |
| `transaction_type` | ENUM | purchase / refund / transfer / withdrawal / deposit |
| `status` | ENUM | pending / completed / failed / reversed |
| `description` | TEXT | Narrative |
| `metadata` | JSON | Arbitrary extra fields |
| `ip_address` | VARCHAR | Origin IP |
| `device_fingerprint` | VARCHAR | Device fingerprint |
| `location_lat` | FLOAT | GPS latitude |
| `location_lng` | FLOAT | GPS longitude |
| `transaction_date` | DATETIME | Business date of transaction |
| `created_at` | DATETIME | Insertion timestamp |
| `fraud_analyzed_at` | DATETIME | When fraud analysis completed |
| `fraud_check_job_id` | VARCHAR | Celery task ID for polling |

### `accounts`
Bank/wallet accounts owned by users under a company.

| Column | Type | Description |
|---|---|---|
| `id` | UUID / PK | |
| `company_id` | FK → companies | |
| `user_id` | FK → users | Account owner |
| `account_number` | VARCHAR (unique) | Masked in viewer role |
| `account_type` | ENUM | checking / savings / credit / wallet |
| `balance` | DECIMAL | Current balance |
| `currency` | VARCHAR | |
| `is_active` | BOOLEAN | |
| `opened_at` | DATETIME | Account opening date |
| `created_at` | DATETIME | |

### `merchants`
Payee entities. Linked to transactions.

| Column | Type | Description |
|---|---|---|
| `id` | UUID / PK | |
| `company_id` | FK → companies | |
| `name` | VARCHAR | Merchant name |
| `category_code` | VARCHAR | MCC (merchant category code) |
| `country` | VARCHAR | ISO country |
| `city` | VARCHAR | |
| `is_flagged` | BOOLEAN | Manually flagged suspicious |
| `created_at` | DATETIME | |

### `categories`
Hierarchical transaction category taxonomy.

| Column | Type | Description |
|---|---|---|
| `id` | UUID / PK | |
| `name` | VARCHAR | e.g. "Food & Dining" |
| `code` | VARCHAR (unique) | e.g. "food_dining" |
| `parent_id` | FK → self | Parent category (nullable) |

### `fraud_alerts`
Created whenever fraud is detected on a transaction. Resolved by analysts.

| Column | Type | Description |
|---|---|---|
| `id` | UUID / PK | |
| `company_id` | FK → companies | |
| `transaction_id` | FK → transactions | |
| `alert_type` | ENUM | velocity / amount_spike / location_anomaly / duplicate / ml_model / rule_based |
| `severity` | ENUM | low / medium / high / critical |
| `confidence_score` | FLOAT | 0.0–1.0 ML confidence |
| `description` | TEXT | Human-readable explanation |
| `is_resolved` | BOOLEAN | |
| `resolved_by` | FK → users | |
| `resolved_at` | DATETIME | |
| `rule_metadata` | JSON | Which rules triggered + values |
| `model_version` | VARCHAR | ML model version that scored this |
| `is_confirmed` | BOOLEAN | Analyst confirmed as real fraud |
| `resolved_by_analyst_label` | VARCHAR | Analyst's resolution label |
| `created_at` | DATETIME | |

### `invitations`
Email invitations for team members. Tokens are stored as SHA-256 hashes only.

| Column | Type | Description |
|---|---|---|
| `id` | UUID / PK | |
| `company_id` | FK → companies | |
| `email` | VARCHAR | Invitee email |
| `role` | ENUM | analyst / viewer (admin cannot be invited) |
| `token_hash` | VARCHAR (unique) | SHA-256 of raw token |
| `status` | ENUM | pending / accepted / revoked / expired |
| `invited_by_id` | FK → users | Admin who sent invite |
| `invited_by_email` | VARCHAR | Denormalized for audit trail |
| `company_name` | VARCHAR | Denormalized for email rendering |
| `expires_at` | DATETIME | `created_at + INVITE_TOKEN_EXPIRE_HOURS` (default 72h) |
| `accepted_at` | DATETIME | When the invitee clicked accept |
| `email_sent_at` | DATETIME | When Celery sent the email |
| `resend_count` | INT | Number of resend operations |
| `created_at` | DATETIME | |

### `saved_queries`
SQL queries saved by users in the Query Lab.

| Column | Type | Description |
|---|---|---|
| `id` | UUID / PK | |
| `company_id` | FK → companies | |
| `user_id` | FK → users | |
| `name` | VARCHAR | Query name |
| `description` | TEXT | |
| `query_text` | TEXT | The SQL |
| `is_public` | BOOLEAN | Visible to all company users |
| `execution_count` | INT | How many times run |
| `last_executed_at` | DATETIME | |
| `created_at` | DATETIME | |
| `updated_at` | DATETIME | |

### `kpi_reports`
Pre-generated KPI snapshots per period. Used for historical trend comparison.

| Column | Type | Description |
|---|---|---|
| `id` | UUID / PK | |
| `company_id` | FK → companies | |
| `report_type` | VARCHAR | monthly / quarterly / annual |
| `period_start` | DATETIME | |
| `period_end` | DATETIME | |
| `metrics` | JSON | `{"revenue": ..., "txn_count": ..., ...}` |
| `generated_at` | DATETIME | |

### `audit_logs`
Append-only compliance log. No foreign key constraints by design (users/companies may be deleted but audit trail must remain).

| Column | Type | Description |
|---|---|---|
| `id` | UUID / PK | |
| `company_id` | UUID (no FK) | Denormalized |
| `user_id` | UUID (no FK) | Denormalized |
| `user_email` | VARCHAR | Denormalized |
| `action` | VARCHAR | e.g. "transaction.create", "fraud.resolve" |
| `resource_type` | VARCHAR | e.g. "transaction", "invitation" |
| `resource_id` | VARCHAR | ID of affected resource |
| `ip_address` | VARCHAR | |
| `user_agent` | VARCHAR | |
| `request_path` | VARCHAR | HTTP path |
| `request_method` | VARCHAR | GET/POST/etc. |
| `response_status` | INT | HTTP response code |
| `duration_ms` | INT | Request latency |
| `metadata` | JSON | Extra context |
| `created_at` | DATETIME | Immutable timestamp |

### `admin_notifications`
System-generated notifications surfaced to admins.

| Column | Type | Description |
|---|---|---|
| `id` | UUID / PK | |
| `company_id` | FK → companies (nullable) | Null = system-wide |
| `notification_type` | VARCHAR | fraud_spike / model_drift / quota_warning |
| `severity` | ENUM | info / warning / critical |
| `title` | VARCHAR | |
| `body` | TEXT | |
| `metadata` | JSON | |
| `is_read` | BOOLEAN | |
| `created_at` | DATETIME | |

### Feature Store Tables
Pre-computed per-user and per-merchant feature vectors for the ML fraud model. Updated by Celery every 6 hours.

**`user_features`** — per `(company_id, user_id)`:
- `avg_txn_amount_30d`, `txn_count_30d`, `unique_merchants_30d`
- `avg_txn_amount_7d`, `txn_count_7d`
- `fraud_rate_30d` (historical fraud label rate)
- `last_txn_at`, `updated_at`

**`merchant_features`** — per `(company_id, merchant_id)`:
- `avg_txn_amount`, `txn_count`, `fraud_rate`, `unique_users`
- `updated_at`

**`velocity_features`** — per `(company_id, account_id)`:
- `txn_count_1h`, `txn_count_24h`, `amount_sum_1h`, `amount_sum_24h`
- `updated_at`

### Analytics Cache Tables
Pre-aggregated tables populated nightly by Celery ETL. Eliminates heavy OLAP queries from the HTTP path.

- **`daily_revenue_summaries`** — `(company_id, date, revenue, txn_count, avg_txn_amount)`
- **`monthly_category_summaries`** — `(company_id, year_month, category_id, amount_sum, txn_count)`
- **`merchant_ranking_caches`** — `(company_id, period, merchant_id, rank, revenue, txn_count)`
- **`kpi_summary_caches`** — `(company_id, period, metrics JSON)`

### Warehouse / Data Mart Tables
Pre-built analytical aggregates from nightly ETL (02:00 UTC).

- **`cohort_retention_metrics`** — `(company_id, cohort_month, period_number, retained_users, cohort_size, retention_rate)`
- **`lifetime_value_metrics`** — `(company_id, segment, avg_ltv, user_count, avg_orders, avg_order_value)`
- **`hourly_transaction_heatmaps`** — `(company_id, day_of_week, hour_of_day, txn_count, avg_amount)`

### Model Monitoring Tables
Populated by weekly Celery monitoring task.

- **`model_performance_metrics`** — `(company_id, model_version, date, precision, recall, f1, auc_pr, sample_count)`
- **`feature_distribution_snapshots`** — `(company_id, feature_name, date, psi_score, mean, std, drift_detected)`

---

## 6. All API Endpoints (Detailed)

Base URL: `http://localhost:8000/api/v1` (dev)

### Auth Endpoints
| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | Public | Register new company + admin user. Creates company, user, and trial subscription in one transaction. Returns `{access_token, refresh_token, user}`. |
| `POST` | `/auth/login` | Public | Email + password login. Validates credentials, updates `last_login`. Returns token pair. |
| `POST` | `/auth/refresh` | Public | Exchanges refresh token for new access + refresh tokens. Validates `type=refresh` claim. |
| `GET` | `/auth/me` | Bearer | Returns current user's profile (`id`, `email`, `role`, `company_id`, `full_name`). |
| `POST` | `/auth/users/invite` | Admin | Legacy: creates a user with password directly (no email flow). |

### Invitation Endpoints
| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/invitations/send` | Admin | Creates invitation record + enqueues Celery email task. Validates email not already a user/pending invite. |
| `POST` | `/invitations/send-bulk` | Admin | Accepts array of `{email, role}`. Dispatches one Celery task per email. Returns per-email status. |
| `GET` | `/invitations` | Admin | Lists all invitations for company (paginated). Shows status, expiry, resend_count. |
| `POST` | `/invitations/{id}/resend` | Admin | Rate-limited (Redis). Revokes old token hash, issues new token, re-enqueues email task. |
| `DELETE` | `/invitations/{id}` | Admin | Sets status to "revoked". Token hash is now invalid. |
| `GET` | `/invitations/validate?token=` | **Public** | Rate-limited (IP). Validates raw token against SHA-256 hash in DB. Returns invitation metadata (company_name, role, email, expiry) if valid. |
| `POST` | `/invitations/accept` | **Public** | Rate-limited (IP). Validates token, creates user with hashed password, marks invitation accepted, returns JWT pair. |

### Transaction Endpoints
| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/transactions` | Bearer | Paginated, filterable list. Filters: `status`, `category_id`, `merchant_id`, `date_from`, `date_to`, `amount_min`, `amount_max`, `search`. Viewer role: account_number, ip_address, device_fingerprint are masked. |
| `POST` | `/transactions` | Analyst+ | Creates a transaction, generates `transaction_ref` if not provided, enqueues `quantyx.fraud.analyze_transaction` Celery task, returns transaction with `fraud_check_job_id`. |
| `GET` | `/transactions/{id}/fraud-status` | Bearer | Polls Celery result backend for fraud job. Returns `{status: pending/complete, fraud_alerts: [...], confidence_score}`. |
| `POST` | `/transactions/bulk-upload` | Admin | Accepts CSV multipart file. Parses with pandas, validates schema, inserts rows in batches, enqueues up to `BULK_UPLOAD_MAX_FRAUD_TASKS` (2000) fraud tasks. Returns `{inserted, errors, job_ids}`. |

### Account & Merchant Endpoints
| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/accounts` | Analyst+ | Create account. Auto-sets `company_id` from JWT. |
| `GET` | `/accounts` | Bearer | List active accounts for company. |
| `POST` | `/merchants` | Analyst+ | Create merchant. |
| `GET` | `/merchants` | Bearer | List merchants for company. |

### Analytics Endpoints
All analytics endpoints require Bearer token. Results are served from Redis cache (if fresh) or pre-aggregated DB cache tables. Cache TTLs vary by endpoint.

| Method | Path | Cache TTL | Description |
|---|---|---|---|
| `GET` | `/analytics/kpi-summary` | 5 min | Total revenue, txn count, active accounts, fraud rate for current period. |
| `GET` | `/analytics/revenue-trends` | 15 min | Daily revenue time series. Uses window functions or `daily_revenue_summaries`. |
| `GET` | `/analytics/customer-segmentation` | 30 min | RFM segmentation: groups customers into Champions / Loyal / At Risk / Lost etc. |
| `GET` | `/analytics/cohort` | 1 hour | Legacy cohort shape (first-purchase month → retention %). |
| `GET` | `/analytics/cohort-retention` | 1 hour | Full retention grid from `cohort_retention_metrics` warehouse table. |
| `GET` | `/analytics/ltv-segments` | 30 min | Customer LTV distribution from `lifetime_value_metrics`. |
| `GET` | `/analytics/top-merchants` | 10 min | Merchant ranking by transaction volume / revenue. |
| `GET` | `/analytics/spending-by-category` | 10 min | Category breakdown by amount. |
| `GET` | `/analytics/transaction-heatmap` | 10 min | Hour-of-day × day-of-week frequency grid (live query). |
| `GET` | `/analytics/heatmap` | 10 min | Same from warehouse table `hourly_transaction_heatmaps`. |

### Fraud Endpoints
| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/fraud/alerts` | Bearer | Paginated fraud alerts. Filters: `severity`, `is_resolved`, `alert_type`, `date_from`, `date_to`. |
| `GET` | `/fraud/alerts/{id}` | Bearer | Single fraud alert with full `rule_metadata` and SHAP explanation fields. |
| `POST` | `/fraud/alerts/{id}/resolve` | Analyst+ | Marks alert resolved, records `resolved_by`, `resolved_at`, `is_confirmed`, `resolved_by_analyst_label`. |
| `GET` | `/fraud/stats` | Bearer | Aggregate stats: total alerts, by severity, by type, resolution rate, avg confidence. |

### Query Lab Endpoints
| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/query-lab/execute` | Analyst+ | Executes SQL query. Scoped to company: `company_id` is injected as bound parameter; schema is restricted to allowed tables. Returns rows + execution time. |
| `GET` | `/query-lab/templates` | Bearer | Returns pre-built SQL query templates (revenue by month, top merchants, etc.). |
| `POST` | `/query-lab/saved` | Analyst+ | Save a query with name + description. |
| `GET` | `/query-lab/saved` | Bearer | List saved queries (own + public queries of company). |
| `DELETE` | `/query-lab/saved/{id}` | Analyst+ | Delete saved query (must own it). |

### Report Endpoints
| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/reports/generate/csv` | Bearer | Streams a CSV of transactions for a date range. Uses chunked pandas export. |
| `GET` | `/reports/generate/pdf` | Bearer | Generates PDF with KPI summary + charts using reportlab. Streamed as `application/pdf`. |

### Subscription Endpoints
| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/subscriptions/plans` | Public | Returns plan catalog with limits and pricing. |
| `GET` | `/subscriptions/current` | Bearer | Current subscription details for company. |
| `POST` | `/subscriptions/subscribe` | Admin | Subscribe to a plan. Creates subscription record. |
| `POST` | `/subscriptions/upgrade` | Admin | Upgrade existing subscription to a higher plan. |
| `GET` | `/subscriptions/usage` | Bearer | API calls used this month vs. limit. |

### AI Analyst Endpoints
| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/analyst/ask` | Analyst+ | Accepts `{question: string}`. Runs LLM with tool-use loop (up to 5 rounds). Returns `{answer, sources, tool_calls_made}`. Rate limited: 20 calls/hour/user via Redis. |
| `GET` | `/analyst/suggested-questions` | Bearer | Returns cached list of suggested questions for onboarding. |
| `GET` | `/analyst/provider-status` | Admin | Shows which LLM providers are configured, active model names. |

### Audit & Model Health Endpoints
| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/audit/logs` | Admin | Paginated audit log. Filters: `action`, `user_id`, `resource_type`, `date_from`, `date_to`. |
| `GET` | `/model-health` | Admin | Returns latest model performance metrics from `model_performance_metrics` table. |

### WebSocket Endpoint
| Type | Path | Auth | Description |
|---|---|---|---|
| `WS` | `/api/v1/ws/company/{company_id}?token=JWT` | Bearer (query param) | Subscribes to Redis channel `quantyx:events:{company_id}`. Receives real-time events: new fraud alerts, transaction updates, system notifications. Server sends heartbeat pings every 30s. |

### System Endpoints (no `/api/v1` prefix)
| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Returns `{status, version, latency_ms, celery_workers, ml_model}`. `status=healthy` only if Celery workers respond. |
| `GET` | `/metrics` | Prometheus scrape endpoint. Refreshes Celery queue depth gauges before responding. |
| `GET` | `/docs` | Swagger UI (OpenAPI 3.1) |
| `GET` | `/redoc` | ReDoc documentation |

---

## 7. Authentication & Authorization System

### Why JWT + RBAC
Quantyx AI is multi-tenant SaaS. Each request must carry proof of identity (who), company ownership (which tenant), and permission level (what they can do). Stateless JWTs allow horizontal scaling without shared session storage.

### Token Structure

**Access Token** (valid 30 minutes):
```json
{
  "sub": "user-uuid",
  "company_id": "company-uuid",
  "role": "admin|analyst|viewer",
  "email": "user@example.com",
  "type": "access",
  "exp": 1234567890,
  "iat": 1234567890
}
```

**Refresh Token** (valid 7 days):
```json
{
  "sub": "user-uuid",
  "company_id": "company-uuid",
  "role": "admin|analyst|viewer",
  "email": "user@example.com",
  "type": "refresh",
  "exp": 1234567890
}
```
Both signed with `SECRET_KEY` using `HS256` algorithm.

### Auth Dependency Chain (`core/dependencies.py`)

```
HTTP Request
    → HTTPBearer extracts token from Authorization header
    → decode_token() validates signature + expiry + type="access"
    → Returns TokenData(user_id, company_id, role, email)
    → Injected as current_user in all protected endpoints
```

Three FastAPI dependency functions:
- `get_current_token` — any authenticated user
- `require_admin` — role must be "admin"
- `require_analyst_or_above` — role must be "admin" or "analyst"

**WebSocket auth:** token passed as query parameter `?token=JWT`, validated to `type=access`, and `company_id` in token must match `company_id` in URL path.

### Role Permissions Matrix

| Feature | Viewer | Analyst | Admin |
|---|---|---|---|
| View transactions | ✅ (masked) | ✅ | ✅ |
| Create transactions | ❌ | ✅ | ✅ |
| Bulk upload CSV | ❌ | ❌ | ✅ |
| View fraud alerts | ✅ | ✅ | ✅ |
| Resolve fraud alerts | ❌ | ✅ | ✅ |
| Use AI Analyst | ❌ | ✅ | ✅ |
| Run SQL queries | ❌ | ✅ | ✅ |
| View analytics | ✅ | ✅ | ✅ |
| Send invitations | ❌ | ❌ | ✅ |
| Manage subscriptions | ❌ | ❌ | ✅ |
| View audit logs | ❌ | ❌ | ✅ |
| View model health | ❌ | ❌ | ✅ |
| LLM provider status | ❌ | ❌ | ✅ |

### PII Masking for Viewers
The `app/utils/masking.py` module transforms transaction response fields for viewer-role users:
- `account_number` → `"****1234"` (last 4 digits only)
- `ip_address` → `"***.***.***.***"`
- `device_fingerprint` → `"[redacted]"`

This happens in the transaction endpoint after fetching data, before serialization.

### Password Security
- `passlib` with `bcrypt` rounds (default 12)
- Passwords never stored in plaintext or logged
- `security.py` provides `hash_password(plain)` and `verify_password(plain, hashed)`

### Frontend Token Management
- Tokens stored in `localStorage` (`access_token`, `refresh_token`)
- Zustand `useAuthStore` holds the decoded user object in memory
- `lib/axios.ts` Axios interceptor:
  1. Attaches `Authorization: Bearer {access_token}` to every request
  2. On 401 response, attempts token refresh via `POST /auth/refresh`
  3. If refresh succeeds, retries the original request with new token
  4. If refresh fails, clears tokens and redirects to `/login`
- `utils/jwtExpiry.ts` checks token expiry before making requests

---

## 8. Multi-Tenancy Architecture

### Design Principle
Quantyx AI uses a **shared-schema multi-tenancy** model: all tenants share the same MySQL database and tables. Tenant isolation is enforced at the query level by always filtering on `company_id`.

### Why shared schema?
- Simpler operations (single DB to backup/monitor)
- Easier schema migrations (one `alembic upgrade head`)
- Works well for SaaS with moderate tenant counts
- Trades some isolation for operational simplicity

### Isolation Enforcement Points

1. **JWT carries `company_id`** — cannot be spoofed without `SECRET_KEY`
2. **Repositories always filter by `company_id`** — e.g. `WHERE transactions.company_id = :company_id`
3. **`company_id` is NEVER from request body** — always from `TokenData` (security rule enforced by `.cursorrules`)
4. **Redis keys** include `company_id`: `quantyx:events:{company_id}`, `quantyx:rate:{company_id}:{user_id}`, etc.
5. **WebSocket channels** are per-company: `quantyx:events:{company_id}`
6. **Analytics cache** and **warehouse tables** have `company_id` on every row
7. **Invitation acceptance** creates users in the inviting company (`invitation.company_id`)

### Tenant Provisioning (Registration Flow)
When a new company registers:
1. `POST /auth/register` → `AuthService.register()`
2. Creates `Company` record with `slug` (lowercased, spaces → dashes)
3. Creates `User` record with role=`admin` linked to company
4. Creates `Subscription` record with `plan_name=starter`, trial state
5. All three in a single DB transaction (atomic)
6. Returns JWT pair with `company_id` embedded

---

## 9. Rate Limiting & Subscription Metering

### Three-Layer Rate Limiting

**Layer 1: IP-level rate limit (all requests)**
- Redis ZADD sliding window: key = `quantyx:ip_rate:{ip_address}`
- Window: 60 seconds
- Limit: 100 requests per minute (configurable `IP_RATE_LIMIT_PER_MINUTE`)
- Blocks unauthenticated abuse

**Layer 2: Per-user plan-based rate limit (authenticated requests)**
- Redis ZADD sliding window: key = `quantyx:plan_rate:{company_id}:{user_id}`
- Limits per plan per minute:
  - Starter: 60 req/min
  - Growth: 300 req/min
  - Enterprise: 1000 req/min
- Plan is cached in Redis for `PLAN_CACHE_TTL_SECONDS` (5 min) to avoid DB lookups

**Layer 3: Monthly API quota (subscription metering)**
- Redis INCR counter: key = `quantyx:monthly:{company_id}:{YYYY-MM}`
- TTL: 32 days (auto-expires)
- Every `QUOTA_SYNC_INTERVAL` (100) calls, syncs to `subscriptions.api_calls_used` in DB
- Returns 429 if `api_calls_used >= api_calls_limit`

**Bypass:** `RATE_LIMIT_BYPASS_EMAILS` (comma-separated) — used for internal admin accounts that skip all rate limits.

**Exempt paths:** subscription read endpoints (`/subscriptions/plans`, `/subscriptions/current`, `/subscriptions/usage`) are exempt from quota check (otherwise a user near quota couldn't even check their quota).

### Why ZADD Sliding Window (not token bucket)?
- Fixed-window counters allow 2× burst at window boundaries
- ZADD with score = timestamp and ZREMRANGEBYSCORE to trim old entries gives true sliding window O(log N) per request
- Redis handles this atomically with Lua scripts

---

## 10. Fraud Detection System

### Overview
Fraud detection is a **hybrid system** combining:
1. **5 deterministic rules** (fast, interpretable, run in Celery)
2. **XGBoost ML model** (probabilistic scoring, trained on feature vectors)
3. **SHAP explanations** (EU AI Act compliance — decisions are explainable)

### The 5 Fraud Rules

**Rule 1: Velocity Check**
- Query: how many transactions from this `account_id` in the last `FRAUD_VELOCITY_WINDOW_MIN` (30) minutes?
- If count ≥ `FRAUD_VELOCITY_THRESHOLD` (5): raise HIGH severity alert
- Why: rapid sequential transactions indicate card testing or credential stuffing

**Rule 2: Amount Spike**
- Compare current transaction amount to user's 30-day rolling average (from `user_features.avg_txn_amount_30d`)
- If `amount > avg * FRAUD_AMOUNT_SPIKE_MULTIPLIER` (3.0): raise MEDIUM alert
- Why: a user whose average transaction is $50 suddenly spending $500 is anomalous

**Rule 3: Location Anomaly**
- If current `location_lat/lng` is set: compute Haversine distance from last transaction
- If distance > `FRAUD_LOCATION_RADIUS_KM` (200 km) in short time: raise HIGH alert
- Why: impossible travel (card used in New York then London within 1 hour)

**Rule 4: Duplicate Detection**
- Check for another transaction with same `amount` + `merchant_id` + `account_id` within `FRAUD_DUPLICATE_WINDOW_MIN` (5) minutes
- If found: raise CRITICAL alert
- Why: double-charge prevention, card skimmer replay attacks

**Rule 5: Flagged Merchant**
- If `merchant.is_flagged = True`: raise MEDIUM alert
- Why: operators can manually flag suspicious merchants (e.g. after receiving complaints)

### ML Scoring Pipeline

**Training** (`backend/ml/train_fraud_model.py`):
1. Loads historical transactions + fraud labels
2. Computes features (same function used in serving — eliminates train/serve skew)
3. Trains XGBoost with `scale_pos_weight` for class imbalance (fraud is rare ~0.1-1%)
4. Saves model artifact + `feature_columns.json` (canonical feature list)
5. Metrics: AUC-PR (not AUC-ROC — more meaningful for imbalanced datasets)

**Serving** (`app/services/ml_fraud_service.py`):
1. Loaded at startup into class-level singleton (`MLFraudService.load()`)
2. `analyze_transaction(tx_id, company_id)`:
   a. Fetches transaction from DB
   b. Fetches `user_features`, `merchant_features`, `velocity_features` from feature store
   c. Assembles feature vector (exactly the columns in `feature_columns.json`)
   d. Calls `model.predict_proba(X)` → confidence score 0.0–1.0
   e. If score > threshold: creates `FraudAlert` with `alert_type=ml_model`
   f. Computes SHAP values for the prediction (top 5 contributing features)
   g. Stores SHAP in `rule_metadata` JSON field
3. All logic is in a Celery task — never runs in the HTTP thread

**SHAP Explainability:**
- Every ML fraud alert includes the top contributing features and their SHAP values
- Example output: `{"feature": "velocity_1h", "shap_value": 0.34, "feature_value": 8}`
- Required for EU AI Act compliance (right to explanation for automated decisions)

### Fraud Task Flow
```
POST /transactions
    → Transaction created in DB
    → Celery task enqueued: analyze_transaction(tx_id, company_id)
    → HTTP returns immediately with fraud_check_job_id

Celery Worker (fraud queue):
    → Checks idempotency (task already processed? skip)
    → Runs 5 rules → collect triggered alerts
    → Runs ML model → get confidence score + SHAP
    → Inserts FraudAlert rows for each triggered signal
    → Publishes WebSocket event: quantyx:events:{company_id}
    → Updates transaction.fraud_analyzed_at

Frontend:
    → Polls GET /transactions/{id}/fraud-status every 2s
    → OR receives WebSocket push event
    → Updates UI with fraud badges
```

### Bulk Upload Fraud Scoring
`POST /transactions/bulk-upload`:
- Parses CSV with pandas (validates required columns)
- Inserts transactions in batches of 100
- Enqueues fraud task per transaction, but **capped at `BULK_UPLOAD_MAX_FRAUD_TASKS` (2000)** to prevent Celery queue flooding
- Returns `{inserted: N, fraud_tasks_queued: M, skipped_fraud_tasks: K}`

---

## 11. Analytics Engine

### Caching Architecture (Why Two Layers?)

**Problem:** Analytics queries (cohort retention, RFM segmentation, revenue trends) involve expensive GROUP BY + window functions over potentially millions of transactions. Running these on every HTTP request would destroy database performance.

**Solution: Two-tier caching**

**Tier 1: Redis Cache (seconds-to-minutes)**
- `app/utils/cache.py` wraps `aioredis` with `get_cache(key)` / `set_cache(key, value, ttl)`
- Used for frequently-requested, recently-computed results
- TTLs per endpoint: KPI=5min, Revenue=15min, Cohort=1h, Merchant=10min, Segmentation=30min
- Cache key: `quantyx:analytics:{company_id}:{endpoint_name}`

**Tier 2: Pre-aggregated DB Tables (analytics cache + warehouse)**
- Celery Beat runs nightly ETL at 02:00 UTC (`quantyx.warehouse.run_nightly_etl`)
- Populates: `cohort_retention_metrics`, `lifetime_value_metrics`, `hourly_transaction_heatmaps`
- Celery Beat refreshes analytics cache hourly (`quantyx.analytics.refresh_all_analytics_caches`)
- When a "cache miss" occurs in Redis, the endpoint reads from these pre-aggregated tables (much cheaper than raw `transactions` table)

**Cache Staleness Logic:**
`ANALYTICS_CACHE_STALE_TX_THRESHOLD = 100` — if more than 100 new transactions have been inserted since last cache refresh, Celery immediately triggers a refresh. This ensures fast-ingestion companies see reasonably fresh data.

### Revenue Trends
- Query: daily aggregation of `SUM(amount)` and `COUNT(*)` from `transactions`
- Served from `daily_revenue_summaries` cache table or Redis
- Supports custom date ranges
- Returns: `[{date, revenue, txn_count, avg_amount}, ...]`

### RFM Customer Segmentation
**R** = Recency (days since last purchase)
**F** = Frequency (number of purchases)
**M** = Monetary (total spend)

Algorithm:
1. Multi-level CTE: compute R, F, M per customer
2. NTILE(5) to assign scores 1-5 for each dimension
3. Combine scores: Champions (R≥4, F≥4), Loyal (F≥3), At Risk (R≤2, F≥2), Lost (R≤2, F≤2)
4. Returns customer count and avg LTV per segment
5. Cached for 30 minutes

### Cohort Retention
- Cohort = month of first transaction
- Measures: what % of users who first transacted in month X are still active in month X+N?
- Data from `cohort_retention_metrics` warehouse table (populated nightly)
- Returns grid: `cohort_month × period_number → retention_rate`
- Displayed as heatmap on frontend

### LTV Segments
- From `lifetime_value_metrics` warehouse table
- Groups users into LTV tiers: High Value / Mid Value / Low Value
- Returns: `[{segment, avg_ltv, user_count, avg_orders, avg_order_value}]`

### Transaction Heatmap
- `hour_of_day (0-23)` × `day_of_week (0-6)` grid
- Cell value: transaction count or total amount
- Source: `hourly_transaction_heatmaps` warehouse table
- Visual: 7×24 grid showing peak hours and days

---

## 12. AI Analyst Feature

### Why It Exists
Analysts and business users need answers to ad-hoc questions like "What were my top merchants last month?" or "Which customer segment has the highest fraud rate?" — but most don't know SQL. The AI Analyst translates natural language to data operations.

### Architecture
```
POST /analyst/ask {question: "..."}
    → Rate limit check (20 calls/hour/user via Redis)
    → AIAnalystService.ask(question, company_id, user_id)
    → LLMProvider.chat() with tool definitions
    → Tool-use loop (max 5 rounds):
        Round 1: LLM generates tool_call
        Round 2: Execute tool (query DB), append result
        Round 3: LLM generates another tool_call or final answer
        ...
    → Return {answer: "...", sources: [...], tool_calls_made: N}
```

### LLM Provider Chain (`app/services/llm_provider.py`)
Three providers in priority order:
1. **Groq** (`groq.AsyncGroq`) — model: `llama-3.3-70b-versatile` — fastest, free tier
2. **Gemini** (`google.genai`) — model: `gemini-1.5-flash` — Google free tier
3. **OpenRouter** (`httpx` → OpenAI-compatible API) — model: `meta-llama/llama-3.1-8b-instruct:free`

Provider selection logic:
- At startup, `LLMProvider.__init__()` checks which API keys are configured
- Providers without keys are **skipped entirely** (not just deprioritized)
- On each call, tries primary → fallback → tertiary in order
- On error (timeout, rate limit, API error), automatically falls through to next provider
- If all providers fail: returns structured error response

**Why not OpenAI/Anthropic?** Both are paid APIs. This project uses only free-tier cloud providers.

### Analyst Tools (`app/services/analyst_tools.py`)
The LLM can invoke these tool functions to fetch data:

| Tool | Description |
|---|---|
| `get_revenue_summary` | Calls `/analytics/revenue-trends` internally |
| `get_customer_segments` | Returns RFM segment counts |
| `get_fraud_stats` | Fraud alert stats |
| `get_top_merchants` | Top N merchants by volume |
| `get_kpi_summary` | Current period KPIs |
| `execute_safe_query` | Runs a **read-only** SQL query with company_id injection |

The LLM generates tool calls as JSON, the service executes them, results are appended to the conversation, and the loop continues until the LLM produces a final text answer.

**Max tool rounds:** `AI_ANALYST_MAX_TOOL_ROUNDS = 5` — prevents infinite loops.
**Max tokens:** `AI_ANALYST_MAX_TOKENS = 1500` — controls cost and response time.

---

## 13. Team Invitations & Email System

### Why Invitations (Not Direct Password Assignment)?
Security best practice. The admin should not know or set a teammate's password. The invitee chooses their own password when accepting. Decouples "access grant" from "credential creation."

### Full Invitation Flow

**Step 1: Admin sends invitation**
```
POST /invitations/send {email: "analyst@corp.com", role: "analyst"}
    → Validate: email not already a user, no pending invite
    → Generate: cryptographically random raw token (secrets.token_urlsafe(32))
    → Compute: token_hash = SHA256(raw_token)
    → Insert: Invitation(token_hash=hash, status="pending", expires_at=now+72h)
    → Enqueue: Celery task quantyx.email.send_invitation(invitation_id, raw_token)
    → HTTP returns immediately: {invitation_id, status: "pending"}
```

**Step 2: Celery sends email**
```
Worker: quantyx.email.send_invitation(invitation_id, raw_token)
    → Load invitation from DB (by id)
    → Render Jinja2 template: invitation.html
        {company_name, invitee_email, role, invite_url, expiry}
    → invite_url = f"{FRONTEND_URL}/accept-invite?token={raw_token}"
    → FastAPI-Mail SMTP send (Gmail/STARTTLS)
    → Update invitation.email_sent_at = now
    → Raw token is NEVER stored in DB; only passed through Redis Celery broker temporarily
```

**Step 3: Invitee validates token**
```
GET /invitations/validate?token=abc123
    → Public endpoint (rate-limited by IP)
    → Compute: SHA256(abc123) → lookup in invitations.token_hash
    → If found, not expired, status=pending:
        Return {company_name, role, email, expires_at}
    → Frontend: pre-fills the accept form
```

**Step 4: Invitee accepts**
```
POST /invitations/accept {token: "abc123", password: "...", full_name: "..."}
    → Validate token (SHA256 lookup)
    → Validate password (strength check)
    → Create User(company_id=invitation.company_id, role=invitation.role, ...)
    → Update invitation.status = "accepted", accepted_at = now
    → Return JWT pair (user is immediately logged in)
```

### Security Properties
- Raw token **never** touches the DB (only the SHA-256 hash is stored)
- Raw token appears only in: Celery task args (in Redis broker temporarily), the email body
- Resend operation **revokes old token** (sets old hash to invalid) before issuing new one
- Token expiry: 72 hours by default
- `validate` and `accept` endpoints are rate-limited by IP (prevents brute-force on token space)

### Email Templates
- `base.html`: table-based layout (not flexbox/grid — Outlook compatibility)
- `invitation.html`: extends base, renders invitation details
- `invitation_text.txt`: plain text version for email clients that don't render HTML
- Jinja2 `autoescape=True` — prevents XSS if company_name contains HTML characters

---

## 14. Celery Workers & Background Tasks

### Why Celery?
HTTP requests must respond in <500ms. Fraud scoring (ML inference + DB queries), email sending (SMTP latency), analytics cache rebuilding (expensive SQL), and ETL jobs all exceed this budget. Celery moves this work to background workers.

### Celery App Configuration (`worker/celery_app.py`)
- **Broker:** Redis (`settings.REDIS_URL`, DB 0)
- **Result Backend:** Redis (stores task results for polling)
- **Beat Scheduler:** RedBeat (Redis-based, distributed-safe — no file locking issues)
- **Serializer:** JSON (not pickle — security)
- **Queues:** `fraud`, `analytics`, `email`, `features`

### All Registered Tasks

**`quantyx.fraud.analyze_transaction`** (Queue: `fraud`)
- Triggered by: `POST /transactions`, bulk upload
- Idempotency: checks `transactions.fraud_analyzed_at IS NULL` before processing
- Runs: 5 rules + ML model in sequence
- Creates: FraudAlert rows
- Publishes: WebSocket event to `quantyx:events:{company_id}`
- Updates: `transactions.fraud_analyzed_at = NOW()`

**`quantyx.email.send_invitation`** (Queue: `email`)
- Triggered by: `POST /invitations/send`, `POST /invitations/{id}/resend`
- Sends: invitation email via FastAPI-Mail SMTP
- Updates: `invitations.email_sent_at`
- Retry: 0 (rule: mutations are not idempotent — don't retry email sends automatically)

**`quantyx.analytics.refresh_analytics_cache`** (Queue: `analytics`)
- Triggered by: beat schedule OR when `ANALYTICS_CACHE_STALE_TX_THRESHOLD` exceeded
- Refreshes: Redis cache keys for analytics endpoints for one company
- Fan-out: `refresh_all_analytics_caches` calls this for each active company

**`quantyx.analytics.refresh_all_analytics_caches`** (Queue: `analytics`)
- Beat: **every hour**
- Iterates all active companies, dispatches `refresh_analytics_cache` per company

**`quantyx.warehouse.run_nightly_etl`** (Queue: `analytics`)
- Beat: **02:00 UTC daily**
- Computes: `cohort_retention_metrics`, `lifetime_value_metrics`, `hourly_transaction_heatmaps`
- Inserts/updates pre-aggregated warehouse tables
- Idempotency: checks `ANALYTICS_CACHE_IDEMPOTENCY_MINUTES` (5 min) — won't re-run if recently ran

**`quantyx.features.recompute_all_features`** (Queue: `features`)
- Beat: **every 6 hours**
- Iterates all companies, recomputes `user_features`, `merchant_features`, `velocity_features`
- Feature computation uses single shared function (eliminates training/serving skew)
- Epsilon (1e-6) added to all denominators (never divide by zero in production)

**`quantyx.monitoring.run_model_health_check`** (Queue: `features`)
- Beat: **weekly, Monday 00:00 UTC**
- Evaluates: model precision, recall, F1, AUC-PR on recent labeled data
- PSI (Population Stability Index) for feature drift detection
- Inserts into: `model_performance_metrics`, `feature_distribution_snapshots`
- Thresholds: F1 < 0.75 or PSI > 0.2 for 3+ features → creates `AdminNotification`

---

## 15. Real-Time WebSocket System

### Architecture
```
Frontend browser
    → WS /api/v1/ws/company/{company_id}?token=JWT
    → FastAPI WebSocket endpoint
    → ws_connection_manager.py:
        - Validates JWT (type=access, company_id match)
        - Registers connection in memory dict: {company_id: [ws1, ws2, ...]}
        - Subscribes to Redis pubsub channel: quantyx:events:{company_id}
        - Forwards incoming messages to all connections for company
        - Sends heartbeat {"type": "ping"} every 30s
        - Handles disconnection: removes from dict, unsubscribes
```

### Event Types Published
- `{type: "fraud_alert", data: {transaction_id, severity, confidence_score}}`
- `{type: "transaction_update", data: {id, status}}`
- `{type: "notification", data: {title, body, severity}}`
- `{type: "ping"}` — server heartbeat

### Why Redis Pub/Sub?
- Multiple Celery workers can publish events
- Multiple FastAPI instances (horizontal scaling) each subscribe
- Redis fan-out ensures all connected clients receive events regardless of which worker processed the transaction
- Channel isolation per `company_id` enforces tenant separation

### Frontend WebSocket (`hooks/useWebSocket.ts`)
- Connects on app load if user is authenticated
- Auto-reconnect with exponential backoff on disconnection
- Graceful degradation: if WebSocket fails, frontend falls back to polling for fraud status
- Updates TanStack Query cache directly on relevant events (optimistic updates)

---

## 16. ML Model — Training, Serving, Monitoring

### Model Training (`backend/ml/train_fraud_model.py`)
```
Input: transactions table (historical) + fraud_alerts (labels)
Features: user velocity, amount ratios, merchant risk, time-of-day, day-of-week
Algorithm: XGBoost with scale_pos_weight (handles class imbalance without SMOTE)
Evaluation: AUC-PR (area under precision-recall curve)
Output: model.pkl + feature_columns.json
```

**Why XGBoost over neural networks?**
- Tabular data: XGBoost consistently outperforms neural nets on tabular financial data
- Interpretable with SHAP
- Fast inference (milliseconds vs. hundreds of ms for neural nets)
- No GPU required for training/inference

**Why `scale_pos_weight` instead of SMOTE?**
- SMOTE generates synthetic samples — risk of overfitting to synthetic data
- `scale_pos_weight = negative_samples / positive_samples` gives the minority class more weight during training

### Model Versioning
- `feature_columns.json` includes: `feature_columns` list, `threshold` float, `trained_at` ISO timestamp, `model_version` string
- Loaded at startup into `MLFraudService._model_version`
- Version appears in every `FraudAlert.model_version` field
- `GET /model-health` returns the current loaded version

### Model Monitoring (`monitoring_tasks.py`)
Weekly health check:
1. Fetches last 30 days of transactions with analyst-confirmed fraud labels
2. Runs model on them, computes: precision, recall, F1, AUC-PR
3. Computes PSI per feature (compares current feature distribution to training distribution)
4. Inserts into `model_performance_metrics` and `feature_distribution_snapshots`
5. Thresholds:
   - F1 < `MODEL_HEALTH_F1_THRESHOLD` (0.75): degraded alert
   - Precision < `MODEL_HEALTH_PRECISION_THRESHOLD` (0.70): degraded alert
   - PSI > `MODEL_HEALTH_PSI_DRIFT_THRESHOLD` (0.2) on 3+ features: drift alert
6. Creates `AdminNotification` for each threshold breach

---

## 17. Query Lab Feature

### Purpose
Analysts and admins can write custom SQL against their company's data without requiring a separate BI tool. Quantyx AI provides a safe, scoped SQL execution environment.

### Safety Architecture
**Query scoping:**
- `company_id` is automatically injected as a bound parameter into every query
- Queries are rewritten to add `AND company_id = :company_id` to WHERE clauses
- Prevents cross-tenant data leakage even if analyst writes `SELECT * FROM transactions`

**Read-only enforcement:**
- DDL statements (`CREATE`, `DROP`, `ALTER`, `TRUNCATE`) are rejected with 400 error
- DML mutations (`INSERT`, `UPDATE`, `DELETE`) are rejected
- Only `SELECT` statements are allowed

**Table allowlist:**
- Only allowed to query: `transactions`, `accounts`, `merchants`, `categories`, `fraud_alerts`
- Cannot query: `users`, `invitations`, `audit_logs`, `subscriptions` (sensitive tables)

### Query Templates
Pre-built queries to help users get started:
- "Revenue by Month"
- "Top 10 Merchants by Volume"
- "Fraud Rate by Category"
- "Monthly Active Users"
- "Average Transaction by Hour"

### Monaco Editor (Frontend)
- Full SQL syntax highlighting
- Auto-complete for table/column names
- Error markers for syntax issues
- Keyboard shortcut: `Ctrl+Enter` or `Cmd+Enter` to execute

### Saved Queries
- Save with name + description
- Toggle `is_public` to share with all company users
- Track `execution_count` and `last_executed_at`
- Personal and public queries displayed in separate tabs

---

## 18. Reports & Exports

### CSV Export (`GET /reports/generate/csv`)
- Streams transaction data for specified date range
- Uses pandas `DataFrame.to_csv()` with chunked streaming
- Response: `Content-Type: text/csv`, `Content-Disposition: attachment; filename=transactions_{date}.csv`
- Tenant-scoped: only company's own transactions
- Fields: transaction_ref, date, amount, currency, merchant, category, status, fraud_flag

### PDF Export (`GET /reports/generate/pdf`)
- Uses **reportlab** library
- Contents:
  - Cover page with company name and report date range
  - KPI summary table: revenue, transaction count, avg amount, fraud rate
  - Revenue trend chart (generated as reportlab drawing)
  - Top merchants table
  - Fraud alert summary
- Response: `Content-Type: application/pdf`, streamed directly

---

## 19. Subscriptions & Plan Management

### Plan Tiers

| Feature | Starter | Growth | Enterprise |
|---|---|---|---|
| Price | Free/Trial | $X/mo | Custom |
| API calls/month | 10,000 | 100,000 | Unlimited |
| Transactions/month | 5,000 | 100,000 | Unlimited |
| API rate limit | 60 req/min | 300 req/min | 1000 req/min |
| Team members | 3 | 15 | Unlimited |
| AI Analyst access | ❌ | ✅ | ✅ |
| Query Lab | ❌ | ✅ | ✅ |
| PDF Reports | ❌ | ✅ | ✅ |

### Plan Enforcement Points
1. **`check_rate_limit`** — per-plan API call rate enforced on every request
2. **Monthly quota** — incremented in Redis, synced to DB every 100 calls
3. **Feature gates** — AI Analyst and Query Lab endpoints check subscription tier before proceeding
4. **Usage endpoint** (`GET /subscriptions/usage`) — shows `{api_calls_used, api_calls_limit, percent_used}`

### Subscription Lifecycle
- New company: auto-created on Starter trial
- `POST /subscriptions/subscribe`: creates/updates subscription record
- `POST /subscriptions/upgrade`: transitions to higher plan, resets `api_calls_used`, updates `ends_at`
- `ends_at` check: if expired and not renewed, plan effectively downgrades to Starter behavior

---

## 20. Audit Logging

### Why Append-Only?
Audit logs are compliance records. They must be:
- Immutable (no UPDATE, no DELETE ever on audit_logs table)
- Complete (every sensitive action logged)
- Available even if users/companies are deleted (hence no FK constraints)

### What Gets Logged
Every write operation on sensitive resources:
- `transaction.create` — who created which transaction
- `fraud.resolve` — who resolved which alert, their label
- `invitation.send` — who invited whom
- `invitation.accept` — who joined via invite
- `user.login` / `user.register`
- `query_lab.execute` — every SQL execution (with query text)
- `subscription.upgrade` — billing changes

### Log Fields
`company_id`, `user_id`, `user_email`, `action`, `resource_type`, `resource_id`, `ip_address`, `user_agent`, `request_path`, `request_method`, `response_status`, `duration_ms`, `metadata` (JSON with extra context), `created_at`

### Querying Audit Logs
`GET /audit/logs` (admin only) with filters:
- `action` (prefix match)
- `user_id`
- `resource_type`
- `date_from` / `date_to`
- Paginated with `page` + `page_size`

---

## 21. Observability — Prometheus, Grafana, Structlog

### Structured Logging (structlog)
All logs are emitted as **JSON** by `structlog`. Key fields:
- `event` — human-readable event name
- `log_level` — INFO / WARNING / ERROR
- `timestamp` — ISO 8601
- `correlation_id` — UUID per request (injected by `RequestLoggingMiddleware`)
- `company_id` / `user_id` (where applicable)
- No raw token values ever appear in logs (security rule)

Example log entry:
```json
{
  "event": "fraud_alert.created",
  "log_level": "INFO",
  "timestamp": "2026-04-05T10:23:45.123Z",
  "company_id": "abc-123",
  "transaction_id": "tx-456",
  "alert_type": "velocity",
  "confidence_score": 0.87,
  "correlation_id": "req-789"
}
```

### Prometheus Metrics (`app/utils/metrics.py`)
Counters and histograms registered at startup:
- `http_requests_total` — labeled by method, path, status_code
- `http_request_duration_seconds` — histogram of response times
- `fraud_alerts_created_total` — labeled by severity, alert_type
- `transactions_created_total` — labeled by currency, type
- `celery_queue_depth` — gauge per queue (refreshed on each `/metrics` scrape)
- `ml_model_inference_seconds` — histogram of ML scoring latency
- `api_rate_limit_hits_total` — labeled by limit_type (ip / plan / quota)

Scrape endpoint: `GET /metrics` (Prometheus text format)

### Grafana Dashboards
Pre-provisioned dashboards in `monitoring/grafana/provisioning/`:
- **Application Overview** — request rate, error rate, p50/p95/p99 latency
- **Fraud Detection** — alerts per minute, severity breakdown, ML model latency
- **Business Metrics** — transactions/min, revenue rate, active companies
- **Celery Workers** — queue depths, task success/failure rates

---

## 22. Frontend Architecture

### Entry Point Flow
```
index.html
    → <div id="root"> 
    → main.tsx: ReactDOM.createRoot().render(<App />)
    → App.tsx:
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
```

### Code Splitting Strategy
All page-level components use `React.lazy()` + `<Suspense fallback={<PageSkeleton />}>`:
- Each page is a separate JS chunk (Vite code splitting)
- On navigation: chunk is fetched + loading skeleton shown
- Result: small initial bundle, fast first load

### Axios Configuration (`lib/axios.ts`)
```
api = axios.create({
  baseURL: getApiV1Base(),  // /api/v1 (dev) or VITE_API_URL + /api/v1 (prod)
  timeout: 30000,
  headers: {"Content-Type": "application/json"}
})

// Request interceptor: inject Bearer token
api.interceptors.request.use(config => {
  const token = localStorage.getItem("access_token")
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Response interceptor: auto-refresh on 401
api.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401) {
      // attempt refresh...
      // on success: update localStorage, retry original request
      // on failure: clear tokens, redirect to /login
    }
  }
)
```

### TanStack Query Configuration (`lib/queryClient.ts`)
```typescript
new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 2 * 60 * 1000,     // 2 minutes
      gcTime: 10 * 60 * 1000,        // 10 minutes (garbage collection)
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
      retry: (failureCount, error) => {
        if (error.response?.status === 401) return false  // don't retry auth errors
        return failureCount < 2
      }
    },
    mutations: {
      retry: 0,   // mutations are not idempotent - never auto-retry
      onError: (error) => {
        // push to notification store → shows toast
      }
    }
  }
})
```

### Vite Dev Proxy (`vite.config.ts`)
```typescript
server: {
  port: 3000,
  proxy: {
    "/api": { target: "http://localhost:8000", changeOrigin: true },
    "/ws": { target: "ws://localhost:8000", ws: true }
  }
}
```
This allows frontend at port 3000 to call `/api/v1/...` without CORS issues in development.

---

## 23. Frontend Routing & Pages

All routes defined in `router/index.tsx` using React Router v7 `createBrowserRouter`.

### Public Routes (no auth required)
| Path | Component | Description |
|---|---|---|
| `/` | `LandingPage` | Marketing landing + CTA to register/login |
| `/login` | `LoginPage` | Email + password login form |
| `/register` | `RegisterPage` | Company + admin user registration form |
| `/accept-invite` | `AcceptInvitePage` | Token validation + password set for invited users |
| `/onboarding` | `WizardPage` | Post-registration onboarding wizard |

### Protected Routes (require JWT via `ProtectedRoute`)
Wrapped in `AppShell` (sidebar + topbar). Unauthorized users → redirect to `/login`.

| Path | Component | Description |
|---|---|---|
| `/dashboard` | `DashboardPage` | KPI cards + live transaction feed |
| `/transactions` | `TransactionsPage` | Transaction list with filters |
| `/analytics` | `AnalyticsPage` | Charts: revenue, cohort, heatmap, LTV, RFM |
| `/fraud` | `FraudPage` | Fraud alerts list + resolution |
| `/query-lab` | `QueryLabPage` | Monaco SQL editor + saved queries |
| `/reports` | `ReportsPage` | CSV/PDF export controls |
| `/settings` | `SettingsPage` | Profile, team management, billing |
| `/ai-analyst` | `AIAnalystPage` | Chat with AI Analyst |

Any unmatched path → redirect to `/dashboard`.

### `ProtectedRoute` Component
```typescript
// Checks: localStorage has access_token + token not expired
// If no valid token: <Navigate to="/login" state={{from: location}} />
// If valid: renders children
```

---

## 24. Frontend State Management

### Zustand Stores

**`auth.store.ts`** (persisted to localStorage)
```typescript
{
  user: User | null,          // decoded JWT user object
  accessToken: string | null,
  refreshToken: string | null,
  isAuthenticated: boolean,
  pendingInviteToken: string | null,  // NOT persisted (cleared on refresh)
  login(tokens, user): void,
  logout(): void,
  updateUser(partial): void,
  setPendingInvite(token): void
}
```

**`wizard.store.ts`** (persisted to localStorage)
```typescript
{
  currentStep: 0 | 1 | 2 | 3 | 4,
  completedSteps: number[],
  data: {
    companyName?: string,
    profileComplete?: boolean,
    invitesSent?: string[],  // email list
  },
  nextStep(): void,
  prevStep(): void,
  markComplete(step): void,
  setData(partial): void,
  reset(): void
}
```

**`filter.store.ts`** (NOT persisted — resets on page refresh)
```typescript
{
  transactionFilters: {
    status?: string,
    category_id?: string,
    date_from?: string,
    date_to?: string,
    amount_min?: number,
    amount_max?: number,
    search?: string,
    page: number,
    page_size: number
  },
  fraudFilters: { severity?, is_resolved?, date_from?, date_to?, page, page_size },
  setTransactionFilter(partial): void,
  setFraudFilter(partial): void,
  resetTransactionFilters(): void
}
```
Filter store values drive TanStack Query `queryKey` arrays — when filters change, queries automatically re-fetch.

**`ui.store.ts`** (persisted)
```typescript
{
  sidebarOpen: boolean,
  activeModal: string | null,
  pageSize: number,
  toggleSidebar(): void,
  openModal(name): void,
  closeModal(): void
}
```

**`theme.store.ts`** (persisted)
```typescript
{
  theme: "light" | "dark",
  toggleTheme(): void
}
```

**`notification.store.ts`** (NOT persisted)
```typescript
{
  toasts: Toast[],
  addToast(type, title, message): void,
  removeToast(id): void
}
```
Used by TanStack Query's global `onError` to surface API errors as toast notifications.

### Immer Middleware
All Zustand stores use `immer` middleware — state mutations are written imperatively (e.g. `state.transactionFilters.page = 1`) instead of spread operators. This prevents accidental partial state replacement bugs.

### TanStack Query Cache Keys
All query keys are structured arrays that include filter/pagination state:
```typescript
// Transactions list
["transactions", filters.transactionFilters]

// Analytics
["analytics", "kpi-summary", company_id]
["analytics", "revenue-trends", company_id, dateRange]
["analytics", "cohort", company_id]

// Fraud
["fraud", "alerts", filters.fraudFilters]
["fraud", "stats", company_id]

// AI Analyst
["analyst", "suggested-questions"]
```
`queryClient.invalidateQueries({queryKey: ["transactions"]})` after a mutation triggers automatic re-fetch of all transaction queries.

---

## 25. Frontend Features — Component-Level Detail

### Auth Pages (`features/auth/`)
**`LandingPage`** — Marketing page with product description, feature highlights, CTA buttons. Uses Framer Motion for entrance animations (opacity + translateY). Links to `/register` and `/login`.

**`LoginPage`** — React Hook Form + Zod schema validation. Fields: `email` (email validation), `password` (required). On submit: calls `auth.service.ts` `login()`, stores tokens in Zustand + localStorage, redirects to `/dashboard` or `/onboarding` (if first login).

**`RegisterPage`** — Fields: `company_name`, `full_name`, `email`, `password`, `confirm_password`. Zod validates password match + minimum 8 chars. Creates company + admin user. On success: redirects to `/onboarding`.

**`AcceptInvitePage`** — On mount: reads `?token=` from URL, calls `GET /invitations/validate?token=...`, pre-fills email (disabled field), shows company name and role. Fields: `full_name`, `password`, `confirm_password`. On submit: calls `POST /invitations/accept`, on success: logs in and redirects to `/onboarding`.

### Dashboard (`features/dashboard/`)
**`DashboardPage`** — Grid of KPI cards (total revenue, transaction count, active accounts, fraud rate). Each card uses `useCountUp` hook for animated number counter on mount.

**`LiveFeedPanel`** — WebSocket-powered real-time feed showing last 20 transactions with inline fraud badges. Updates when `useWebSocket` hook receives `transaction_update` or `fraud_alert` events. Falls back to polling if WebSocket disconnects.

**`useDashboard.ts`** — TanStack Query hook wrapping `GET /analytics/kpi-summary`.

### Transactions (`features/transactions/`)
**`TransactionsPage`** — Full-page table with:
- Sidebar filter panel (status, category, date range, amount range, search)
- Pagination controls (page, page_size)
- Row-level fraud badge (`FraudStatusBadge` component)
- Viewer role: account_number shown masked

**`FraudStatusBadge`** — Shows pending/fraud/clear badge. If `fraud_check_job_id` is set and `fraud_analyzed_at` is null, polls `GET /transactions/{id}/fraud-status` every 2 seconds until resolved.

**`useTransactions.ts`** — TanStack Query with `placeholderData: keepPreviousData` (no layout jump during page changes).

### Analytics (`features/analytics/`)
**`AnalyticsPage`** — Tab layout with 5 chart sections:
1. **Revenue Trends** — Recharts LineChart, data from `useAnalytics("revenue-trends")`
2. **RFM Segments** — Recharts PieChart, customer segment distribution
3. **Cohort Retention** — `CohortRetentionTable.tsx` — custom heatmap table with color-coded cells (green = high retention, red = low)
4. **Transaction Heatmap** — `TransactionHeatmap.tsx` — 7×24 grid using inline styles for cell intensity
5. **LTV Segments** — `LTVSegmentChart.tsx` — Recharts BarChart of LTV tiers

**`useAnalytics.ts`** — Generic hook: `useAnalytics(endpoint, params?)` wraps TanStack Query with appropriate cache keys and stale times.

### Fraud (`features/fraud/`)
**`FraudPage`** — Two-panel layout:
- Left: paginated alerts list with severity badges, filter by resolved/unresolved
- Right: selected alert detail panel with `FraudExplanationCard`

**`FraudExplanationCard`** — Renders `rule_metadata` JSON as human-readable explanation. Shows SHAP values if `alert_type === "ml_model"`. "Resolve" button opens modal with confirmation + analyst label input.

### Query Lab (`features/query-lab/`)
**`QueryLabPage`** — Split layout:
- Left panel: Monaco editor (SQL mode), execute button, templates dropdown, saved queries list
- Right panel: results table (scrollable, up to 1000 rows), execution time badge

**`useQueryLab.ts`** — Mutation hook for execute, queries for templates and saved queries.

### AI Analyst (`features/ai-analyst/`)
**`AIAnalystPage`** — Chat interface layout:
- Message history (alternating user/assistant)
- `AnalystMessage.tsx` — renders assistant responses with markdown, code blocks for any SQL generated
- Input: textarea with Shift+Enter for newline, Enter to send
- Suggested questions: pre-populated chips from `GET /analyst/suggested-questions`
- Shows token/rate limit remaining

### Settings (`features/settings/`)
**`SettingsPage`** — Three tabs:
1. **Profile** — Update name, email, password
2. **Team** — List company members, show invited/pending, send new invites (admin only)
3. **Billing** — Current plan, usage meter, upgrade options (admin only)

---

## 26. Onboarding Wizard

### Purpose
After first registration, new admins are guided through a multi-step wizard to complete company setup before reaching the dashboard. Ensures high activation rates and helps users get value quickly.

### Wizard Steps (`features/wizard/`)

**Step 1: Welcome** (`Step1Welcome.tsx`)
- Lottie celebration animation (`wizardLottieUrls.ts` → hosted Lottie JSON URLs)
- Company name confirmation
- "Let's Get Started" CTA

**Step 2: Profile Setup** (`Step2Profile.tsx`)
- Full name, job title, phone (optional)
- Saves to Zustand wizard store

**Step 3: Company Details** (`Step3Company.tsx`)
- Company size, industry, country
- Customizes the experience (relevant SQL templates, etc.)

**Step 4: Invite Team** (`Step4InviteTeam.tsx`)
- Add up to 5 email + role pairs
- Calls `POST /invitations/send-bulk` on "Send Invites" click
- Can skip ("I'll do this later")

**Step 5: Success** (`Step5Success.tsx`)
- Lottie success animation (`loop: false`)
- Summary of completed steps
- "Go to Dashboard" → navigates to `/dashboard`

### Wizard Shell Components
- **`WizardShell.tsx`** — wrapper with progress bar + step navigation
- **`WizardProgressBar.tsx`** — animated progress indicator (Framer Motion width animation)
- **`StepAnimator.tsx`** — AnimatePresence `mode="wait"` wrapper between steps
- **`LottiePlayer.tsx`** — wrapper around `lottie-react` with `useReducedMotion()` check

### Wizard State Persistence
`wizard.store.ts` is persisted to localStorage. If user refreshes mid-wizard, they resume at the correct step. Wizard is only shown once: `wizard.store.reset()` is called after Step 5.

---

## 27. End-to-End Data Flows

### Flow 1: User Login
```
User types email + password → LoginPage form submits
→ auth.service.ts: POST /auth/login {email, password}
→ FastAPI: validates credentials via AuthService.login()
    → user_repo.get_by_email(email, company_id=None)  [no tenant scoping for login]
    → verify_password(plain, user.hashed_password)
    → create_token_pair(user.id, user.company_id, user.role, user.email)
    → updates user.last_login
→ Response: {access_token, refresh_token, user: {id, email, role, company_id}}
→ Frontend: stores tokens in localStorage, sets Zustand auth store
→ React Router: navigate to /dashboard
→ Dashboard: AppShell renders, queries start firing (useDashboard, useAnalytics)
```

### Flow 2: Creating a Transaction + Fraud Detection
```
Frontend: POST /transactions {account_id, merchant_id, amount, currency, ...}
→ check_rate_limit (IP + plan + quota)
→ require_analyst_or_above (JWT check)
→ ingestion_service.create_transaction(data, current_user)
    → transaction_ref = uuid if not provided
    → session.add(Transaction(..., company_id=current_user.company_id))
    → session.commit()
    → celery_app.send_task("quantyx.fraud.analyze_transaction",
        args=[transaction.id, current_user.company_id])
    → stores Celery task_id as fraud_check_job_id
→ Response: {transaction + fraud_check_job_id: "celery-task-uuid"}

Celery Worker (async):
→ analyze_transaction(transaction_id, company_id)
    → fetch transaction from DB
    → run 5 rules (velocity, amount spike, location, duplicate, merchant flag)
    → run ML model (if loaded): get confidence score + SHAP
    → for each triggered rule: INSERT INTO fraud_alerts(...)
    → UPDATE transactions SET fraud_analyzed_at = NOW()
    → Redis PUBLISH quantyx:events:{company_id} {type:"fraud_alert", ...}

Frontend (polling):
→ FraudStatusBadge polls GET /transactions/{id}/fraud-status every 2s
→ Or receives WebSocket push event
→ Shows fraud badge with severity/confidence
```

### Flow 3: Analytics Dashboard Load
```
User navigates to /analytics
→ AnalyticsPage mounts
→ 5 parallel TanStack Query calls fire:
    GET /analytics/kpi-summary
    GET /analytics/revenue-trends
    GET /analytics/cohort-retention
    GET /analytics/transaction-heatmap
    GET /analytics/ltv-segments

For each request → FastAPI:
→ check_rate_limit
→ get_current_token (JWT)
→ analytics_service.get_{endpoint}(company_id)
    → check Redis cache (key: quantyx:analytics:{company_id}:{endpoint})
    → if HIT: return cached value (deserialized from JSON)
    → if MISS:
        → query analytics_cache table or warehouse table (pre-aggregated)
        → if cache tables empty: query raw transactions table (expensive fallback)
        → set Redis cache with TTL
        → return data
→ Response: JSON data

Frontend:
→ TanStack Query stores responses in cache (staleTime: 2min)
→ Recharts/custom components render visualizations
→ Skeleton screens shown during loading (not spinners)
```

### Flow 4: AI Analyst Question
```
User types: "What were my top 3 merchants last month?"
→ POST /analyst/ask {question: "..."}
→ check rate limit: Redis key quantyx:analyst:{user_id} ZADD sliding window
    (20 calls/hour per user)
→ AIAnalystService.ask(question, company_id, user_id)
    → Build system prompt with company context, available tools
    → LLMProvider.chat(messages, tools=[get_top_merchants, get_revenue_summary, ...])
    
    Round 1: LLM responds with tool_call:
    {function: "get_top_merchants", args: {period: "last_month", limit: 3}}
    
    → Execute get_top_merchants(company_id=..., period="last_month", limit=3)
        → calls internal analytics service
        → returns [{merchant: "Starbucks", revenue: 12500}, ...]
    
    → Append tool result to conversation
    
    Round 2: LLM responds with final answer:
    "Your top 3 merchants last month were: 1. Starbucks ($12,500)..."
    
→ Return {answer: "...", sources: ["get_top_merchants"], tool_calls_made: 1}
→ Frontend renders answer in chat bubble with Markdown
```

### Flow 5: Team Invitation Accept Flow
```
Admin: POST /invitations/send {email: "new@corp.com", role: "analyst"}
→ invitation_service.send_invite(email, role, admin_user)
    → validate no existing user/invite with email
    → raw_token = secrets.token_urlsafe(32)
    → token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    → INSERT INTO invitations(token_hash=..., status="pending", ...)
    → celery.send_task("quantyx.email.send_invitation", [invitation_id, raw_token])
→ Response: {invitation_id, status: "pending"}

Celery Worker:
→ send_invitation(invitation_id, raw_token)
    → load invitation from DB
    → render invitation.html template with Jinja2
        {company_name, role, invite_url=FRONTEND_URL+/accept-invite?token=raw_token}
    → send via FastAPI-Mail (SMTP/Gmail)
    → UPDATE invitations SET email_sent_at = NOW()

Invitee receives email, clicks link:
→ Browser: GET /accept-invite?token=abc123
→ AcceptInvitePage mounts
→ GET /invitations/validate?token=abc123
    → SHA256(abc123) → lookup in DB → return {company_name, role, email}
→ Shows pre-filled form with company name + role

Invitee submits:
→ POST /invitations/accept {token: "abc123", full_name: "...", password: "..."}
    → SHA256 lookup → validate not expired, status=pending
    → CREATE User(company_id=invitation.company_id, role=invitation.role, ...)
    → UPDATE invitation SET status="accepted", accepted_at=NOW()
    → create_token_pair(user.id, user.company_id, user.role, user.email)
→ Response: {access_token, refresh_token, user}
→ Frontend: stores tokens, redirects to /onboarding (as new user)
```

---

## 28. Environment Variables Reference

All settings in `backend/app/core/config.py` via pydantic-settings.

### Application
| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | "Quantyx AI" | App display name |
| `APP_VERSION` | "1.0.0" | Version string |
| `DEBUG` | false | Enables debug mode |
| `SECRET_KEY` | (placeholder) | **MUST change in prod** — JWT signing key, 32+ chars |

### Database
| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | localhost | MySQL hostname |
| `DB_PORT` | 3306 | MySQL port |
| `DB_NAME` | quantyx_ai | Database name |
| `DB_USER` | quantyx | DB username |
| `DB_PASSWORD` | quantyx_password | **Change in prod** |

### Redis
| Variable | Default | Description |
|---|---|---|
| `REDIS_HOST` | localhost | Redis hostname |
| `REDIS_PORT` | 6379 | Redis port |
| `REDIS_DB` | 0 | Redis database index |
| `REDIS_PASSWORD` | (none) | Redis AUTH password |

### JWT
| Variable | Default | Description |
|---|---|---|
| `ALGORITHM` | HS256 | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Refresh token lifetime |

### Rate Limiting
| Variable | Default | Description |
|---|---|---|
| `IP_RATE_LIMIT_PER_MINUTE` | 100 | IP-level limit |
| `API_RATE_LIMIT_WINDOW_SECONDS` | 60 | Sliding window duration |
| `QUOTA_SYNC_INTERVAL` | 100 | Calls before DB sync |
| `PLAN_CACHE_TTL_SECONDS` | 300 | How long to cache plan in Redis |
| `RATE_LIMIT_BYPASS_EMAILS` | "" | Comma-separated bypass list |

### Fraud & ML
| Variable | Default | Description |
|---|---|---|
| `FRAUD_VELOCITY_THRESHOLD` | 5 | Max transactions in window |
| `FRAUD_VELOCITY_WINDOW_MIN` | 30 | Velocity check window (min) |
| `FRAUD_AMOUNT_SPIKE_MULTIPLIER` | 3.0 | Spike threshold multiplier |
| `FRAUD_LOCATION_RADIUS_KM` | 200.0 | Location anomaly distance |
| `FRAUD_DUPLICATE_WINDOW_MIN` | 5 | Duplicate detection window |
| `BULK_UPLOAD_MAX_FRAUD_TASKS` | 2000 | Max fraud tasks from CSV upload |
| `ML_MODEL_DIR` | backend/ml | Directory with model artifacts |
| `MODEL_HEALTH_F1_THRESHOLD` | 0.75 | Alert if F1 drops below |
| `MODEL_HEALTH_PSI_DRIFT_THRESHOLD` | 0.2 | PSI drift threshold |

### Cache TTLs
| Variable | Default | Description |
|---|---|---|
| `CACHE_TTL_KPI` | 300 | KPI summary cache (5 min) |
| `CACHE_TTL_REVENUE` | 900 | Revenue trends cache (15 min) |
| `CACHE_TTL_COHORT` | 3600 | Cohort cache (1 hour) |
| `CACHE_TTL_MERCHANT` | 600 | Merchant cache (10 min) |
| `CACHE_TTL_SEGMENTATION` | 1800 | Segmentation cache (30 min) |

### Email / SMTP
| Variable | Default | Description |
|---|---|---|
| `MAIL_USERNAME` | "" | SMTP username (Gmail address) |
| `MAIL_PASSWORD` | "" | SMTP app password |
| `MAIL_FROM` | "" | From address |
| `MAIL_FROM_NAME` | "Quantyx AI" | From display name |
| `MAIL_SERVER` | smtp.gmail.com | SMTP server |
| `MAIL_PORT` | 587 | SMTP port (STARTTLS) |
| `MAIL_STARTTLS` | true | Use STARTTLS |

### Invitations
| Variable | Default | Description |
|---|---|---|
| `INVITE_TOKEN_EXPIRE_HOURS` | 72 | Token validity window |
| `INVITE_SECRET_KEY` | (placeholder) | **Change in prod** |
| `FRONTEND_URL` | http://localhost:3000 | Used to build invite links |

### LLM / AI Analyst
| Variable | Default | Description |
|---|---|---|
| `LLM_PRIMARY_PROVIDER` | groq | Primary LLM provider |
| `LLM_FALLBACK_PROVIDER` | gemini | Fallback if primary fails |
| `LLM_TERTIARY_PROVIDER` | openrouter | Last resort |
| `GROQ_API_KEY` | "" | Groq API key (gsk_ prefix) |
| `GROQ_MODEL` | llama-3.3-70b-versatile | |
| `GEMINI_API_KEY` | "" | Gemini API key (AIzaSy prefix) |
| `GEMINI_MODEL` | gemini-1.5-flash | |
| `OPENROUTER_API_KEY` | "" | OpenRouter key (sk-or-v1- prefix) |
| `OPENROUTER_MODEL` | meta-llama/llama-3.1-8b-instruct:free | |
| `AI_ANALYST_MAX_TOKENS` | 1500 | Max tokens per response |
| `AI_ANALYST_RATE_LIMIT_PER_HOUR` | 20 | Max analyst calls per user/hour |
| `AI_ANALYST_MAX_TOOL_ROUNDS` | 5 | Max LLM tool-use iterations |

### Frontend (Vite)
| Variable | Description |
|---|---|
| `VITE_API_URL` | Production API base URL (e.g. `https://api.quantyx.ai`) |
| `VITE_WS_URL` | Production WebSocket URL (e.g. `wss://api.quantyx.ai`) |

---

## 29. CI/CD Pipeline

### CI (`/.github/workflows/ci.yml`)
Triggers on: `push` to any branch, `pull_request` to `main`

Backend checks:
1. `ruff check .` — Python linting
2. `mypy app/` — type checking (strict mode)
3. `pytest tests/ -v` — test suite
4. Coverage report

Frontend checks:
1. `npm run type-check` — TypeScript compilation (no emit)
2. `npm run lint` — ESLint
3. `npm run build` — production build (catches import errors)

### CD (`/.github/workflows/cd.yml`)
Triggers on: `push` to `main`

Steps:
1. Build Docker image for backend
2. Build Docker image for frontend (nginx)
3. Push to container registry
4. Deploy to production (configuration depends on hosting target)

---

## 30. Docker & Infrastructure Setup

### `docker-compose.yml` (Development)
Services:
- **`db`** — MySQL 8.0, port 3306, volume `mysql_data`
- **`redis`** — Redis 7 Alpine, port 6379
- **`backend`** — FastAPI app, port 8000, depends on db + redis, mounts `./backend`
- **`worker`** — Celery worker, same image as backend, command: `celery -A app.worker.celery_app worker`
- **`beat`** — Celery Beat, command: `celery -A app.worker.celery_app beat --scheduler redbeat.RedBeatScheduler`
- **`frontend`** — Vite dev server, port 3000, mounts `./frontend`

### `docker-compose.prod.yml` (Production overrides)
- Backend: no volume mount (code baked in)
- Frontend: built static files served by nginx
- Resources: CPU/memory limits
- Restart: `always` policy

### Monitoring Stack
`monitoring/prometheus.yml`:
- Scrapes: `backend:8000/metrics` every 15s
- Scrapes: `redis_exporter:9121/metrics`

Grafana provisioning:
- Datasource: Prometheus at `http://prometheus:9090`
- Dashboards: auto-provisioned from JSON files

---

## 31. Alembic Migrations

All schema changes are managed via Alembic with async SQLAlchemy support.

### Migration Files (`backend/alembic/versions/`)
| Migration | Description |
|---|---|
| `0001_initial_schema.py` | Creates: companies, users, subscriptions, transactions, accounts, merchants, categories |
| `0002_*.py` | fraud_alerts table |
| `0003_*.py` | saved_queries table |
| `0004_*.py` | kpi_reports, audit_logs |
| `0005_*.py` | Feature store tables (user_features, merchant_features, velocity_features) |
| `0006_*.py` | Analytics cache tables (daily_revenue_summaries, etc.) |
| `0007_*.py` | Warehouse tables (cohort_retention_metrics, etc.) |
| `0008_*.py` | Model monitoring tables |
| `0009_*.py` | admin_notifications |
| `0010_*.py` | Indexes for performance (transactions.company_id, transactions.transaction_date, fraud_alerts.company_id) |
| `0011_invitations.py` | Invitations table (latest) |

### Running Migrations
```bash
cd backend
alembic upgrade head      # apply all pending migrations
alembic downgrade -1      # roll back one migration
alembic current           # show current revision
```

---

## 32. Security Model

### Defense in Depth Layers

**Layer 1: Network**
- CORS: only allowed origins can make requests (prevents CSRF from other domains)
- HTTPS in production (nginx terminates TLS)

**Layer 2: Authentication**
- JWT signed with `SECRET_KEY` (min 32 chars)
- Short access token lifetime (30 min) limits breach window
- Refresh tokens for session continuity
- WebSocket tokens validated with same JWT verification

**Layer 3: Authorization**
- Role-based: admin / analyst / viewer
- `company_id` only from JWT (never from request body)
- Endpoint-level `require_admin` / `require_analyst_or_above` decorators

**Layer 4: Data Layer**
- Every query has `WHERE company_id = :company_id` (parameterized)
- No string formatting in SQL ever (prevents SQL injection)
- Query Lab: DDL/DML blocked, only SELECT allowed

**Layer 5: Application**
- Password hashing: bcrypt (12 rounds)
- Invite tokens: only SHA-256 hash stored in DB
- PII masking for viewer role
- No secrets in code (always environment variables)

**Layer 6: Audit**
- Append-only audit logs (no UPDATE/DELETE)
- All write operations logged with user + IP + timestamp
- structlog JSON structured logging (no raw token values ever)

### Rate Limiting as Security Control
- IP rate limiting prevents credential stuffing on login endpoint
- Invite token validation is rate-limited by IP (prevents brute-force on token space)
- AI Analyst rate limit prevents LLM API cost abuse

---

## 33. Dependencies Reference

### Backend (`backend/requirements.txt`)
```
fastapi                      # Web framework
uvicorn[standard]            # ASGI server
sqlalchemy[asyncio]          # ORM with async support
aiomysql                     # Async MySQL driver
pymysql                      # Sync MySQL driver (for Alembic)
alembic                      # Database migrations
pydantic                     # Data validation
pydantic-settings            # Settings from env
python-jose[cryptography]    # JWT encoding/decoding
passlib[bcrypt]              # Password hashing
redis                        # Redis client
celery                       # Task queue
redbeat                      # Redis-based Celery beat scheduler
pandas                       # Data manipulation (CSV, feature engineering)
numpy                        # Numerical operations
scikit-learn                 # ML preprocessing
xgboost                      # Gradient boosting for fraud model
shap                         # ML explainability
fastapi-mail                 # Email sending
jinja2                       # Template engine
reportlab                    # PDF generation
openpyxl                     # Excel/CSV export
structlog                    # Structured logging
prometheus-client            # Metrics
httpx                        # Async HTTP (OpenRouter LLM calls)
groq                         # Groq LLM client
google-generativeai          # Gemini LLM client
pytest                       # Test framework
pytest-asyncio               # Async test support
httpx                        # Test client
ruff                         # Python linter
mypy                         # Type checker
```

### Frontend (`frontend/package.json`)
```
react                        # UI library
react-dom                    # React DOM renderer
typescript                   # Type safety
vite                         # Build tool + dev server
@vitejs/plugin-react         # React fast refresh
tailwindcss                  # CSS framework
@tanstack/react-query        # Server state management
zustand                      # Global state management
immer                        # Immutable state (Zustand middleware)
axios                        # HTTP client
react-router-dom             # Client-side routing
react-hook-form              # Form state
zod                          # Schema validation (forms + API responses)
@hookform/resolvers          # RHF + Zod integration
recharts                     # SVG charts
framer-motion                # Animations
lottie-react                 # Lottie JSON animations
@monaco-editor/react         # SQL editor
lucide-react                 # Icons
clsx                         # className utility
tailwind-merge               # Tailwind class merging (cn utility)
```

---

*Document generated: April 5, 2026*
*Project: Quantyx AI — Production-grade Multi-tenant Fintech SaaS*
*Branch: feature/team-invitations-email*
