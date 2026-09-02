"""Phase 6 quick demos must advance the real simulator, not fabricated UI values."""

import inspect

import pytest

from backend.app.prediction import PredictionService
from backend.app.simulation import AssemblyLineSimulator


def test_demo_advance_uses_normal_simulation_pipeline():
    simulator = AssemblyLineSimulator()
    simulator.pause()
    try:
        before = simulator.state().simulation.simulation_time
        simulator.advance_demo(35)
        after = simulator.state().simulation.simulation_time
        assert after == pytest.approx(before + 35)
        source = inspect.getsource(AssemblyLineSimulator.advance_demo).lower()
        assert "self._advance" in source
        assert "risk" not in source
        assert "forecast" not in source
    finally:
        simulator.shutdown()


def test_bottleneck_demo_produces_prediction_from_physical_drift():
    simulator = AssemblyLineSimulator()
    simulator.pause()
    predictions = PredictionService()
    try:
        healthy = predictions.prediction(simulator.state(), "FA-02")
        healthy_risk = next(item.risk for item in healthy.assessments if item.station_id == "FA-02")

        simulator.set_chassis_drift(True)
        simulator.advance_demo(380)
        drifted = predictions.prediction(simulator.state(), "FA-02")
        drifted_risk = next(item.risk for item in drifted.assessments if item.station_id == "FA-02")

        assert drifted_risk > healthy_risk
        assert drifted_risk >= 0.35
        assert drifted.forecasts["300"].impacts
    finally:
        simulator.shutdown()


def test_demo_advance_rejects_unsafe_ranges():
    simulator = AssemblyLineSimulator()
    simulator.pause()
    try:
        for seconds in (0, -1, 2401):
            with pytest.raises(ValueError):
                simulator.advance_demo(seconds)
    finally:
        simulator.shutdown()
