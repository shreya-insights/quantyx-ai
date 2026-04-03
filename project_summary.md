# Quantyx AI — Detailed Low-Level Project Summary

This document is a **technical deep-dive** into the Quantyx AI repository: architecture, data layer, API surface, frontend structure, infrastructure, and notable implementation details. It reflects the codebase as of the analysis date and is intended for engineers onboarding or auditing the system.

---

## 1. Executive overview

**Quantyx AI** is a **multi-tenant financial analytics SaaS** shaped as:

- A **FastAPI** backend (Python, async SQLAlchemy, MySQL 8, Redis).
- A **Vite + React + TypeScript** SPA (not Next.js — the root `README.md` marketing diagram is outdated).
- **JWT-based auth** with roles (`admin`, `analyst`, `viewer`).
- **Tenant isolation** primarily via `company_id` on rows and dependency-injected `CurrentUser` / `TokenData`.
- **SQL-heavy analytics** in `AnalyticsRepository` (raw MySQL: CTEs, window functions, cohort logic).
- **Rule-based fraud detection** triggered after transaction creation (not ML-driven in application code today).
- **Optional Redis** for JSON caching and a simple sliding-window rate limiter (`CacheManager`).

---

## 2. Repository layout

| Path | Purpose |
|------|---------|
| `backend/` | FastAPI app, Alembic, tests, Docker image, `requirements.txt` |
| `frontend/` | Vite React SPA, Tailwind, feature folders, Docker + Nginx production image |
| `docker-compose.yml` | Dev stack: MySQL 8, Redis, optional backend/frontend containers |
| `docker-compose.prod.yml` | Production-oriented compose (referenced in docs) |
| `.env.example` | Root template for DB, Redis, JWT, CORS, seed admin hints |
| `SETUP.md` | Local setup (Windows/macOS), Alembic, two-terminal workflow |
| `steps.md` | Condensed checklist (if present in your clone) |

---

## 3. Backend — runtime and configuration

### 3.1 Entry point

- **`app/main.py`** builds the FastAPI app via `create_application()`.
- Registers **CORS** from `settings.ALLOWED_ORIGINS` (type `list[str]` in Pydantic; **`.env` must use JSON array syntax** for list fields with `pydantic-settings`, e.g. `["http://localhost:3000"]`, or parsing fails before custom validators run).
- Adds **`RequestLoggingMiddleware`**, mounts **`/api/v1`** via `api_router`.
- **Lifecycle:** startup logs version; shutdown closes global Redis client if created.
- **`GET /health`** returns JSON status (used by Docker `HEALTHCHECK`).

### 3.2 Settings (`app/core/config.py`)

Loaded from **`backend/.env`** (working directory when running Uvicorn from `backend/`).

Notable fields:

- **Database:** `DB_*` → `DATABASE_URL` (`mysql+aiomysql://...`) and `SYNC_DATABASE_URL` (`mysql+pymysql://...`) for Alembic sync URL configuration in `alembic.ini` override.
- **Redis:** `REDIS_URL` property builds `redis://...` with optional password.
- **JWT:** `SECRET_KEY`, `ALGORITHM`, access/refresh expirations.
- **Fraud thresholds:** `FRAUD_VELOCITY_*`, `FRAUD_AMOUNT_SPIKE_MULTIPLIER`, `FRAUD_LOCATION_RADIUS_KM`, `FRAUD_DUPLICATE_WINDOW_MIN` (used by `FraudDetectionService`).
- **Cache TTLs:** `CACHE_TTL_*` consumed by `AnalyticsService` when writing Redis keys.

### 3.3 Database session (`app/db/session.py`)

- **`create_async_engine`** with `pool_pre_ping`, `pool_size=10`, `max_overflow=20`, `pool_recycle=3600`, `echo=DEBUG`.
- **`get_db`:** yields `AsyncSession`, **commits on success**, **rolls back on exception**, always closes. Endpoints depend on this generator via `DBSession`.

### 3.4 Declarative base (`app/db/base.py`)

- **`Base`** subclasses SQLAlchemy 2.0 **`DeclarativeBase`**.
- Default **`__tablename__`** rule: class name lowercased + `"s"` (overridden explicitly on models where needed, e.g. `companies`, `users`).

---

## 4. Data model and migrations

### 4.1 ORM models (`app/models/`)

Core entities:

