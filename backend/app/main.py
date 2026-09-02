from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .models import HistoryPoint, OperationalEvent, Station, StationObservation, TwinState, TwinSynchronization, Vehicle, VehicleThread
from .simulation import AssemblyLineSimulator
from .prediction import PredictionService
from .prediction.models import PredictionState
from .incidents import IncidentService
from .incidents.models import Incident

app = FastAPI(title="LineLens API", version="0.5.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:5176",
        "http://localhost:5176",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
simulator = AssemblyLineSimulator()
prediction_service = PredictionService()
incident_service = IncidentService()


class SpeedRequest(BaseModel):
    speed: float


class ObservationConditionRequest(BaseModel):
    drop: bool | None = None
    noise: float | None = None


class ScenarioRequest(BaseModel):
    active: bool = True


class IncidentNoteRequest(BaseModel):
    note: str


class DemoAdvanceRequest(BaseModel):
    seconds: float


def refresh_incidents() -> list[Incident]:
    """Evaluate existing production/quality signals; this has no simulator control path."""
    state = simulator.state()
    prediction = prediction_service.prediction(state, "FA-02")
    incident_service.evaluate(
        state,
        prediction,
        simulator.quality_monitored_vehicles(),
        simulator.quality_genealogy(),
    )
    return incident_service.list_incidents()


@app.get("/api/state", response_model=TwinState)
def get_state() -> TwinState:
    return simulator.state()


@app.get("/api/stations", response_model=list[Station])
def get_stations() -> list[Station]:
    return simulator.stations()


@app.get("/api/stations/{station_id}", response_model=Station)
def get_station(station_id: str) -> Station:
    station = simulator.station(station_id)
    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")
    return station


@app.get("/api/vehicles", response_model=list[Vehicle])
def get_vehicles() -> list[Vehicle]:
    return simulator.vehicles()


@app.get("/api/events", response_model=list[OperationalEvent])
def get_events() -> list[OperationalEvent]:
    return simulator.events()


@app.get("/api/history", response_model=list[HistoryPoint])
def get_history() -> list[HistoryPoint]:
    return simulator.history()


@app.get("/api/twin/state", response_model=TwinState)
def get_twin_state() -> TwinState:
    return simulator.state()


@app.get("/api/twin/stations", response_model=list[Station])
def get_twin_stations() -> list[Station]:
    return simulator.stations()


@app.get("/api/twin/stations/{station_id}", response_model=Station)
def get_twin_station(station_id: str) -> Station:
    station = simulator.station(station_id)
    if station is None:
        raise HTTPException(status_code=404, detail="Station not found")
    return station


@app.get("/api/twin/observations", response_model=list[StationObservation])
def get_observations() -> list[StationObservation]:
    return simulator.observations()


@app.get("/api/twin/synchronization", response_model=TwinSynchronization)
def get_synchronization() -> TwinSynchronization:
    return simulator.synchronization()


@app.get("/api/predictions", response_model=PredictionState)
def get_predictions(station_id: str = "FA-02") -> PredictionState:
    return prediction_service.prediction(simulator.state(), station_id)


@app.post("/api/twin/testing/stations/{station_id}/observation-condition", response_model=TwinState)
def set_observation_condition(station_id: str, payload: ObservationConditionRequest) -> TwinState:
    try:
        simulator.set_observation_condition(station_id, drop=payload.drop, noise=payload.noise)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return simulator.state()


@app.get("/api/vehicles/{vehicle_id}/thread", response_model=VehicleThread)
def get_vehicle_thread(vehicle_id: str) -> VehicleThread:
    thread = simulator.vehicle_thread(vehicle_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Vehicle build record not found")
    return thread


@app.post("/api/simulation/reset", response_model=TwinState)
def reset_simulation() -> TwinState:
    simulator.reset()
    prediction_service.reset()
    incident_service.reset()
    return simulator.state()


@app.post("/api/simulation/pause", response_model=TwinState)
def pause_simulation() -> TwinState:
    simulator.pause()
    return simulator.state()


@app.post("/api/simulation/resume", response_model=TwinState)
def resume_simulation() -> TwinState:
    simulator.resume()
    return simulator.state()


@app.post("/api/simulation/speed", response_model=TwinState)
def set_speed(payload: SpeedRequest) -> TwinState:
    try:
        simulator.set_speed(payload.speed)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return simulator.state()


@app.post("/api/simulation/scenarios/chassis-fixture-drift", response_model=TwinState)
def set_chassis_fixture_drift(payload: ScenarioRequest) -> TwinState:
    simulator.set_chassis_drift(payload.active)
    return simulator.state()


@app.post("/api/simulation/scenarios/weld-drift", response_model=TwinState)
def set_weld_drift(payload: ScenarioRequest) -> TwinState:
    simulator.set_weld_drift(payload.active)
    return simulator.state()


@app.post("/api/simulation/demo/advance", response_model=TwinState)
def advance_demo(payload: DemoAdvanceRequest) -> TwinState:
    try:
        simulator.advance_demo(payload.seconds)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return simulator.state()


@app.get("/api/quality/vehicles", response_model=list[dict])
def get_quality_vehicles(threshold: float = 0.60) -> list[dict]:
    return simulator.quality_vehicles(threshold)


@app.get("/api/quality/vehicles/all", response_model=list[dict])
def get_monitored_quality_vehicles() -> list[dict]:
    return simulator.quality_monitored_vehicles()


@app.get("/api/quality/scenario", response_model=dict)
def get_quality_scenario() -> dict:
    return simulator.quality_scenario()


@app.get("/api/quality/vehicles/{vehicle_id}", response_model=dict)
def get_quality_vehicle(vehicle_id: str) -> dict:
    vehicle_quality = simulator.quality_vehicle(vehicle_id)
    if vehicle_quality is None:
        raise HTTPException(status_code=404, detail="Vehicle quality record not found")
    return vehicle_quality


@app.get("/api/quality/genealogy", response_model=dict)
def get_quality_genealogy() -> dict:
    return simulator.quality_genealogy()


@app.get("/api/quality/metrics", response_model=dict)
def get_quality_metrics() -> dict:
    return simulator.quality_metrics()


@app.get("/api/incidents", response_model=list[Incident])
def get_incidents(status: str = "active") -> list[Incident]:
    refresh_incidents()
    return incident_service.list_incidents(include_resolved=status.lower() in {"all", "resolved", "history"})


@app.get("/api/incidents/history", response_model=list[Incident])
def get_incident_history() -> list[Incident]:
    refresh_incidents()
    return [incident for incident in incident_service.list_incidents(include_resolved=True) if incident.status.value == "RESOLVED"]


@app.get("/api/incidents/{incident_id}", response_model=Incident)
def get_incident(incident_id: str) -> Incident:
    refresh_incidents()
    incident = incident_service.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@app.post("/api/incidents/{incident_id}/acknowledge", response_model=Incident)
def acknowledge_incident(incident_id: str) -> Incident:
    try:
        return incident_service.acknowledge(incident_id, simulator.state().simulation.simulation_time)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Incident not found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/api/incidents/{incident_id}/investigate", response_model=Incident)
def investigate_incident(incident_id: str) -> Incident:
    try:
        return incident_service.investigate(incident_id, simulator.state().simulation.simulation_time)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Incident not found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/api/incidents/{incident_id}/note", response_model=Incident)
def add_incident_note(incident_id: str, payload: IncidentNoteRequest) -> Incident:
    try:
        return incident_service.note(incident_id, simulator.state().simulation.simulation_time, payload.note)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Incident not found") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/incidents/{incident_id}/resolve", response_model=Incident)
def resolve_incident(incident_id: str) -> Incident:
    try:
        return incident_service.resolve(incident_id, simulator.state().simulation.simulation_time)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Incident not found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
