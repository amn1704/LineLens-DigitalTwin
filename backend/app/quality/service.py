from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..models import (
    DefectFamily,
    InspectionResult,
    QualityEvidence,
    QualityLevel,
    StationObservation,
    StationTwinEstimate,
    VehicleQualityPrediction,
    VehicleThread,
)
from .features import QualityFeatureBuilder
from .genealogy import GenealogyAnalyzer
from .model import QualityModel


@dataclass
class QualityRecord:
    vehicle_id: str
    current_prediction: VehicleQualityPrediction | None = None
    prediction_history: list[VehicleQualityPrediction] = field(default_factory=list)
    inspection_result: InspectionResult | None = None
    # Retained separately so EOL evaluation never changes a past forecast.
    first_prediction: VehicleQualityPrediction | None = None
    first_inspection_prediction: VehicleQualityPrediction | None = None


class QualityService:
    """Main service for vehicle quality prediction and genealogy analysis."""
    
    def __init__(self) -> None:
        self._feature_builder = QualityFeatureBuilder()
        self._model = QualityModel()
        self._genealogy = GenealogyAnalyzer()
        
        # Vehicle quality records
        self._quality_records: dict[str, QualityRecord] = {}
        
        # Metrics tracking
        self._predictions_made = 0
        self._inspections_completed = 0
        self._true_positives = 0
        self._false_positives = 0
        self._true_negatives = 0
        self._false_negatives = 0
        self._prediction_lead_times: list[float] = []
        self._unnecessary_inspections = 0
        
        # Recent high-risk vehicles for genealogy
        self._high_risk_history: deque[str] = deque(maxlen=50)
        
        # Model version
        self._model_version = self._model.MODEL_VERSION
    
    def reset(self) -> None:
        """Reset quality service state."""
        self._quality_records.clear()
        self._predictions_made = 0
        self._inspections_completed = 0
        self._true_positives = 0
        self._false_positives = 0
        self._true_negatives = 0
        self._false_negatives = 0
        self._prediction_lead_times.clear()
        self._unnecessary_inspections = 0
        self._high_risk_history.clear()
    
    def update_vehicle_quality(
        self,
        vehicle_thread: VehicleThread,
        current_station_id: str,
        current_time: float,
        station_observations: dict[str, StationObservation],
        station_twins: dict[str, StationTwinEstimate],
    ) -> VehicleQualityPrediction | None:
        """Update quality prediction for a vehicle based on current state."""
        
        # Get or create quality record
        record = self._quality_records.setdefault(vehicle_thread.vehicle_id, QualityRecord(vehicle_thread.vehicle_id))
        # Build feature snapshot
        snapshot = self._feature_builder.build_snapshot(
            vehicle_thread,
            current_station_id,
            current_time,
            station_observations,
            station_twins,
        )
        
        # Generate prediction
        prediction_result = self._model.predict(snapshot)
        
        # Convert to domain model
        prediction = self._to_quality_prediction(snapshot, prediction_result, current_station_id, current_time)
        
        # Update record
        record.current_prediction = prediction
        record.prediction_history.append(prediction)
        if record.first_prediction is None:
            record.first_prediction = prediction
        if prediction.risk >= 0.60 and record.first_inspection_prediction is None:
            record.first_inspection_prediction = prediction
        
        # Track high-risk vehicles for genealogy
        if prediction.risk >= 0.60:  # INSPECT threshold
            if vehicle_thread.vehicle_id not in self._high_risk_history:
                self._high_risk_history.append(vehicle_thread.vehicle_id)
        
        self._predictions_made += 1
        
        return prediction
    
    def _to_quality_prediction(
        self,
        snapshot,
        prediction_result,
        current_station_id: str,
        current_time: float,
    ) -> VehicleQualityPrediction:
        """Convert model prediction to domain model."""
        
        from ..models import QualityEvidence, QualityLevel
        
        # Convert evidence
        evidence = []
        for factor, contribution in prediction_result.feature_contributions.items():
            if abs(contribution) > 0.05:  # Only include meaningful contributions
                value_str = f"{contribution:+.3f}"
                evidence.append(QualityEvidence(factor=factor, value=value_str, contribution=contribution))
        
        # Determine recommended inspection point
        recommended_inspection = self._recommend_inspection_point(
            current_station_id,
            prediction_result.likely_defect_family,
            prediction_result.likely_origin_station,
        )
        
        # Map quality level
        quality_level = self._risk_to_level(prediction_result.risk)
        
        return VehicleQualityPrediction(
            vehicle_id=snapshot.vehicle_id,
            prediction_timestamp=current_time,
            station_at_prediction=current_station_id,
            risk=prediction_result.risk,
            confidence=prediction_result.confidence,
            likely_defect_family=prediction_result.likely_defect_family,
            likely_origin_station=prediction_result.likely_origin_station,
            recommended_inspection_point=recommended_inspection,
            evidence=evidence,
            quality_level=quality_level,
            model_version=prediction_result.model_version,
        )
    
    def _recommend_inspection_point(self, current_station: str, defect_family: str | None, origin_station: str | None) -> str | None:
        """Recommend earliest sensible inspection point."""
        
        station_order = {"BIW-01": 0, "BIW-02": 1, "BIW-03": 2, "PAINT-01": 3,
                         "PAINT-02": 4, "PAINT-03": 5, "FA-01": 6, "FA-02": 7,
                         "FA-03": 8, "FA-04": 9, "FA-05": 10}
        current_index = station_order.get(current_station, 10)
        if defect_family and ("body" in defect_family.lower() or "weld" in defect_family.lower()):
            return "Body Shop Exit" if current_index <= 2 else "Next available quality hold"
        
        # If origin station is known, recommend inspection after that station
        if origin_station:
            # Map origin to logical inspection point
            if origin_station.startswith("BIW"):
                return "Body Shop Exit"
            elif origin_station.startswith("PAINT"):
                return "Paint Booth Exit"
            elif origin_station.startswith("FA"):
                return "End-of-Line Inspection"
        
        # Default: recommend EOL
        return "End-of-Line Inspection"
    
    def _risk_to_level(self, risk: float) -> QualityLevel:
        """Map risk score to quality level."""
        from ..models import QualityLevel
        
        if risk >= 0.82:
            return QualityLevel.HIGH
        elif risk >= 0.60:
            return QualityLevel.INSPECT
        elif risk >= 0.35:
            return QualityLevel.WATCH
        else:
            return QualityLevel.LOW
    
    def record_inspection_result(
        self,
        vehicle_id: str,
        inspection_time: float,
        inspection_station: str,
        passed: bool,
        defect_family: str | None = None,
    ) -> InspectionResult:
        """Record actual inspection result and update metrics."""
        
        from ..models import DefectFamily, InspectionStatus
        
        record = self._quality_records.get(vehicle_id)
        if not record:
            # Create record if it doesn't exist
            record = QualityRecord(vehicle_id)
            self._quality_records[vehicle_id] = record
        
        # Create inspection result
        result_str = "PASS" if passed else f"FAIL - {defect_family}" if defect_family else "FAIL"
        defect_enum = DefectFamily(defect_family) if defect_family else None
        
        inspection_result = InspectionResult(
            vehicle_id=vehicle_id, inspection_timestamp=inspection_time,
            inspection_station=inspection_station, result=result_str,
            defect_family=defect_enum,
            inspection_status=InspectionStatus.CONFIRMED if not passed else InspectionStatus.CLEARED,
        )
        
        record.inspection_result = inspection_result
        self._inspections_completed += 1
        
        # Update prediction metrics if prediction exists
        evaluation_prediction = record.first_inspection_prediction or record.first_prediction
        if evaluation_prediction:
            prediction_was_risky = evaluation_prediction.risk >= 0.60
            actually_defective = not passed
            
            if prediction_was_risky and actually_defective:
                self._true_positives += 1
                # Calculate lead time
                lead_time = inspection_time - evaluation_prediction.prediction_timestamp
                self._prediction_lead_times.append(lead_time)
            elif prediction_was_risky and not actually_defective:
                self._false_positives += 1
                self._unnecessary_inspections += 1
            elif not prediction_was_risky and actually_defective:
                self._false_negatives += 1
            else:
                self._true_negatives += 1
        
        return inspection_result
    
    def get_vehicle_quality(self, vehicle_id: str) -> dict | None:
        """Get quality information for a specific vehicle."""
        
        record = self._quality_records.get(vehicle_id)
        if not record:
            return None
        
        return {
            "vehicle_id": record.vehicle_id,
            "current_prediction": record.current_prediction.model_dump(mode="json") if record.current_prediction else None,
            "prediction_history": [prediction.model_dump(mode="json") for prediction in record.prediction_history],
            "inspection_result": record.inspection_result.model_dump(mode="json") if record.inspection_result else None,
        }
    
    def get_high_risk_vehicles(self, threshold: float = 0.60) -> list[dict]:
        """Get vehicles above risk threshold."""
        
        high_risk = []
        for record in self._quality_records.values():
            if record.current_prediction and record.current_prediction.risk >= threshold:
                vehicle_info = {
                    "vehicle_id": record.vehicle_id,
                    "risk": record.current_prediction.risk,
                    "confidence": record.current_prediction.confidence,
                    "likely_defect_family": record.current_prediction.likely_defect_family,
                    "likely_origin_station": record.current_prediction.likely_origin_station,
                    "recommended_inspection": record.current_prediction.recommended_inspection_point,
                    "quality_level": record.current_prediction.quality_level,
                    "prediction_timestamp": record.current_prediction.prediction_timestamp,
                    "station_at_prediction": record.current_prediction.station_at_prediction,
                    "inspection_status": record.inspection_result.inspection_status.value if record.inspection_result else "PREDICTED",
                }
                high_risk.append(vehicle_info)
        
        # Sort by risk (highest first)
        high_risk.sort(key=lambda x: x["risk"], reverse=True)
        return high_risk

    def get_monitored_vehicles(self) -> list[dict]:
        """Return the full monitored population, ordered so evolving risk is visible."""
        rows = []
        for record in self._quality_records.values():
            prediction = record.current_prediction
            if prediction is None:
                continue
            rows.append({
                "vehicle_id": record.vehicle_id,
                "risk": prediction.risk,
                "confidence": prediction.confidence,
                "quality_level": prediction.quality_level.value,
                "station_at_prediction": prediction.station_at_prediction,
                "likely_defect_family": prediction.likely_defect_family.value if prediction.likely_defect_family else None,
                "inspection_status": record.inspection_result.inspection_status.value if record.inspection_result else "PREDICTED",
                "prediction_timestamp": prediction.prediction_timestamp,
            })
        return sorted(rows, key=lambda row: (row["risk"], row["prediction_timestamp"]), reverse=True)
    
    def analyze_genealogy(
        self,
        current_time: float,
        vehicle_threads: dict[str, VehicleThread],
        baseline_threads: dict[str, VehicleThread] | None = None,
    ) -> dict:
        """Analyze genealogy of high-risk vehicles."""
        
        # Get high-risk cohort
        high_risk_vehicles = self.get_high_risk_vehicles(threshold=0.60)
        high_risk_ids = {v["vehicle_id"] for v in high_risk_vehicles}
        
        # Get their predictions
        cohort_predictions = []
        for vehicle_id in high_risk_ids:
            record = self._quality_records.get(vehicle_id)
            if record and record.current_prediction:
                cohort_predictions.append(record.current_prediction)
        
        # Get baseline (recent normal production)
        if baseline_threads is None:
            baseline_ids = set(self._quality_records.keys()) - high_risk_ids
            baseline_threads = {vid: vehicle_threads.get(vid) for vid in baseline_ids if vehicle_threads.get(vid)}
        
        # Run genealogy analysis
        return self._genealogy.analyze_cohort(
            cohort_predictions,
            vehicle_threads,
            baseline_threads,
            current_time,
        )
    
    def get_quality_metrics(self) -> dict:
        """Calculate and return quality metrics."""
        
        total_predictions = self._predictions_made
        total_vehicles = len(self._quality_records)
        total_inspections = self._inspections_completed
        
        if total_inspections == 0:
            return {
                "total_vehicles": total_vehicles,
                "total_predictions": total_predictions,
                "defective_vehicles": 0,
                "defect_rate": 0.0,
                "true_positives": 0,
                "false_positives": 0,
                "true_negatives": 0,
                "false_negatives": 0,
                "precision": None,
                "recall": None,
                "false_positive_rate": None,
                "prediction_lead_time_mean": None,
                "prediction_lead_time_max": None,
                "early_interception_opportunity": None,
                "unnecessary_inspections": self._unnecessary_inspections,
                "model_version": self._model_version,
                "model_status": self._model.audit(),
                "validation_state": "AWAITING_EOL_OUTCOMES",
            }
        
        # Calculate rates
        precision = self._true_positives / (self._true_positives + self._false_positives) if (self._true_positives + self._false_positives) > 0 else None
        recall = self._true_positives / (self._true_positives + self._false_negatives) if (self._true_positives + self._false_negatives) > 0 else None
        fpr = self._false_positives / (self._false_positives + self._true_negatives) if (self._false_positives + self._true_negatives) > 0 else None
        
        # Lead time statistics
        lead_time_mean = sum(self._prediction_lead_times) / len(self._prediction_lead_times) if self._prediction_lead_times else None
        lead_time_max = max(self._prediction_lead_times) if self._prediction_lead_times else None
        
        # Early interception opportunity
        defective_vehicles = self._true_positives + self._false_negatives
        early_interception = (self._true_positives / defective_vehicles) if defective_vehicles > 0 else None
        
        return {
            "total_vehicles": total_vehicles,
            "total_predictions": total_predictions,
            "defective_vehicles": defective_vehicles,
            "defect_rate": defective_vehicles / total_inspections if total_inspections > 0 else 0.0,
            "true_positives": self._true_positives,
            "false_positives": self._false_positives,
            "true_negatives": self._true_negatives,
            "false_negatives": self._false_negatives,
            "precision": round(precision, 3) if precision is not None else None,
            "recall": round(recall, 3) if recall is not None else None,
            "false_positive_rate": round(fpr, 3) if fpr is not None else None,
            "prediction_lead_time_mean": round(lead_time_mean, 1) if lead_time_mean is not None else None,
            "prediction_lead_time_max": round(lead_time_max, 1) if lead_time_max is not None else None,
            "early_interception_opportunity": round(early_interception, 3) if early_interception is not None else None,
            "unnecessary_inspections": self._unnecessary_inspections,
            "model_version": self._model_version,
            "model_status": self._model.audit(),
            "validation_state": "VALID" if defective_vehicles > 0 else "CONFIRMED_ZERO_FAILURES",
        }
    
    def get_all_vehicles_quality(self) -> list[dict]:
        """Get quality info for all tracked vehicles."""
        
        all_vehicles = []
        for record in self._quality_records.values():
            vehicle_info = {
                "vehicle_id": record.vehicle_id,
                "risk": record.current_prediction.risk if record.current_prediction else 0.0,
                "confidence": record.current_prediction.confidence if record.current_prediction else 0.0,
                "likely_defect_family": record.current_prediction.likely_defect_family if record.current_prediction else None,
                "quality_level": record.current_prediction.quality_level if record.current_prediction else "LOW",
                "inspection_status": record.inspection_result.inspection_status.value if record.inspection_result else "PREDICTED",
            }
            all_vehicles.append(vehicle_info)
        
        return all_vehicles