- **`Company`** — `subscription_tier` enum (`starter` / `growth` / `enterprise`), optional `api_key`, `slug` unique.
- **`User`** — belongs to `company_id`, unique `email`, `hashed_password`, `role` enum (`admin` / `analyst` / `viewer`).
- **`Category`** — hierarchical optional `parent_id`; seeded by `backend/scripts/init.sql` (Docker MySQL init).
- **`Account`** — `company_id`, optional `user_id`, `account_number` unique globally, `account_type`, `balance`, currency.
- **`Merchant`** — `company_id`, location fields, `category_code`, `is_flagged`.
- **`Transaction`** — `company_id`, `account_id`, optional `merchant_id` / `category_id`, unique `transaction_ref`, amounts, enums for type/status, **`metadata` JSON** (Python attr `metadata_` maps to column `metadata`), fraud-related fields (`ip_address`, `device_fingerprint`, `location_lat` / `location_lng`), `transaction_date`.
- **`FraudAlert`** — links `transaction_id`, `alert_type`, `severity`, `confidence_score`, resolution fields, `rule_metadata`.
- **`KpiReport`** — `report_type`, period, `metrics` JSON.
- **`Subscription`** — plan, status, billing cycle, limits (`api_calls_*`, `transaction_limit`), `PLAN_LIMITS` / `PLAN_PRICING` **Python constants** (not enforced everywhere automatically — see services/endpoints).
- **`SavedQuery`** — Query Lab persistence per `user_id` / `company_id`.

Indexes: composite indexes on `(company_id, transaction_date)`, account/merchant/status combinations, aligned with analytics query patterns.

### 4.2 Alembic

- **`alembic/env.py`**: loads `Base.metadata` and all models; **online mode** uses **async** engine + `run_sync` for migrations.
- **Single revision:** `alembic/versions/0001_initial_schema.py` creates all tables and indexes.
- **Comment in migration:** mentions partitioning by year for `transactions`; the checked-in migration creates a **standard** `transactions` table (partition DDL may be manual/ops-level elsewhere).

### 4.3 Docker MySQL seed

- **`backend/scripts/init.sql`**: `INSERT IGNORE` into **`categories`** for MCC-style codes (Groceries, Restaurants, etc.).

---

## 5. Security and authorization

### 5.1 Passwords and JWT (`app/core/security.py`)

- **passlib** bcrypt for hash/verify.
- **python-jose** HS256 JWTs: `sub` = user id string, embedded **`company_id`**, **`role`**, **`email`**, `type` = `access` | `refresh`, `exp` set from settings.

### 5.2 Dependencies (`app/core/dependencies.py`)

- **`HTTPBearer(auto_error=False)`** → **`get_current_token`** → **`TokenData`**.
- **`require_admin`**, **`require_analyst_or_above`** for route guards.
- Type aliases: **`CurrentUser`**, **`AdminUser`**, **`AnalystUser`**, **`DBSession`**.

### 5.3 Exceptions (`app/core/exceptions.py`)

- **`QuantyxException`** subclasses map to HTTP status + **`error_code`** (used by a dedicated handler in `main.py` for consistent JSON: `error_code`, `detail`).

### 5.4 Tenant isolation pattern

- **Repositories** (e.g. `TransactionRepository.get_company_transactions`) take **`company_id`** from the token and apply filters.
- **Risk area — Query Lab:** `QueryLabService._validate_sql` blocks obvious DML/DDL and requires leading `SELECT`, but **`ALLOWED_TABLES` is defined and not used** in the execution path. The docstring claims automatic **`company_id` scoping via WHERE injection**, but the implemented `execute_query` **wraps the user SQL in a CTE and applies only a row `LIMIT`**. **Analyst-written SELECTs that omit `company_id` could read cross-tenant rows** if they reference shared tables. Treat Query Lab as **trusted-user** or harden before production multi-tenant use.

---

## 6. Caching and Redis (`app/utils/cache.py`)

- **Singleton async Redis** from `REDIS_URL`.
- **`CacheManager`:** JSON serialize/deserialize, keys prefixed `quantyx:`.
- **`invalidate_company`:** `KEYS` + `DELETE` by pattern `quantyx:*:{company_id}:*` (OK for dev/small scale; **`KEYS` is O(N)** and not ideal for large Redis instances).
- **`rate_limit_check`:** `INCR` with `EXPIRE` on first hit — **fixed window**, not true sliding window (naming vs behavior).
- **Failure mode:** rate limit **fails open** (`return True, 0`) if Redis errors.

---

## 7. Service layer (business logic)

### 7.1 Auth (`app/services/auth_service.py`)

- **`register_company`:** validates unique email + company slug; creates `Company` with `api_key` `qx_` + token; admin `User`; **`Subscription`** in **`trial`**, 14-day `ends_at`, starter limits (`api_calls_limit=1000`, `transaction_limit=10000`).
- **`login`:** verify password, `update_last_login`, return token pair.
- **`refresh_tokens`:** validate refresh JWT, re-issue pair.
- **`invite_user`:** admin-only path in router; creates user with chosen role.

### 7.2 Ingestion (`app/services/ingestion_service.py`)

