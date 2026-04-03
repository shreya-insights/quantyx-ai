# Quantyx AI — Full local development setup

This guide walks through installing prerequisites, creating the database, running migrations, and starting the **FastAPI** backend and **Vite + React** frontend on **macOS** and **Windows**. No backend code changes are required.

> **Stack (this repository):** Python 3.11+, FastAPI, MySQL 8.x, Redis (recommended), Node.js 20+, Vite, TypeScript, Tailwind CSS.

---

## Table of contents

1. [What you need (overview)](#1-what-you-need-overview)
2. [Project layout and configuration files](#2-project-layout-and-configuration-files)
3. [macOS setup](#3-macos-setup)
4. [Windows setup (detailed)](#4-windows-setup-detailed)
5. [Database: create schema with Alembic (both platforms)](#5-database-create-schema-with-alembic-both-platforms)
6. [Run the backend (FastAPI / Uvicorn)](#6-run-the-backend-fastapi--uvicorn)
7. [Run the frontend (Vite)](#7-run-the-frontend-vite)
8. [Optional: Docker for MySQL + Redis only](#8-optional-docker-for-mysql--redis-only)
9. [Verify the app](#9-verify-the-app)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. What you need (overview)

| Component | Role | Typical install |
|-----------|------|-----------------|
| **Python 3.11+** | Backend runtime | python.org, Homebrew (Mac), Microsoft Store / python.org (Windows) |
| **pip / venv** | Python packages & isolated env | Included with Python |
| **MySQL Server 8** | Application database | Homebrew (Mac), MySQL Installer or Chocolatey (Windows) |
| **Redis** | Caching & rate limiting (recommended) | Homebrew `redis` (Mac), Docker, WSL, or Memurai (Windows) |
| **Node.js 20+ (LTS)** | Frontend tooling | nodejs.org (both platforms) |
| **npm** | Installs frontend deps | Ships with Node.js |
| **Git** | Clone the repo | git-scm.com |

You will use **two terminal windows** in normal development: one for the **backend**, one for the **frontend**.

---

## 2. Project layout and configuration files

After cloning, open a terminal **inside the project folder** (the folder that contains `backend/` and `frontend/`).

- **Backend config:** The app reads environment variables from a file named `.env` in the **`backend`** directory when you run Uvicorn from `backend/` (current working directory matters).
- **Frontend config:** Copy `frontend/.env.example` to `frontend/.env` for local API URL.

**Recommended first step:**

1. Copy the root template:  
   `cp .env.example .env` (Mac/Linux) or `copy .env.example .env` (Windows CMD)  
   Edit `.env` if you change passwords or hosts.
2. Copy the same values into the backend folder so the API can load them:  
   `cp .env backend/.env` (Mac/Linux) or `copy .env backend\.env` (Windows)  
   Alternatively, create `backend/.env` manually with the same `DB_*`, `REDIS_*`, and `SECRET_KEY` values as in `.env.example`.

Default values in `.env.example` assume:

- Database name: `quantyx_ai`
- DB user: `quantyx`
- DB password: `quantyx_password`
- MySQL host: `localhost`, port `3306`
- Redis: `localhost:6379`

If you use different credentials, update **both** `.env` (root) and `backend/.env` consistently.

---

## 3. macOS setup

### 3.1 Install Homebrew (if needed)

See [https://brew.sh](https://brew.sh). Then:

```bash
brew update
```

### 3.2 Install Python 3.11+

```bash
brew install python@3.11
```

Confirm:

```bash
python3 --version
```

### 3.3 Install Node.js 20+

```bash
brew install node@20
```

Or install the LTS installer from [https://nodejs.org](https://nodejs.org). Confirm:

```bash
node --version
npm --version
```

### 3.4 Install MySQL 8 (Homebrew)

```bash
brew install mysql
brew services start mysql
```

`brew services start mysql` runs MySQL in the background and starts it on login.

### 3.5 Create database and user (macOS)

Open the MySQL client (you will be prompted for the MySQL **root** password you set during first-time setup):

```bash
mysql -u root -p
```

In the MySQL prompt, run (adjust names/passwords if you changed `.env`):

```sql
CREATE DATABASE IF NOT EXISTS quantyx_ai
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'quantyx'@'localhost' IDENTIFIED BY 'quantyx_password';
GRANT ALL PRIVILEGES ON quantyx_ai.* TO 'quantyx'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

If `CREATE USER` fails because the user exists, use:

```sql
ALTER USER 'quantyx'@'localhost' IDENTIFIED BY 'quantyx_password';
```

### 3.6 Install Redis (recommended)

```bash
brew install redis
brew services start redis
```

Test:

```bash
redis-cli ping
```

Expected: `PONG`.

### 3.7 Python virtual environment and backend dependencies

From the **project root**:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Keep this terminal open; you will use it to run Alembic and Uvicorn (see sections 5–6).

### 3.8 Frontend dependencies

Open a **second** terminal, from project root:

```bash
cd frontend
cp ../.env.example .env
# Or: cp .env.example .env
npm install
```

---

## 4. Windows setup (detailed)

This section assumes **64-bit Windows 10/11**. Paths use backslashes where typical for Windows.

### 4.1 Install Python 3.11+

1. Download the installer from [https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/).
2. Run the installer. **Important:** Enable **“Add python.exe to PATH”**.
3. Close and reopen **Command Prompt** or **PowerShell**, then verify:

```powershell
python --version
```

If `python` is not found, try the **Python Launcher**:

```powershell
py --version
```

Use `py` instead of `python` in the commands below if that is what works on your machine.

### 4.2 PowerShell: allow scripts (for venv activation)

If you use PowerShell and activation fails with an execution policy error:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4.3 Install Node.js 20 LTS

1. Download the **LTS** Windows installer from [https://nodejs.org](https://nodejs.org).
2. Run it with default options (includes **npm**).
3. Open a **new** terminal and verify:

```powershell
node --version
npm --version
```

### 4.4 MySQL on Windows — choose one path

#### Option A: MySQL Installer (recommended for beginners)

1. Download **MySQL Installer** from [https://dev.mysql.com/downloads/installer/](https://dev.mysql.com/downloads/installer/).
2. Choose **Developer Default** or **Server only** and install **MySQL Server 8** and **MySQL Workbench** (optional but useful).
3. During setup, set a **root password** and remember it. Enable **TCP/IP**, port **3306**.
4. Finish the wizard and ensure the **MySQL80** Windows service is **Running** (Services app → `MySQL80`).

#### Option B: MySQL already installed (XAMPP, WAMP, older install)

1. Confirm the service is running (Services → MySQL or MariaDB).
2. Note the port (often **3306**). If it is not 3306, set `DB_PORT` in `.env` / `backend/.env` accordingly.
3. Use **MySQL Workbench** or the command-line client to connect as **root** and run the same SQL as in [section 3.5](#35-create-database-and-user-macos) to create `quantyx_ai` and user `quantyx`.

#### Option C: Chocolatey (if you use it)

```powershell
choco install mysql -y
```

Then configure the server and root password per Chocolatey’s notes, and create the database/user as in section 3.5.

### 4.5 Create database and user on Windows

**Using MySQL Workbench**

1. Open MySQL Workbench, connect to **Local instance** (localhost, root).
2. Open a new SQL tab, paste:

```sql
CREATE DATABASE IF NOT EXISTS quantyx_ai
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'quantyx'@'localhost' IDENTIFIED BY 'quantyx_password';
GRANT ALL PRIVILEGES ON quantyx_ai.* TO 'quantyx'@'localhost';
FLUSH PRIVILEGES;
```

3. Execute (lightning bolt). You should see success.

**Using Command Prompt (if `mysql.exe` is on PATH)**

MySQL’s `bin` folder is often:

`C:\Program Files\MySQL\MySQL Server 8.0\bin`

```cmd
cd "C:\Program Files\MySQL\MySQL Server 8.0\bin"
mysql -u root -p
```

Then paste the same SQL as above.

### 4.6 Redis on Windows

Redis does not ship as a native Microsoft service. Common options:

| Option | Notes |
|--------|--------|
| **Docker Desktop** | Run `redis:7-alpine` on port 6379 (see [section 8](#8-optional-docker-for-mysql--redis-only)). |
| **WSL2** | Install Ubuntu in WSL, then `sudo apt install redis-server` and run Redis inside Linux. |
| **Memurai** | Redis-compatible Windows service ([https://www.memurai.com](https://www.memurai.com)). |

If Redis is not running, some features may degrade (caching/rate limits); starting Redis is strongly recommended.

### 4.7 Python virtual environment and backend dependencies (Windows)

From **Command Prompt** or **PowerShell**, go to the project folder (use quotes if the path contains spaces, e.g. `Desktop\Quantyx AI`):

```powershell
cd "C:\path\to\Quantyx AI\backend"
python -m venv .venv
```

**Activate:**

- **Command Prompt (cmd.exe):**

```cmd
.venv\Scripts\activate.bat
```

- **PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4.8 Frontend dependencies (Windows)

From a **second** terminal, project root:

```powershell
cd "C:\path\to\Quantyx AI\frontend"
copy ..\.env.example .env
npm install
```

---

## 5. Database: create schema with Alembic (both platforms)

Alembic applies SQL migrations and creates all tables. **MySQL must be running** and the user must have `DATABASE` and `CREATE` privileges on `quantyx_ai`.

1. Ensure `backend/.env` exists and contains correct `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.
2. Activate the backend virtual environment (same as in sections 3.7 or 4.7).
3. Working directory must be **`backend`** (where `alembic.ini` lives):

```bash
cd backend
# Mac/Linux:
source .venv/bin/activate
# Windows CMD:
# .venv\Scripts\activate.bat
# Windows PowerShell:
# .\.venv\Scripts\Activate.ps1

alembic upgrade head
```

You should see Alembic apply revisions without errors. If you see `Access denied`, fix DB user/password in `backend/.env`. If tables already exist from a failed run, you may need to drop the database and recreate it (development only), then run `alembic upgrade head` again.

---

## 6. Run the backend (FastAPI / Uvicorn)

With the backend venv **activated** and **`cd backend`**:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **API:** [http://localhost:8000](http://localhost:8000)  
- **Interactive docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

Leave this terminal running.

---

## 7. Run the frontend (Vite)

In a **second** terminal, from project root:

```bash
cd frontend
npm run dev
```

Vite dev server is usually **http://localhost:5173** (check the terminal output). Confirm `frontend/.env` contains:

```env
VITE_API_URL=http://localhost:8000
```

If the browser shows CORS or connection errors, ensure the backend is running and `ALLOWED_ORIGINS` in `backend/.env` includes your Vite origin (e.g. `http://localhost:5173`). You can set:

```env
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

Restart Uvicorn after changing `.env`.

---

## 8. Optional: Docker for MySQL + Redis only

If you prefer not to install MySQL/Redis on the host, install **Docker Desktop** (Mac or Windows) and run only infrastructure:

```bash
docker compose up -d mysql redis
```

Then in `backend/.env`.

- Set `DB_HOST=127.0.0.1` (or `localhost`) and `DB_PORT=3306` — the compose file maps 3306.
- Set `REDIS_HOST=localhost`, `REDIS_PORT=6379`.

Run the backend and frontend **locally** as in sections 6–7 (do not rely on the compose `backend` service unless you intend full containerized dev).

---

## 9. Verify the app

1. Open the frontend URL (e.g. `http://localhost:5173`).
2. Register a company via `/docs` (`POST /api/v1/auth/register`) or the UI, or log in if you already have a user.
3. Open **Transactions** and **Upload CSV** if you have a demo file (CSV columns must match the API’s ingestion expectations).

---

## 10. Troubleshooting

| Issue | What to try |
|-------|-------------|
| **`Address already in use` on port 8000** | Another process uses Uvicorn’s port. Stop it or run: `uvicorn app.main:app --reload --port 8001` and set `VITE_API_URL` accordingly. |
| **`mysql` command not found** | Add MySQL `bin` to PATH, or use MySQL Workbench for SQL. |
| **Alembic fails / connection refused** | MySQL service not started; wrong `DB_HOST`/`DB_PORT`; firewall blocking localhost. |
| **Redis connection errors** | Start Redis (or Docker Redis), or use Docker Compose as in section 8. |
| **Path with spaces** (e.g. `Quantyx AI`) | Always quote paths in PowerShell: `cd "C:\Users\...\Quantyx AI"` |
| **Frontend cannot reach API** | Check `VITE_API_URL`, backend running, and `ALLOWED_ORIGINS` including the Vite port. |

---

## Quick reference: two terminals

| Terminal | Directory | Commands |
|----------|-----------|----------|
| **1 — Backend** | `backend/` | `source .venv/bin/activate` (Mac) or `.\.venv\Scripts\Activate.ps1` (Win) → `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` |
| **2 — Frontend** | `frontend/` | `npm run dev` |

---

## After setup

- **Migrations:** `cd backend && alembic upgrade head` (after pulling new code that adds migrations).
- **Tests:** `cd backend && pytest tests/ -v` (if pytest is installed via `requirements.txt`).

For containerized full-stack run, see the root `README.md` and `docker compose up -d`.
