from datetime import date, timedelta
from io import BytesIO

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.core.dependencies import AnalystUser, DBSession
from app.services.analytics_service import AnalyticsService
from app.utils.cache import get_cache_manager

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/generate/csv")
async def download_kpi_csv(
    current_user: AnalystUser,
    db: DBSession,
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
):
    """Export KPI summary + revenue trend as CSV."""
    import csv
    import io

    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    cache = await get_cache_manager()
    service = AnalyticsService(db, cache)

    trend_result = await service.get_revenue_trend(current_user.company_id, months=12)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Month", "Inflow", "Outflow", "Net Flow", "Transactions", "MoM Growth %"])
    for point in trend_result.data.data:
        writer.writerow([
            point.month, point.inflow, point.outflow,
            point.net_flow, point.transaction_count,
            point.mom_growth_pct or ""
        ])

    output.seek(0)
    filename = f"quantyx_revenue_{start_date}_{end_date}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/generate/pdf")
async def download_kpi_pdf(
    current_user: AnalystUser,
    db: DBSession,
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
):
    """Export KPI summary as PDF report using ReportLab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    cache = await get_cache_manager()
    service = AnalyticsService(db, cache)
    kpi_result = await service.get_kpi_summary(current_user.company_id, start_date, end_date)
    kpi = kpi_result.data

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Quantyx AI — KPI Report", styles["Title"]))
    elements.append(Paragraph(f"Period: {start_date} to {end_date}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    table_data = [
        ["Metric", "Value"],
        ["Total Transactions", f"{kpi.total_transactions:,}"],
        ["Total Volume", f"${kpi.total_volume:,.2f}"],
        ["Total Inflow", f"${kpi.total_inflow:,.2f}"],
        ["Total Outflow", f"${kpi.total_outflow:,.2f}"],
        ["Unique Customers", f"{kpi.unique_customers:,}"],
        ["Avg Transaction Value", f"${kpi.avg_transaction_value:,.2f}"],
        ["Fraud Alert Count", f"{kpi.fraud_alert_count}"],
        ["Fraud Alert Rate", f"{kpi.fraud_alert_rate_pct:.4f}%"],
    ]

    table = Table(table_data, colWidths=[250, 200])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4ff")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    filename = f"quantyx_kpi_{start_date}_{end_date}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
