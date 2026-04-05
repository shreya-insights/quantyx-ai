"""
Fraud Model Training Script — run offline or via CI.

Usage (from backend/ directory):
    python -m ml.train_fraud_model

Outputs:
    backend/ml/fraud_model.pkl       — XGBoost model artifact
    backend/ml/feature_columns.json  — serving contract (threshold, feature order, metadata)

Design decisions:
    XGBoost over LightGBM: tighter SHAP integration, Stripe's default for tabular fraud.
    scale_pos_weight: correct for 1:500 imbalance — no SMOTE, no synthetic fraud data.
    eval_metric="aucpr": AUC-PR is correct for imbalanced datasets. AUC-ROC is misleading
        at 0.2% fraud rate; Stripe's team uses AUC-PR as primary metric.
    Threshold tuning: maximize F1 on validation (not default 0.5 probability cutoff).
    Fixed seed: reproducible experiments — Google ML standard.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sqlalchemy import create_engine
from xgboost import XGBClassifier

from app.core.config import settings
from app.services.feature_engineering import FEATURE_COLUMNS

RANDOM_SEED: int = 42
TEST_SIZE: float = 0.2
PSI_BASELINE_MIN_SAMPLES: int = 30
EARLY_STOPPING_ROUNDS: int = 30
N_ESTIMATORS: int = 300
MAX_DEPTH: int = 6
LEARNING_RATE: float = 0.05
SUBSAMPLE: float = 0.8
COLSAMPLE_BYTREE: float = 0.8
THRESHOLD_MIN: float = 0.30
THRESHOLD_MAX: float = 0.90
THRESHOLD_STEP: float = 0.01
TRAINING_LOOKBACK_DAYS: int = 180

np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

_TRAINING_QUERY = f"""
SELECT
    t.id,
    t.amount,
    t.transaction_date,
    t.account_id,
    t.merchant_id,
    t.company_id,
    COALESCE(uf.avg_amount_7d, 0)          AS avg_amount_7d,
    COALESCE(uf.avg_amount_30d, 0)         AS avg_amount_30d,
    COALESCE(uf.avg_amount_90d, 0)         AS avg_amount_90d,
    COALESCE(uf.std_amount_30d, 0)         AS std_amount_30d,
    COALESCE(uf.tx_count_7d, 0)            AS tx_count_7d,
    COALESCE(uf.tx_count_30d, 0)           AS tx_count_30d,
    COALESCE(uf.unique_merchants_30d, 0)   AS unique_merchants_30d,
    COALESCE(uf.fraud_rate_30d, 0)         AS fraud_rate_30d,
    COALESCE(mf.fraud_rate_30d, 0)         AS merchant_fraud_rate,
    HOUR(t.transaction_date)               AS hour_of_day,
    DAYOFWEEK(t.transaction_date)          AS day_of_week,
    CASE WHEN HOUR(t.transaction_date) BETWEEN 2 AND 5 THEN 1 ELSE 0 END AS is_night,
    CASE WHEN DAYOFWEEK(t.transaction_date) IN (1,7)   THEN 1 ELSE 0 END AS is_weekend,
    COALESCE(fa_flag.severity, 'none')     AS fraud_label
FROM transactions t
LEFT JOIN accounts a
       ON a.id = t.account_id
LEFT JOIN user_features uf
       ON uf.user_id = a.user_id
      AND uf.company_id = t.company_id
LEFT JOIN merchant_features mf
       ON mf.merchant_id = t.merchant_id
      AND mf.company_id = t.company_id
LEFT JOIN (
    SELECT transaction_id, MIN(severity) AS severity
    FROM fraud_alerts
    WHERE severity IN ('high', 'critical')
      AND alert_type != 'ml_fraud_score'
    GROUP BY transaction_id
) fa_flag ON fa_flag.transaction_id = t.id
WHERE t.transaction_date >= NOW() - INTERVAL {TRAINING_LOOKBACK_DAYS} DAY
"""

_VELOCITY_QUERY = """
SELECT
    t.id                    AS transaction_id,
    COALESCE(v15.tx_count, 0) AS velocity_15min,
    COALESCE(v60.tx_count, 0) AS velocity_60min
FROM transactions t
LEFT JOIN accounts a ON a.id = t.account_id
LEFT JOIN velocity_features v15
       ON v15.user_id = a.user_id
      AND v15.company_id = t.company_id
      AND v15.window_minutes = 15
LEFT JOIN velocity_features v60
       ON v60.user_id = a.user_id
      AND v60.company_id = t.company_id
      AND v60.window_minutes = 60
"""

_MERCHANT_HISTORY_QUERY = """
SELECT
    t.id AS transaction_id,
    CASE WHEN EXISTS (
        SELECT 1 FROM transactions t2
        INNER JOIN accounts a2 ON a2.id = t2.account_id
        WHERE a2.user_id = (SELECT user_id FROM accounts WHERE id = t.account_id)
          AND t2.merchant_id = t.merchant_id
          AND t2.id < t.id
    ) THEN 0 ELSE 1 END AS is_new_merchant
