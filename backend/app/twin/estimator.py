from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from math import exp, sqrt

from ..models import (
    SensorMode,
    StationBaseline,
    StationObservation,
    StationTwinEstimate,
    TwinHistoryPoint,
    TwinSynchronization,
)


@dataclass(frozen=True)
class StationDefinition:
    station_id: str
    sensor_mode: SensorMode
    nominal_cycle: float


@dataclass
class _Baseline:
    cycle_mean: float
    cycle_variance: float = 4.0
    utilization_mean: float = 0.82
    queue_mean: float = 0.8
    samples: int = 0

    @property
    def cycle_stddev(self) -> float:
        return max(0.7, sqrt(max(self.cycle_variance, 0.49)))

    def update(self, cycle: float, utilization: float | None, queue: int | None) -> None:
        # A slow EWMA keeps personal healthy fingerprints stable.  A 3σ gate prevents
        # blocked/starved excursions and extreme noise from becoming the new normal.
        envelope = max(3 * self.cycle_stddev, 4.0)
        if self.samples >= 5 and abs(cycle - self.cycle_mean) > envelope:
            return
        alpha = 0.11 if self.samples < 12 else 0.045
        previous = self.cycle_mean
        self.cycle_mean += alpha * (cycle - self.cycle_mean)
        self.cycle_variance = max(0.49, (1 - alpha) * (self.cycle_variance + alpha * (cycle - previous) ** 2))
        if utilization is not None:
            self.utilization_mean += alpha * (utilization - self.utilization_mean)
        if queue is not None:
            self.queue_mean += alpha * (queue - self.queue_mean)
        self.samples += 1


@dataclass
class _Estimate:
    cycle: float
    last_observation: float | None = None
    last_assimilation: float = 0.0
    observed_cycle: float | None = None
    last_completed_timestamp: float | None = None
    residuals: deque[float] = field(default_factory=lambda: deque(maxlen=8))
    history: deque[TwinHistoryPoint] = field(default_factory=lambda: deque(maxlen=100))
    confidence: float = 0.45
    source: str = "Estimated from historical process model"
    evidence: list[str] = field(default_factory=list)
    indirect: bool = True


