from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import ProcessStep, StationObservation, StationTwinEstimate, VehicleThread


@dataclass
class VehicleQualitySnapshot:
    """Features available at prediction time - NO future information, NO ground truth."""
    
    vehicle_id: str
    variant: str
    prediction_timestamp: float
    station_at_prediction: str
    completed_steps: list[ProcessStep]
    
    # Process-specific features (only from completed stations)
    weld_energy_deviation: float | None = None
    weld_variance_multiplier: float | None = None
    robot_cell_id: str | None = None
    weld_gun_id: str | None = None
    electrode_cap_lot: str | None = None
    fixture_id: str | None = None
    paint_batch: str | None = None
    torque_tool_id: str | None = None
    calibration_rig_id: str | None = None
    
    # Cycle performance features
    station_residuals: dict[str, float] = field(default_factory=dict)
    cycle_deviations: dict[str, float] = field(default_factory=dict)
    avg_cycle_deviation: float = 0.0
    max_cycle_deviation: float = 0.0
    
    # Station twin confidence features
    twin_confidences: dict[str, float] = field(default_factory=dict)
    avg_twin_confidence: float = 0.0
    min_twin_confidence: float = 0.0
    
    # Process variability features
    process_variance_scores: dict[str, float] = field(default_factory=dict)
    avg_process_variance: float = 0.0
    
    # Vehicle context
    total_completed_stations: int = 0
    line_progress: float = 0.0
    
    # Feature availability flags (for handling missing telemetry)
    has_weld_telemetry: bool = False
    has_full_telemetry_at_risk_station: bool = False
    signal_completeness: float = 0.0


