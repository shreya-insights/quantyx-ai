"""Single source of truth for fraud ML features — training and online serving.

The same computation paths MUST be used offline and online to avoid training-serving skew.
CRITICAL: FEATURE_COLUMNS order and keys must match feature_columns.json from training.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Final

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.feature_store import MerchantFeatures, UserFeatures, VelocityFeature
from app.models.merchant import Merchant
from app.models.transaction import Transaction

FEATURE_EPSILON: Final[float] = 1e-6
VELOCITY_WINDOWS_MINUTES: Final[tuple[int, ...]] = (15, 60, 1440)
NIGHT_HOUR_START: Final[int] = 2
NIGHT_HOUR_END: Final[int] = 5
WEEKEND_WEEKDAY: Final[frozenset[int]] = frozenset({5, 6})

# MCC / category codes commonly associated with higher chargeback risk (static allowlist, not user input).
HIGH_RISK_MERCHANT_CATEGORY_CODES: Final[frozenset[str]] = frozenset(
    {"7801", "7995", "4829", "6012"}
)

# CRITICAL: must match feature_columns.json saved during model training.
# Any change here requires retraining the model.
FEATURE_COLUMNS: Final[list[str]] = [
    "avg_amount_7d",
    "avg_amount_30d",
    "avg_amount_90d",
    "std_amount_30d",
    "tx_count_7d",
    "tx_count_30d",
    "velocity_15min",
    "velocity_60min",
    "unique_merchants_30d",
    "fraud_rate_30d",
    "merchant_fraud_rate",
    "amount",
    "amount_to_avg_ratio",
    "amount_zscore",
    "is_new_merchant",
    "is_night",
    "is_weekend",
    "hour_of_day",
    "day_of_week",
]

_USER_FEATURES_SQL = text("""
    SELECT
        AVG(CASE WHEN t.transaction_date >= NOW() - INTERVAL 7 DAY THEN t.amount END)
            AS avg_amount_7d,
        AVG(CASE WHEN t.transaction_date >= NOW() - INTERVAL 30 DAY THEN t.amount END)
            AS avg_amount_30d,
        AVG(CASE WHEN t.transaction_date >= NOW() - INTERVAL 90 DAY THEN t.amount END)
            AS avg_amount_90d,
        STDDEV(CASE WHEN t.transaction_date >= NOW() - INTERVAL 30 DAY THEN t.amount END)
            AS std_amount_30d,
        COUNT(CASE WHEN t.transaction_date >= NOW() - INTERVAL 7 DAY THEN 1 END)
            AS tx_count_7d,
        COUNT(CASE WHEN t.transaction_date >= NOW() - INTERVAL 30 DAY THEN 1 END)
            AS tx_count_30d,
        COUNT(CASE WHEN t.transaction_date >= NOW() - INTERVAL 1 HOUR THEN 1 END)
            AS tx_count_1h,
        COUNT(DISTINCT CASE WHEN t.transaction_date >= NOW() - INTERVAL 30 DAY
            THEN t.merchant_id END) AS unique_merchants_30d,
        COUNT(DISTINCT CASE WHEN t.transaction_date >= NOW() - INTERVAL 30 DAY
            THEN t.category_id END) AS unique_categories_30d,
        AVG(CASE
            WHEN t.transaction_date >= NOW() - INTERVAL 30 DAY AND EXISTS (
                SELECT 1 FROM fraud_alerts f
                WHERE f.transaction_id = t.id AND f.company_id = :company_id
            ) THEN 1.0 ELSE 0.0 END) AS fraud_rate_30d,
        (SELECT HOUR(t2.transaction_date)
         FROM transactions t2
         INNER JOIN accounts a2 ON t2.account_id = a2.id
         WHERE a2.user_id = :user_id AND a2.company_id = :company_id
           AND t2.company_id = :company_id
           AND t2.transaction_date >= NOW() - INTERVAL 30 DAY
         GROUP BY HOUR(t2.transaction_date)
         ORDER BY COUNT(*) DESC
         LIMIT 1) AS most_common_hour,
        (SELECT DAYOFWEEK(t2.transaction_date)
         FROM transactions t2
         INNER JOIN accounts a2 ON t2.account_id = a2.id
         WHERE a2.user_id = :user_id AND a2.company_id = :company_id
           AND t2.company_id = :company_id
           AND t2.transaction_date >= NOW() - INTERVAL 30 DAY
         GROUP BY DAYOFWEEK(t2.transaction_date)
         ORDER BY COUNT(*) DESC
         LIMIT 1) AS most_common_dow
    FROM transactions t
    WHERE t.account_id IN (
        SELECT id FROM accounts
        WHERE user_id = :user_id AND company_id = :company_id
    )
      AND t.company_id = :company_id
