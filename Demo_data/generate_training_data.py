#!/usr/bin/env python3
"""
ML Training Data Generator — creates a labelled bulk-upload CSV for the fraud model.

Design:
  - 3 accounts (ids 1, 2, 3) × 180 days of transactions = rich feature history
  - Amount spikes deliberately crafted at 12-18× the 90-day debit average
    so they survive average-contamination from simultaneous bulk insert and
    still hit CRITICAL severity (> 10× multiplier threshold).
  - Spread: 70% baseline in days 91-180 (outside 90-day window),
            30% baseline inside 90-day window, spikes only inside 90-day window.
  - Night-pattern debits (02:00-04:30) included for LOW-severity coverage.
  - unique transaction_ref via UUID4 to avoid collisions with existing rows.

Usage:
    python Demo_data/generate_training_data.py
    # → writes Demo_data/quantyx_fraud_training_data.csv
"""
from __future__ import annotations

import csv
import random
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

RANDOM_SEED: int = 42
random.seed(RANDOM_SEED)

OUT_PATH = Path(__file__).resolve().parent / "quantyx_fraud_training_data.csv"

FIELDNAMES = [
    "account_id",
    "amount",
    "currency",
    "transaction_type",
    "status",
    "description",
    "transaction_date",
    "transaction_ref",
]

# Account ids that exist in the seeded DB.
# id=1 already has baseline history — we add more for the other two.
ACCOUNTS = [
    {"id": 2, "type": "savings",  "baseline_lo": 220.0, "baseline_hi": 420.0, "spike_amount": 14000.0},
    {"id": 3, "type": "credit",   "baseline_lo":  55.0, "baseline_hi": 155.0, "spike_amount":  4500.0},
]

# Days of history to generate
HISTORY_DAYS: int = 180
# How far back the 90-day window starts (transactions older than this do NOT
# affect the rolling average at the time the Celery task runs)
ROLLING_WINDOW_DAYS: int = 90

# Spike parameters — placed inside the 90-day window
SPIKES_PER_ACCOUNT: int = 18

# Night pattern rows per account (LOW severity — enrich feature space)
NIGHT_ROWS_PER_ACCOUNT: int = 25


def _ts(day_offset: int, hour: int, minute: int) -> str:
    """Return ISO datetime string for today - day_offset at given hour:minute."""
    d = date.today() - timedelta(days=day_offset)
    return datetime.combine(d, datetime.min.time()).replace(
        hour=hour, minute=minute, second=0
    ).strftime("%Y-%m-%d %H:%M:%S")


def _ref() -> str:
    return f"TRN-{uuid.uuid4().hex[:16].upper()}"


def build_rows() -> list[dict]:
    rows: list[dict] = []

    for acc in ACCOUNTS:
        acc_id = acc["id"]
        lo = acc["baseline_lo"]
        hi = acc["baseline_hi"]
        spike_amt = acc["spike_amount"]

        # ── Baseline: days 91-180 (2 transactions per day, 180 rows) ──────────
        for day in range(HISTORY_DAYS, ROLLING_WINDOW_DAYS, -1):
            amount = round(random.uniform(lo, hi), 2)
            rows.append({
                "account_id": acc_id,
                "amount": amount,
                "currency": "USD",
                "transaction_type": "debit",
                "status": "completed",
                "description": f"Routine debit — baseline day {HISTORY_DAYS - day + 1}",
                "transaction_date": _ts(day, random.randint(9, 17), random.randint(0, 59)),
                "transaction_ref": _ref(),
            })
            # Second transaction same day
            rows.append({
                "account_id": acc_id,
                "amount": round(random.uniform(lo * 0.4, lo * 0.8), 2),
                "currency": "USD",
                "transaction_type": "debit",
                "status": "completed",
                "description": "Small routine debit",
                "transaction_date": _ts(day, random.randint(18, 20), random.randint(0, 59)),
                "transaction_ref": _ref(),
            })

        # ── Baseline: days 3-90 (3 transactions per day, 264 rows) ───────────
        for day in range(ROLLING_WINDOW_DAYS, 3, -1):
            for slot in range(3):
                amount = round(random.uniform(lo, hi), 2)
                hour = [10, 13, 16][slot]
                rows.append({
                    "account_id": acc_id,
                    "amount": amount,
                    "currency": "USD",
                    "transaction_type": "debit",
                    "status": "completed",
                    "description": f"Routine debit slot {slot + 1}",
                    "transaction_date": _ts(day, hour, random.randint(0, 59)),
                    "transaction_ref": _ref(),
                })

        # ── Amount spikes inside 90-day window (HIGH / CRITICAL labels) ───────
        spike_days = random.sample(range(3, ROLLING_WINDOW_DAYS - 2), SPIKES_PER_ACCOUNT)
        for day in spike_days:
            # Vary spike amount slightly so model sees distribution
            amount = round(spike_amt * random.uniform(0.9, 1.2), 2)
            rows.append({
                "account_id": acc_id,
                "amount": amount,
                "currency": "USD",
                "transaction_type": "debit",
                "status": "completed",
                "description": f"Fraud signal — anomalous high-value debit",
                "transaction_date": _ts(day, random.randint(14, 22), random.randint(0, 59)),
                "transaction_ref": _ref(),
            })

        # ── Night pattern rows inside 90-day window (LOW labels, feature ──────
        # ── diversity for is_night feature) ──────────────────────────────────
        night_days = random.sample(range(3, ROLLING_WINDOW_DAYS - 2), NIGHT_ROWS_PER_ACCOUNT)
        for day in night_days:
            amount = round(random.uniform(lo * 0.5, lo), 2)
            rows.append({
                "account_id": acc_id,
                "amount": amount,
                "currency": "USD",
                "transaction_type": "debit",
                "status": "completed",
                "description": "Unusual hour debit — night pattern demo",
                "transaction_date": _ts(day, random.randint(2, 4), random.randint(0, 59)),
                "transaction_ref": _ref(),
            })

        # ── Periodic payroll credits (enrich credit-side feature space) ───────
        for week in range(0, HISTORY_DAYS // 7):
            day = week * 7 + 3
            if day >= HISTORY_DAYS:
                continue
            rows.append({
                "account_id": acc_id,
                "amount": round(random.uniform(2800, 3500), 2),
                "currency": "USD",
                "transaction_type": "credit",
                "status": "completed",
                "description": "Inbound ACH — payroll",
                "transaction_date": _ts(day, 9, 0),
                "transaction_ref": _ref(),
            })

    rows.sort(key=lambda r: r["transaction_date"])
    return rows


def main() -> None:
    rows = build_rows()
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    spikes = sum(1 for r in rows if "anomalous" in str(r["description"]))
    nights = sum(1 for r in rows if "night pattern" in str(r["description"]).lower())
    print(f"Wrote {total} rows to {OUT_PATH}")
    print(f"  Amount spikes : {spikes} rows (→ HIGH/CRITICAL labels after rule analysis)")
    print(f"  Night patterns: {nights} rows (→ LOW labels)")
    print(f"  Normal baseline: {total - spikes - nights} rows")
    print(f"  Expected fraud rate after ingestion: ~{spikes / total * 100:.1f}%")


if __name__ == "__main__":
    main()
