from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from math import exp
from statistics import fmean, pvariance

from ..models import Station, TwinState
from .models import BottleneckAssessment, BottleneckFeatures, RiskHistoryPoint


@dataclass(frozen=True)
class _Sample:
    time: float
    cycle: float
    queue: int
    completed: int
    state: str
    buffer_level: int


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return min(high, max(low, value))


class BottleneckRiskEngine:
    """Interpretable risk model whose only operational input is TwinState."""

    def __init__(self) -> None:
        self._samples: dict[str, deque[_Sample]] = defaultdict(lambda: deque(maxlen=80))
        self._risk_history: dict[str, deque[RiskHistoryPoint]] = defaultdict(lambda: deque(maxlen=120))

    def assess(self, state: TwinState) -> list[BottleneckAssessment]:
        buffer_by_station = {buffer.downstream_station: buffer.level for buffer in state.buffers}
        station_by_id = {station.id: station for station in state.stations}
        now = state.simulation.simulation_time
        for station in state.stations:
            samples = self._samples[station.id]
            if not samples or now - samples[-1].time >= 1.0:
                samples.append(_Sample(
                    time=now, cycle=station.twin.estimated_cycle if station.twin else station.cycle_time,
                    queue=station.queue_length, completed=station.vehicles_completed,
                    state=station.operational_state.value,
                    buffer_level=buffer_by_station.get(station.id, 0),
                ))

        assessments: list[BottleneckAssessment] = []
        for index, station in enumerate(state.stations):
            if station.twin is None:
                continue
            downstream = state.stations[index + 1] if index + 1 < len(state.stations) else None
            features = self._features(station, downstream, station_by_id)
            risk = self._risk(features)
            confidence = self._confidence(station, features)
            level = "LOW" if risk < 0.25 else "ELEVATED" if risk < 0.50 else "HIGH" if risk < 0.75 else "SEVERE"
            evidence = self._evidence(station, features)
            history = self._risk_history[station.id]
            if not history or now - history[-1].simulation_time >= 2.0:
                history.append(RiskHistoryPoint(simulation_time=round(now, 1), risk=round(risk, 3), confidence=round(confidence, 3)))
            assessments.append(BottleneckAssessment(
                station_id=station.id, station_name=station.name, risk=round(risk, 3),
                confidence=round(confidence, 3), level=level, features=features,
                evidence=evidence, history=list(history),
            ))
        return assessments

    def _rate(self, station_id: str, expected_cycle: float) -> float:
        samples = self._samples[station_id]
        if len(samples) < 2 or samples[-1].time <= samples[0].time:
            return 3600 / max(expected_cycle, 1)
        elapsed = samples[-1].time - samples[0].time
        completed = max(0, samples[-1].completed - samples[0].completed)
        return completed / elapsed * 3600 if completed else 0.0

    def _features(self, station: Station, downstream: Station | None, station_by_id: dict[str, Station]) -> BottleneckFeatures:
        twin = station.twin
        assert twin is not None
        samples = self._samples[station.id]
        recent_cycles = [point.estimated_cycle for point in twin.history[-10:]] or [twin.estimated_cycle]
        completion_rate = self._rate(station.id, twin.expected_cycle)
        expected_rate = 3600 / max(twin.expected_cycle, 1)
        downstream_rate = self._rate(downstream.id, downstream.twin.expected_cycle) if downstream and downstream.twin else completion_rate
        elapsed = samples[-1].time - samples[0].time if len(samples) > 1 else 0.0
        queue_growth = (samples[-1].queue + samples[-1].buffer_level - samples[0].queue - samples[0].buffer_level) / max(elapsed / 60, 1) if elapsed else 0.0
        blocked_ratio = sum(sample.state == "BLOCKED" for sample in samples) / max(1, len(samples))
        starved_ratio = sum(sample.state == "STARVED" for sample in samples) / max(1, len(samples))
        buffer_fill_rate = (samples[-1].buffer_level - samples[0].buffer_level) / max(elapsed / 60, 1) if elapsed else 0.0
        healthy_envelope = max(3 * twin.baseline.cycle_stddev, 4.0)
        evidence_points = twin.history[-8:]
        persistent = sum(point.residual > healthy_envelope for point in evidence_points) / max(4, len(evidence_points))
        return BottleneckFeatures(
            cycle_to_takt_ratio=round(twin.estimated_cycle / max(station.takt_time, 1), 3),
            health_residual=twin.residual, normalized_residual=twin.normalized_deviation,
            residual_trend=twin.residual_trend,
            rolling_cycle_mean=round(fmean(recent_cycles), 2),
            rolling_cycle_variance=round(pvariance(recent_cycles), 3) if len(recent_cycles) > 1 else 0.0,
            station_completion_rate=round(completion_rate, 2),
            completion_rate_change=round((completion_rate - expected_rate) / max(expected_rate, 1), 3),
            upstream_queue_growth=round(queue_growth, 3), downstream_arrival_rate=round(downstream_rate, 2),
            utilization=station.utilization, blocked_time_ratio=round(blocked_ratio, 3),
            starved_time_ratio=round(starved_ratio, 3), accumulator_fill_rate=round(buffer_fill_rate, 3),
            evidence_persistence=round(_clamp(persistent), 3),
        )

    def _risk(self, f: BottleneckFeatures) -> float:
        residual_pressure = _clamp((f.normalized_residual - 2.0) / 4.0)
        rolling_pressure = _clamp((f.rolling_cycle_mean / max(1.0, f.rolling_cycle_mean - f.health_residual) - 1.04) / 0.20)
        takt_pressure = _clamp((f.cycle_to_takt_ratio - 1.04) / 0.28)
        trend = 1.0 if f.residual_trend == "RISING" else 0.28 if f.residual_trend == "STABLE" and f.health_residual > 0 else 0.0
        completion_loss = _clamp(-f.completion_rate_change / 0.25)
        queue_growth = _clamp(f.upstream_queue_growth / 2.0)
        variability = _clamp(f.rolling_cycle_variance / 18.0)
        z = (
            -3.55
            + 2.0 * residual_pressure * (0.35 + 0.65 * f.evidence_persistence)
            + 1.15 * rolling_pressure
            + 0.85 * takt_pressure
            + 0.75 * trend * f.evidence_persistence
            + 0.55 * completion_loss
            + 0.48 * queue_growth
            + 0.28 * variability
            + 0.35 * f.blocked_time_ratio
        )
        return _clamp(1 / (1 + exp(-z)), 0.01, 0.96)

    def _confidence(self, station: Station, f: BottleneckFeatures) -> float:
        twin_confidence = station.twin.confidence if station.twin else 0.4
        history_depth = min(1.0, len(self._samples[station.id]) / 12)
        stability = exp(-f.rolling_cycle_variance / 45.0)
        score = twin_confidence * 0.68 + history_depth * 0.16 + stability * 0.12 + f.evidence_persistence * 0.04
        return _clamp(score, 0.18, 0.97)

    def _evidence(self, station: Station, f: BottleneckFeatures) -> list[str]:
        expected_rate = 3600 / max(station.twin.expected_cycle if station.twin else station.nominal_cycle_time, 1)
        completion_delta = (f.station_completion_rate - expected_rate) / max(expected_rate, 1) * 100
        return [
            f"Twin cycle {station.twin.estimated_cycle:.1f}s vs expected {station.twin.expected_cycle:.1f}s",
            f"Residual {station.twin.residual:+.1f}s · {station.twin.residual_trend.lower()}",
            f"Cycle / takt {f.cycle_to_takt_ratio:.2f}×",
            f"Incoming queue {station.queue_length} · growth {f.upstream_queue_growth:+.1f}/min",
            f"Recent completion rate {completion_delta:+.0f}% vs healthy",
        ]
