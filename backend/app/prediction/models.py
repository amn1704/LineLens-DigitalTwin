from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SnapshotStation(BaseModel):
    id: str
    name: str
    expected_cycle: float
    estimated_cycle: float
    cycle_stddev: float
    cycle_progress: float
    cycle_drift_per_second: float
    operational_state: str
    queue_level: int
    queue_capacity: int
    transfer_mode: str
    buffer_id: str | None = None
    current_busy: bool
    utilization: float
    twin_confidence: float
    completed_vehicles: int


class SnapshotBuffer(BaseModel):
    id: str
    name: str
    downstream_station: str
    capacity: int
    level: int


class TwinSnapshot(BaseModel):
    simulation_time: float
    takt_time: float
    current_throughput: float
    current_wip: int
    stations: list[SnapshotStation]
    buffers: list[SnapshotBuffer]


class BottleneckFeatures(BaseModel):
    cycle_to_takt_ratio: float
    health_residual: float
    normalized_residual: float
    residual_trend: str
    rolling_cycle_mean: float
    rolling_cycle_variance: float
    station_completion_rate: float
    completion_rate_change: float
    upstream_queue_growth: float
    downstream_arrival_rate: float
    utilization: float
    blocked_time_ratio: float
    starved_time_ratio: float
    accumulator_fill_rate: float
    evidence_persistence: float


class RiskHistoryPoint(BaseModel):
    simulation_time: float
    risk: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)


class BottleneckAssessment(BaseModel):
    station_id: str
    station_name: str
    risk: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    level: str
    features: BottleneckFeatures
    evidence: list[str]
    history: list[RiskHistoryPoint]


class ForwardScenario(BaseModel):
    horizon_seconds: int
    action: None = None
    seed: int = 275
    assumption: str = "NO_INTERVENTION"


class TrajectoryPoint(BaseModel):
    offset_seconds: int
    throughput_per_hour: float
    completed_vehicles: int
    wip: int
    station_queues: dict[str, int]
    station_states: dict[str, str]
    accumulator_levels: dict[str, int]


class ForecastImpact(BaseModel):
    entity_id: str
    entity_type: Literal["STATION", "ACCUMULATION_BUFFER", "LINE"]
    impact_type: str
    eta_seconds: float
    eta_range_low: float
    eta_range_high: float
    confidence: float = Field(ge=0, le=1)
    current_value: float | str
    projected_value: float | str
    severity: str


class OutcomeMetrics(BaseModel):
    throughput_per_hour: float
    throughput_change_percent: float
    completed_vehicles: int
    wip: int
    peak_queue: int
    blocked_time_seconds: float
    starved_time_seconds: float
    accumulator_peak: dict[str, int]


class ForwardResult(BaseModel):
    snapshot_time: float
    source_station_id: str
    scenario: ForwardScenario
    forecast_confidence: float = Field(ge=0, le=1)
    trajectory: list[TrajectoryPoint]
    impacts: list[ForecastImpact]
    metrics: OutcomeMetrics


class ForecastAlert(BaseModel):
    alert_id: str
    simulation_time: float
    severity: str
    alert_type: Literal["FORECAST"] = "FORECAST"
    source: str
    message: str


class ValidationMetric(BaseModel):
    horizon_seconds: int
    evaluated: bool
    queue_mae: float | None = None
    accumulator_mae: float | None = None
    throughput_mae: float | None = None
    state_accuracy: float | None = None


class ForecastValidation(BaseModel):
    triggered_at: float | None = None
    first_actual_impact_at: float | None = None
    prediction_lead_time_seconds: float | None = None
    impact_eta_error_seconds: float | None = None
    metrics: list[ValidationMetric] = []


class PredictionState(BaseModel):
    generated_at: float
    label: str = "Simulation-derived prototype prediction"
    primary_station_id: str
    assessments: list[BottleneckAssessment]
    forecasts: dict[str, ForwardResult]
    alerts: list[ForecastAlert]
    validation: ForecastValidation
