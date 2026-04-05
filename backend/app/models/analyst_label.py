"""Analyst ground-truth labels for fraud case review."""

from enum import Enum as PyEnum


class AnalystGroundTruth(str, PyEnum):
    """Human reviewer label — not a model prediction."""

    FRAUD = "fraud"
    LEGITIMATE = "legitimate"
