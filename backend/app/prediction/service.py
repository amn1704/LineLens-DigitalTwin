from __future__ import annotations

from collections import deque

from ..models import TwinState
from .forward import ForwardTwinSimulator
from .models import (
    ForecastAlert,
    ForecastValidation,
    ForwardResult,
    PredictionState,
    ValidationMetric,
)
from .risk import BottleneckRiskEngine
from .snapshot import snapshot_from_twin


HORIZONS = (120, 300, 600, 900)


class PredictionService:
    """Caches Twin-driven prediction and tracks synthetic forecast validation."""

    def __init__(self) -> None:
        self._risk = BottleneckRiskEngine()
        self._forward = ForwardTwinSimulator()
        self._cache: dict[tuple, dict[str, ForwardResult]] = {}
        self._alerts: deque[ForecastAlert] = deque(maxlen=30)
        self._alert_keys: set[str] = set()
        self._previous_risk: dict[str, float] = {}
        self._alert_sequence = 0
        self._validation_trigger: float | None = None
        self._validation_results: dict[int, ForwardResult] = {}
        self._validation_metrics: dict[int, ValidationMetric] = {}
        self._first_actual_impact: float | None = None
        self._predicted_first_impact_eta: float | None = None
        self._actual_state_since: dict[str, float] = {}

    def reset(self) -> None:
        self.__init__()

    def prediction(self, state: TwinState, source_station_id: str = "FA-02") -> PredictionState:
        assessments = self._risk.assess(state)
        assessment_by_id = {assessment.station_id: assessment for assessment in assessments}
        if source_station_id not in assessment_by_id:
            source_station_id = max(assessments, key=lambda item: item.risk).station_id
        source = assessment_by_id[source_station_id]
        snapshot = snapshot_from_twin(state)
        fingerprint = (
            source_station_id,
            int(snapshot.simulation_time / 8),
            tuple((station.id, round(station.estimated_cycle, 1), station.queue_level, station.operational_state) for station in snapshot.stations),
        )
        forecasts = self._cache.get(fingerprint)
        if forecasts is None:
            forecasts = {
                str(horizon): self._forward.simulate(snapshot, horizon, source_station_id, seed=275)
                for horizon in HORIZONS
            }
            if source.risk < 0.25:
                forecasts = {
                    key: result.model_copy(update={"impacts": []}) for key, result in forecasts.items()
                }
            self._cache = {fingerprint: forecasts}
        self._update_alerts(state, assessments, source, forecasts)
        self._update_validation(state, assessments, snapshot, source_station_id, forecasts)
        return PredictionState(
            generated_at=state.simulation.simulation_time, primary_station_id=source_station_id,
            assessments=assessments, forecasts=forecasts, alerts=list(self._alerts),
            validation=self._validation_model(),
        )

    def _emit(self, state: TwinState, key: str, severity: str, source: str, message: str) -> None:
        if key in self._alert_keys:
            return
        self._alert_keys.add(key)
        self._alert_sequence += 1
        self._alerts.appendleft(ForecastAlert(
            alert_id=f"FC-{self._alert_sequence:05d}", simulation_time=state.simulation.simulation_time,
            severity=severity, source=source, message=message,
        ))

    def _update_alerts(self, state, assessments, source, forecasts) -> None:
        for assessment in assessments:
            previous = self._previous_risk.get(assessment.station_id, assessment.risk)
            for threshold, severity in ((0.35, "NOTICE"), (0.60, "WARNING"), (0.82, "CRITICAL")):
                if previous < threshold <= assessment.risk:
                    self._emit(state, f"risk:{assessment.station_id}:{threshold}", severity, assessment.station_name,
                               f"Bottleneck risk crossed {int(threshold * 100)}% · prototype forecast")
            self._previous_risk[assessment.station_id] = assessment.risk
        if source.risk >= 0.45:
            for impact in forecasts["600"].impacts[:4]:
                key = f"impact:{source.station_id}:{impact.entity_id}:{impact.impact_type}"
                label = next((item.station_name for item in assessments if item.station_id == impact.entity_id), impact.entity_id)
                message = f"{label} {impact.impact_type.replace('_', ' ').lower()} projected in {impact.eta_seconds / 60:.1f} min"
                self._emit(state, key, impact.severity, source.station_name, message)

    def _update_validation(self, state: TwinState, assessments, snapshot, source_station_id, forecasts) -> None:
        chassis = next((assessment for assessment in assessments if assessment.station_id == "FA-02"), None)
        if chassis and chassis.risk >= 0.45 and self._validation_trigger is None:
            self._validation_trigger = state.simulation.simulation_time
            if source_station_id == "FA-02":
                self._validation_results = {int(key): value for key, value in forecasts.items() if int(key) <= 600}
            else:
                self._validation_results = {
                    horizon: self._forward.simulate(snapshot, horizon, "FA-02", seed=275) for horizon in (120, 300, 600)
                }
            material_impacts = [
                impact
                for impact in self._validation_results[600].impacts
                if impact.impact_type in {"UPSTREAM_BLOCKING", "DOWNSTREAM_STARVATION"}
            ]
            self._predicted_first_impact_eta = min(
                (impact.eta_seconds for impact in material_impacts), default=None
            )
            self._emit(state, "validation:initialized", "INFO", "Forward Twin", "No-action forecast initialized for synthetic validation")
        if self._validation_trigger is None:
            return
        station_by_id = {station.id: station for station in state.stations}
        material = False
        for station_id, material_state, duration in (("FA-01", "BLOCKED", 20), ("FA-03", "STARVED", 30), ("FA-04", "STARVED", 30), ("FA-05", "STARVED", 30)):
            station = station_by_id.get(station_id)
            if station and station.operational_state.value == material_state:
                since = self._actual_state_since.setdefault(station_id, state.simulation.simulation_time)
                material = material or state.simulation.simulation_time - since >= duration
            else:
                self._actual_state_since.pop(station_id, None)
        if material and self._first_actual_impact is None:
            self._first_actual_impact = state.simulation.simulation_time
        elapsed = state.simulation.simulation_time - self._validation_trigger
        actual_accumulators = {buffer.id: buffer.level for buffer in state.buffers}
        for horizon, result in self._validation_results.items():
            if horizon in self._validation_metrics or elapsed < horizon:
                continue
            predicted = result.trajectory[-1]
            actual_queues = {station.id: station.queue_length for station in state.stations}
            queue_errors = [abs(predicted.station_queues.get(station_id, 0) - level) for station_id, level in actual_queues.items()]
            accumulator_errors = [
                abs(predicted.accumulator_levels.get(buffer_id, 0) - level)
                for buffer_id, level in actual_accumulators.items()
            ]
            state_matches = [predicted.station_states.get(station.id) == station.operational_state.value for station in state.stations]
            self._validation_metrics[horizon] = ValidationMetric(
                horizon_seconds=horizon, evaluated=True,
                queue_mae=round(sum(queue_errors) / max(1, len(queue_errors)), 3),
                accumulator_mae=round(sum(accumulator_errors) / max(1, len(accumulator_errors)), 3),
                throughput_mae=round(abs(predicted.throughput_per_hour - state.throughput_per_hour), 3),
                state_accuracy=round(sum(state_matches) / max(1, len(state_matches)), 3),
            )

    def _validation_model(self) -> ForecastValidation:
        lead = None
        if self._validation_trigger is not None and self._first_actual_impact is not None:
            lead = self._first_actual_impact - self._validation_trigger
        eta_error = None
        if lead is not None and self._predicted_first_impact_eta is not None:
            eta_error = abs(lead - self._predicted_first_impact_eta)
        return ForecastValidation(
            triggered_at=self._validation_trigger, first_actual_impact_at=self._first_actual_impact,
            prediction_lead_time_seconds=round(lead, 1) if lead is not None else None,
            impact_eta_error_seconds=round(eta_error, 1) if eta_error is not None else None,
            metrics=[self._validation_metrics.get(horizon, ValidationMetric(horizon_seconds=horizon, evaluated=False)) for horizon in (120, 300, 600)],
        )
