"""
ML Fraud Serving — singleton XGBoost model + SHAP explainability.

Design:
    Class-level state: model, explainer, threshold, feature_columns loaded once per process.
    Lazy imports: xgboost/shap/joblib only imported inside load() — not at module init.
        This prevents ImportError in test environments where ML deps are not installed.
    Fail-open: load() raises FileNotFoundError; callers catch it and fall back to rules-only.
    SHAP TreeExplainer init is expensive (~200ms); must not run per-request.
    feature_columns read from manifest JSON — single source of truth, never re-hardcoded here.

FAANG pattern: EU AI Act Article 13 requires explanations for automated fraud decisions.
SHAP Shapley values provide mathematical guarantees (efficiency + symmetry axioms) unlike LIME.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Final

import structlog
from pydantic import BaseModel

from app.core.config import settings
from app.utils.metrics import ML_FRAUD_SCORE_DISTRIBUTION

if TYPE_CHECKING:
    import shap
    from xgboost import XGBClassifier

logger = structlog.get_logger(__name__)

ML_TOP_SHAP_FEATURES: Final[int] = 5
ML_THRESHOLD_DEFAULT: Final[float] = 0.65

HUMAN_LABELS: Final[dict[str, str]] = {
    "velocity_15min": "Transaction speed (last 15 min)",
    "velocity_60min": "Transaction speed (last hour)",
    "amount_to_avg_ratio": "Amount vs. typical spending",
    "amount_zscore": "Amount deviation from average",
    "is_night": "Night-time transaction (2 AM–5 AM)",
    "is_weekend": "Weekend transaction",
    "is_new_merchant": "New merchant (never seen before)",
    "fraud_rate_30d": "Recent personal fraud history",
    "merchant_fraud_rate": "Merchant's fraud history",
    "tx_count_30d": "Recent transaction frequency",
    "tx_count_7d": "Weekly transaction frequency",
    "avg_amount_30d": "30-day average spend",
    "avg_amount_7d": "7-day average spend",
    "avg_amount_90d": "90-day average spend",
    "std_amount_30d": "Spend variability",
    "unique_merchants_30d": "Merchant diversity (30 days)",
    "amount": "Transaction amount",
    "hour_of_day": "Hour of transaction",
    "day_of_week": "Day of week",
}


class ShapReason(BaseModel):
    feature: str
    shap_value: float
    human_label: str
    direction: str


class MLFraudResult(BaseModel):
    model_config = {"protected_namespaces": ()}

    fraud_probability: float
    is_fraud: bool
    top_reasons: list[ShapReason]
    explanation_text: str
    model_version: str


class MLFraudService:
    """Process-level singleton for XGBoost inference + SHAP explanation."""

    _model: ClassVar[XGBClassifier | None] = None
    _explainer: ClassVar[shap.TreeExplainer | None] = None
    _feature_columns: ClassVar[list[str]] = []
    _threshold: ClassVar[float] = ML_THRESHOLD_DEFAULT
    _model_version: ClassVar[str] = "unknown"

    @classmethod
    def load(cls) -> None:
        """Load model + SHAP explainer from ML_MODEL_DIR.

        Raises FileNotFoundError when artifacts have not been trained yet.
        Callers should catch this and fall back to rules-only mode.
        """
        import joblib
        from xgboost import XGBClassifier as _XGB  # noqa: F401

        model_dir = Path(settings.ML_MODEL_DIR)
        model_path = model_dir / "fraud_model.pkl"
        manifest_path = model_dir / "feature_columns.json"

        if not manifest_path.exists():
            raise FileNotFoundError(f"ML manifest not found: {manifest_path}")
        if not model_path.exists():
            raise FileNotFoundError(f"ML model not found: {model_path}")

        manifest: dict[str, Any] = json.loads(manifest_path.read_text())
        cls._model = joblib.load(model_path)
        cls._feature_columns = manifest["feature_columns"]
        cls._threshold = float(manifest.get("threshold", ML_THRESHOLD_DEFAULT))
        cls._model_version = manifest.get("trained_at", "unknown")

        # Use XGBoost's native SHAP via booster.predict(pred_contribs=True).
        # shap.TreeExplainer has a known incompatibility with XGBoost >=3.x
        # (base_score stored as array instead of scalar).
        cls._explainer = cls._model.get_booster()

        logger.info(
            "ml_model.loaded",
            model_version=cls._model_version,
            threshold=cls._threshold,
            n_features=len(cls._feature_columns),
        )

    @classmethod
    def is_loaded(cls) -> bool:
        return cls._model is not None and cls._explainer is not None

    def predict_with_explanation(
        self,
        features: dict[str, float],
        *,
        company_id: int | None = None,
    ) -> MLFraudResult:
        """Score one transaction and return top-N SHAP reasons.

        features must contain all keys in _feature_columns (extras are ignored).
        company_id scopes ML score histogram to tenant (omit only in tests).
        """
        import numpy as np
        import pandas as pd

        if not self.is_loaded():
            raise RuntimeError("MLFraudService.load() must be called before inference.")

        X = (
            pd.DataFrame([features])[self._feature_columns]
            .fillna(0)
            .astype(np.float32)
        )

        prob = float(self._model.predict_proba(X)[0, 1])  # type: ignore[union-attr]

        if company_id is not None:
            ML_FRAUD_SCORE_DISTRIBUTION.labels(company_id=str(company_id)).observe(prob)

        import xgboost as xgb

        dmatrix = xgb.DMatrix(X)
        # pred_contribs returns shape (n_samples, n_features + 1); last col is bias term.
        contribs = self._explainer.predict(dmatrix, pred_contribs=True)  # type: ignore[union-attr]
        shap_row = contribs[0, :-1]

        reasons = sorted(
            [
                ShapReason(
                    feature=f,
                    shap_value=round(float(v), 6),
                    human_label=HUMAN_LABELS.get(f, f),
                    direction="increases fraud risk" if v > 0 else "decreases fraud risk",
                )
                for f, v in zip(self._feature_columns, shap_row)
            ],
            key=lambda r: abs(r.shap_value),
            reverse=True,
        )
        top = reasons[:ML_TOP_SHAP_FEATURES]

        return MLFraudResult(
            fraud_probability=round(prob, 6),
            is_fraud=prob >= self._threshold,
            top_reasons=top,
            explanation_text=_build_explanation(prob, top),
            model_version=self._model_version,
        )


def _build_explanation(prob: float, reasons: list[ShapReason]) -> str:
    if not reasons:
        return f"Fraud probability: {prob:.1%}"
    primary = reasons[0]
    others = [r.human_label for r in reasons[1:3]]
    base = (
        f"This transaction scored {prob:.1%} fraud probability. "
        f"Primary signal: {primary.human_label} ({primary.direction})."
    )
    if others:
        base += f" Also flagged: {', '.join(others)}."
    return base
