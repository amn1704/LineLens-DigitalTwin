from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import VehicleQualityPrediction, VehicleThread


@dataclass
class FactorAnalysis:
    factor_type: str
    factor_id: str
    factor_name: str
    cohort_count: int
    cohort_size: int
    baseline_count: int
    baseline_size: int
    cohort_prevalence: float
    baseline_prevalence: float
    risk_lift: float


class GenealogyAnalyzer:
    """Analyzes digital threads to find common factors across high-risk vehicles."""
    
    def __init__(self) -> None:
        self._min_cohort_size = 3
        self._min_support = 2
        self._min_risk_lift = 1.5
    
    def analyze_cohort(
        self,
        cohort_predictions: list[VehicleQualityPrediction],
        cohort_threads: dict[str, VehicleThread],
        baseline_threads: dict[str, VehicleThread],
        analysis_time: float,
    ) -> dict:
        """Analyze cohort of high-risk vehicles for common process factors."""
        
        if len(cohort_predictions) < self._min_cohort_size:
            return self._empty_analysis(analysis_time, "Cohort too small for analysis")
        
        cohort_vehicle_ids = {p.vehicle_id for p in cohort_predictions}
        cohort_size = len(cohort_vehicle_ids)
        baseline_size = len(baseline_threads)
        
        # Extract all potential factors from cohort and baseline
        cohort_factors = self._extract_factors(cohort_vehicle_ids, cohort_threads)
        baseline_factors = self._extract_factors(set(baseline_threads.keys()), baseline_threads)
        
        # Calculate enrichment for each factor
        factor_analyses = []
        weld_hypothesis = any(prediction.likely_origin_station == "BIW-02" for prediction in cohort_predictions)
        for factor_key, factor_info in cohort_factors.items():
            # Once the independent vehicle forecast points to the weld process,
            # compare the weld genealogy fields rather than allowing unrelated
            # downstream batch coincidence to outrank the implicated process.
            if weld_hypothesis and not (
                factor_info["type"] in {"robot_cell", "consumable_lot"}
                or (factor_info["type"] == "tool" and str(factor_info["id"]).startswith("WG-"))
            ):
                continue
            baseline_count = baseline_factors.get(factor_key, {}).get("count", 0)
            
            if factor_info["count"] < self._min_support:
                continue
            
            cohort_prevalence = factor_info["count"] / cohort_size
            baseline_prevalence = baseline_count / baseline_size if baseline_size > 0 else 0
            
            # Calculate risk lift (avoid division by zero)
            # A small continuity correction keeps lift finite and avoids claiming
            # certainty merely because the recent baseline has no occurrence.
            risk_lift = (factor_info["count"] + 0.5) / cohort_size
            risk_lift /= (baseline_count + 0.5) / max(1, baseline_size)
            
            if risk_lift < self._min_risk_lift:
                continue
            
            factor_analyses.append(FactorAnalysis(
                factor_type=factor_info["type"],
                factor_id=factor_info["id"],
                factor_name=factor_info["name"],
                cohort_count=factor_info["count"],
                cohort_size=cohort_size,
                baseline_count=baseline_count,
                baseline_size=baseline_size,
                cohort_prevalence=cohort_prevalence,
                baseline_prevalence=baseline_prevalence,
                risk_lift=risk_lift,
            ))
        
        # Sort by risk lift and support
        factor_analyses.sort(key=lambda x: (x.risk_lift, x.cohort_count), reverse=True)
        
        # Determine likely origin process
        likely_origin = self._determine_likely_origin(factor_analyses, cohort_predictions)
        
        # Calculate analysis confidence
        analysis_confidence = self._calculate_analysis_confidence(factor_analyses, cohort_size)
        
        return {
            "analysis_timestamp": analysis_time,
            "cohort_definition": f"High-risk vehicles (risk >= 0.60)",
            "cohort_size": cohort_size,
            "baseline_size": baseline_size,
            "common_factors": [
                {
                    "factor_type": fa.factor_type,
                    "factor_id": fa.factor_id,
                    "factor_name": fa.factor_name,
                    "support": fa.cohort_count,
                    "cohort_prevalence": round(fa.cohort_prevalence, 3),
                    "baseline_prevalence": round(fa.baseline_prevalence, 3),
                    "risk_lift": round(fa.risk_lift, 2),
                    "confidence": round(self._factor_confidence(fa), 3),
                }
                for fa in factor_analyses[:10]  # Top 10 factors
            ],
            "likely_origin_process": likely_origin,
            "analysis_confidence": round(analysis_confidence, 3),
        }
    
    def _extract_factors(self, vehicle_ids: set[str], threads: dict[str, VehicleThread]) -> dict:
        """Extract potential common factors from vehicle digital threads."""
        
        factors = defaultdict(lambda: {"count": 0, "type": "", "id": "", "name": ""})
        
        for vehicle_id in vehicle_ids:
            thread = threads.get(vehicle_id)
            if not thread:
                continue
            
            for step in thread.completed_steps:
                metadata = step.metadata or {}
                
                # Extract tool/equipment factors
                if "weld_gun" in metadata:
                    key = f"tool:{metadata['weld_gun']}"
                    factors[key] = {
                        "count": factors[key]["count"] + 1,
                        "type": "tool",
                        "id": metadata["weld_gun"],
                        "name": f"Weld Gun {metadata['weld_gun']}",
                    }
                
                if "robot_cell" in metadata:
                    key = f"robot_cell:{metadata['robot_cell']}"
                    factors[key] = {
                        "count": factors[key]["count"] + 1,
                        "type": "robot_cell",
                        "id": metadata["robot_cell"],
                        "name": f"Robot Cell {metadata['robot_cell']}",
                    }
                
                if "electrode_cap_lot" in metadata:
                    key = f"consumable:{metadata['electrode_cap_lot']}"
                    factors[key] = {
                        "count": factors[key]["count"] + 1,
                        "type": "consumable_lot",
                        "id": metadata["electrode_cap_lot"],
                        "name": f"Electrode Cap Lot {metadata['electrode_cap_lot']}",
                    }
                
                if "fixture" in metadata:
                    key = f"fixture:{metadata['fixture']}"
                    factors[key] = {
                        "count": factors[key]["count"] + 1,
                        "type": "fixture",
                        "id": metadata["fixture"],
                        "name": f"Fixture {metadata['fixture']}",
                    }
                
                if "paint_batch" in metadata:
                    key = f"batch:{metadata['paint_batch']}"
                    factors[key] = {
                        "count": factors[key]["count"] + 1,
                        "type": "paint_batch",
                        "id": metadata["paint_batch"],
                        "name": f"Paint Batch {metadata['paint_batch']}",
                    }
                
                if "torque_tool" in metadata:
                    key = f"tool:{metadata['torque_tool']}"
                    factors[key] = {
                        "count": factors[key]["count"] + 1,
                        "type": "tool",
                        "id": metadata["torque_tool"],
                        "name": f"Torque Tool {metadata['torque_tool']}",
                    }
        
        return dict(factors)
    
    def _determine_likely_origin(self, factor_analyses: list[FactorAnalysis], predictions: list[VehicleQualityPrediction]) -> str | None:
        """Determine most likely process origin based on factor analysis."""
        
        if not factor_analyses:
            return None
        
        # Count factor types
        type_counts = Counter(fa.factor_type for fa in factor_analyses[:5])
        
        # Robot-cell and weld-gun metadata are both evidence of the Robotic Weld
        # process; factor type labels need not literally contain "weld".
        weld_related = sum(
            count for type_name, count in type_counts.items()
            if type_name in {"tool", "robot_cell", "consumable_lot"}
        )
        
        if weld_related >= 2:
            return "BIW-02"  # Robotic Weld Cell
        
        # Check prediction origins
        origin_counts = Counter(p.likely_origin_station for p in predictions if p.likely_origin_station)
        if origin_counts:
            return origin_counts.most_common(1)[0][0]
        
        return factor_analyses[0].factor_id if factor_analyses else None
    
    def _calculate_analysis_confidence(self, factor_analyses: list[FactorAnalysis], cohort_size: int) -> float:
        """Calculate overall confidence in the genealogy analysis."""
        
        if not factor_analyses:
            return 0.0
        
        # Base confidence from cohort size
        size_confidence = min(1.0, cohort_size / 10.0)
        
        # Confidence from strongest factor
        strongest_factor = factor_analyses[0]
        factor_confidence = min(1.0, max(0.0, (strongest_factor.risk_lift - 1.0) / 3.0))
        
        # Confidence from factor consistency
        if len(factor_analyses) >= 2:
            top_lifts = [fa.risk_lift for fa in factor_analyses[:3]]
            consistency = max(0.0, 1.0 - (max(top_lifts) - min(top_lifts)) / max(top_lifts))
        else:
            consistency = 0.5
        
        return (size_confidence * 0.4 + factor_confidence * 0.4 + consistency * 0.2)
    
    def _factor_confidence(self, factor_analysis: FactorAnalysis) -> float:
        """Calculate confidence for individual factor."""
        
        # Support confidence
        support_confidence = min(1.0, factor_analysis.cohort_count / 5.0)
        
        # Lift confidence
        lift_confidence = min(1.0, (factor_analysis.risk_lift - 1.0) / 4.0)
        
        return (support_confidence * 0.6 + lift_confidence * 0.4)
    
    def _empty_analysis(self, analysis_time: float, reason: str) -> dict:
        """Return empty analysis result."""
        return {
            "analysis_timestamp": analysis_time,
            "cohort_definition": "High-risk vehicles",
            "cohort_size": 0,
            "baseline_size": 0,
            "common_factors": [],
            "likely_origin_process": None,
            "analysis_confidence": 0.0,
            "analysis_note": reason,
        }
