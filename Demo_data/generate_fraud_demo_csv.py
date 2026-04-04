#!/usr/bin/env python3
"""
Regenerate quantyx_fraud_demo_transactions.csv for bulk upload + fraud/analytics demos.

Uses the last ~90 calendar days ending 2 days before *today* so amount-spike (90d debit avg)
and analytics windows stay meaningful. Requires account_id=1 for your tenant (seed or create
an account and adjust ACCOUNT_ID below).

Run: python Demo_data/generate_fraud_demo_csv.py
"""
from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from pathlib import Path

ACCOUNT_ID = 1
DEMO_SPAN_DAYS = 55


def main() -> None:
    out = Path(__file__).resolve().parent / "quantyx_fraud_demo_transactions.csv"
    end_day = date.today() - timedelta(days=2)
    start = datetime.combine(end_day - timedelta(days=DEMO_SPAN_DAYS - 1), datetime.min.time()).replace(
        hour=11, minute=0
    )

    rows: list[dict[str, str | float | int]] = []
    for i in range(DEMO_SPAN_DAYS):
        d = start + timedelta(days=i)
        debit_amt = round(88.0 + (i % 7) * 4.5, 2)
        rows.append(
            {
                "account_id": ACCOUNT_ID,
                "amount": debit_amt,
                "currency": "USD",
                "transaction_type": "debit",
                "status": "completed",
                "description": f"Coffee and retail — baseline day {i + 1}",
                "transaction_date": d.replace(hour=13, minute=5).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        if i % 4 == 0:
            rows.append(
                {
                    "account_id": ACCOUNT_ID,
                    "amount": round(3200 + i * 15, 2),
                    "currency": "USD",
                    "transaction_type": "credit",
                    "status": "completed",
                    "description": "Inbound ACH — payroll",
                    "transaction_date": d.replace(hour=9, minute=0).strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

    for nd in [8, 22, 35, 48]:
        d = start + timedelta(days=nd)
        rows.append(
            {
                "account_id": ACCOUNT_ID,
                "amount": 62.50,
                "currency": "USD",
                "transaction_type": "debit",
                "status": "completed",
                "description": "Unusual hour debit — demo night pattern",
                "transaction_date": d.replace(hour=3, minute=25).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    spike_date = start + timedelta(days=52)
    rows.append(
        {
            "account_id": ACCOUNT_ID,
            "amount": 4999.99,
            "currency": "USD",
            "transaction_type": "debit",
            "status": "completed",
            "description": "DEMO spike — high-value single debit",
            "transaction_date": spike_date.replace(hour=15, minute=42).strftime("%Y-%m-%d %H:%M:%S"),
        }
    )

    rows.sort(key=lambda r: str(r["transaction_date"]))

    fieldnames = [
        "account_id",
        "amount",
        "currency",
        "transaction_type",
        "status",
        "description",
        "transaction_date",
    ]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
