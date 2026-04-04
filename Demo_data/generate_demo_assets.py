#!/usr/bin/env python3
"""Generate Quantyx demo transaction files (CSV, XLSX, PDF) for QA and demos.

Run: backend/.venv/bin/python Demo_data/generate_demo_assets.py

Single source generates CSV, XLSX, and PDF so formats stay aligned.
"""
from __future__ import annotations

import csv
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
ACCOUNTS = (1, 2, 3)
BASE = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def _row(
    account_id: int,
    amount: float,
    currency: str,
    tx_type: str,
    status: str,
    description: str,
    when: datetime,
) -> dict[str, str]:
    return {
        "account_id": str(account_id),
        "amount": f"{amount:.2f}",
        "currency": currency,
        "transaction_type": tx_type,
        "status": status,
        "description": description,
        "transaction_date": when.strftime("%Y-%m-%d %H:%M:%S"),
    }


def _baseline_history_rows() -> list[dict[str, str]]:
    """Debit/credit history so 90-day average exists for amount-spike scenarios."""
    out: list[dict[str, str]] = []
    for i in range(24):
        d = BASE + timedelta(days=i * 3)
        out.append(
            _row(
                1,
                1200.0 + (i % 5) * 100,
                "USD",
                "debit",
                "completed",
                f"Grocery debit baseline {i}",
                d,
            )
        )
    for i in range(12):
        out.append(
            _row(
                1,
                4500.0,
                "USD",
                "credit",
                "completed",
                f"Payroll credit {i}",
                BASE + timedelta(days=i * 5, hours=2),
            )
        )
    return out


def _type_status_currency_rows() -> list[dict[str, str]]:
    """All transaction_type and status enum values; multi-currency samples."""
    return [
        _row(2, 250.0, "EUR", "debit", "completed", "Coffee shop — EUR", BASE + timedelta(days=2)),
        _row(2, 800.0, "EUR", "credit", "completed", "Cashback — EUR", BASE + timedelta(days=3)),
        _row(2, 300.0, "GBP", "transfer", "completed", "Internal transfer", BASE + timedelta(days=4)),
        _row(3, 99.99, "USD", "refund", "completed", "Partial refund", BASE + timedelta(days=5)),
        _row(1, 75.0, "USD", "debit", "pending", "ACH pending", BASE + timedelta(days=60)),
        _row(1, 88.0, "USD", "debit", "failed", "Card declined", BASE + timedelta(days=61)),
        _row(2, 400.0, "USD", "debit", "reversed", "Chargeback reversed", BASE + timedelta(days=62)),
    ]


def _fraud_heuristic_rows() -> list[dict[str, str]]:
    """Night debit, velocity burst, and large debit for rule-based demos."""
    night = datetime(2026, 3, 20, 3, 15, 0, tzinfo=timezone.utc)
    v_base = datetime(2026, 3, 28, 14, 0, 0, tzinfo=timezone.utc)
    out = [
        _row(
            1,
            199.0,
            "USD",
            "debit",
            "completed",
            "Night window debit (02–05 UTC)",
            night,
        )
    ]
    for j in range(6):
        out.append(
            _row(
                1,
                25.0 + j,
                "USD",
                "debit",
                "completed",
                f"Velocity micro-payment {j + 1}/6",
                v_base + timedelta(minutes=j * 4),
            )
        )
    out.append(
        _row(
            1,
            125000.0,
            "USD",
            "debit",
            "completed",
            "Large debit vs 90d average",
            datetime(2026, 3, 30, 16, 10, 0, tzinfo=timezone.utc),
        )
    )
    return out


def _analytics_spread_rows() -> list[dict[str, str]]:
    """Extra INR volume for dashboards and date-range filters."""
    out: list[dict[str, str]] = []
    start = datetime(2026, 4, 1, 11, 30, 0, tzinfo=timezone.utc)
    for k in range(8):
        when = start + timedelta(days=k)
        aid = ACCOUNTS[k % 3]
        out.append(
            _row(
                aid,
                500.0 + k * 200,
                "INR",
                "debit",
                "completed",
                f"Retail analytics row {k}",
                when,
            )
        )
    return out


def _rows_main() -> list[dict[str, str]]:
    parts = [
        _baseline_history_rows(),
        _type_status_currency_rows(),
        _fraud_heuristic_rows(),
        _analytics_spread_rows(),
    ]
    return [r for block in parts for r in block]