""")

_MERCHANT_FEATURES_SQL = text("""
    SELECT
        AVG(CASE WHEN t.transaction_date >= NOW() - INTERVAL 30 DAY THEN t.amount END)
            AS avg_amount,
        COUNT(CASE WHEN t.transaction_date >= NOW() - INTERVAL 30 DAY THEN 1 END)
            AS tx_count_30d,
        AVG(CASE
            WHEN t.transaction_date >= NOW() - INTERVAL 30 DAY AND EXISTS (
                SELECT 1 FROM fraud_alerts f
                WHERE f.transaction_id = t.id AND f.company_id = :company_id
            ) THEN 1.0 ELSE 0.0 END) AS fraud_rate_30d,
        COUNT(DISTINCT CASE WHEN t.transaction_date >= NOW() - INTERVAL 30 DAY
            THEN t.account_id END) AS unique_users_30d
    FROM transactions t
    WHERE t.merchant_id = :merchant_id
      AND t.company_id = :company_id
""")

_VELOCITY_SQL_TEMPLATE = """
    SELECT
        COUNT(*) AS tx_count,
        COALESCE(SUM(t.amount), 0) AS total_amount,
        COUNT(DISTINCT t.merchant_id) AS unique_merchants
    FROM transactions t
    WHERE t.account_id IN (
        SELECT id FROM accounts
        WHERE user_id = :user_id AND company_id = :company_id
    )
      AND t.company_id = :company_id
      AND t.transaction_date >= NOW() - INTERVAL {minutes} MINUTE
