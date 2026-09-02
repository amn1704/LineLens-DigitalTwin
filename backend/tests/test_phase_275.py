from __future__ import annotations

import inspect
import statistics
import unittest

from backend.app.models import OperationalState, SensorMode, StationObservation
from backend.app.simulation import AssemblyLineSimulator, CONNECTIONS, SPECS
from backend.app.twin.estimator import StationDefinition, TwinStateEstimator


def observation(
    station_id: str,
    timestamp: float,
    *,
    cycle: float | None = 60.0,
    completed: float | None = None,
    quality: float = 0.96,
    state: OperationalState = OperationalState.RUNNING,
) -> StationObservation:
    return StationObservation(
        station_id=station_id,
        timestamp=timestamp,
        operational_state=state,
        vehicle_id="VH-TEST" if cycle is not None else None,
        queue_level=1,
        cycle_time=cycle,
        cycle_progress=0.5 if cycle is not None else None,
        completed_cycle_time=completed,
        entry_timestamp=timestamp - 20,
        last_departure_timestamp=timestamp if completed is not None else None,
        conveyor_occupied=True,
        source="Deterministic test observation",
        quality=quality,
        signals=["PLC state", "cycle timestamp", "vehicle identity", "tool telemetry"] if cycle is not None else ["PLC state", "conveyor occupancy"],
    )


class EstimatorArchitectureTests(unittest.TestCase):
    def make_estimator(self, mode: SensorMode = SensorMode.FULL, nominal: float = 60.0) -> TwinStateEstimator:
        estimator = TwinStateEstimator([StationDefinition("S-01", mode, nominal)])
        warm = [observation("S-01", float(i), cycle=nominal, completed=nominal) for i in range(1, 9)]
        estimator.bootstrap(warm, 10.0)
        return estimator

    def test_estimator_has_no_station_runtime_dependency(self) -> None:
        source = inspect.getsource(TwinStateEstimator)
        self.assertIn("StationObservation", source)
        self.assertNotIn("._stations", source)
        self.assertNotIn("._vehicles", source)
        parameters = inspect.signature(TwinStateEstimator.assimilate).parameters
        self.assertIn("StationObservation", str(parameters["observations"].annotation))

    def test_estimator_continues_during_dropout(self) -> None:
        estimator = self.make_estimator()
        estimator.assimilate([observation("S-01", 20.0, cycle=62.0)], 20.0)
        before = estimator.station_estimate("S-01", 20.0)
        estimator.assimilate([], 30.0)
        after = estimator.station_estimate("S-01", 30.0)
        self.assertAlmostEqual(after.estimated_cycle, before.estimated_cycle, places=5)

    def test_observed_history_has_gap_during_dropout(self) -> None:
        estimator = self.make_estimator()
        estimator.assimilate([observation("S-01", 20.0, cycle=62.0)], 20.0)
        estimator.assimilate([], 30.0)
        history = estimator.station_estimate("S-01", 30.0).history
        self.assertIsNotNone(history[-2].observed_cycle)
        self.assertIsNone(history[-1].observed_cycle)

    def test_confidence_falls_with_observation_age(self) -> None:
        estimator = self.make_estimator()
        estimator.assimilate([observation("S-01", 20.0)], 20.0)
        fresh = estimator.station_estimate("S-01", 20.0).confidence
        estimator.assimilate([], 60.0)
        stale = estimator.station_estimate("S-01", 60.0).confidence
        self.assertLess(stale, fresh)

    def test_confidence_recovers_progressively_after_restoration(self) -> None:
        estimator = self.make_estimator()
        estimator.assimilate([observation("S-01", 20.0)], 20.0)
        estimator.assimilate([], 60.0)
        stale = estimator.station_estimate("S-01", 60.0).confidence
        estimator.assimilate([observation("S-01", 61.0, cycle=60.8)], 61.0)
        restored = estimator.station_estimate("S-01", 61.0).confidence
        self.assertGreater(restored, stale)
        self.assertLess(restored, 0.99)

    def test_noise_is_filtered_and_expected_baseline_remains_stable(self) -> None:
        estimator = self.make_estimator()
        injected = [-5.0, 4.5, -4.0, 5.0, -3.5, 4.0, -4.8, 3.8, -3.0, 4.6, -4.2, 3.4]
        observed_values, twin_values, expected_values = [], [], []
        for index, offset in enumerate(injected, start=20):
            value = 60.0 + offset
            estimator.assimilate([observation("S-01", float(index), cycle=value, quality=0.70)], float(index))
            estimate = estimator.station_estimate("S-01", float(index))
            observed_values.append(value)
            twin_values.append(estimate.estimated_cycle)
            expected_values.append(estimate.expected_cycle)
        observed_variance = statistics.pvariance(observed_values)
        twin_variance = statistics.pvariance(twin_values)
        self.assertGreater(observed_variance, twin_variance * 2)
        self.assertLess(statistics.pvariance(expected_values), 0.01)

    def test_station_specific_baselines_differ(self) -> None:
        definitions = [StationDefinition("A", SensorMode.FULL, 55.0), StationDefinition("B", SensorMode.FULL, 63.0)]
        estimator = TwinStateEstimator(definitions)
        warm = []
        for i in range(8):
            warm.extend([observation("A", i, cycle=55.0, completed=55.0), observation("B", i, cycle=63.0, completed=63.0)])
        estimator.bootstrap(warm, 10.0)
        self.assertNotEqual(estimator.station_estimate("A", 10).expected_cycle, estimator.station_estimate("B", 10).expected_cycle)

    def test_abnormal_period_does_not_modify_healthy_baseline(self) -> None:
        estimator = self.make_estimator()
        before = estimator.station_estimate("S-01", 10.0).baseline
        estimator.assimilate([observation("S-01", 20.0, cycle=None, completed=91.0, state=OperationalState.BLOCKED)], 20.0)
        after = estimator.station_estimate("S-01", 20.0).baseline
        self.assertEqual(after.samples, before.samples)
        self.assertEqual(after.expected_cycle, before.expected_cycle)


