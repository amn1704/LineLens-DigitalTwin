from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from .features import VehicleQualitySnapshot


@dataclass(frozen=True)
class QualityPrediction:
    risk: float
    confidence: float
    likely_defect_family: str | None
    likely_origin_station: str | None
    feature_contributions: dict[str, float]
    model_version: str


class QualityModel:
    """Small, deterministic and interpretable synthetic quality classifier."""

    MODEL_VERSION = "quality-logreg-v1"
    MODEL_PATH = Path("backend/app/quality/quality_model.pkl")
    SCALER_PATH = Path("backend/app/quality/quality_scaler.pkl")
    ARTIFACT_PATH = Path(__file__).with_name("quality_model_artifact.json")
    FEATURE_NAMES = (
        "weld_energy_deviation", "weld_variance_multiplier", "avg_cycle_deviation",
        "max_cycle_deviation", "avg_twin_confidence", "min_twin_confidence",
        "signal_completeness", "has_weld_telemetry", "is_suv_variant", "is_ev_variant",
    )
    THRESHOLD_WATCH = 0.35
    THRESHOLD_INSPECT = 0.60
    THRESHOLD_HIGH = 0.82

    def __init__(self, force_fallback: bool = False) -> None:
        self._model: LogisticRegression | None = None
        self._scaler: StandardScaler | None = None
        self._is_fallback = False
        self._source = "synthetic-trained"
        self._artifact: dict[str, object] = {}
        if force_fallback:
            self._initialize_fallback()
        else:
            self._load_or_train()

    def _load_or_train(self) -> None:
        try:
            if self.ARTIFACT_PATH.exists():
                self._load_json_artifact()
                return
            if self.MODEL_PATH.exists() and self.SCALER_PATH.exists():
                with self.MODEL_PATH.open("rb") as handle:
                    self._model = pickle.load(handle)
                with self.SCALER_PATH.open("rb") as handle:
                    self._scaler = pickle.load(handle)
                self._source = "artifact"
                return
            self._train_synthetic_model()
        except Exception:
            self._initialize_fallback()

    def _load_json_artifact(self) -> None:
        """Load the checked-in, reproducible logistic-regression artifact."""
        self._artifact = json.loads(self.ARTIFACT_PATH.read_text(encoding="utf-8"))
        if tuple(self._artifact["feature_names"]) != self.FEATURE_NAMES:
            raise ValueError("Quality model artifact feature schema does not match")
        self._scaler = StandardScaler()
        self._scaler.mean_ = np.asarray(self._artifact["mean"], dtype=float)
        self._scaler.scale_ = np.asarray(self._artifact["scale"], dtype=float)
        self._scaler.var_ = self._scaler.scale_ ** 2
        self._scaler.n_features_in_ = len(self.FEATURE_NAMES)
        self._model = LogisticRegression()
        self._model.classes_ = np.asarray([0, 1])
        self._model.coef_ = np.asarray([self._artifact["coefficients"]], dtype=float)
        self._model.intercept_ = np.asarray([self._artifact["intercept"]], dtype=float)
        self._model.n_features_in_ = len(self.FEATURE_NAMES)
        self._source = "versioned-synthetic-artifact"

    def _train_synthetic_model(self) -> None:
        """Create a repeatable historical synthetic dataset; never use live units."""
        rng = np.random.default_rng(407)
        rows: list[list[float]] = []
        labels: list[int] = []
        for index in range(2400):
            drifted = index % 5 == 0
            energy = abs(rng.normal(0.135 if drifted else 0.020, 0.045 if drifted else 0.014))
            variance = max(0.35, rng.normal(1.85 if drifted else 0.68, 0.38 if drifted else 0.18))
            average_cycle = rng.normal(0.12 if drifted else 0.01, 0.055 if drifted else 0.025)
            maximum_cycle = abs(average_cycle) + abs(rng.normal(0.10 if drifted else 0.03, 0.035))
            twin_confidence = float(np.clip(rng.normal(0.80, 0.09), 0.35, 0.96))
            minimum_confidence = max(0.20, twin_confidence - abs(rng.normal(0.08, 0.04)))
            completeness = float(np.clip(rng.normal(0.90 if not drifted else 0.86, 0.10), 0.25, 1.0))
            weld_available = 1.0 if rng.random() < completeness else 0.0
            suv = 1.0 if index % 3 == 1 else 0.0
            ev = 1.0 if index % 3 == 2 else 0.0
            row = [energy, variance, average_cycle, maximum_cycle, twin_confidence, minimum_confidence, completeness, weld_available, suv, ev]
            z = -4.4 + 10.0 * energy + 1.15 * variance + 1.1 * maximum_cycle + 0.25 * suv + 0.40 * ev
            probability = 1.0 / (1.0 + np.exp(-z))
            rows.append(row)
            labels.append(int(rng.random() < probability))
        self._scaler = StandardScaler().fit(rows)
        self._model = LogisticRegression(random_state=407, class_weight="balanced", max_iter=1200)
        self._model.fit(self._scaler.transform(rows), labels)

    def audit(self) -> dict[str, object]:
        """Expose only model provenance and synthetic evaluation, never live labels."""
        if self._is_fallback:
            return {"mode": "fallback", "source": self._source, "model_version": self.MODEL_VERSION}
        metadata = dict(self._artifact.get("training", {}))
        return {
            "mode": "prediction",
            "source": self._source,
            "model_version": self.MODEL_VERSION,
            "feature_names": list(self.FEATURE_NAMES),
            "coefficients": {name: round(float(value), 4) for name, value in zip(self.FEATURE_NAMES, self._model.coef_[0])},
            "training": metadata,
        }

    def _initialize_fallback(self) -> None:
        """A deterministic, explicitly identifiable fallback when an artifact fails."""
        reference = np.array([
            [0.00, 0.65, 0.00, 0.03, 0.84, 0.76, 0.92, 1, 0, 0],
            [0.15, 1.80, 0.12, 0.26, 0.84, 0.76, 0.90, 1, 0, 0],
            [0.22, 2.30, 0.18, 0.35, 0.72, 0.61, 0.75, 1, 1, 0],
        ])
        self._scaler = StandardScaler().fit(reference)
        self._model = LogisticRegression(random_state=407)
        self._model.classes_ = np.array([0, 1])
        self._model.coef_ = np.array([[1.65, 1.20, 0.52, 0.80, -0.12, -0.16, -0.25, 0.32, 0.10, 0.16]])
        self._model.intercept_ = np.array([-2.05])
        self._is_fallback = True
        self._source = "deterministic-fallback"

    def _snapshot_to_features(self, snapshot: VehicleQualitySnapshot) -> list[float]:
        return [abs(snapshot.weld_energy_deviation or 0.0), snapshot.weld_variance_multiplier or 0.0,
                snapshot.avg_cycle_deviation, snapshot.max_cycle_deviation, snapshot.avg_twin_confidence,
                snapshot.min_twin_confidence, snapshot.signal_completeness, float(snapshot.has_weld_telemetry),
                float(snapshot.variant == "SUV"), float(snapshot.variant == "EV")]

    def predict(self, snapshot: VehicleQualitySnapshot) -> QualityPrediction:
        assert self._model is not None and self._scaler is not None
        raw = self._snapshot_to_features(snapshot)
        scaled = self._scaler.transform([raw])[0]
        risk = float(self._model.predict_proba([scaled])[0, 1])
        contributions = {name: round(float(value * coefficient), 4) for name, value, coefficient in zip(self.FEATURE_NAMES, scaled, self._model.coef_[0])}
        weld_evidence = (snapshot.weld_energy_deviation is not None and abs(snapshot.weld_energy_deviation) >= 0.055) or (snapshot.weld_variance_multiplier or 0) >= 1.15
        return QualityPrediction(risk=min(0.98, max(0.01, risk)), confidence=self._confidence(snapshot),
            likely_defect_family="Body geometry / weld integrity" if weld_evidence else None,
            likely_origin_station="BIW-02" if weld_evidence else None,
            feature_contributions=contributions,
            model_version=self.MODEL_VERSION + (" (fallback)" if self._is_fallback else ""))

    @staticmethod
    def _confidence(snapshot: VehicleQualitySnapshot) -> float:
        progress = min(1.0, snapshot.total_completed_stations / 3)
        confidence = 0.38 + 0.24 * snapshot.signal_completeness + 0.20 * snapshot.avg_twin_confidence + 0.10 * progress
        if not snapshot.has_weld_telemetry and snapshot.robot_cell_id:
            confidence -= 0.18
        return round(min(0.95, max(0.20, confidence)), 3)

    def is_fallback(self) -> bool:
        return self._is_fallback

    @property
    def source(self) -> str:
        return self._source