- **pandas** `read_csv`; normalizes column names.
- **Required columns:** `account_id`, `amount`, `currency`, `transaction_type`, `transaction_date`.
- Optional `merchant_id`, `category_id`, `description`, `status` (defaults).
- Builds **`Transaction`** rows with generated `CSV-` prefixed refs; bulk persistence via repository.

### 7.3 Fraud (`app/services/fraud_service.py`)

**Pure rule engine** (no `sklearn` import in app code — **scikit-learn is listed in `requirements.txt` but unused** in the scanned codebase):

1. **Velocity** — count in window vs `FRAUD_VELOCITY_THRESHOLD` / `FRAUD_VELOCITY_WINDOW_MIN`.
2. **Amount spike** — debit only; compares to **90-day account average** via `TransactionRepository.get_account_recent_avg`.
3. **Location anomaly** — haversine distance vs prior tx in **2 hours** vs `FRAUD_LOCATION_RADIUS_KM`.
4. **Duplicate** — same amount + merchant within `FRAUD_DUPLICATE_WINDOW_MIN`.
5. **Night pattern** — debits **02:00–05:00** (timezone: server/local implicit on `transaction_date`).

Persists **`FraudAlert`** rows and flushes.

### 7.4 Analytics (`app/services/analytics_service.py` + `analytics_repo.py`)

- **Repository** runs **`sqlalchemy.text`** queries with bound `:company_id` (and other params).
- Features include **revenue trend** (CTE + `LAG` MoM %), **RFM** (`NTILE(5)` + segment naming), **cohort retention** (MySQL `PERIOD_DIFF`-style logic in repo), merchant rankings, KPI summary, category spend, frequency histograms, etc.
- **Service** maps rows to **Pydantic response models** and, when `CacheManager` is passed, uses **per-feature TTL** from settings.

### 7.5 Query Lab (`app/services/query_lab_service.py`)

- Ships **built-in `QUERY_TEMPLATES`** (strings of MySQL SQL) for UI/examples.
- **`execute_query`:** validation + CTE wrap + `text(wrapped_sql)` execute.
- **`save_query` / `get_saved_queries`:** visibility by `user_id` or `is_public` within company.

### 7.6 Subscriptions (`app/services/subscription_service.py`)

- Read/upgrade flows and plan metadata (inspect file for exact enforcement hooks when extending metering).

---

## 8. Repositories

- **`BaseRepository`** generic: `get_by_id`, `get_all`, `count`, `create`, `update`, `delete` using async `select` / `flush` / `refresh`.
- **`TransactionRepository`**, **`UserRepository`**, **`FraudRepository`**, **`AnalyticsRepository`** — domain-specific queries, some raw SQL, some ORM.

---

## 9. HTTP API (`/api/v1`)

Router composition **`app/api/v1/router.py`:**

| Prefix / router | Concern |
|-----------------|--------|
| `/auth` | Register, login, refresh, `me`, invite user |
| `/transactions` | CRUD list/create, bulk CSV upload, nested routers for accounts/merchants |
| `/analytics` | Revenue, RFM, cohorts, KPIs, merchants, etc. |
| `/fraud` | Alerts listing, resolve, stats |
| `/query-lab` | Execute SQL, templates, save/list queries |
| `/reports` | CSV stream, PDF (ReportLab) export |
| `/subscriptions` | Plan and billing-related endpoints |

**Representative behaviors:**

- **List transactions:** `PaginatedResponse`, filters parsed into **`TransactionFilter`**, `page` / `page_size` capped (e.g. `le=200`).
- **Create transaction:** requires **`AnalystUser`**; creates **`COMPLETED`** tx; runs **`FraudDetectionService.analyze_transaction`** synchronously in-request.
- **Reports:** **analyst** guard; CSV built with stdlib `csv`; PDF uses **ReportLab** tables/paragraphs.

---

## 10. Schemas (Pydantic)

Under **`app/schemas/`**: request/response models for **auth**, **transactions**, **analytics**, **fraud**, **query_lab**, **subscription**, **common** (e.g. pagination wrapper). Used for OpenAPI generation and response validation.

---

## 11. Frontend — low-level structure

### 11.1 Bootstrap

- **`main.tsx`** — React root, **`QueryClientProvider`**, **`RouterProvider`** with router from **`src/router/index.tsx`**.
- **`App.tsx`** — minimal shell around router (if used).

### 11.2 Routing (`src/router/index.tsx`)

- **React Router v7** `createBrowserRouter`.
- **Lazy-loaded** pages with **`Suspense`** + **`PageSkeleton`**.
- **Public:** `/`, `/login`, `/register`.
- **Protected:** wrapper **`ProtectedRoute`** + **`AppShell`** layout; children `/dashboard`, `/transactions`, `/analytics`, `/fraud`, `/query-lab`, `/reports`, `/settings`.

