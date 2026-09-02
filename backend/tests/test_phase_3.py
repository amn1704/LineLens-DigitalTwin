from __future__ import annotations

import inspect
import unittest

from backend.app.models import TwinHistoryPoint
from backend.app.prediction import PredictionService
from backend.app.prediction.forward import ForwardTwinSimulator
from backend.app.prediction.risk import BottleneckRiskEngine
from backend.app.prediction.snapshot import snapshot_from_twin
from backend.app.simulation import AssemblyLineSimulator


class Phase3PredictionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.simulator = AssemblyLineSimulator()
        self.simulator.pause()

    def tearDown(self) -> None:
        self.simulator.shutdown()

    def drifted_prediction(self):
        service = PredictionService()
        self.simulator.set_chassis_drift(True)
        prediction = None
        for _ in range(18):
            self.simulator._advance(15.0)
            prediction = service.prediction(self.simulator.state(), "FA-02")
        return service, prediction

    def test_a_scenario_changes_physical_process_only(self) -> None:
        vehicle = next(vehicle for vehicle in self.simulator._vehicles.values() if vehicle.current_index == 7)
        healthy_cycle = self.simulator._cycle_for(7, vehicle)
        self.simulator.set_chassis_drift(True)
        self.simulator._scenario_started = self.simulator._simulation_time - 360
        drifted_cycle = self.simulator._cycle_for(7, vehicle)
        self.assertGreater(drifted_cycle, healthy_cycle + 12)
        scenario_source = inspect.getsource(AssemblyLineSimulator.set_chassis_drift)
        self.assertNotIn("risk", scenario_source.lower())
        self.assertNotIn("forecast", scenario_source.lower())

    def test_b_risk_responds_to_twin_degradation_without_scenario_flag(self) -> None:
        state = self.simulator.state()
        stations = list(state.stations)
        index = next(i for i, station in enumerate(stations) if station.id == "FA-02")
        twin = stations[index].twin
        history = [TwinHistoryPoint(simulation_time=1200 + i * 2, observed_cycle=70 + i * .4, estimated_cycle=68 + i * .5, expected_cycle=60, residual=8 + i * .5, confidence=.8) for i in range(8)]
        degraded_twin = twin.model_copy(update={"estimated_cycle": 72.0, "residual": 12.0, "normalized_deviation": 7.0, "residual_trend": "RISING", "history": history})
        stations[index] = stations[index].model_copy(update={"cycle_time": 72.0, "twin": degraded_twin})
        degraded_state = state.model_copy(update={"stations": stations})
        assessment = next(item for item in BottleneckRiskEngine().assess(degraded_state) if item.station_id == "FA-02")
        self.assertIsNone(degraded_state.simulation.active_scenario)
        self.assertGreater(assessment.risk, 0.45)

    def test_c_healthy_line_remains_low_risk(self) -> None:
        service = PredictionService()
        maximum = 0.0
        for _ in range(40):
            self.simulator._advance(15.0)
            prediction = service.prediction(self.simulator.state(), "FA-02")
            maximum = max(maximum, max(item.risk for item in prediction.assessments))
        self.assertLess(maximum, 0.25)
        self.assertFalse(prediction.alerts)

    def test_d_forward_clone_does_not_mutate_live_state(self) -> None:
        state_before = self.simulator.state()
        serialized = state_before.model_dump_json()
        snapshot = snapshot_from_twin(state_before)
        ForwardTwinSimulator().simulate(snapshot, 600, "FA-02", seed=275)
        self.assertEqual(state_before.model_dump_json(), serialized)
        self.assertEqual(self.simulator.state().simulation.simulation_time, state_before.simulation.simulation_time)

    def test_e_same_snapshot_and_seed_are_deterministic(self) -> None:
        snapshot = snapshot_from_twin(self.simulator.state())
        engine = ForwardTwinSimulator()
        first = engine.simulate(snapshot, 600, "FA-02", seed=275)
        second = engine.simulate(snapshot, 600, "FA-02", seed=275)
        self.assertEqual(first.model_dump(), second.model_dump())

    def test_f_direct_coupled_topology_has_no_buffer(self) -> None:
        snapshot = snapshot_from_twin(self.simulator.state())
        direct = [station for station in snapshot.stations if station.transfer_mode == "DIRECT_COUPLED"]
        self.assertTrue(direct)
        self.assertTrue(all(station.buffer_id is None and station.queue_capacity == 1 for station in direct))

    def test_g_accumulation_capacity_is_respected(self) -> None:
        snapshot = snapshot_from_twin(self.simulator.state())
        result = ForwardTwinSimulator().simulate(snapshot, 900, "FA-02", seed=275)
        capacities = {buffer.id: buffer.capacity for buffer in snapshot.buffers}
        for point in result.trajectory:
            for buffer_id, level in point.accumulator_levels.items():
                self.assertLessEqual(level, capacities[buffer_id])

    def test_h_upstream_congestion_emerges_from_slowdown(self) -> None:
        _, prediction = self.drifted_prediction()
        impacts = prediction.forecasts["600"].impacts
        self.assertTrue(any(impact.entity_id == "FA-01" and impact.impact_type == "UPSTREAM_BLOCKING" for impact in impacts))
        self.assertTrue(any(impact.entity_id == "FA-02" and impact.impact_type == "QUEUE_GROWTH" for impact in impacts))

    def test_i_downstream_starvation_emerges_from_slowdown(self) -> None:
        _, prediction = self.drifted_prediction()
        downstream = [(impact.entity_id, impact.eta_seconds) for impact in prediction.forecasts["600"].impacts if impact.impact_type == "DOWNSTREAM_STARVATION"]
        self.assertEqual([item[0] for item in downstream], ["FA-03", "FA-04", "FA-05"])
        self.assertEqual([item[1] for item in downstream], sorted(item[1] for item in downstream))

    def test_j_eta_matches_trajectory_threshold_crossing(self) -> None:
        _, prediction = self.drifted_prediction()
        result = prediction.forecasts["600"]
        impact = next(impact for impact in result.impacts if impact.entity_id == "FA-02" and impact.impact_type == "QUEUE_GROWTH")
        initial = result.trajectory[0].station_queues["FA-02"]
        first_sample = next(point.offset_seconds for point in result.trajectory if point.station_queues["FA-02"] > initial)
        self.assertLessEqual(impact.eta_seconds, first_sample)
        self.assertLess(first_sample - impact.eta_seconds, 30)

    def test_k_forecast_confidence_declines_with_lower_twin_confidence(self) -> None:
        snapshot = snapshot_from_twin(self.simulator.state())
        engine = ForwardTwinSimulator()
        normal = engine.simulate(snapshot, 600, "FA-02")
        low_snapshot = snapshot.model_copy(update={"stations": [station.model_copy(update={"twin_confidence": .35}) for station in snapshot.stations]})
        low = engine.simulate(low_snapshot, 600, "FA-02")
        self.assertLess(low.forecast_confidence, normal.forecast_confidence)

    def test_l_all_requested_horizons_are_stored(self) -> None:
        prediction = PredictionService().prediction(self.simulator.state(), "FA-02")
        self.assertEqual(set(prediction.forecasts), {"120", "300", "600", "900"})
        for horizon, result in prediction.forecasts.items():
            self.assertEqual(result.trajectory[-1].offset_seconds, int(horizon))

    def test_m_healthy_forward_throughput_matches_live(self) -> None:
        state = self.simulator.state()
        result = PredictionService().prediction(state, "FA-02").forecasts["600"]
        error = abs(result.metrics.throughput_per_hour - state.throughput_per_hour) / max(state.throughput_per_hour, 1)
        self.assertLessEqual(error, 0.12)

    def test_dropout_and_legacy_prediction_paths(self) -> None:
        service = PredictionService()
        fresh = service.prediction(self.simulator.state(), "FA-02")
        fresh_confidence = next(item.confidence for item in fresh.assessments if item.station_id == "FA-02")
        self.simulator.set_observation_condition("FA-02", drop=True)
        self.simulator._advance(45)
        dropped = service.prediction(self.simulator.state(), "FA-02")
        dropped_assessment = next(item for item in dropped.assessments if item.station_id == "FA-02")
        legacy_assessment = next(item for item in dropped.assessments if item.station_id == "FA-01")
        self.assertLess(dropped_assessment.confidence, fresh_confidence)
        self.assertGreaterEqual(legacy_assessment.risk, 0)
        self.assertLess(legacy_assessment.confidence, fresh_confidence)

    def test_forecast_vs_actual_checkpoint_evaluates(self) -> None:
        service, prediction = self.drifted_prediction()
        self.assertIsNotNone(prediction.validation.triggered_at)
        for _ in range(10):
            self.simulator._advance(15)
            prediction = service.prediction(self.simulator.state(), "FA-02")
        metric = next(item for item in prediction.validation.metrics if item.horizon_seconds == 120)
        self.assertTrue(metric.evaluated)
        self.assertIsNotNone(metric.queue_mae)


if __name__ == "__main__":
    unittest.main()
