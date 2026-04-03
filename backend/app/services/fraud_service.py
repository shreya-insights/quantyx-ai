"""
Fraud Detection Service — Rule-based engine with 5 detection rules.

Rules:
  1. Velocity Rule     — >N transactions from same account in M minutes
  2. Amount Spike Rule — Amount > K× the account's 90-day rolling average
  3. Location Anomaly  — New location outside R km radius within 2 hours
  4. Duplicate Rule    — Same amount + merchant within M minutes
  5. Night Pattern     — Debit transactions between 2 AM–5 AM
"""
import math
from datetime import datetime, timezone

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.fraud_alert import AlertSeverity, AlertType, FraudAlert
from app.models.transaction import Transaction
from app.repositories.fraud_repo import FraudRepository
from app.repositories.transaction_repo import TransactionRepository

logger = structlog.get_logger()


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance in km between two lat/lng points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class FraudDetectionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.fraud_repo = FraudRepository(session)
        self.tx_repo = TransactionRepository(session)

    async def analyze_transaction(self, transaction: Transaction) -> list[FraudAlert]:
        """Run all fraud rules against a newly created transaction."""
        alerts: list[FraudAlert] = []

        results = await self._run_velocity_rule(transaction)
        alerts.extend(results)

        results = await self._run_amount_spike_rule(transaction)
        alerts.extend(results)

        results = await self._run_location_anomaly_rule(transaction)
        alerts.extend(results)

        results = await self._run_duplicate_rule(transaction)
        alerts.extend(results)

        results = await self._run_night_pattern_rule(transaction)
        alerts.extend(results)

        if alerts:
            self.session.add_all(alerts)
            await self.session.flush()
            logger.info(
                "fraud_alerts_created",
                transaction_id=transaction.id,
                alert_count=len(alerts),
            )

        return alerts

    async def _run_velocity_rule(self, tx: Transaction) -> list[FraudAlert]:
        count = await self.fraud_repo.check_velocity(
            tx.company_id,
            tx.account_id,
            settings.FRAUD_VELOCITY_THRESHOLD,
            settings.FRAUD_VELOCITY_WINDOW_MIN,
        )
        if count >= settings.FRAUD_VELOCITY_THRESHOLD:
            confidence = min(0.95, 0.5 + (count - settings.FRAUD_VELOCITY_THRESHOLD) * 0.05)
            severity = AlertSeverity.HIGH if count >= 10 else AlertSeverity.MEDIUM
            return [
                FraudAlert(
                    company_id=tx.company_id,
                    transaction_id=tx.id,
                    alert_type=AlertType.VELOCITY_BREACH,
                    severity=severity,
                    confidence_score=round(confidence * 100, 2),
                    description=(
                        f"Account made {count} transactions in the last "
                        f"{settings.FRAUD_VELOCITY_WINDOW_MIN} minutes "
                        f"(threshold: {settings.FRAUD_VELOCITY_THRESHOLD})"
                    ),
                    rule_metadata=f"count={count},threshold={settings.FRAUD_VELOCITY_THRESHOLD}",
                )
            ]
        return []

    async def _run_amount_spike_rule(self, tx: Transaction) -> list[FraudAlert]:
        if tx.transaction_type.value != "debit":
            return []

        avg = await self.tx_repo.get_account_recent_avg(tx.account_id, days=90)
        if avg is None or avg <= 0:
            return []

        multiplier = float(tx.amount) / avg
        if multiplier > settings.FRAUD_AMOUNT_SPIKE_MULTIPLIER:
            severity = AlertSeverity.CRITICAL if multiplier > 10 else AlertSeverity.HIGH
            confidence = min(99.0, 50.0 + multiplier * 3)
            return [
                FraudAlert(
                    company_id=tx.company_id,
                    transaction_id=tx.id,
                    alert_type=AlertType.UNUSUAL_AMOUNT,
                    severity=severity,
                    confidence_score=round(confidence, 2),
                    description=(
                        f"Transaction amount ${float(tx.amount):.2f} is {multiplier:.1f}× "
                        f"the 90-day average of ${avg:.2f}"
                    ),
                    rule_metadata=f"amount={tx.amount},avg={avg:.2f},multiplier={multiplier:.2f}",
                )
            ]
        return []

    async def _run_location_anomaly_rule(self, tx: Transaction) -> list[FraudAlert]:
        if not tx.location_lat or not tx.location_lng:
            return []

        recent = await self.tx_repo.get_recent_location(tx.account_id, hours=2)
        if not recent:
            return []

        prev_lat, prev_lng = recent
        dist_km = _haversine_km(prev_lat, prev_lng, float(tx.location_lat), float(tx.location_lng))

        if dist_km > settings.FRAUD_LOCATION_RADIUS_KM:
            return [
                FraudAlert(
                    company_id=tx.company_id,
                    transaction_id=tx.id,
                    alert_type=AlertType.LOCATION_ANOMALY,
                    severity=AlertSeverity.HIGH,
                    confidence_score=min(99.0, round(dist_km / 10, 2)),
                    description=(
                        f"Transaction location is {dist_km:.0f}km from previous location "
                        f"within 2 hours (threshold: {settings.FRAUD_LOCATION_RADIUS_KM}km)"
                    ),
                    rule_metadata=f"dist_km={dist_km:.1f},lat={tx.location_lat},lng={tx.location_lng}",
                )
            ]
        return []

    async def _run_duplicate_rule(self, tx: Transaction) -> list[FraudAlert]:
        is_dup = await self.fraud_repo.check_duplicate(
            tx.company_id,
            tx.account_id,
            float(tx.amount),
            tx.merchant_id,
            settings.FRAUD_DUPLICATE_WINDOW_MIN,
        )
        if is_dup:
            return [
                FraudAlert(
                    company_id=tx.company_id,
                    transaction_id=tx.id,
                    alert_type=AlertType.DUPLICATE_TRANSACTION,
                    severity=AlertSeverity.MEDIUM,
                    confidence_score=90.0,
                    description=(
                        f"Duplicate transaction detected: same amount ${float(tx.amount):.2f} "
                        f"at same merchant within {settings.FRAUD_DUPLICATE_WINDOW_MIN} minutes"
                    ),
                    rule_metadata=f"amount={tx.amount},merchant_id={tx.merchant_id}",
                )
            ]
        return []

    async def _run_night_pattern_rule(self, tx: Transaction) -> list[FraudAlert]:
        if tx.transaction_type.value != "debit":
            return []
        tx_hour = tx.transaction_date.hour
        if 2 <= tx_hour <= 5:
            return [
                FraudAlert(
                    company_id=tx.company_id,
                    transaction_id=tx.id,
                    alert_type=AlertType.NIGHT_PATTERN,
                    severity=AlertSeverity.LOW,
                    confidence_score=60.0,
                    description=(
                        f"Debit transaction at unusual hour: {tx_hour:02d}:00 "
                        f"(flagged window: 02:00–05:00)"
                    ),
                    rule_metadata=f"hour={tx_hour}",
                )
            ]
        return []

    async def resolve_alert(
        self, alert_id: int, company_id: int, resolved_by: int, note: str | None = None
    ) -> FraudAlert:
        alert = await self.fraud_repo.get_by_id(alert_id)
        if not alert or alert.company_id != company_id:
            from app.core.exceptions import NotFoundError
            raise NotFoundError("Fraud alert")

        alert.is_resolved = True
        alert.resolved_by = resolved_by
        alert.resolved_at = datetime.now(timezone.utc)
        if note:
            alert.description = (alert.description or "") + f"\n[Resolution note: {note}]"
        await self.session.flush()
        return alert