### 11.3 API client (`src/lib/axios.ts`)

- **Base URL:** `${VITE_API_URL}/api/v1` (default `http://localhost:8000`).
- **Request interceptor:** attaches `Bearer` from `localStorage` `access_token`.
- **Response interceptor:** on **401**, clears tokens + `quantyx-auth` (Zustand persist key) and redirects to login.

### 11.4 State and data fetching

- **Zustand** stores: **`auth.store`**, **`theme.store`** (persisted where configured).
- **TanStack Query** client in **`lib/queryClient.ts`**; feature hooks under **`features/*/hooks/`** call **`services/*.ts`** (axios wrappers).

### 11.5 UI

- **`components/ui`:** Button, Card, Input, Modal, Badge, Spinner, Skeleton.
- **`components/layout`:** Sidebar, Topbar, AppShell.
- **Tailwind** + **`cn`** utility (`clsx` + `tailwind-merge`).
- **Monaco** editor in Query Lab feature; **Recharts** for analytics visuals.

### 11.6 Dev server (`vite.config.ts`)

- **Port 3000** (not Vite’s default 5173).
- **Proxy:** `/api` → `http://localhost:8000` (useful if relative API paths are ever adopted; current axios uses absolute `VITE_API_URL`).

---

## 12. Testing (`backend/tests/`)

- **`conftest.py`:** **`sqlite+aiosqlite:///:memory:`** test engine, **`Base.metadata.create_all`** for session scope, **`httpx.AsyncClient`** + **`ASGITransport`** against **`app.main.app`**, overrides **`get_db`**.
- **Note:** CI workflow also provisions **MySQL + Redis** services; pytest env can target MySQL for integration-style runs — align local/CI env vars when reproducing failures.
- Tests present: **`test_auth.py`**, **`test_analytics.py`** (expand coverage as needed).

---

## 13. Tooling and CI (`.github/workflows/`)

- **`ci.yml`:** Python **3.11**, `pip install -r requirements.txt` + **aiosqlite**, **ruff** (subset of rules), **mypy** (`continue-on-error: true`), **pytest** with DB env pointing at service MySQL.
- **`cd.yml`:** deployment pipeline (read for cloud targets).

---

## 14. Containers

### 14.1 Backend Dockerfile

- **`python:3.11-slim`**, installs build deps for MySQL client, **`pip install -r requirements.txt`**, non-root user **`quantyx`**, **`uvicorn`** on **8000**.

### 14.2 Frontend Dockerfile

- **Multi-stage:** **Node 20** `npm ci` + `npm run build` with **`VITE_API_URL` build arg**; **Nginx** serves **`dist`**, SPA routing via custom **`nginx.conf`**.

### 14.3 `docker-compose.yml` (excerpt)

- **MySQL 8.0** with env `MYSQL_*`, port **3306**, **`init.sql`** mounted, **`mysql_native_password`**, healthcheck.
- **Redis 7** alpine, **AOF**, memory cap/policy.
- Optional **backend** / **frontend** services for full containerized dev.

---

## 15. Dependency highlights (`backend/requirements.txt`)

- **Web:** FastAPI, Uvicorn[standard], multipart.
- **DB:** SQLAlchemy 2, aiomysql, pymysql, Alembic, cryptography, greenlet.
- **Auth/validation:** Pydantic v2, pydantic-settings, python-jose, passlib, bcrypt.
- **Data/ML/reporting:** pandas, numpy, **scikit-learn (unused in app code per grep)**, reportlab, openpyxl.
- **Infra:** redis, aiofiles, httpx, structlog, python-dotenv.
- **Dev/test/quality:** pytest, pytest-asyncio, pytest-cov, ruff, mypy.

---

## 16. Known gaps and documentation drift (factual)

1. **Root `README.md`** describes **Next.js 14**; the implemented UI is **Vite + React**.
2. **`scikit-learn`** is not imported by application modules found under `backend/app/` (only declared in requirements).
3. **Query Lab** tenant scoping is **not** implemented as described in the service docstring; **`ALLOWED_TABLES` is unused** — security review recommended.
4. **Transaction partitioning** is commented in migration; single table in Alembic revision.
5. **`get_db` commits after every request** that completes without exception — understand implications for multi-step business transactions (may need explicit transaction boundaries for some flows).

---

## 17. Quick mental model

```
Browser (React SPA, port 3000 in dev)
    → HTTP JSON to FastAPI :8000 /api/v1
        → JWT → TokenData(company_id, role)
        → AsyncSession (MySQL)
            → Services → Repositories / raw SQL
        → Optional Redis (cache, rate limit)
MySQL 8 (tenant rows keyed by company_id)
```

---

*End of `project_summary.md`.*
