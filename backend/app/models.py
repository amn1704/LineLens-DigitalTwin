from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class Section(str, Enum):
    BODY_SHOP = "Body Shop"
    PAINT_SHOP = "Paint Shop"
    FINAL_ASSEMBLY = "Final Assembly"


class SensorMode(str, Enum):
    FULL = "FULL TELEMETRY"
    LIMITED = "LIMITED TELEMETRY"
    BASIC = "LEGACY / BASIC SIGNALS"


class Health(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


class OperationalState(str, Enum):
    RUNNING = "RUNNING"
    IDLE = "IDLE"
    BLOCKED = "BLOCKED"
    STARVED = "STARVED"
    CHANGEOVER = "CHANGEOVER"
    WARNING = "WARNING"
    OFFLINE = "OFFLINE"


class VehicleStatus(str, Enum):
    PROCESSING = "PROCESSING"
    BUFFERED = "BUFFERED"
    TRANSFERRING = "TRANSFERRING"
    COMPLETED = "COMPLETED"


class DefectFamily(str, Enum):
    BODY_WELD = "Body geometry / weld integrity"
    PAINT = "Paint surface"
    FASTENER = "Fastener / torque"


class InspectionStatus(str, Enum):
    PREDICTED = "PREDICTED"
    INSPECTION_PENDING = "INSPECTION_PENDING"
    CONFIRMED = "CONFIRMED"
    CLEARED = "CLEARED"


class QualityLevel(str, Enum):
    LOW = "LOW"
    WATCH = "WATCH"
    INSPECT = "INSPECT"
    HIGH = "HIGH"


class Vehicle(BaseModel):
    vehicle_id: str
    variant: str
    body_color: str
    batch_id: str
    current_station: str | None
    next_station: str | None
    production_stage: str
    progress: float = Field(ge=0, le=1)
    entry_time: float
    time_in_station: float
    total_line_time: float
    status: VehicleStatus
    buffer_id: str | None = None
    queue_kind: str | None = None
    # Phase 4: Quality indicators
    quality_risk: float = Field(ge=0, le=1, default=0.0)
    quality_level: QualityLevel = QualityLevel.LOW


class ProcessStep(BaseModel):
    station_id: str
    station_name: str
    entry_time: float
    exit_time: float
    cycle_time: float
    result: str
    equipment_id: str
    metadata: dict[str, str | float | bool]


class VehicleThread(BaseModel):
    vehicle_id: str
    variant: str
    body_color: str
    batch_id: str
    current_station: str | None = None
    line_progress: float = Field(ge=0, le=1)
    total_line_time: float
    completed_steps: list[ProcessStep]


class StationObservation(BaseModel):
    """Synthetic plant-facing data only; intentionally excludes simulator-only internals."""

    station_id: str
    timestamp: float
    operational_state: OperationalState | None = None
    vehicle_id: str | None = None
    queue_level: int | None = None
    cycle_time: float | None = None
    cycle_progress: float | None = None
    completed_cycle_time: float | None = None
    entry_timestamp: float | None = None
    last_departure_timestamp: float | None = None
    conveyor_occupied: bool | None = None
    temperature: float | None = None
    vibration: float | None = None
    power: float | None = None
    torque: float | None = None
    calibration_status: str | None = None
    source: str
    quality: float = Field(ge=0, le=1)
    signals: list[str]


class StationBaseline(BaseModel):
    expected_cycle: float
    cycle_stddev: float
    expected_utilization: float
    normal_queue: float
    samples: int


class StationTwinEstimate(BaseModel):
    expected_cycle: float
    estimated_cycle: float
    estimated_range_low: float
    estimated_range_high: float
    observed_cycle: float | None = None
    residual: float
    normalized_deviation: float
    residual_trend: str
    confidence: float = Field(ge=0, le=1)
    data_age: float = Field(ge=0)
    source: str
    evidence: list[str]
    estimated_from_indirect_evidence: bool
    last_observation: float | None = None
    last_assimilation: float
    baseline: StationBaseline
    history: list["TwinHistoryPoint"] = []


class TwinHistoryPoint(BaseModel):
    simulation_time: float
    observed_cycle: float | None = None
    estimated_cycle: float
    expected_cycle: float
    residual: float
    confidence: float


class TwinSynchronization(BaseModel):
    status: str
    overall_confidence: float = Field(ge=0, le=1)
    data_coverage: float = Field(ge=0, le=1)
    last_assimilation: float
    data_age: float = Field(ge=0)


class Station(BaseModel):
    id: str
    name: str
    section: Section
    process: str
    operational_state: OperationalState
    cycle_time: float
    nominal_cycle_time: float
    takt_time: float
    cycle_progress: float = Field(ge=0, le=1)
    buffer_capacity: int
    buffer_level: int
    queue_length: int
    transfer_mode: str
    buffer_name: str | None = None
    current_vehicle: str | None
    vehicles_completed: int
    utilization: float
    health: Health
    sensor_mode: SensorMode
    temperature: float | None = None
    vibration: float | None = None
    power: float | None = None
    torque: float | None = None
    calibration_status: str | None = None
    last_updated: str
    observation: StationObservation | None = None
    twin: StationTwinEstimate | None = None


class OperationalEvent(BaseModel):
    event_id: str
    simulation_time: float
    severity: str
    source: str
    message: str


class HistoryPoint(BaseModel):
    simulation_time: float
    throughput_per_hour: float
    avg_cycle_time: float
    body_utilization: float
    paint_utilization: float
    final_utilization: float


class SimulationInfo(BaseModel):
    simulation_time: float
    shift_elapsed: float
    takt_time: float
    speed: float
    is_running: bool
    vehicles_in_process: int
    stations_running: int
    completed_vehicles: int
    avg_utilization: float
    active_scenario: str | None = None
    quality_scenario_active: bool = False


class AccumulationBuffer(BaseModel):
    id: str
    name: str
    upstream_station: str
    downstream_station: str
    capacity: int
    level: int
    vehicle_ids: list[str]


class TwinState(BaseModel):
    timestamp: str
    throughput_per_hour: float
    simulation: SimulationInfo
    stations: list[Station]
    vehicles: list[Vehicle]
    buffers: list[AccumulationBuffer]
    events: list[OperationalEvent]
    history: list[HistoryPoint]
    synchronization: TwinSynchronization | None = None


class QualityEvidence(BaseModel):
    factor: str
    value: str
    contribution: float | None = None


class VehicleQualityPrediction(BaseModel):
    vehicle_id: str
    prediction_timestamp: float
    station_at_prediction: str
    risk: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    likely_defect_family: DefectFamily | None = None
    likely_origin_station: str | None = None
    recommended_inspection_point: str | None = None
    evidence: list[QualityEvidence]
    quality_level: QualityLevel
    model_version: str = "quality-logreg-v1"


class InspectionResult(BaseModel):
    vehicle_id: str
    inspection_timestamp: float
    inspection_station: str
    result: str  # "PASS" or "FAIL - {defect_family}"
    defect_family: DefectFamily | None = None
    inspection_status: InspectionStatus


class VehicleQualityRecord(BaseModel):
    vehicle_id: str
    current_prediction: VehicleQualityPrediction | None = None
    prediction_history: list[VehicleQualityPrediction] = Field(default_factory=list)
    inspection_result: InspectionResult | None = None


class CommonFactor(BaseModel):
    factor_type: str  # "tool", "fixture", "robot_cell", "consumable_lot", etc.
    factor_id: str
    factor_name: str
    support: int  # Number of vehicles in cohort with this factor
    cohort_size: int
    baseline_prevalence: float
    cohort_prevalence: float
    risk_lift: float
    confidence: float = Field(ge=0, le=1)


class GenealogyAnalysis(BaseModel):
    analysis_timestamp: float
    cohort_definition: str
    cohort_size: int
    baseline_size: int
    common_factors: list[CommonFactor]
    likely_origin_process: str | None = None
    analysis_confidence: float = Field(ge=0, le=1)


class QualityMetrics(BaseModel):
    total_vehicles: int
    total_predictions: int = 0
    defective_vehicles: int
    defect_rate: float
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision: float | None = None
    recall: float | None = None
    false_positive_rate: float | None = None
    prediction_lead_time_mean: float | None = None
    prediction_lead_time_max: float | None = None
    early_interception_opportunity: float | None = None
    unnecessary_inspections: int = 0
    model_version: str = "quality-logreg-v1"
