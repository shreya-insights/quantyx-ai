"""Unit tests for PSI, F1 aggregation, and recommendation thresholds."""

import numpy as np

from app.models.model_monitoring import PsiStatus
from app.services.model_monitoring_service import (
    RECOMMENDATION_MONITOR,
    RECOMMENDATION_RETRAIN,
    RECOMMENDATION_STABLE,
    _f1_from_pr,
    _psi_from_histogram,
    compute_psi_for_feature,
    recommendation_from_metrics,
)


def test_psi_identical_reference_and_actual() -> None:
    expected = [0.1] * 10
    actual = [0.1] * 10
    assert abs(_psi_from_histogram(expected, actual)) < 1e-9


def test_psi_detects_distribution_shift() -> None:
    expected = [0.1] * 10
    shifted = [0.05] * 5 + [0.15] * 5
    s = float(sum(shifted))
    actual = [x / s for x in shifted]
    assert _psi_from_histogram(expected, actual) > 0.01


def test_f1_harmonic_mean() -> None:
    p, r = 0.8, 0.5
    want = 2 * p * r / (p + r)
    assert abs((_f1_from_pr(p, r) or 0) - want) < 1e-9
    assert _f1_from_pr(None, 1.0) is None
    assert _f1_from_pr(1.0, None) is None


def test_compute_psi_feature_matches_baseline_on_same_draw() -> None:
    rng = np.random.default_rng(0)
    values = rng.standard_normal(800)
    edges = np.quantile(values, np.linspace(0.0, 1.0, 11))
    counts, _ = np.histogram(values, bins=edges)
    total = float(counts.sum())
    expected_pct = (counts.astype(float) / total).tolist()
    baseline = {"bin_edges": edges.tolist(), "expected_pct": expected_pct}
    psi, status = compute_psi_for_feature(values, baseline)
    assert psi is not None
    assert psi < 0.02
    assert status == PsiStatus.STABLE


def test_recommendation_respects_thresholds(monkeypatch) -> None:
    import app.services.model_monitoring_service as mon

    monkeypatch.setattr(mon.settings, "MODEL_HEALTH_PSI_DRIFT_MIN_FEATURES", 3)
    monkeypatch.setattr(mon.settings, "MODEL_HEALTH_F1_THRESHOLD", 0.75)
    monkeypatch.setattr(mon.settings, "MODEL_HEALTH_PRECISION_THRESHOLD", 0.70)

    assert recommendation_from_metrics(0.9, 0.9, 0) == RECOMMENDATION_STABLE
    assert recommendation_from_metrics(0.9, 0.9, 3) == RECOMMENDATION_RETRAIN
    assert recommendation_from_metrics(0.5, 0.9, 0) == RECOMMENDATION_MONITOR
    assert recommendation_from_metrics(0.9, 0.5, 0) == RECOMMENDATION_MONITOR
    assert (
        recommendation_from_metrics(0.9, 0.9, 0, monitor_features=1)
        == RECOMMENDATION_MONITOR
    )