class TwinStateEstimator:
    """Explainable observation-only estimator using EWMA baselines and adaptive filtering.

    The simulator calls :meth:`assimilate` with `StationObservation` values.  This
    class does not receive StationRuntime objects or direct access to simulator
    fields, which keeps the prototype's ground-truth boundary explicit.
    """

    def __init__(self, definitions: list[StationDefinition]) -> None:
        self._definitions = {definition.station_id: definition for definition in definitions}
        self._baselines = {definition.station_id: _Baseline(definition.nominal_cycle) for definition in definitions}
        self._estimates = {definition.station_id: _Estimate(definition.nominal_cycle) for definition in definitions}
        self._last_assimilation = 0.0

    def bootstrap(self, observations: list[StationObservation], simulation_time: float) -> None:
        """Prime each station with synthetic warm-shift observations, never raw truth."""
        for observation in sorted(observations, key=lambda item: item.timestamp):
            baseline = self._baselines[observation.station_id]
            estimate = self._estimates[observation.station_id]
            if observation.completed_cycle_time is not None:
                baseline.update(observation.completed_cycle_time, None, observation.queue_level)
                estimate.cycle += 0.35 * (observation.completed_cycle_time - estimate.cycle)
            estimate.last_observation = observation.timestamp
            estimate.last_assimilation = simulation_time
            maturity_confidence = {
                SensorMode.FULL: 0.82,
                SensorMode.LIMITED: 0.70,
                SensorMode.BASIC: 0.58,
            }[self._definitions[observation.station_id].sensor_mode]
            estimate.confidence = max(estimate.confidence, maturity_confidence)

    def assimilate(self, observations: list[StationObservation], simulation_time: float) -> None:
        observed_by_station = {observation.station_id: observation for observation in observations}
        for station_id, definition in self._definitions.items():
            observation = observed_by_station.get(station_id)
            estimate = self._estimates[station_id]
            baseline = self._baselines[station_id]
            if observation is None:
                # Missing data is deliberately not filled from plant truth.  The last
                # credible estimate remains available while confidence decays.
                estimate.confidence = max(0.18, estimate.confidence * 0.975)
                estimate.last_assimilation = simulation_time
                residual = estimate.cycle - baseline.cycle_mean
                estimate.history.append(TwinHistoryPoint(
                    simulation_time=round(simulation_time, 1), observed_cycle=None,
                    estimated_cycle=round(estimate.cycle, 2), expected_cycle=round(baseline.cycle_mean, 2),
                    residual=round(residual, 2), confidence=round(estimate.confidence, 3),
                ))
                continue

            estimate.last_observation = observation.timestamp
            estimate.last_assimilation = simulation_time
            direct_cycle = observation.cycle_time
            completed_cycle = observation.completed_cycle_time
            healthy = observation.operational_state is not None and observation.operational_state.value not in {"BLOCKED", "STARVED", "WARNING", "OFFLINE"}
            baseline_eligible = (
                completed_cycle is not None
                and healthy
                and observation.quality >= 0.72
                and (baseline.samples < 5 or abs(completed_cycle - baseline.cycle_mean) <= max(3 * baseline.cycle_stddev, 4.0))
            )
            if baseline_eligible and observation.last_departure_timestamp != estimate.last_completed_timestamp:
                baseline.update(completed_cycle, None, observation.queue_level)
                estimate.last_completed_timestamp = observation.last_departure_timestamp

            if direct_cycle is not None:
                # Full telemetry: current observed cycle is the main measurement.
                # Full telemetry remains the strongest evidence, but a moderate
                # adaptive gain prevents short-lived sensor noise from appearing as
                # a physical process change in the twin.
                gain = 0.36 * observation.quality
                candidate = direct_cycle
                estimate.observed_cycle = direct_cycle
                estimate.indirect = False
                estimate.source = "Full telemetry"
                estimate.evidence = ["PLC cycle events", "vehicle timestamps", *observation.signals[:2]]
            else:
                # Limited and legacy cells use process evidence without inventing a
                # direct cycle sensor.  Completion timestamps influence the estimate
                # only after they arrive; otherwise topology and baseline dominate.
                latest_cycle = completed_cycle if completed_cycle is not None else baseline.cycle_mean
                queue_delta = (observation.queue_level if observation.queue_level is not None else baseline.queue_mean) - baseline.queue_mean
                age_term = 0.0
                if observation.entry_timestamp is not None and observation.operational_state == "RUNNING":
                    age_term = max(0.0, simulation_time - observation.entry_timestamp - baseline.cycle_mean) * 0.12
                candidate = latest_cycle * 0.78 + baseline.cycle_mean * 0.22 + queue_delta * 0.34 + age_term
                gain = (0.44 if definition.sensor_mode is SensorMode.LIMITED else 0.30) * observation.quality
                estimate.observed_cycle = None
                estimate.indirect = True
                estimate.source = "Limited telemetry" if definition.sensor_mode is SensorMode.LIMITED else "Legacy / basic signals"
                estimate.evidence = [*observation.signals[:3], "Historical process model"]

            estimate.cycle += max(0.08, gain) * (candidate - estimate.cycle)
            residual = estimate.cycle - baseline.cycle_mean
            estimate.residuals.append(residual)
            target_confidence = self._confidence(definition, observation, estimate, baseline, simulation_time)
            # Recovery is progressive after a data gap; it never snaps from stale to fully synchronized.
            estimate.confidence += 0.38 * (target_confidence - estimate.confidence)
            estimate.history.append(TwinHistoryPoint(
                simulation_time=round(simulation_time, 1), observed_cycle=round(direct_cycle, 2) if direct_cycle is not None else None,
                estimated_cycle=round(estimate.cycle, 2), expected_cycle=round(baseline.cycle_mean, 2),
                residual=round(residual, 2), confidence=round(estimate.confidence, 3),
            ))
        self._last_assimilation = simulation_time

    def _confidence(self, definition: StationDefinition, observation: StationObservation, estimate: _Estimate, baseline: _Baseline, now: float) -> float:
        base = {SensorMode.FULL: 0.90, SensorMode.LIMITED: 0.72, SensorMode.BASIC: 0.58}[definition.sensor_mode]
        signal_score = min(1.0, len(observation.signals) / (5 if definition.sensor_mode is SensorMode.FULL else 3))
        age = max(0.0, now - observation.timestamp)
        freshness = exp(-age / 80)
        consistency = exp(-abs(estimate.cycle - baseline.cycle_mean) / max(baseline.cycle_stddev * 5, 3))
        history = min(1.0, baseline.samples / 12)
        quality = observation.quality
        score = base * 0.50 + signal_score * 0.13 + freshness * 0.13 + consistency * 0.11 + history * 0.05 + quality * 0.03
        return min(0.99, max(0.18, score))

    def station_estimate(self, station_id: str, simulation_time: float) -> StationTwinEstimate:
        baseline = self._baselines[station_id]
        estimate = self._estimates[station_id]
        age = max(0.0, simulation_time - estimate.last_observation) if estimate.last_observation is not None else simulation_time
        if age > 0:
            confidence = max(0.18, estimate.confidence * exp(-age / 240))
        else:
            confidence = estimate.confidence
        source = estimate.source
        evidence = estimate.evidence or ["Historical process model"]
        indirect = estimate.indirect
        if age > 8:
            source = "Estimated after data gap"
            evidence = ["Last valid observation", "Topology continuity", "Historical process model"]
            indirect = True
        residual = estimate.cycle - baseline.cycle_mean
        residual_history = list(estimate.residuals)
        trend = "STABLE"
        if len(residual_history) >= 4:
            recent = sum(residual_history[-3:]) / 3
            earlier = sum(residual_history[:3]) / min(3, len(residual_history))
            threshold = max(0.35, baseline.cycle_stddev * 0.18)
            trend = "RISING" if recent - earlier > threshold else "FALLING" if earlier - recent > threshold else "STABLE"
        spread = baseline.cycle_stddev * (1.1 + (1 - confidence) * 1.8)
        return StationTwinEstimate(
            expected_cycle=round(baseline.cycle_mean, 2), estimated_cycle=round(estimate.cycle, 2),
            estimated_range_low=round(max(0, estimate.cycle - spread), 2), estimated_range_high=round(estimate.cycle + spread, 2),
            observed_cycle=round(estimate.observed_cycle, 2) if estimate.observed_cycle is not None else None,
            residual=round(residual, 2), normalized_deviation=round(residual / max(baseline.cycle_stddev, 0.7), 2), residual_trend=trend,
            confidence=round(confidence, 3), data_age=round(age, 1), source=source,
            evidence=evidence, estimated_from_indirect_evidence=indirect,
            last_observation=round(estimate.last_observation, 1) if estimate.last_observation is not None else None,
            last_assimilation=round(estimate.last_assimilation, 1), baseline=StationBaseline(
                expected_cycle=round(baseline.cycle_mean, 2), cycle_stddev=round(baseline.cycle_stddev, 2),
                expected_utilization=round(baseline.utilization_mean, 3), normal_queue=round(baseline.queue_mean, 2), samples=baseline.samples,
            ), history=list(estimate.history),
        )

    def synchronization(self, simulation_time: float) -> TwinSynchronization:
        estimates = [self.station_estimate(station_id, simulation_time) for station_id in self._definitions]
        confidence = sum(estimate.confidence for estimate in estimates) / max(1, len(estimates))
        coverage = sum(estimate.data_age < 24 for estimate in estimates) / max(1, len(estimates))
        latest = max((estimate.last_assimilation for estimate in estimates), default=0.0)
        age = max(0.0, simulation_time - latest)
        status = "TWIN SYNCHRONIZED" if confidence >= 0.74 and coverage >= 0.7 else "TWIN PARTIALLY SYNCHRONIZED"
        return TwinSynchronization(status=status, overall_confidence=round(confidence, 3), data_coverage=round(coverage, 3), last_assimilation=round(latest, 1), data_age=round(age, 1))
