"""Phase 5: deterministic, human-in-the-loop incident workflow coverage."""

from backend.app.incidents import IncidentService
from backend.app.incidents.models import IncidentStatus, IncidentType
from backend.app.prediction import PredictionService
from backend.app.simulation import AssemblyLineSimulator


def evaluate(simulator: AssemblyLineSimulator, prediction_service: PredictionService, incidents: IncidentService):
    state = simulator.state()
    prediction = prediction_service.prediction(state, "FA-02")
    incidents.evaluate(
        state,
        prediction,
        simulator.quality_monitored_vehicles(),
        simulator.quality_genealogy(),
    )
    return state, prediction


def test_healthy_baseline_creates_no_incident():
    simulator = AssemblyLineSimulator()
    simulator.pause()
    prediction = PredictionService()
    incidents = IncidentService()
    try:
        for _ in range(40):
            simulator._advance(15)
            evaluate(simulator, prediction, incidents)
        assert incidents.list_incidents() == []
    finally:
        simulator.shutdown()


def test_sustained_chassis_risk_creates_one_deduplicated_production_incident_with_forecast():
    simulator = AssemblyLineSimulator()
    simulator.pause()
    prediction = PredictionService()
    incidents = IncidentService()
    try:
        simulator.set_chassis_drift(True)
        for _ in range(22):
            simulator._advance(15)
            _, forecast = evaluate(simulator, prediction, incidents)
        active = incidents.list_incidents()
        assert len(active) == 1
        incident = active[0]
        assert incident.type == IncidentType.PRODUCTION
        assert incident.title == "Chassis Marriage slowdown"
        assert incident.expected_impact != ""
        assert any(item.label == "Cycle time" for item in incident.evidence)
        assert incident.response_window_seconds is not None
        assert "fixture alignment" in " ".join(incident.recommended_checks).lower()
        assert forecast.forecasts["600"].impacts
        # More high-risk samples update the same operational issue rather than duplicating it.
        for _ in range(16):
            simulator._advance(15)
            evaluate(simulator, prediction, incidents)
        assert len(incidents.list_incidents()) == 1
    finally:
        simulator.shutdown()


def test_quality_cohort_creates_incident_from_real_vehicle_and_genealogy_evidence():
    simulator = AssemblyLineSimulator()
    simulator.pause()
    prediction = PredictionService()
    incidents = IncidentService()
    try:
        simulator.set_weld_drift(True)
        for _ in range(120):
            simulator._advance(15)
            evaluate(simulator, prediction, incidents)
        incident = next(item for item in incidents.list_incidents() if item.type == IncidentType.QUALITY)
        assert len(incident.affected_vehicles) >= IncidentService.QUALITY_COHORT_MINIMUM
        assert any(item.label == "Common pattern" and "WG-04" in item.value for item in incident.evidence)
        assert any(item.label == "Potential lead time" for item in incident.evidence)
        assert incident.response_metrics.detection_lead_time_seconds is not None
        assert "electrode-cap" in " ".join(incident.recommended_checks).lower()
        assert incident.owner_role == "Body Shop Quality Supervisor"
    finally:
        simulator.shutdown()


def test_workflow_transitions_timestamps_history_and_no_machine_control():
    simulator = AssemblyLineSimulator()
    simulator.pause()
    prediction = PredictionService()
    incidents = IncidentService()
    try:
        simulator.set_chassis_drift(True)
        for _ in range(20):
            simulator._advance(15)
            state, _ = evaluate(simulator, prediction, incidents)
        incident = incidents.list_incidents()[0]
        scenario_before = simulator.state().simulation.active_scenario
        acknowledged = incidents.acknowledge(incident.incident_id, state.simulation.simulation_time)
        investigating = incidents.investigate(incident.incident_id, state.simulation.simulation_time + 15)
        noted = incidents.note(incident.incident_id, state.simulation.simulation_time + 25, "Fixture check completed.")
        resolved = incidents.resolve(incident.incident_id, state.simulation.simulation_time + 40)
        assert acknowledged.acknowledged_at is not None
        assert investigating.investigating_at is not None
        assert any("Fixture check" in event.message for event in noted.timeline)
        assert resolved.status == IncidentStatus.RESOLVED
        assert resolved.response_metrics.resolution_seconds is not None
        assert resolved in incidents.list_incidents(include_resolved=True)
        assert simulator.state().simulation.active_scenario == scenario_before
        # A healthy-looking single sample never automatically closes an active incident.
        simulator.set_chassis_drift(True)
        for _ in range(4):
            simulator._advance(15)
            state, _ = evaluate(simulator, prediction, incidents)
        reopened = incidents.list_incidents()[0]
        simulator.set_chassis_drift(False)
        simulator._advance(15)
        evaluate(simulator, prediction, incidents)
        assert reopened.status != IncidentStatus.RESOLVED
    finally:
        simulator.shutdown()
