from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class IncidentType(str, Enum):
    PRODUCTION = "PRODUCTION"
    QUALITY = "QUALITY"


class IncidentStatus(str, Enum):
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    MONITORING = "MONITORING"
    RESOLVED = "RESOLVED"


class IncidentTimelineEvent(BaseModel):
    timestamp: float
    kind: str
    message: str
    actor: str = "LineLens"


class IncidentEvidence(BaseModel):
    label: str
    value: str
    baseline: str | None = None
    detail: str | None = None


class AffectedAsset(BaseModel):
    asset_id: str
    name: str
    area: str
    role: str = "Affected station"


class AffectedVehicle(BaseModel):
    vehicle_id: str
    current_location: str
    quality_risk: float = Field(ge=0, le=1)
    inspection_status: str


class IncidentOutcome(BaseModel):
    predicted_impact_happened: bool | None = None
    suspected_factor_confirmed: bool | None = None
    process_returned_toward_baseline: bool | None = None
    affected_vehicles_inspected: int = 0


class IncidentResponseMetrics(BaseModel):
    detection_lead_time_seconds: float | None = None
    acknowledgement_seconds: float | None = None
    investigation_seconds: float | None = None
    resolution_seconds: float | None = None
    vehicles_exposed: int = 0


class Incident(BaseModel):
    incident_id: str
    type: IncidentType
    title: str
    status: IncidentStatus
    severity: str
    detected_at: float
    updated_at: float
    source: str
    confidence: float = Field(ge=0, le=1)
    summary: str
    expected_impact: str
    response_window_seconds: float | None = None
    affected_assets: list[AffectedAsset] = Field(default_factory=list)
    affected_vehicles: list[AffectedVehicle] = Field(default_factory=list)
    evidence: list[IncidentEvidence] = Field(default_factory=list)
    recommended_checks: list[str] = Field(default_factory=list)
    owner_role: str
    timeline: list[IncidentTimelineEvent] = Field(default_factory=list)
    outcome: IncidentOutcome = Field(default_factory=IncidentOutcome)
    response_metrics: IncidentResponseMetrics = Field(default_factory=IncidentResponseMetrics)
    acknowledged_at: float | None = None
    investigating_at: float | None = None
    resolved_at: float | None = None
    recurrence_of: str | None = None