class SimulationInvariantTests(unittest.TestCase):
    def setUp(self) -> None:
        self.simulator = AssemblyLineSimulator()
        self.simulator.pause()

    def tearDown(self) -> None:
        self.simulator.shutdown()

    def test_legacy_observations_exclude_unavailable_direct_telemetry(self) -> None:
        by_id = {item.station_id: item for item in self.simulator.observations()}
        for spec in SPECS:
            if spec.sensor_mode is SensorMode.BASIC:
                self.assertIsNone(by_id[spec.station_id].cycle_time)
                self.assertIsNone(by_id[spec.station_id].cycle_progress)
                self.assertIsNone(by_id[spec.station_id].vehicle_id)
                self.assertIsNone(by_id[spec.station_id].temperature)

    def test_vehicle_thread_process_order_is_correct(self) -> None:
        vehicle = next(item for item in self.simulator.vehicles() if item.current_station == "FA-04")
        thread = self.simulator.vehicle_thread(vehicle.vehicle_id)
        self.assertIsNotNone(thread)
        expected = [spec.station_id for spec in SPECS[:9]]
        self.assertEqual([step.station_id for step in thread.completed_steps], expected)

    def test_completed_vehicle_thread_persists_with_monotonic_timestamps(self) -> None:
        vehicle = next(item for item in self.simulator.vehicles() if item.current_station == "FA-05")
        self.simulator._advance(90.0)
        thread = self.simulator.vehicle_thread(vehicle.vehicle_id)
        self.assertIsNotNone(thread)
        self.assertIsNone(thread.current_station)
        self.assertEqual([step.station_id for step in thread.completed_steps], [spec.station_id for spec in SPECS])
        for previous, following in zip(thread.completed_steps, thread.completed_steps[1:]):
            self.assertLessEqual(previous.exit_time, following.entry_time)

    def test_explicit_accumulation_capacity_is_never_exceeded(self) -> None:
        for _ in range(900):
            self.simulator._advance(1.0)
            for connection in CONNECTIONS:
                if connection.buffer_id:
                    self.assertLessEqual(len(self.simulator._buffers[connection.buffer_id]), connection.capacity)

    def test_direct_connections_do_not_invent_buffer_entities(self) -> None:
        state = self.simulator.state()
        actual_ids = {buffer.id for buffer in state.buffers}
        expected_ids = {connection.buffer_id for connection in CONNECTIONS if connection.buffer_id}
        self.assertEqual(actual_ids, expected_ids)
        for connection in CONNECTIONS:
            if connection.mode == "DIRECT_COUPLED":
                self.assertIsNone(connection.buffer_id)


if __name__ == "__main__":
    unittest.main()