FROM transactions t
"""


def _load_training_data(engine) -> tuple[pd.DataFrame, pd.Series]:
    """Join all feature tables into a single labeled dataset."""
    df = pd.read_sql(_TRAINING_QUERY, engine)
    vel = pd.read_sql(_VELOCITY_QUERY, engine).set_index("transaction_id")
    merch = pd.read_sql(_MERCHANT_HISTORY_QUERY, engine).set_index("transaction_id")

    df = df.set_index("id")
    df["velocity_15min"] = df.index.map(vel["velocity_15min"]).fillna(0)
    df["velocity_60min"] = df.index.map(vel["velocity_60min"]).fillna(0)
    df["is_new_merchant"] = df.index.map(merch["is_new_merchant"]).fillna(0)

    epsilon = 1e-6
    df["amount_to_avg_ratio"] = df["amount"] / (df["avg_amount_30d"] + epsilon)
    df["amount_zscore"] = (df["amount"] - df["avg_amount_30d"]) / (df["std_amount_30d"] + epsilon)

    y = (df["fraud_label"] != "none").astype(int)
    print(f"Dataset: {len(df)} samples, {y.sum()} fraud ({y.mean() * 100:.3f}%)")
    return df[FEATURE_COLUMNS].fillna(0), y


def _build_feature_psi_baselines(
    df: pd.DataFrame, feature_names: list[str]
) -> dict[str, dict]:
    """Training histogram per feature — reference percents for production PSI."""
    baselines: dict[str, dict] = {}
    for col in feature_names:
        s = df[col].astype(float).replace([np.inf, -np.inf], np.nan).dropna()
        if len(s) < PSI_BASELINE_MIN_SAMPLES:
            continue
        edges = np.quantile(s, np.linspace(0.0, 1.0, 11)).astype(float)
        counts, _ = np.histogram(s, bins=edges)
        total = float(counts.sum())
        if total <= 0:
            continue
        baselines[col] = {
            "bin_edges": edges.tolist(),
            "expected_pct": (counts.astype(float) / total).tolist(),
        }
    return baselines


def _tune_threshold(
    model: XGBClassifier, X_val: pd.DataFrame, y_val: pd.Series
) -> tuple[float, float]:
    """Scan threshold range, return (best_threshold, best_f1)."""
    probs = model.predict_proba(X_val)[:, 1]
    best_f1, best_threshold = 0.0, 0.5
    thresholds = np.arange(THRESHOLD_MIN, THRESHOLD_MAX, THRESHOLD_STEP)
    for t in thresholds:
        preds = (probs >= t).astype(int)
        _, _, f1, _ = precision_recall_fscore_support(
            y_val, preds, average="binary", zero_division=0
        )
        if f1 > best_f1:
            best_f1, best_threshold = f1, float(t)
    return best_threshold, best_f1


def train() -> None:
    engine = create_engine(settings.SYNC_DATABASE_URL)
    X, y = _load_training_data(engine)

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_SEED, stratify=y
    )

    neg = int((y_train == 0).sum())
    pos = int((y_train == 1).sum())
    scale_pos_weight = neg / max(pos, 1)
    print(f"scale_pos_weight: {scale_pos_weight:.1f} (neg={neg}, pos={pos})")

    model = XGBClassifier(
        n_estimators=N_ESTIMATORS,
        max_depth=MAX_DEPTH,
        learning_rate=LEARNING_RATE,
        subsample=SUBSAMPLE,
        colsample_bytree=COLSAMPLE_BYTREE,
        scale_pos_weight=scale_pos_weight,
        eval_metric="aucpr",
        early_stopping_rounds=EARLY_STOPPING_ROUNDS,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=50,
    )

    val_probs = model.predict_proba(X_val)[:, 1]
    aucpr = average_precision_score(y_val, val_probs)
    best_threshold, best_f1 = _tune_threshold(model, X_val, y_val)
    print(f"Val AUC-PR: {aucpr:.4f}")
    print(f"Best threshold: {best_threshold:.2f}, F1: {best_f1:.4f}")

    output_dir = Path(settings.ML_MODEL_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    model_path = output_dir / "fraud_model.pkl"
    manifest_path = output_dir / "feature_columns.json"

    joblib.dump(model, model_path)
    manifest = {
        "feature_columns": FEATURE_COLUMNS,
        "threshold": best_threshold,
        "baseline_f1": best_f1,
        "val_aucpr": aucpr,
        "trained_at": pd.Timestamp.now().isoformat(),
        "n_samples": len(X),
        "fraud_rate_pct": float(y.mean() * 100),
        "feature_psi_baselines": _build_feature_psi_baselines(X_train, FEATURE_COLUMNS),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print(f"Model saved:    {model_path}")
    print(f"Manifest saved: {manifest_path}")


if __name__ == "__main__":
    train()
