# Quantyx AI — Complete Local Setup Guide

> **Who this guide is for:** Anyone — developer or not — who has cloned this repo and wants to run the entire app on their own laptop. Every step is explained from scratch. No prior experience with Python, Node.js, or databases is assumed.

---

## What you will have running by the end

| Service | URL | What it does |
|---|---|---|
| **Frontend** (React) | http://localhost:3000 | The web app you interact with |
| **Backend API** (FastAPI) | http://localhost:8000 | The server the frontend talks to |
| **API Docs** (Swagger) | http://localhost:8000/docs | Interactive API explorer |
| **Celery Worker** | (background process) | Processes fraud detection + emails |
| **MySQL** | localhost:3306 | Stores all data |
| **Redis** | localhost:6379 | Caching + task queue |

---

## Table of Contents

1. [What you need to install first](#1-what-you-need-to-install-first)
2. [Clone the project](#2-clone-the-project)
3. [Set up MySQL database](#3-set-up-mysql-database)
4. [Set up Redis](#4-set-up-redis)
5. [Configure the backend .env file](#5-configure-the-backend-env-file)
6. [Get your free Groq API key (AI Analyst feature)](#6-get-your-free-groq-api-key-ai-analyst-feature)
7. [Set up Gmail for invitation emails](#7-set-up-gmail-for-invitation-emails)
8. [Install Python and backend dependencies](#8-install-python-and-backend-dependencies)
9. [Run database migrations (create all tables)](#9-run-database-migrations-create-all-tables)
10. [Start the backend server](#10-start-the-backend-server)
11. [Start the Celery worker (fraud + emails)](#11-start-the-celery-worker-fraud--emails)
12. [Start the Celery Beat scheduler (scheduled jobs)](#12-start-the-celery-beat-scheduler-scheduled-jobs)
13. [Set up and start the frontend](#13-set-up-and-start-the-frontend)
14. [Register your first account](#14-register-your-first-account)
15. [Test the invitation email flow](#15-test-the-invitation-email-flow)
16. [Test the AI Analyst](#16-test-the-ai-analyst)
17. [Quick reference: all terminals at a glance](#17-quick-reference-all-terminals-at-a-glance)
18. [Windows-specific instructions](#18-windows-specific-instructions)
19. [Troubleshooting](#19-troubleshooting)

---

## 1. What you need to install first

Before anything else, install these four programs on your computer. Click each link to download.

| Program | Why you need it | Download |
|---|---|---|
| **Git** | To clone (download) the project code | https://git-scm.com/downloads |
| **Python 3.11 or newer** | To run the backend | https://www.python.org/downloads/ |
| **Node.js 20 LTS** | To run the frontend | https://nodejs.org/ (choose "LTS") |
| **MySQL 8** | The database | See Section 3 below |
| **Redis** | Caching + background jobs | See Section 4 below |

### How to verify each is installed

Open a **Terminal** (Mac: press `Cmd+Space`, type "Terminal") or **Command Prompt** (Windows: press `Win+R`, type `cmd`) and run these commands one by one:

```bash
git --version
# Expected: git version 2.x.x

python3 --version
# Expected: Python 3.11.x (Mac/Linux)
# On Windows try: python --version

node --version
# Expected: v20.x.x

npm --version
# Expected: 10.x.x
```

If any of these say "command not found" or "not recognized", the program is not installed yet — go back and install it before continuing.

---

## 2. Clone the project

Open a terminal and navigate to where you want the project folder to be. For example, to put it on your Desktop:

**Mac/Linux:**
```bash
cd ~/Desktop
git clone https://github.com/shreya-insights/quantyx-ai.git "Quantyx AI"
cd "Quantyx AI"
```

**Windows (Command Prompt):**
```cmd
cd %USERPROFILE%\Desktop
git clone https://github.com/shreya-insights/quantyx-ai.git "Quantyx AI"
cd "Quantyx AI"
```

After cloning, you should see these folders inside:
```
Quantyx AI/
├── backend/       ← Python/FastAPI server code
├── frontend/      ← React web app code
├── monitoring/    ← Prometheus/Grafana config
├── .env.example   ← Template for environment variables
└── SETUP.md       ← This file
```

---

## 3. Set up MySQL database

MySQL is the database that stores all your transactions, users, companies, fraud alerts, etc.

### Mac: Install with Homebrew

**Step 1: Install Homebrew** (if you don't have it — it's a package manager for Mac):
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Step 2: Install and start MySQL:**
```bash
brew install mysql
brew services start mysql
```

**Step 3: Set up MySQL root password** (first time only):
```bash
mysql_secure_installation
```
Follow the prompts. When asked to set a root password, choose something you'll remember (e.g. `root123`). Answer **Yes** to all security questions.

**Step 4: Create the Quantyx database and user:**
```bash
mysql -u root -p
```
Enter your root password when prompted. You'll see a `mysql>` prompt. Now paste these commands:

```sql
CREATE DATABASE IF NOT EXISTS quantyx_ai
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'quantyx'@'localhost' IDENTIFIED BY 'quantyx_password';
GRANT ALL PRIVILEGES ON quantyx_ai.* TO 'quantyx'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Windows: Install MySQL

**Option A (Recommended for beginners): MySQL Installer**
1. Go to https://dev.mysql.com/downloads/installer/
2. Download **MySQL Installer for Windows** (the ~450MB "full" version)
3. Run the installer, choose **Developer Default**
4. When asked for a root password, set one you'll remember
5. Finish the installation — MySQL will now run as a Windows background service

**Then create the database:** Open **MySQL Workbench** (installed with the above), connect to "Local instance MySQL80", open a new SQL tab, paste and run:
```sql
CREATE DATABASE IF NOT EXISTS quantyx_ai
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'quantyx'@'localhost' IDENTIFIED BY 'quantyx_password';
GRANT ALL PRIVILEGES ON quantyx_ai.* TO 'quantyx'@'localhost';
FLUSH PRIVILEGES;
```

**Option B: Docker (if you have Docker Desktop installed):**
```bash
docker run -d --name quantyx-mysql \
  -e MYSQL_ROOT_PASSWORD=root123 \
  -e MYSQL_DATABASE=quantyx_ai \
  -e MYSQL_USER=quantyx \
  -e MYSQL_PASSWORD=quantyx_password \
  -p 3306:3306 \
  mysql:8.0
```
This creates the database automatically — skip the SQL commands above if using Docker.

---

## 4. Set up Redis

Redis is used for caching analytics data and powering the background task queue. The app will mostly work without it, but fraud detection and email invitations won't work without Redis.

### Mac:
```bash
brew install redis
brew services start redis
```

Test it works:
```bash
redis-cli ping
```
You should see `PONG`.

### Windows:
Redis doesn't run natively on Windows. Choose one:

**Option A (Easiest): Docker Desktop**
1. Install Docker Desktop from https://www.docker.com/products/docker-desktop/
2. Run:
```bash
docker run -d --name quantyx-redis -p 6379:6379 redis:7-alpine
```

**Option B: WSL2 (Windows Subsystem for Linux)**
1. Open PowerShell as Administrator and run: `wsl --install`
2. Restart your PC, then open Ubuntu from the Start menu
3. Inside Ubuntu:
```bash
sudo apt update
sudo apt install redis-server
sudo service redis-server start
redis-cli ping
```

**Option C: Memurai** (Redis-compatible Windows service)
Download from https://www.memurai.com/ — free for development use.

---

## 5. Configure the backend `.env` file

The `.env` file is a text file that holds all your secret settings (passwords, API keys). The backend reads this file when it starts.

### Create the file

**Mac/Linux** — from the project root folder:
```bash
cp .env.example backend/.env
```

**Windows:**
```cmd
copy .env.example backend\.env
```

### Edit the file

Open `backend/.env` in any text editor (Notepad, VS Code, TextEdit). It looks like this:

```env
APP_NAME=Quantyx AI
APP_VERSION=1.0.0
DEBUG=false
SECRET_KEY=change-this-to-a-random-64-char-string-in-production-NEVER-commit

DB_HOST=localhost
DB_PORT=3306
DB_NAME=quantyx_ai
DB_USER=quantyx
DB_PASSWORD=quantyx_password

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001

RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

FIRST_ADMIN_EMAIL=admin@quantyx.ai
FIRST_ADMIN_PASSWORD=Admin@Quantyx123!
FIRST_COMPANY_NAME=Quantyx Demo Corp
FIRST_COMPANY_SLUG=quantyx-demo
```

**Now add these additional sections** at the bottom of `backend/.env` (you need to add them — they are not in `.env.example`):

```env
# ─── Invitation Tokens ────────────────────────────────────────────────────────
INVITE_TOKEN_EXPIRE_HOURS=72
INVITE_SECRET_KEY=change-this-to-another-random-64-char-string
FRONTEND_URL=http://localhost:3000

# ─── Email / SMTP (Gmail) ─────────────────────────────────────────────────────
# Fill this in after completing Section 7 of this guide
MAIL_USERNAME=your-gmail@gmail.com
MAIL_PASSWORD=your-gmail-app-password
MAIL_FROM=your-gmail@gmail.com
MAIL_FROM_NAME=Quantyx AI
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_STARTTLS=true
MAIL_SSL_TLS=false

# ─── AI Analyst / LLM (Groq - free) ──────────────────────────────────────────
# Fill this in after completing Section 6 of this guide
LLM_PRIMARY_PROVIDER=groq
LLM_FALLBACK_PROVIDER=gemini
LLM_TERTIARY_PROVIDER=openrouter
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-flash
OPENROUTER_API_KEY=
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
AI_ANALYST_MAX_TOKENS=1500
AI_ANALYST_RATE_LIMIT_PER_HOUR=20
AI_ANALYST_MAX_TOOL_ROUNDS=5

# ─── Fraud Detection Thresholds ───────────────────────────────────────────────
FRAUD_VELOCITY_THRESHOLD=5
FRAUD_VELOCITY_WINDOW_MIN=30
FRAUD_AMOUNT_SPIKE_MULTIPLIER=3.0
FRAUD_LOCATION_RADIUS_KM=200.0
FRAUD_DUPLICATE_WINDOW_MIN=5
BULK_UPLOAD_MAX_FRAUD_TASKS=2000

# ─── ML Model ─────────────────────────────────────────────────────────────────
ML_MODEL_DIR=backend/ml
```

**What each section means:**
- `SECRET_KEY` — A long random string used to sign login tokens. Change this to anything random (type random characters). **Never share this.**
- `DB_*` — Your MySQL database connection. If you used the default credentials above, leave these as-is.
- `REDIS_*` — Your Redis connection. Leave as-is if running locally.
- `MAIL_*` — Your Gmail credentials for sending invitation emails (set up in Section 7).
- `GROQ_API_KEY` — Your Groq API key for the AI Analyst feature (get in Section 6).
- `FRONTEND_URL` — This is the URL the invite email links point to. Keep as `http://localhost:3000` for local development.

---

## 6. Get your free Groq API key (AI Analyst feature)

Groq provides a **free** AI API that powers the AI Analyst chat feature. No credit card needed.

**Step 1: Create a Groq account**
1. Go to https://console.groq.com/
2. Click **Sign Up** (you can sign up with Google)
3. Verify your email

**Step 2: Generate an API key**
1. Once logged in, click **API Keys** in the left sidebar (or go to https://console.groq.com/keys)
2. Click **Create API Key**
3. Give it a name like "Quantyx Local Dev"
4. Click **Submit**
5. **Copy the key immediately** — it starts with `gsk_` and looks like: `gsk_abc123xyz456...`
   > ⚠️ You can only see this key once. If you lose it, create a new one.

**Step 3: Add to your .env file**
Open `backend/.env` and replace:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
```
with your actual key:
```env
GROQ_API_KEY=gsk_abc123xyz456...
```

**Free tier limits:** Groq's free tier allows ~14,400 requests/day with the `llama-3.3-70b-versatile` model — more than enough for development.

**Optional: Add a Gemini API key as fallback**

If you want a backup AI provider:
1. Go to https://aistudio.google.com/app/apikey
2. Sign in with Google
3. Click **Create API Key**
4. Copy the key (starts with `AIzaSy`)
5. Add to `.env`: `GEMINI_API_KEY=AIzaSy...`

---

## 7. Set up Gmail for invitation emails

When an admin invites a team member, Quantyx AI sends them an email with a link. This is done via Gmail's SMTP service. You need to set up an **App Password** (a special password just for this app — not your real Gmail password).

> **Why App Password and not my real password?** Gmail blocks apps from using your actual password for security. App Passwords are specific to one app and can be revoked anytime.

### Step 1: Enable 2-Step Verification on your Google account

> Skip this step if you already have 2-Step Verification enabled.

1. Go to https://myaccount.google.com/security
2. Under "How you sign in to Google", click **2-Step Verification**
3. Follow the steps to enable it (usually takes 2 minutes)

### Step 2: Create an App Password

1. Go to https://myaccount.google.com/apppasswords
   (If you don't see this page, make sure 2-Step Verification is enabled)
2. At the bottom, you'll see a dropdown that says "Select app"
3. Click the dropdown and choose **Other (Custom name)**
4. Type `Quantyx AI` and click **Generate**
5. Google will show you a **16-character password** like `abcd efgh ijkl mnop`
6. **Copy this password** (you'll only see it once)

### Step 3: Add to your .env file

Open `backend/.env` and fill in:
```env
MAIL_USERNAME=youremail@gmail.com
MAIL_PASSWORD=abcdefghijklmnop
MAIL_FROM=youremail@gmail.com
MAIL_FROM_NAME=Quantyx AI
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_STARTTLS=true
MAIL_SSL_TLS=false
```

Replace:
- `youremail@gmail.com` → your actual Gmail address (in both `MAIL_USERNAME` and `MAIL_FROM`)
- `abcdefghijklmnop` → the 16-character App Password (without spaces)

**Example:**
```env
MAIL_USERNAME=sarah.jones@gmail.com
MAIL_PASSWORD=xkqrabcdefghijkl
MAIL_FROM=sarah.jones@gmail.com
MAIL_FROM_NAME=Quantyx AI
```

> **Note:** If you don't want to set up email right now, that's fine. The invitation feature won't work, but everything else will. You can come back and add the email settings later.

---

## 8. Install Python and backend dependencies

Now we install all the Python packages the backend needs.

### Step 1: Open a terminal in the `backend` folder

**Mac/Linux:**
```bash
cd "/path/to/Quantyx AI/backend"
```
(Replace `/path/to` with where you cloned the project. If it's on your Desktop: `cd ~/Desktop/"Quantyx AI"/backend`)

**Windows:**
```cmd
cd "C:\Users\YourName\Desktop\Quantyx AI\backend"
```

### Step 2: Create a virtual environment

A virtual environment is an isolated Python installation just for this project — it won't affect anything else on your computer.

**Mac/Linux:**
```bash
python3 -m venv .venv
```

**Windows:**
```cmd
python -m venv .venv
```

### Step 3: Activate the virtual environment

**Mac/Linux:**
```bash
source .venv/bin/activate
```
Your terminal prompt will change to show `(.venv)` at the beginning — that means it's activated.

**Windows (Command Prompt):**
```cmd
.venv\Scripts\activate.bat
```

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
```
If PowerShell gives an error about execution policy, run this first:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Step 4: Upgrade pip and install packages

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs ~50 packages. It may take 3–10 minutes depending on your internet speed. You'll see a lot of text scrolling — that's normal.

When it finishes, you should see something like:
```
Successfully installed fastapi-0.111.1 uvicorn-0.30.3 sqlalchemy-2.0.31 ...
```

> **Tip:** Keep this terminal open — you'll use it in the next steps.

---

## 9. Run database migrations (create all tables)

Alembic is a tool that creates all the database tables automatically. This replaces having to write SQL manually.

**Make sure:**
- You are inside the `backend/` folder
- The virtual environment is activated (you see `(.venv)` in your prompt)
- MySQL is running
- `backend/.env` has the correct `DB_*` settings

Run:
```bash
alembic upgrade head
```

You'll see output like:
```
INFO  [alembic.runtime.migration] Context impl MySQLImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial_schema, initial schema
INFO  [alembic.runtime.migration] Running upgrade 0001 -> 0002, fraud alerts
INFO  [alembic.runtime.migration] Running upgrade 0002 -> 0003, saved queries
...
INFO  [alembic.runtime.migration] Running upgrade 0010 -> 0011, invitations
```

This creates all 22 database tables (companies, users, transactions, fraud_alerts, invitations, etc.).

**If you see an error like "Access denied":**
- Check that MySQL is running: `brew services list` (Mac) or check Windows Services
- Check that your `DB_USER`, `DB_PASSWORD`, `DB_NAME` in `backend/.env` match what you set up in Section 3
- Try connecting manually: `mysql -u quantyx -p quantyx_ai` — enter `quantyx_password`

**If you see "Can't connect to MySQL":**
- MySQL is not running. Mac: `brew services start mysql`. Windows: Open Services, find MySQL80, click Start.

---

## 10. Start the backend server

This starts the FastAPI backend on port 8000.

**Make sure you are in the `backend/` folder with the virtual environment activated**, then run:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using WatchFiles
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO     quantyx_startup version=1.0.0 debug=False
INFO     ml_model.not_found.running_rules_only
INFO:     Application startup complete.
```

The line `ml_model.not_found.running_rules_only` is normal — it means the ML fraud model hasn't been trained yet. The rules-based fraud detection still works.

**Test it:** Open http://localhost:8000/health in your browser. You should see:
```json
{
  "status": "degraded",
  "app": "Quantyx AI",
  "version": "1.0.0",
  "latency_ms": 5,
  "celery_workers": "no_workers",
  "ml_model": "not_loaded"
}
```
`"celery_workers": "no_workers"` is expected — you haven't started the worker yet. We'll do that next.

**Also test the API docs:** Open http://localhost:8000/docs — you should see a full interactive API documentation page.

> **Keep this terminal running.** Open a new terminal for the next steps.

---

## 11. Start the Celery worker (fraud + emails)

The Celery worker runs in the background and handles:
- Fraud detection on every new transaction
- Sending invitation emails via Gmail
- Rebuilding analytics caches

**Open a new terminal** and navigate to the `backend` folder again:

**Mac/Linux:**
```bash
cd ~/Desktop/"Quantyx AI"/backend
source .venv/bin/activate
```

**Windows:**
```cmd
cd "C:\Users\YourName\Desktop\Quantyx AI\backend"
.venv\Scripts\activate.bat
```

Then start the worker:

**Mac/Linux:**
```bash
celery -A app.worker.celery_app worker \
  --loglevel=info \
  --queues=fraud,email,analytics,features \
  --concurrency=4
```

**Windows:**
```cmd
celery -A app.worker.celery_app worker --loglevel=info --queues=fraud,email,analytics,features --concurrency=4 --pool=solo
```
> On Windows, add `--pool=solo` — Windows doesn't support the default `prefork` multiprocessing model.

You should see:
```
 -------------- celery@yourcomputer v5.4.0 (opalescent)
--- ***** -----
-- ******* ---- macOS-13.x-arm64
- *** --- * ---
- ** ---------- [config]
- ** ---------- .> app:         quantyx:0x...
- ** ---------- .> transport:   redis://localhost:6379//
- ** ---------- .> results:     redis://localhost:6379/
- *** --- * --- .> concurrency: 4 (prefork)
-- ******* ----
--- ***** ----- [queues]
 -------------- .> fraud           exchange=fraud(direct) key=fraud
                .> email           exchange=email(direct) key=email
                .> analytics       exchange=analytics(direct) key=analytics
                .> features        exchange=features(direct) key=features

[tasks]
  . quantyx.analytics.refresh_all_analytics_caches
  . quantyx.analytics.refresh_analytics_cache
  . quantyx.email.send_invitation
  . quantyx.features.recompute_all_features
  . quantyx.fraud.analyze_transaction
  . quantyx.monitoring.run_model_health_check
  . quantyx.warehouse.run_nightly_etl

[2026-04-05 10:00:00,000: INFO/MainProcess] Connected to redis://localhost:6379//
[2026-04-05 10:00:00,000: INFO/MainProcess] celery@yourcomputer ready.
```

Now go back to a browser and refresh http://localhost:8000/health — you should now see `"celery_workers": "ok"`.

> **Keep this terminal running.** Open another new terminal for the next step.

---

## 12. Start the Celery Beat scheduler (scheduled jobs)

Celery Beat runs scheduled tasks automatically:
- **Every hour:** Refresh analytics caches for all companies
- **Every 6 hours:** Recompute ML feature vectors
- **2:00 AM UTC daily:** Run nightly data warehouse ETL
- **Every Monday 12:00 AM UTC:** Run ML model health check

**Open another new terminal** and navigate to `backend`:

**Mac/Linux:**
```bash
cd ~/Desktop/"Quantyx AI"/backend
source .venv/bin/activate
celery -A app.worker.celery_app beat \
  --scheduler redbeat.RedBeatScheduler \
  --loglevel=info
```

**Windows:**
```cmd
cd "C:\Users\YourName\Desktop\Quantyx AI\backend"
.venv\Scripts\activate.bat
celery -A app.worker.celery_app beat --scheduler redbeat.RedBeatScheduler --loglevel=info
```

You should see:
```
[2026-04-05 10:00:00,000: INFO/MainProcess] beat: Starting...
[2026-04-05 10:00:00,000: INFO/MainProcess] Scheduler: Sending due task quantyx.analytics.refresh_all_analytics_caches
```

> **Note:** Beat is optional for basic testing. Without it, analytics caches won't auto-refresh on a schedule (but you can still trigger them manually). Fraud detection and email invitations work without Beat.

---

## 13. Set up and start the frontend

**Open yet another new terminal** (you now have up to 4 terminals — backend, worker, beat, and this one for frontend).

### Step 1: Navigate to the frontend folder

**Mac/Linux:**
```bash
cd ~/Desktop/"Quantyx AI"/frontend
```

**Windows:**
```cmd
cd "C:\Users\YourName\Desktop\Quantyx AI\frontend"
```

### Step 2: Create the frontend .env file

**Mac/Linux:**
```bash
cp .env.example .env
```

**Windows:**
```cmd
copy .env.example .env
```

Open `frontend/.env` in a text editor. It should look like:
```env
# VITE_API_URL=
VITE_APP_NAME=Quantyx AI
```

> **Leave `VITE_API_URL` commented out for local development.** The Vite dev server automatically proxies all `/api/*` requests to `http://localhost:8000`. You do NOT need to set it.

### Step 3: Install frontend packages

```bash
npm install
```

This downloads all the JavaScript packages the frontend needs (~300MB, takes 1–3 minutes). You'll see a progress bar.

### Step 4: Start the frontend dev server

```bash
npm run dev
```

You should see:
```
  VITE v5.x.x  ready in 800 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: http://192.168.x.x:3000/
  ➜  press h + enter to show help
```

> **The frontend always runs on port 3000** (configured in `vite.config.ts`). Open http://localhost:3000 in your browser.

---

## 14. Register your first account

1. Open http://localhost:3000 in your browser
2. Click **Get Started** or navigate to http://localhost:3000/register
3. Fill in:
   - **Company name:** e.g. "My Test Company"
   - **Your full name:** e.g. "John Smith"
   - **Email:** any email address (e.g. `admin@test.com`)
   - **Password:** must be 8+ characters
4. Click **Create Account**
5. You'll be redirected to the onboarding wizard — go through the 5 steps

You're now logged in as the **Admin** of your company. The admin can:
- View all data
- Send team invitations
- Manage billing/subscriptions
- Access AI Analyst and Query Lab

### To log in again later:
Go to http://localhost:3000/login and use the email + password you just created.

---

## 15. Test the invitation email flow

This tests that Gmail email sending works correctly.

### Send an invitation
1. Log in as Admin
2. Go to **Settings** → **Team** tab
3. Enter an email address to invite (use a real email address you can check)
4. Select role: **Analyst**
5. Click **Send Invitation**

### What happens next
1. A Celery task is created in the background
2. The Celery worker picks it up and sends an email via your Gmail
3. The recipient gets an email with a link like: `http://localhost:3000/accept-invite?token=abc123...`
4. Clicking the link opens the Accept Invitation page
5. The invitee sets their password and joins your company as an Analyst

### Check the worker logs
In your Celery worker terminal, you should see:
```
[INFO/ForkPoolWorker-1] Task quantyx.email.send_invitation succeeded
```

### Troubleshooting email
If you don't receive the email:
- Check your spam/junk folder
- Verify `MAIL_USERNAME` and `MAIL_PASSWORD` in `backend/.env` are correct
- Make sure you used an **App Password** (not your real Gmail password)
- Check the Celery worker terminal for error messages
- Make sure 2-Step Verification is enabled on your Gmail account (required for App Passwords)

---

## 16. Test the AI Analyst

1. Make sure your `GROQ_API_KEY` is set in `backend/.env` and the backend was restarted after adding it
2. Log in as Admin or Analyst
3. Click **AI Analyst** in the left sidebar
4. Type a question like: `"What is the total revenue this month?"`
5. The AI will respond with an analysis of your data

**If you get an error:**
- Check that `GROQ_API_KEY` starts with `gsk_` in your `.env`
- Make sure you saved the `.env` file and **restarted the backend** (press `Ctrl+C` in the backend terminal and run uvicorn again)
- Visit http://localhost:8000/api/v1/analyst/provider-status (you must be logged in as Admin) to see which providers are configured

---

## 17. Quick reference: all terminals at a glance

In normal development, you run **4 terminal windows**:

| Terminal | Folder | Command | What it does |
|---|---|---|---|
| **Terminal 1 — Backend** | `backend/` | `source .venv/bin/activate` then `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` | API server |
| **Terminal 2 — Worker** | `backend/` | `source .venv/bin/activate` then `celery -A app.worker.celery_app worker --loglevel=info --queues=fraud,email,analytics,features --concurrency=4` | Background jobs |
| **Terminal 3 — Beat** | `backend/` | `source .venv/bin/activate` then `celery -A app.worker.celery_app beat --scheduler redbeat.RedBeatScheduler --loglevel=info` | Scheduled tasks |
| **Terminal 4 — Frontend** | `frontend/` | `npm run dev` | Web app |

**Minimum to run the app** (just to browse the UI):
- Terminal 1 (Backend) + Terminal 4 (Frontend) — everything will render
- Without Terminal 2 (Worker), fraud detection and emails won't work
- Without Terminal 3 (Beat), scheduled cache refreshes won't run

---

## 18. Windows-specific instructions

### PowerShell execution policy error
If you see: `cannot be loaded because running scripts is disabled on this system`
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### "python" vs "python3" vs "py"
On Windows, depending on how Python was installed:
- Try `python --version` first
- If that fails, try `py --version`
- Use whichever works throughout this guide

### Virtual environment activation on Windows
- **CMD:** `.venv\Scripts\activate.bat`
- **PowerShell:** `.\.venv\Scripts\Activate.ps1`
- **Git Bash:** `source .venv/Scripts/activate`

### Celery on Windows
Windows doesn't support Celery's default multiprocessing (`prefork`). Always add `--pool=solo`:
```cmd
celery -A app.worker.celery_app worker --loglevel=info --queues=fraud,email,analytics,features --concurrency=4 --pool=solo
```

### Path with spaces
The project folder is called "Quantyx AI" — note the space. Always quote the path:
```cmd
cd "C:\Users\YourName\Desktop\Quantyx AI"
```

### MySQL on PATH (Windows)
If `mysql` command isn't found in CMD, add MySQL to PATH:
1. Open Start → search "Environment Variables"
2. Under "System variables", find `Path` and click Edit
3. Add: `C:\Program Files\MySQL\MySQL Server 8.0\bin`
4. Click OK, restart CMD

---

## 19. Troubleshooting

### Backend won't start

**Error: `ModuleNotFoundError: No module named 'app'`**
- Make sure you're running uvicorn from inside the `backend/` folder
- Make sure the virtual environment is activated (you see `(.venv)` in the prompt)

**Error: `Address already in use` (port 8000)**
- Something else is using port 8000. Find and stop it:
  - Mac: `lsof -ti:8000 | xargs kill`
  - Windows: `netstat -ano | findstr :8000` → note the PID → `taskkill /PID {pid} /F`
- Or use a different port: `uvicorn app.main:app --reload --port 8001`
  - Then update `ALLOWED_ORIGINS` in backend/.env and restart

**Error: `Connection refused` to MySQL**
- MySQL isn't running. 
  - Mac: `brew services start mysql`
  - Windows: Open Services.msc, find MySQL80, click Start

**Error: `Access denied for user 'quantyx'`**
- The MySQL user `quantyx` wasn't created, or the password is wrong
- Connect as root: `mysql -u root -p`
- Re-run the SQL from Section 3

### Alembic migration errors

**Error: `Can't connect to MySQL server`**
- MySQL is not running (see above)
- `DB_HOST` is wrong in `backend/.env` — should be `localhost`

**Error: `Table 'companies' already exists`**
- You ran migrations before on a dirty database
- Drop and recreate the database (development only):
  ```sql
  mysql -u root -p
  DROP DATABASE quantyx_ai;
  CREATE DATABASE quantyx_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  EXIT;
  ```
  Then run `alembic upgrade head` again

### Frontend issues

**Frontend shows blank page / console errors**
- Make sure the backend is running (http://localhost:8000/health should respond)
- Open browser DevTools (F12), check the Console tab for red errors
- Check the Network tab — if `/api/v1/auth/me` returns 502, the backend proxy isn't working

**Error: `EADDRINUSE: address already in use :::3000`**
- Port 3000 is in use. Find and kill the process:
  - Mac: `lsof -ti:3000 | xargs kill`
  - Or change the port in `vite.config.ts`: `server: { port: 3001 }`

**`npm install` fails with permission errors (Mac)**
- Don't use `sudo npm install`. Instead:
  ```bash
  sudo chown -R $(whoami) ~/.npm
  npm install
  ```

### Celery worker issues

**Worker shows `Cannot connect to redis://localhost:6379/`**
- Redis isn't running
  - Mac: `brew services start redis` → `redis-cli ping` should return `PONG`
  - Windows: Start Docker Redis container or Memurai service

**Worker starts but tasks don't run**
- Make sure the worker is watching the right queues: `--queues=fraud,email,analytics,features`
- Check there are no import errors in the worker startup output

### Email not being sent

**No email received after sending invitation**
1. Check the Celery worker terminal for error messages
2. Verify `MAIL_PASSWORD` is the 16-char App Password (not your Gmail login password)
3. Make sure 2-Step Verification is enabled on your Google account
4. Try the Gmail SMTP settings manually:
   ```python
   # Quick test (run in Python):
   import smtplib
   s = smtplib.SMTP('smtp.gmail.com', 587)
   s.starttls()
   s.login('youremail@gmail.com', 'your-app-password')
   print("Success!")
   ```

### AI Analyst not working

**Error: "No LLM providers configured"**
- `GROQ_API_KEY` is empty or incorrect in `backend/.env`
- Make sure the key starts with `gsk_`
- **Restart the backend** after adding/changing API keys — the backend reads `.env` only at startup

**Error: "Rate limit exceeded"**
- You've made more than 20 AI Analyst calls in the last hour (default limit)
- Wait an hour, or increase: `AI_ANALYST_RATE_LIMIT_PER_HOUR=50` in `backend/.env` and restart

---

## Complete .env template for backend

For reference, here is the complete `backend/.env` file with all possible settings. Copy this, fill in your values, and save as `backend/.env`:

```env
# ─── Application ──────────────────────────────────────────────────────────────
APP_NAME=Quantyx AI
APP_VERSION=1.0.0
DEBUG=false
SECRET_KEY=replace-this-with-64-random-characters-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# ─── Database (MySQL 8.0) ─────────────────────────────────────────────────────
DB_HOST=localhost
DB_PORT=3306
DB_NAME=quantyx_ai
DB_USER=quantyx
DB_PASSWORD=quantyx_password

# ─── Redis ────────────────────────────────────────────────────────────────────
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# ─── JWT ──────────────────────────────────────────────────────────────────────
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# ─── CORS ─────────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001

# ─── Rate Limiting ────────────────────────────────────────────────────────────
IP_RATE_LIMIT_PER_MINUTE=100
API_RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_BYPASS_EMAILS=

# ─── Seed Data (used only on first startup if seeding is implemented) ─────────
FIRST_ADMIN_EMAIL=admin@quantyx.ai
FIRST_ADMIN_PASSWORD=Admin@Quantyx123!
FIRST_COMPANY_NAME=Quantyx Demo Corp
FIRST_COMPANY_SLUG=quantyx-demo

# ─── Invitation Tokens ────────────────────────────────────────────────────────
INVITE_TOKEN_EXPIRE_HOURS=72
INVITE_SECRET_KEY=replace-this-with-another-64-random-characters-YYYYYYY
FRONTEND_URL=http://localhost:3000

# ─── Email / SMTP (Gmail) ─────────────────────────────────────────────────────
MAIL_USERNAME=your-gmail@gmail.com
MAIL_PASSWORD=your-16-char-app-password
MAIL_FROM=your-gmail@gmail.com
MAIL_FROM_NAME=Quantyx AI
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_STARTTLS=true
MAIL_SSL_TLS=false

# ─── AI Analyst / LLM Providers ───────────────────────────────────────────────
LLM_PRIMARY_PROVIDER=groq
LLM_FALLBACK_PROVIDER=gemini
LLM_TERTIARY_PROVIDER=openrouter
GROQ_API_KEY=gsk_your_groq_key_here
GROQ_MODEL=llama-3.3-70b-versatile
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-flash
OPENROUTER_API_KEY=
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
AI_ANALYST_MAX_TOKENS=1500
AI_ANALYST_RATE_LIMIT_PER_HOUR=20
AI_ANALYST_MAX_TOOL_ROUNDS=5

# ─── Fraud Detection Thresholds ───────────────────────────────────────────────
FRAUD_VELOCITY_THRESHOLD=5
FRAUD_VELOCITY_WINDOW_MIN=30
FRAUD_AMOUNT_SPIKE_MULTIPLIER=3.0
FRAUD_LOCATION_RADIUS_KM=200.0
FRAUD_DUPLICATE_WINDOW_MIN=5
BULK_UPLOAD_MAX_FRAUD_TASKS=2000

# ─── ML Model ─────────────────────────────────────────────────────────────────
ML_MODEL_DIR=backend/ml

# ─── Cache TTLs (seconds) ─────────────────────────────────────────────────────
CACHE_TTL_KPI=300
CACHE_TTL_REVENUE=900
CACHE_TTL_COHORT=3600
CACHE_TTL_MERCHANT=600
CACHE_TTL_SEGMENTATION=1800

# ─── Analytics Cache ──────────────────────────────────────────────────────────
ANALYTICS_CACHE_FRESHNESS_MINUTES=60
ANALYTICS_CACHE_STALE_TX_THRESHOLD=100
ANALYTICS_CACHE_IDEMPOTENCY_MINUTES=5
```

---

## After pulling new code from GitHub

When you pull updates from GitHub, run these commands to catch up:

```bash
# 1. Update Python dependencies (if requirements.txt changed)
cd backend
source .venv/bin/activate     # Mac/Linux
# .venv\Scripts\activate.bat  # Windows
pip install -r requirements.txt

# 2. Apply any new database migrations
alembic upgrade head

# 3. Update frontend packages (if package.json changed)
cd ../frontend
npm install

# 4. Restart backend and worker (Ctrl+C then rerun)
```

---

## Running tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

---

*Quantyx AI — Local Setup Guide*
*Last updated: April 2026*
