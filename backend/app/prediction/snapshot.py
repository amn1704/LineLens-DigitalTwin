from __future__ import annotations

from ..models import TwinState
from .models import SnapshotBuffer, SnapshotStation, TwinSnapshot


def snapshot_from_twin(state: TwinState) -> TwinSnapshot:
    """Create an immutable forward-model input using public Twin state only."""
    buffers_by_station = {buffer.downstream_station: buffer for buffer in state.buffers}
    stations: list[SnapshotStation] = []
    for station in state.stations:
        twin = station.twin
        if twin is None:
            continue
        history = twin.history[-8:]
        drift = 0.0
        if twin.residual_trend == "RISING" and len(history) >= 3:
            elapsed = history[-1].simulation_time - history[0].simulation_time
            if elapsed > 0:
                drift = max(0.0, min(0.045, (history[-1].estimated_cycle - history[0].estimated_cycle) / elapsed))
        buffer = buffers_by_station.get(station.id)
        queue_level = buffer.level if buffer else station.queue_length
        queue_capacity = buffer.capacity if buffer else 2 if station.transfer_mode == "LINE_ENTRY" else 1
        stations.append(SnapshotStation(
            id=station.id, name=station.name, expected_cycle=twin.expected_cycle,
            estimated_cycle=twin.estimated_cycle, cycle_stddev=twin.baseline.cycle_stddev,
            cycle_progress=station.cycle_progress, cycle_drift_per_second=round(drift, 5),
            operational_state=station.operational_state.value,
            queue_level=queue_level, queue_capacity=queue_capacity,
            transfer_mode=station.transfer_mode, buffer_id=buffer.id if buffer else None,
            current_busy=station.operational_state.value in {"RUNNING", "BLOCKED"},
            utilization=station.utilization, twin_confidence=twin.confidence,
            completed_vehicles=station.vehicles_completed,
        ))
    return TwinSnapshot(
        simulation_time=state.simulation.simulation_time, takt_time=state.simulation.takt_time,
        current_throughput=state.throughput_per_hour,
        current_wip=state.simulation.vehicles_in_process, stations=stations,
        buffers=[SnapshotBuffer(
            id=buffer.id, name=buffer.name, downstream_station=buffer.downstream_station,
            capacity=buffer.capacity, level=buffer.level,
        ) for buffer in state.buffers],
    )