class QualityFeatureBuilder:
    """Builds quality prediction features from vehicle digital thread."""
    
    def __init__(self) -> None:
        self._weld_station_ids = {"BIW-02"}  # Robotic Weld Cell
        self._paint_station_ids = {"PAINT-02"}  # Paint Booth
        self._torque_station_ids = {"FA-03"}  # Wheel & Torque
        self._inspection_station_id = "FA-05"  # End-of-Line Inspection
    
    def build_snapshot(
        self,
        vehicle_thread: VehicleThread,
        current_station_id: str,
        current_time: float,
        station_observations: dict[str, StationObservation],
        station_twins: dict[str, StationTwinEstimate],
    ) -> VehicleQualitySnapshot:
        """Build quality features using only information available at prediction time."""
        
        snapshot = VehicleQualitySnapshot(
            vehicle_id=vehicle_thread.vehicle_id,
            variant=vehicle_thread.variant,
            prediction_timestamp=current_time,
            station_at_prediction=current_station_id,
            completed_steps=list(vehicle_thread.completed_steps),
        )
        
        # The manufacturing thread is the source of record.  A quality snapshot
        # deliberately ignores current observations from a later unit at the same
        # station and accepts only steps completed before this prediction time.
        completed_steps = [
            step for step in vehicle_thread.completed_steps if step.exit_time <= current_time
        ]
        snapshot.completed_steps = completed_steps
        for step in completed_steps:
            self._extract_process_metadata(snapshot, step)
            
            # Calculate cycle performance metrics
            if step.station_id in station_twins:
                twin = station_twins[step.station_id]
                # Step-local Twin values are preferred whenever they were written
                # by the simulator.  The supplied current Twin is only a safe
                # compatibility fallback for historic records without them.
                metadata = step.metadata or {}
                expected = float(metadata.get("twin_expected_cycle", twin.expected_cycle))
                confidence = float(metadata.get("twin_confidence", twin.confidence))
                residual = float(metadata.get("twin_residual", step.cycle_time - expected))
                snapshot.station_residuals[step.station_id] = residual
                snapshot.cycle_deviations[step.station_id] = residual / max(twin.baseline.cycle_stddev, 0.1)
                snapshot.twin_confidences[step.station_id] = confidence
        
        # Calculate aggregate metrics
        if snapshot.cycle_deviations:
            deviations = list(snapshot.cycle_deviations.values())
            snapshot.avg_cycle_deviation = sum(deviations) / len(deviations)
            snapshot.max_cycle_deviation = max(abs(d) for d in deviations)
        
        if snapshot.twin_confidences:
            confidences = list(snapshot.twin_confidences.values())
            snapshot.avg_twin_confidence = sum(confidences) / len(confidences)
            snapshot.min_twin_confidence = min(confidences)
        
        # Calculate weld-specific features if available
        self._calculate_weld_features(snapshot, station_observations, station_twins)
        
        # Set context features
        snapshot.total_completed_stations = len(completed_steps)
        snapshot.line_progress = vehicle_thread.line_progress
        
        # Calculate signal completeness
        relevant_stations = self._weld_station_ids | self._paint_station_ids | self._torque_station_ids
        completed_relevant = [s for s in completed_steps if s.station_id in relevant_stations]
        if completed_relevant:
            available_signals = sum(
                1
                for step in completed_relevant
                if self._step_has_available_signal(step, station_observations, current_time, vehicle_thread.vehicle_id)
            )
            snapshot.signal_completeness = available_signals / len(completed_relevant)
        
        # Set telemetry availability flags
        snapshot.has_weld_telemetry = any(
            step.station_id in self._weld_station_ids
            and self._step_has_available_signal(step, station_observations, current_time, vehicle_thread.vehicle_id)
            for step in completed_steps
        )
        
        snapshot.has_full_telemetry_at_risk_station = snapshot.has_weld_telemetry
        
        return snapshot

    @staticmethod
    def _step_has_available_signal(step, observations, current_time: float, vehicle_id: str) -> bool:
        metadata = step.metadata or {}
        if "weld_telemetry_available" in metadata:
            return bool(metadata["weld_telemetry_available"])
        observation = observations.get(step.station_id)
        return bool(
            observation
            and observation.timestamp <= current_time
            and (observation.vehicle_id is None or observation.vehicle_id == vehicle_id)
        )
    
    def _extract_process_metadata(self, snapshot: VehicleQualitySnapshot, step: ProcessStep) -> None:
        """Extract process-specific equipment and metadata from completed steps."""
        metadata = step.metadata or {}
        
        # Robotic Weld Cell metadata
        if step.station_id in self._weld_station_ids:
            snapshot.robot_cell_id = metadata.get("robot_cell")
            # Enhanced weld metadata will be added by simulator
            snapshot.weld_gun_id = metadata.get("weld_gun")
            snapshot.electrode_cap_lot = metadata.get("electrode_cap_lot")
        
        # Paint Booth metadata
        elif step.station_id in self._paint_station_ids:
            snapshot.paint_batch = metadata.get("paint_batch")
        
        # Wheel & Torque metadata
        elif step.station_id in self._torque_station_ids:
            snapshot.torque_tool_id = metadata.get("torque_tool")
        
        # General fixture metadata
        if "fixture" in metadata:
            snapshot.fixture_id = metadata.get("fixture")
        
        # ADAS calibration metadata
        if "calibration_rig" in metadata:
            snapshot.calibration_rig_id = metadata.get("calibration_rig")
    
    def _calculate_weld_features(
        self,
        snapshot: VehicleQualitySnapshot,
        station_observations: dict[str, StationObservation],
        station_twins: dict[str, StationTwinEstimate],
    ) -> None:
        """Calculate weld-specific quality features if weld process completed."""
        
        if not snapshot.robot_cell_id or not any(s.station_id in self._weld_station_ids for s in snapshot.completed_steps):
            return
        
        # Prefer vehicle-owned process evidence written at weld completion.  It is
        # never replaced by a later live station sample belonging to another body.
        weld_step = next((step for step in snapshot.completed_steps if step.station_id in self._weld_station_ids), None)
        weld_metadata = weld_step.metadata if weld_step else {}
        weld_obs = None
        weld_twin = None
        for station_id in self._weld_station_ids:
            observation = station_observations.get(station_id)
            if observation and observation.vehicle_id == snapshot.vehicle_id and observation.timestamp <= snapshot.prediction_timestamp:
                weld_obs = observation
            if station_id in station_twins:
                weld_twin = station_twins[station_id]
        
        if weld_twin:
            # Calculate weld energy deviation from expected
            if "weld_energy_deviation" in weld_metadata:
                snapshot.weld_energy_deviation = float(weld_metadata["weld_energy_deviation"])
            elif weld_obs and weld_obs.power is not None:
                baseline_power = 48.0  # kW baseline from simulator
                snapshot.weld_energy_deviation = (weld_obs.power - baseline_power) / baseline_power
            
            # Calculate weld variance based on twin residual
            if snapshot.station_residuals:
                weld_residuals = [r for sid, r in snapshot.station_residuals.items() if sid in self._weld_station_ids]
                if weld_residuals:
                    avg_residual = sum(weld_residuals) / len(weld_residuals)
                    baseline_stddev = weld_twin.baseline.cycle_stddev
                    snapshot.weld_variance_multiplier = float(
                        weld_metadata.get("weld_variance_multiplier", abs(avg_residual) / max(baseline_stddev, 0.1))
                    )
                    snapshot.process_variance_scores["BIW-02"] = snapshot.weld_variance_multiplier
                    snapshot.avg_process_variance = snapshot.weld_variance_multiplier
