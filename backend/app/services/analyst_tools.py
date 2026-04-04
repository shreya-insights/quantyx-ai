"""Analyst tool registry for the AI Copilot.

Defines the JSON schemas that are sent to the LLM so it knows what tools
exist, and implements the secure execution layer that enforces company_id
isolation — the LLM can never override the tenant boundary regardless of
what it sends in tool_input.

All results are capped at MAX_TOOL_ROWS to stay within free-tier context
window limits.
"""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.analytics_repo import AnalyticsRepository
from app.repositories.fraud_repo import FraudRepository

logger = structlog.get_logger(__name__)

MAX_TOOL_ROWS = 200
_DEFAULT_MONTHS = 6
_DEFAULT_DAYS = 30
_DEFAULT_TOP_N = 20


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "get_revenue_trend",
        "description": (
            "Returns monthly revenue trend including inflow, outflow, net flow, "
            "transaction count, and month-over-month growth percentage. "
            "Use when asked about revenue over time, growth trends, or monthly performance."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "months": {
                    "type": "integer",
                    "description": "Number of months to look back (1-24). Default 6.",
                    "minimum": 1,
                    "maximum": 24,
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_fraud_summary",
        "description": (
            "Returns fraud alert statistics: total alerts, open vs resolved counts, "
            "severity breakdown (critical/high/medium/low), resolution rate, "
            "average resolution time, and a 7-day trend. "
            "Use when asked about fraud activity, risk levels, or alert status."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_top_merchants",
        "description": (
            "Returns top merchants ranked by revenue with transaction count, "
            "average transaction value, revenue share percentage, and category rank. "
            "Use when asked about best-performing merchants, merchant rankings, or category leaders."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Lookback window in days (1-365). Default 30.",
                    "minimum": 1,
                    "maximum": 365,
                },
                "top_n": {
                    "type": "integer",
                    "description": "Number of top merchants to return (1-50). Default 20.",
                    "minimum": 1,
                    "maximum": 50,
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_kpi_comparison",
        "description": (
            "Returns KPI summary for a specific date range: total transactions, "
            "total volume, inflow, outflow, unique customers, unique merchants, "
            "average transaction value, and active days. "
            "Use when asked about KPIs, performance for a specific period, or comparisons."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format.",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format.",
                },
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "get_category_breakdown",
        "description": (
            "Returns spending broken down by merchant category: total amount, "
            "transaction count, and percentage of total spend per category. "
            "Use when asked about spending patterns, category analysis, or where money is going."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Lookback window in days (1-365). Default 30.",
                    "minimum": 1,
                    "maximum": 365,
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_account_summary",
        "description": (
            "Returns daily net flow and running balance trend for a specific account. "
            "Use when asked about a specific account's balance history or cash flow over time."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "integer",
                    "description": "The numeric account ID to summarise.",
                },
                "days": {
                    "type": "integer",
                    "description": "Lookback window in days (1-365). Default 90.",
                    "minimum": 1,
                    "maximum": 365,
                },
            },
            "required": ["account_id"],
        },
    },
]


async def execute_tool(
    tool_name: str,
    tool_input: dict[str, Any],
    company_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    """Execute a named tool and return its result with row count.

    Security: company_id is ALWAYS sourced from the JWT-verified parameter.
    The LLM-controlled tool_input cannot override the tenant boundary under
    any circumstances — this function ignores any company_id in tool_input.
    """
    analytics = AnalyticsRepository(db)
    fraud = FraudRepository(db)

    try:
        if tool_name == "get_revenue_trend":
            months = int(tool_input.get("months", _DEFAULT_MONTHS))
            months = max(1, min(months, 24))
            rows = await analytics.get_revenue_trend(company_id, months)
            rows = rows[:MAX_TOOL_ROWS]
            return {"data": rows, "row_count": len(rows), "tool": tool_name}

        if tool_name == "get_fraud_summary":
            stats = await fraud.get_fraud_stats(company_id)
            return {"data": [stats], "row_count": 1, "tool": tool_name}

        if tool_name == "get_top_merchants":
            days = int(tool_input.get("days", _DEFAULT_DAYS))
            top_n = int(tool_input.get("top_n", _DEFAULT_TOP_N))
            days = max(1, min(days, 365))
            top_n = max(1, min(top_n, MAX_TOOL_ROWS))
            rows = await analytics.get_top_merchants(company_id, days, top_n)
            rows = rows[:MAX_TOOL_ROWS]
            return {"data": rows, "row_count": len(rows), "tool": tool_name}

        if tool_name == "get_kpi_comparison":
            start_date = str(tool_input.get("start_date", ""))
            end_date = str(tool_input.get("end_date", ""))
            if not start_date or not end_date:
                return {
                    "error": "start_date and end_date are required",
                    "data": [],
                    "row_count": 0,
                    "tool": tool_name,
                }
            kpi = await analytics.get_kpi_summary(company_id, start_date, end_date)
            return {"data": [kpi], "row_count": 1, "tool": tool_name}

        if tool_name == "get_category_breakdown":
            days = int(tool_input.get("days", _DEFAULT_DAYS))
            days = max(1, min(days, 365))
            rows = await analytics.get_spending_by_category(company_id, days)
            rows = rows[:MAX_TOOL_ROWS]
            return {"data": rows, "row_count": len(rows), "tool": tool_name}

        if tool_name == "get_account_summary":
            account_id = int(tool_input.get("account_id", 0))
            days = int(tool_input.get("days", 90))
            days = max(1, min(days, 365))
            if not account_id:
                return {
                    "error": "account_id is required",
                    "data": [],
                    "row_count": 0,
                    "tool": tool_name,
                }
            rows = await analytics.get_account_balance_trend(company_id, account_id, days)
            rows = rows[:MAX_TOOL_ROWS]
            return {"data": rows, "row_count": len(rows), "tool": tool_name}

        logger.warning("analyst_tools.unknown_tool", tool_name=tool_name)
        return {"error": "Unknown tool", "data": [], "row_count": 0, "tool": tool_name}

    except Exception as exc:
        logger.error(
            "analyst_tools.execute.error",
            tool_name=tool_name,
            company_id=company_id,
            error=str(exc),
        )
        return {
            "error": f"Tool execution failed: {str(exc)}",
            "data": [],
            "row_count": 0,
            "tool": tool_name,
        }
