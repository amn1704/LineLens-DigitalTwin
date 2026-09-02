from __future__ import annotations

from dataclasses import dataclass
from random import Random

from .models import (
    ForecastImpact,
    ForwardResult,
    ForwardScenario,
    OutcomeMetrics,
    TrajectoryPoint,
    TwinSnapshot,
)


TRANSFER_SECONDS = 4.0
STEP_SECONDS = 2.0
SAMPLE_SECONDS = 30


@dataclass
class _ForwardStation:
    busy: bool
    remaining: float
    queue: int
    state: str
    blocked_time: float = 0.0
    starved_time: float = 0.0
    completed: int = 0
    peak_queue: int = 0


@dataclass
class _Transfer:
    target: int
    remaining: float


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return min(high, max(low, value))


class ForwardTwinSimulator:
    """Disposable deterministic production-flow clone built from a TwinSnapshot."""

    def simulate(self, snapshot: TwinSnapshot, horizon_seconds: int, source_station_id: str, seed: int = 275) -> ForwardResult:
        if horizon_seconds not in {120, 300, 600, 900}:
            raise ValueError("Horizon must be 120, 300, 600, or 900 seconds")
        rng = Random(seed)
        specs = snapshot.stations
        source_index = next((i for i, spec in enumerate(specs) if spec.id == source_station_id), 0)
        buffers = {buffer.downstream_station: buffer for buffer in snapshot.buffers}
        states = [
            _ForwardStation(
                busy=station.current_busy,
                remaining=max(0.0, station.estimated_cycle * (1 - station.cycle_progress)) if station.current_busy else 0.0,
                queue=station.queue_level,
                state=station.operational_state,
                peak_queue=station.queue_level,
            )
            for station in specs
        ]
        initial_queues = {station.id: states[index].queue for index, station in enumerate(specs)}
        initial_buffers = {buffer.id: buffer.level for buffer in snapshot.buffers}
        transfers: list[_Transfer] = []
        accumulator_peak = dict(initial_buffers)
        first_queue_growth: dict[int, float] = {}
        first_blocked: dict[int, float] = {}
        first_starved: dict[int, float] = {}
        total_completed = 0
        next_entry = snapshot.takt_time
        trajectory: list[TrajectoryPoint] = []

        def capacity(index: int) -> int:
            return specs[index].queue_capacity

        def pending(index: int) -> int:
            return sum(transfer.target == index for transfer in transfers)

        def projected_cycle(index: int, offset: float) -> float:
            spec = specs[index]
            trend = spec.cycle_drift_per_second * offset
            deterministic_variation = rng.gauss(0.0, spec.cycle_stddev * 0.10)
            return max(spec.expected_cycle * 0.75, spec.estimated_cycle + trend + deterministic_variation)

        def sample(offset: int) -> None:
            elapsed = max(offset, 1)
            throughput = total_completed / elapsed * 3600
            station_queues = {spec.id: states[i].queue for i, spec in enumerate(specs)}
            station_states = {spec.id: states[i].state for i, spec in enumerate(specs)}
            accumulator_levels = {
                buffer.id: states[next(i for i, spec in enumerate(specs) if spec.id == buffer.downstream_station)].queue
                for buffer in snapshot.buffers
            }
            wip = sum(int(state.busy) + state.queue for state in states) + len(transfers)
            trajectory.append(TrajectoryPoint(
                offset_seconds=offset, throughput_per_hour=round(throughput if offset else snapshot.current_throughput, 2),
                completed_vehicles=total_completed, wip=wip, station_queues=station_queues,
                station_states=station_states, accumulator_levels=accumulator_levels,
            ))

        sample(0)
        for offset in range(int(STEP_SECONDS), horizon_seconds + 1, int(STEP_SECONDS)):
            if offset >= next_entry:
                if states[0].queue < capacity(0):
                    states[0].queue += 1
                next_entry += snapshot.takt_time

            for transfer in list(transfers):
                transfer.remaining -= STEP_SECONDS
                if transfer.remaining <= 0 and states[transfer.target].queue < capacity(transfer.target):
                    states[transfer.target].queue += 1
                    transfers.remove(transfer)

            for index in reversed(range(len(states))):
                state = states[index]
                if state.busy:
                    state.remaining -= STEP_SECONDS
                    if state.remaining <= 0:
                        if index == len(states) - 1:
                            state.busy = False
                            state.completed += 1
                            total_completed += 1
                        elif states[index + 1].queue + pending(index + 1) < capacity(index + 1):
                            state.busy = False
                            state.completed += 1
                            transfers.append(_Transfer(index + 1, TRANSFER_SECONDS))
                        else:
                            state.state = "BLOCKED"
                            state.blocked_time += STEP_SECONDS
                            first_blocked.setdefault(index, float(offset))
                if not state.busy and state.queue > 0:
                    state.queue -= 1
                    state.busy = True
                    state.remaining = projected_cycle(index, float(offset))
                    state.state = "RUNNING"
                elif not state.busy:
                    state.state = "STARVED"
                    state.starved_time += STEP_SECONDS
                    if state.starved_time >= 12:
                        # Downstream propagation is recorded only after the immediately
                        # preceding process has itself shown sustained arrival loss.
                        if index == source_index + 1 or index - 1 in first_starved:
                            first_starved.setdefault(index, float(offset - 10))
                elif state.state != "BLOCKED":
                    state.state = "RUNNING"
                state.peak_queue = max(state.peak_queue, state.queue)
                if state.queue > initial_queues[specs[index].id]:
                    first_queue_growth.setdefault(index, float(offset))

            for buffer in snapshot.buffers:
                buffer_index = next(i for i, spec in enumerate(specs) if spec.id == buffer.downstream_station)
                accumulator_peak[buffer.id] = max(accumulator_peak[buffer.id], states[buffer_index].queue)
            if offset % SAMPLE_SECONDS == 0 or offset == horizon_seconds:
                sample(offset)

        average_confidence = sum(spec.twin_confidence for spec in specs) / max(1, len(specs))
        variability = sum(spec.cycle_stddev for spec in specs) / max(1, len(specs))
        forecast_confidence = _clamp(average_confidence * (1 - horizon_seconds / 4200) * (1 / (1 + variability / 45)), 0.25, 0.94)
        final = trajectory[-1]
        impacts: list[ForecastImpact] = []

        def add_impact(index: int, impact_type: str, eta: float, current: float | str, projected: float | str, severity: str) -> None:
            spread = 15 + eta * (1 - forecast_confidence) * 0.34
            impacts.append(ForecastImpact(
                entity_id=specs[index].id, entity_type="STATION", impact_type=impact_type,
                eta_seconds=round(eta, 1), eta_range_low=round(max(0, eta - spread), 1),
                eta_range_high=round(eta + spread, 1), confidence=round(forecast_confidence, 3),
                current_value=current, projected_value=projected, severity=severity,
            ))

        for index, eta in first_queue_growth.items():
            if source_index - 1 <= index <= source_index and final.station_queues[specs[index].id] > initial_queues[specs[index].id]:
                # A one-step queue fluctuation can clear before it becomes a visible
                # congestion trend. Report the first persisted trajectory crossing so
                # the ETA is directly auditable in the operator-facing forecast chart.
                sampled_crossing = next(
                    (
                        point.offset_seconds
                        for point in trajectory
                        if point.station_queues[specs[index].id] > initial_queues[specs[index].id]
                    ),
                    eta,
                )
                add_impact(index, "QUEUE_GROWTH", float(sampled_crossing), initial_queues[specs[index].id], final.station_queues[specs[index].id], "NOTICE")
        for index, eta in first_blocked.items():
            if index < source_index:
                add_impact(index, "UPSTREAM_BLOCKING", eta, specs[index].operational_state, "BLOCKED", "WARNING")
        for index, eta in first_starved.items():
            if index > source_index:
                add_impact(index, "DOWNSTREAM_STARVATION", eta, specs[index].operational_state, "STARVED", "WARNING")

        throughput_change = (final.throughput_per_hour - snapshot.current_throughput) / max(snapshot.current_throughput, 1) * 100
        if throughput_change <= -8:
            spread = 20 + horizon_seconds * (1 - forecast_confidence) * 0.12
            impacts.append(ForecastImpact(
                entity_id="LINE", entity_type="LINE", impact_type="THROUGHPUT_LOSS",
                eta_seconds=float(horizon_seconds), eta_range_low=max(0, horizon_seconds - spread),
                eta_range_high=horizon_seconds + spread, confidence=round(forecast_confidence, 3),
                current_value=snapshot.current_throughput, projected_value=final.throughput_per_hour,
                severity="WARNING" if throughput_change > -18 else "CRITICAL",
            ))
        impacts.sort(key=lambda impact: impact.eta_seconds)
        metrics = OutcomeMetrics(
            throughput_per_hour=final.throughput_per_hour,
            throughput_change_percent=round(throughput_change, 1), completed_vehicles=total_completed,
            wip=final.wip, peak_queue=max(state.peak_queue for state in states),
            blocked_time_seconds=round(sum(state.blocked_time for state in states), 1),
            starved_time_seconds=round(sum(state.starved_time for state in states), 1),
            accumulator_peak=accumulator_peak,
        )
        return ForwardResult(
            snapshot_time=snapshot.simulation_time, source_station_id=source_station_id,
            scenario=ForwardScenario(horizon_seconds=horizon_seconds, seed=seed),
            forecast_confidence=round(forecast_confidence, 3), trajectory=trajectory,
            impacts=impacts, metrics=metrics,
        )