"""


def _f(v: Any) -> float:
    return 0.0 if v is None else float(v)


def _i(v: Any) -> int:
    return 0 if v is None else int(v)


def _merchant_high_risk(merchant: Merchant | None) -> bool:
    if merchant is None:
        return False
    if merchant.is_flagged:
        return True
    code = (merchant.category_code or "").strip()
    return code in HIGH_RISK_MERCHANT_CATEGORY_CODES


class FeatureEngineeringService:
    """Computes and persists feature rows; builds the online feature vector."""

    async def compute_user_features(
        self, user_id: int, company_id: int, db: AsyncSession
    ) -> None:
        """Aggregates user behavior in one query, then idempotent upsert."""
        result = await db.execute(
            _USER_FEATURES_SQL, {"user_id": user_id, "company_id": company_id}
        )
        row = result.mappings().first()
        payload = _user_row_to_payload(user_id, company_id, row)
        await _upsert_user_features(db, payload)
        await db.commit()

    async def compute_merchant_features(
        self, merchant_id: int, company_id: int, db: AsyncSession
    ) -> None:
        """Merchant-level aggregates for shared-risk signals."""
        result = await db.execute(
            _MERCHANT_FEATURES_SQL, {"merchant_id": merchant_id, "company_id": company_id}
        )
        agg = result.mappings().first()
        m_result = await db.execute(
            select(Merchant).where(
                Merchant.id == merchant_id, Merchant.company_id == company_id
            )
        )
        merchant = m_result.scalar_one_or_none()
        high_risk = _merchant_high_risk(merchant)
        payload = _merchant_row_to_payload(merchant_id, company_id, agg, high_risk)
        await _upsert_merchant_features(db, payload)
        await db.commit()

    async def compute_velocity_features(
        self, user_id: int, company_id: int, db: AsyncSession
    ) -> None:
        """Refreshes rolling-window velocity rows (15 / 60 / 1440 minutes)."""
        for minutes in VELOCITY_WINDOWS_MINUTES:
            sql = text(_VELOCITY_SQL_TEMPLATE.format(minutes=minutes))
            result = await db.execute(
                sql, {"user_id": user_id, "company_id": company_id}
            )
            r = result.mappings().first()
            payload = {
                "user_id": user_id,
                "company_id": company_id,
                "window_minutes": minutes,
                "tx_count": _i(r.get("tx_count") if r else None),
                "total_amount": _f(r.get("total_amount") if r else None),
                "unique_merchants": _i(r.get("unique_merchants") if r else None),
            }
            await _upsert_velocity(db, payload)
        await db.commit()

    async def get_features_for_transaction(
        self,
        account_id: int,
        merchant_id: int | None,
        amount: float,
        company_id: int,
        transaction_date: datetime,
        db: AsyncSession,
    ) -> dict[str, float]:
        """Flat feature dict for model input; keys match FEATURE_COLUMNS."""
        acc_result = await db.execute(
            select(Account).where(
                Account.id == account_id, Account.company_id == company_id
            )
        )
        account = acc_result.scalar_one_or_none()
        user_id = account.user_id if account else None

        uf: UserFeatures | None = None
        if user_id is not None:
            u_row = await db.execute(
                select(UserFeatures).where(
                    UserFeatures.user_id == user_id,
                    UserFeatures.company_id == company_id,
                )
            )
            uf = u_row.scalar_one_or_none()

        mf: MerchantFeatures | None = None
        if merchant_id is not None:
            m_row = await db.execute(
                select(MerchantFeatures).where(
                    MerchantFeatures.merchant_id == merchant_id,
                    MerchantFeatures.company_id == company_id,
                )
            )
            mf = m_row.scalar_one_or_none()

        vel_15, vel_60 = 0, 0
        if user_id is not None:
            vel_15 = await _velocity_count(db, user_id, company_id, 15)
            vel_60 = await _velocity_count(db, user_id, company_id, 60)

        avg30 = _f(uf.avg_amount_30d if uf else None)
        std30 = _f(uf.std_amount_30d if uf else None)
        ratio = amount / (avg30 + FEATURE_EPSILON)
        zscore = (amount - avg30) / (std30 + FEATURE_EPSILON)

        is_new_merchant = 0.0
        if user_id is not None and merchant_id is not None:
            had_before = await _user_had_merchant_before(
                db, user_id, company_id, merchant_id
            )
            is_new_merchant = 0.0 if had_before else 1.0

        hour = transaction_date.hour
        dow = transaction_date.weekday()
        is_night = 1.0 if NIGHT_HOUR_START <= hour <= NIGHT_HOUR_END else 0.0
        is_weekend = 1.0 if dow in WEEKEND_WEEKDAY else 0.0

        merchant_fraud = _f(mf.fraud_rate_30d if mf else None)

        out = {
            "avg_amount_7d": _f(uf.avg_amount_7d if uf else None),
            "avg_amount_30d": avg30,
            "avg_amount_90d": _f(uf.avg_amount_90d if uf else None),
            "std_amount_30d": std30,
            "tx_count_7d": float(_i(uf.tx_count_7d if uf else None)),
            "tx_count_30d": float(_i(uf.tx_count_30d if uf else None)),
            "velocity_15min": float(vel_15),
            "velocity_60min": float(vel_60),
            "unique_merchants_30d": float(_i(uf.unique_merchants_30d if uf else None)),
            "fraud_rate_30d": _f(uf.fraud_rate_30d if uf else None),
            "merchant_fraud_rate": merchant_fraud,
            "amount": float(amount),
            "amount_to_avg_ratio": ratio,
            "amount_zscore": zscore,
            "is_new_merchant": is_new_merchant,
            "is_night": is_night,
            "is_weekend": is_weekend,
            "hour_of_day": float(hour),
            "day_of_week": float(dow),
        }
        for key in FEATURE_COLUMNS:
            if key not in out:
                raise RuntimeError(f"feature key missing: {key}")
        return {k: float(out[k]) for k in FEATURE_COLUMNS}


def _user_row_to_payload(
    user_id: int, company_id: int, row: dict[str, Any] | None
) -> dict[str, Any]:
    if not row:
        row = {}
    mch = row.get("most_common_hour")
    mcd = row.get("most_common_dow")
    return {
        "user_id": user_id,
        "company_id": company_id,
        "avg_amount_7d": _f(row.get("avg_amount_7d")),
        "avg_amount_30d": _f(row.get("avg_amount_30d")),
        "avg_amount_90d": _f(row.get("avg_amount_90d")),
        "std_amount_30d": _f(row.get("std_amount_30d")),
        "tx_count_7d": _i(row.get("tx_count_7d")),
        "tx_count_30d": _i(row.get("tx_count_30d")),
        "tx_count_1h": _i(row.get("tx_count_1h")),
        "unique_merchants_30d": _i(row.get("unique_merchants_30d")),
        "unique_categories_30d": _i(row.get("unique_categories_30d")),
        "fraud_rate_30d": _f(row.get("fraud_rate_30d")),
        "most_common_hour": 12 if mch is None else int(mch),
        "most_common_dow": 1 if mcd is None else int(mcd),
        "version": 1,
    }


def _merchant_row_to_payload(
    merchant_id: int,
    company_id: int,
    row: dict[str, Any] | None,
    is_high_risk_category: bool,
) -> dict[str, Any]:
    if not row:
        row = {}
    return {
        "merchant_id": merchant_id,
        "company_id": company_id,
        "avg_amount": _f(row.get("avg_amount")),
        "tx_count_30d": _i(row.get("tx_count_30d")),
        "fraud_rate_30d": _f(row.get("fraud_rate_30d")),
        "unique_users_30d": _i(row.get("unique_users_30d")),
        "is_high_risk_category": is_high_risk_category,
    }


async def _upsert_user_features(db: AsyncSession, vals: dict[str, Any]) -> None:
    """Load-or-create upsert — works on MySQL and SQLite (tests)."""
    res = await db.execute(
        select(UserFeatures).where(
            UserFeatures.user_id == vals["user_id"],
            UserFeatures.company_id == vals["company_id"],
        )
    )
    row = res.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if row is None:
        db.add(
            UserFeatures(
                user_id=vals["user_id"],
                company_id=vals["company_id"],
                avg_amount_7d=vals["avg_amount_7d"],
                avg_amount_30d=vals["avg_amount_30d"],
                avg_amount_90d=vals["avg_amount_90d"],
                std_amount_30d=vals["std_amount_30d"],
                tx_count_7d=vals["tx_count_7d"],
                tx_count_30d=vals["tx_count_30d"],
                tx_count_1h=vals["tx_count_1h"],
                unique_merchants_30d=vals["unique_merchants_30d"],
                unique_categories_30d=vals["unique_categories_30d"],
                fraud_rate_30d=vals["fraud_rate_30d"],
                most_common_hour=vals["most_common_hour"],
                most_common_dow=vals["most_common_dow"],
                version=vals["version"],
                computed_at=now,
            )
        )
    else:
        row.avg_amount_7d = vals["avg_amount_7d"]
        row.avg_amount_30d = vals["avg_amount_30d"]
        row.avg_amount_90d = vals["avg_amount_90d"]
        row.std_amount_30d = vals["std_amount_30d"]
        row.tx_count_7d = vals["tx_count_7d"]
        row.tx_count_30d = vals["tx_count_30d"]
        row.tx_count_1h = vals["tx_count_1h"]
        row.unique_merchants_30d = vals["unique_merchants_30d"]
        row.unique_categories_30d = vals["unique_categories_30d"]
        row.fraud_rate_30d = vals["fraud_rate_30d"]
        row.most_common_hour = vals["most_common_hour"]
        row.most_common_dow = vals["most_common_dow"]
        row.version = vals["version"]
        row.computed_at = now


async def _upsert_merchant_features(db: AsyncSession, vals: dict[str, Any]) -> None:
    res = await db.execute(
        select(MerchantFeatures).where(
            MerchantFeatures.merchant_id == vals["merchant_id"],
            MerchantFeatures.company_id == vals["company_id"],
        )
    )
    row = res.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if row is None:
        db.add(
            MerchantFeatures(
                merchant_id=vals["merchant_id"],
                company_id=vals["company_id"],
                avg_amount=vals["avg_amount"],
                tx_count_30d=vals["tx_count_30d"],
                fraud_rate_30d=vals["fraud_rate_30d"],
                unique_users_30d=vals["unique_users_30d"],
                is_high_risk_category=vals["is_high_risk_category"],
                computed_at=now,
            )
        )
    else:
        row.avg_amount = vals["avg_amount"]
        row.tx_count_30d = vals["tx_count_30d"]
        row.fraud_rate_30d = vals["fraud_rate_30d"]
        row.unique_users_30d = vals["unique_users_30d"]
        row.is_high_risk_category = vals["is_high_risk_category"]
        row.computed_at = now


async def _upsert_velocity(db: AsyncSession, vals: dict[str, Any]) -> None:
    res = await db.execute(
        select(VelocityFeature).where(
            VelocityFeature.user_id == vals["user_id"],
            VelocityFeature.company_id == vals["company_id"],
            VelocityFeature.window_minutes == vals["window_minutes"],
        )
    )
    row = res.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if row is None:
        db.add(
            VelocityFeature(
                user_id=vals["user_id"],
                company_id=vals["company_id"],
                window_minutes=vals["window_minutes"],
                tx_count=vals["tx_count"],
                total_amount=vals["total_amount"],
                unique_merchants=vals["unique_merchants"],
                computed_at=now,
            )
        )
    else:
        row.tx_count = vals["tx_count"]
        row.total_amount = vals["total_amount"]
        row.unique_merchants = vals["unique_merchants"]
        row.computed_at = now


async def _velocity_count(
    db: AsyncSession, user_id: int, company_id: int, window_minutes: int
) -> int:
    result = await db.execute(
        select(VelocityFeature.tx_count).where(
            VelocityFeature.user_id == user_id,
            VelocityFeature.company_id == company_id,
            VelocityFeature.window_minutes == window_minutes,
        )
    )
    v = result.scalar_one_or_none()
    return _i(v)


async def _user_had_merchant_before(
    db: AsyncSession,
    user_id: int,
    company_id: int,
    merchant_id: int,
) -> bool:
    subq = select(Account.id).where(
        Account.user_id == user_id, Account.company_id == company_id
    )
    q = (
        select(Transaction.id)
        .where(
            Transaction.company_id == company_id,
            Transaction.merchant_id == merchant_id,
            Transaction.account_id.in_(subq),
        )
        .limit(1)
    )
    result = await db.execute(q)
    return result.scalar_one_or_none() is not None