def _rows_validation_errors() -> list[dict[str, str]]:
    return [
        {
            "account_id": "1",
            "amount": "-50.00",
            "currency": "USD",
            "transaction_type": "debit",
            "status": "completed",
            "description": "Invalid negative amount",
            "transaction_date": "2026-04-02 10:00:00",
        },
        {
            "account_id": "1",
            "amount": "100.00",
            "currency": "USD",
            "transaction_type": "not_a_real_type",
            "status": "completed",
            "description": "Invalid transaction_type",
            "transaction_date": "2026-04-02 10:05:00",
        },
        {
            "account_id": "1",
            "amount": "100.00",
            "currency": "USD",
            "transaction_type": "debit",
            "status": "completed",
            "description": "Bad date",
            "transaction_date": "not-a-date",
        },
    ]


def write_csv(path: Path, data: Iterable[dict[str, str]]) -> None:
    rows = list(data)
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def write_xlsx(path: Path, main_rows: list[dict[str, str]]) -> None:
    import pandas as pd

    df = pd.DataFrame(main_rows)
    instructions = pd.DataFrame(
        {
            "Topic": [
                "API bulk upload",
                "Required columns",
                "account_id",
                "Fraud analysis",
                "This workbook",
            ],
            "Detail": [
                "POST /api/v1/transactions/bulk-upload accepts .csv only.",
                "account_id, amount, currency, transaction_type, transaction_date",
                "Must exist in your tenant (create accounts first).",
                "Bulk CSV insert does not enqueue Celery fraud by default; use single POST "
                "/api/v1/transactions for async fraud/ML.",
                "Export sheet Transactions as CSV (UTF-8) for upload.",
            ],
        }
    )
    with pd.ExcelWriter(path, engine="openpyxl") as xl:
        df.to_excel(xl, sheet_name="Transactions", index=False)
        instructions.to_excel(xl, sheet_name="Instructions", index=False)


def write_pdf(path: Path, main_rows: list[dict[str, str]]) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    body = (
        "Companion files: quantyx_demo_full_suite.csv, quantyx_demo_full_suite.xlsx, "
        "demo_upload_validation_errors.csv. "
        "Exercises list filters, bulk upload, and analytics. "
        "Use API-created transactions for async fraud/ML on each row."
    )
    story = [
        Paragraph("<b>Quantyx AI — Demo transaction dataset</b>", styles["Title"]),
        Spacer(1, 12),
        Paragraph(body, styles["BodyText"]),
        Spacer(1, 12),
        Paragraph("<b>Required CSV columns</b>", styles["Heading2"]),
        Paragraph(
            "account_id, amount, currency, transaction_type, transaction_date. "
            "Optional: status, description, merchant_id, category_id.",
            styles["BodyText"],
        ),
        Spacer(1, 12),
        Paragraph("<b>Coverage</b>", styles["BodyText"]),
        Paragraph(
            "Types debit/credit/transfer/refund; statuses pending/completed/failed/reversed; "
            "USD, EUR, GBP, INR; velocity, night-hour, and spike-friendly rows.",
            styles["BodyText"],
        ),
        Spacer(1, 18),
        Paragraph("<b>Sample (first 12 rows)</b>", styles["Heading2"]),
    ]
    sample = main_rows[:12]
    hdr = list(sample[0].keys())
    tbl = Table([hdr] + [[r[c] for c in hdr] for r in sample], repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ]
        )
    )
    story.append(tbl)
    SimpleDocTemplate(str(path), pagesize=letter).build(story)


def main() -> None:
    main_rows = _rows_main()
    write_csv(OUT_DIR / "quantyx_demo_full_suite.csv", main_rows)
    write_csv(OUT_DIR / "demo_upload_validation_errors.csv", _rows_validation_errors())
    write_xlsx(OUT_DIR / "quantyx_demo_full_suite.xlsx", main_rows)
    write_pdf(OUT_DIR / "quantyx_demo_dataset_guide.pdf", main_rows)
    print(f"Wrote {len(main_rows)} rows to quantyx_demo_full_suite.csv and .xlsx")
    print("Wrote demo_upload_validation_errors.csv")
    print("Wrote quantyx_demo_dataset_guide.pdf")


if __name__ == "__main__":
    main()
