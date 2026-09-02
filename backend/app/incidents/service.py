from __future__ import annotations

from collections import deque

from ..models import TwinState
from ..prediction.models import PredictionState
from .models import (
    AffectedAsset,
    AffectedVehicle,
    Incident,
    IncidentEvidence,
    IncidentResponseMetrics,
    IncidentStatus,
    IncidentTimelineEvent,
    IncidentType,
)
from .playbooks import PLAYBOOKS


class IncidentService:
    """Human workflow records driven by existing prediction services, never controls."""

    PRODUCTION_RISK_THRESHOLD = 0.45
    QUALITY_RISK_THRESHOLD = 0.60
    QUALITY_COHORT_MINIMUM = 2
    HISTORY_LIMIT = 50

    def __init__(self) -> None:
        self._active: dict[IncidentType, Incident] = {}
        self._history: deque[Incident] = deque(maxlen=self.HISTORY_LIMIT)
        self._sequence = 0
        self._production_seen_at: float | None = None
        self._last_resolved: dict[IncidentType, Incident] = {}

    def reset(self) -> None:
        self.__init__()

    def evaluate(
        self,
        state: TwinState,
        prediction: PredictionState,
        quality_vehicles: list[dict],
        genealogy: dict,
    ) -> list[Incident]:
        now = state.simulation.simulation_time
        self._evaluate_production(state, prediction, now)
        self._evaluate_quality(state, quality_vehicles, genealogy, now)
        return self.list_incidents(include_resolved=False)

    def _evaluate_production(self, state: TwinState, prediction: PredictionState, now: float) -> None:
        assessment = next((item for item in prediction.assessments if item.station_id == "FA-02"), None)
        if not assessment or assessment.risk < self.PRODUCTION_RISK_THRESHOLD:
            self._production_seen_at = None
            return
        if self._production_seen_at is None:
            self._production_seen_at = now
            return
        # A short sustained interval prevents a single noisy sample from becoming an incident.
        if now - self._production_seen_at < 12:
            return
        forecast = prediction.forecasts.get("600")
        impacts = forecast.impacts if forecast else []
        material = [impact for impact in impacts if impact.impact_type in {"UPSTREAM_BLOCKING", "DOWNSTREAM_STARVATION", "OUTPUT_REDUCTION"}]
        first = min(material or impacts, key=lambda impact: impact.eta_seconds, default=None)
        station = next((item for item in state.stations if item.id == "FA-02"), None)
        if station is None:
            return
        expected = self._impact_label(first) if first else "Downstream flow may be affected if the slowdown continues."
        evidence = [
            IncidentEvidence(label="Cycle time", value=f"{station.cycle_time:.1f} s"),
            IncidentEvidence(label="Normal", value=f"{station.nominal_cycle_time:.1f} s"),
            IncidentEvidence(label="Difference from normal", value=f"{station.cycle_time - station.nominal_cycle_time:+.1f} s"),
            IncidentEvidence(label="Incoming queue", value=f"{station.queue_length} vehicles"),
            IncidentEvidence(label="Trend", value="Getting worse" if assessment.features.residual_trend == "RISING" else "Being watched"),
        ]
        incident = self._active.get(IncidentType.PRODUCTION)
        if incident is None:
            incident = self._create(
                incident_type=IncidentType.PRODUCTION, now=now, severity="HIGH" if assessment.risk >= .60 else "MEDIUM",
                title="Chassis Marriage slowdown", source=station.name, confidence=assessment.confidence,
                summary="Chassis Marriage is taking longer than normal.", expected_impact=expected,
                response_window=first.eta_seconds if first else None,
                assets=[AffectedAsset(asset_id=station.id, name=station.name, area=station.section.value, role="Source station")],
                evidence=evidence,
            )
        else:
            incident.updated_at = now
            incident.confidence = assessment.confidence
            incident.severity = "HIGH" if assessment.risk >= .60 else "MEDIUM"
            incident.expected_impact = expected
            incident.response_window_seconds = first.eta_seconds if first else None
            incident.evidence = evidence
            incident.response_metrics.detection_lead_time_seconds = first.eta_seconds if first else incident.response_metrics.detection_lead_time_seconds
            self._record_system_update(incident, now, "Risk remains elevated; incident evidence refreshed.")

    def _evaluate_quality(self, state: TwinState, rows: list[dict], genealogy: dict, now: float) -> None:
        cohort = [row for row in rows if float(row.get("risk", 0)) >= self.QUALITY_RISK_THRESHOLD]
        factors = genealogy.get("common_factors", []) if genealogy else []
        if len(cohort) < self.QUALITY_COHORT_MINIMUM or not factors:
            return
        primary = factors[0]
        factor_name = primary.get("factor_name") or primary.get("factor_id") or "Shared weld pattern"
        origin = genealogy.get("likely_origin_process") or "Robotic Weld Cell"
        station_index = {station.id: index for index, station in enumerate(state.stations)}
        earliest = min(cohort, key=lambda row: station_index.get(str(row.get("station_at_prediction")), len(state.stations)))
        warning_station = str(earliest.get("station_at_prediction") or "Body Shop Exit")
        warning_index = station_index.get(warning_station, 0)
        eol_index = next((index for index, station in enumerate(state.stations) if station.id == "FA-05"), len(state.stations) - 1)
        remaining_stations = state.stations[warning_index + 1 : eol_index + 1]
        potential_lead = round(sum(station.nominal_cycle_time for station in remaining_stations), 1)
        vehicles = [
            AffectedVehicle(
                vehicle_id=row["vehicle_id"], current_location=row.get("current_station") or "In production",
                quality_risk=float(row.get("risk", 0)), inspection_status=str(row.get("inspection_status", "PREDICTED")),
            )
            for row in cohort[:12]
        ]
        evidence = [
            IncidentEvidence(label="Vehicles needing review", value=str(len(cohort))),
            IncidentEvidence(label="Likely origin", value=origin),
            IncidentEvidence(label="Common pattern", value=str(factor_name), detail="Appears more often in the risky vehicle group."),
            IncidentEvidence(label="Pattern strength", value=f"{float(primary.get('risk_lift', 0)):.1f}× more common"),
            IncidentEvidence(label="Normal discovery", value="End-of-Line Inspection"),
            IncidentEvidence(label="LineLens warning", value=warning_station),
            IncidentEvidence(label="Potential lead time", value=f"{potential_lead / 60:.1f} min", detail=f"{len(remaining_stations)} processes before normal discovery."),
        ]
        incident = self._active.get(IncidentType.QUALITY)
        if incident is None:
            incident = self._create(
                incident_type=IncidentType.QUALITY, now=now, severity="HIGH",
                title="Quality containment", source=origin, confidence=float(genealogy.get("analysis_confidence", .5)),
                summary=f"{len(cohort)} vehicles show the same weld-quality pattern.",
                expected_impact="These vehicles can be reviewed before normal End-of-Line inspection.",
                response_window=potential_lead,
                assets=[AffectedAsset(asset_id="BIW-02", name=origin, area="Body Shop", role="Likely origin")],
                vehicles=vehicles, evidence=evidence,
            )
        else:
            incident.updated_at = now
            incident.confidence = float(genealogy.get("analysis_confidence", incident.confidence))
            incident.summary = f"{len(cohort)} vehicles show the same weld-quality pattern."
            incident.affected_vehicles = vehicles
            incident.evidence = evidence
            incident.response_metrics.vehicles_exposed = len(cohort)
            incident.response_window_seconds = potential_lead
            incident.response_metrics.detection_lead_time_seconds = potential_lead
            self._record_system_update(incident, now, "Quality cohort refreshed from current vehicle evidence.")

    def _create(self, incident_type: IncidentType, now: float, severity: str, title: str, source: str, confidence: float, summary: str, expected_impact: str, response_window: float | None, assets: list[AffectedAsset], evidence: list[IncidentEvidence], vehicles: list[AffectedVehicle] | None = None) -> Incident:
        self._sequence += 1
        playbook = PLAYBOOKS[incident_type]
        recurrence = self._last_resolved.get(incident_type)
        incident = Incident(
            incident_id=f"INC-{self._sequence:04d}", type=incident_type, title=title, status=IncidentStatus.NEW,
            severity=severity, detected_at=now, updated_at=now, source=source, confidence=round(confidence, 3),
            summary=summary, expected_impact=expected_impact, response_window_seconds=round(response_window, 1) if response_window is not None else None,
            affected_assets=assets, affected_vehicles=vehicles or [], evidence=evidence,
            recommended_checks=list(playbook.checks), owner_role=playbook.owner_role,
            timeline=[IncidentTimelineEvent(timestamp=now, kind="SYSTEM", message="LineLens created this incident from sustained prediction evidence.")],
            response_metrics=IncidentResponseMetrics(detection_lead_time_seconds=round(response_window, 1) if response_window is not None else None, vehicles_exposed=len(vehicles or [])),
            recurrence_of=recurrence.incident_id if recurrence and now - (recurrence.resolved_at or now) <= 900 else None,
        )
        self._active[incident_type] = incident
        return incident

    def _record_system_update(self, incident: Incident, now: float, message: str) -> None:
        # At most one background update per simulated minute; user actions remain prominent.
        if not incident.timeline or now - incident.timeline[-1].timestamp >= 60:
            incident.timeline.append(IncidentTimelineEvent(timestamp=now, kind="SYSTEM", message=message))

    def _impact_label(self, impact) -> str:
        labels = {
            "DOWNSTREAM_STARVATION": "A downstream station may run out of incoming vehicles.",
            "UPSTREAM_BLOCKING": "The incoming queue may continue to grow.",
            "OUTPUT_REDUCTION": "End-of-Line output may fall.",
        }
        prefix = labels.get(impact.impact_type, "Production flow may be affected.")
        return f"{prefix} First expected impact in {impact.eta_seconds / 60:.1f} min."

    def list_incidents(self, include_resolved: bool = False) -> list[Incident]:
        items = list(self._active.values())
        if include_resolved:
            items.extend(self._history)
        return sorted(items, key=lambda item: (item.status == IncidentStatus.RESOLVED, -item.updated_at))

    def get(self, incident_id: str) -> Incident | None:
        for incident in self.list_incidents(include_resolved=True):
            if incident.incident_id == incident_id:
                return incident
        return None

    def acknowledge(self, incident_id: str, now: float) -> Incident:
        incident = self._require_active(incident_id)
        if incident.status == IncidentStatus.NEW:
            incident.status = IncidentStatus.ACKNOWLEDGED
            incident.acknowledged_at = now
            incident.response_metrics.acknowledgement_seconds = round(now - incident.detected_at, 1)
            incident.timeline.append(IncidentTimelineEvent(timestamp=now, kind="USER", actor="Plant team", message="Supervisor acknowledged the incident."))
        return incident

    def investigate(self, incident_id: str, now: float) -> Incident:
        incident = self._require_active(incident_id)
        if incident.status == IncidentStatus.NEW:
            self.acknowledge(incident_id, now)
        if incident.status == IncidentStatus.ACKNOWLEDGED:
            incident.status = IncidentStatus.INVESTIGATING
            incident.investigating_at = now
            incident.response_metrics.investigation_seconds = round(now - incident.detected_at, 1)
            incident.timeline.append(IncidentTimelineEvent(timestamp=now, kind="USER", actor="Plant team", message="Investigation started."))
        return incident

    def note(self, incident_id: str, now: float, note: str) -> Incident:
        incident = self._require_active(incident_id)
        message = note.strip()
        if not message:
            raise ValueError("A note cannot be empty")
        incident.timeline.append(IncidentTimelineEvent(timestamp=now, kind="USER", actor="Plant team", message=message[:300]))
        incident.updated_at = now
        return incident

    def resolve(self, incident_id: str, now: float) -> Incident:
        incident = self._require_active(incident_id)
        if incident.status == IncidentStatus.NEW:
            self.acknowledge(incident_id, now)
        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = now
        incident.updated_at = now
        incident.response_metrics.resolution_seconds = round(now - incident.detected_at, 1)
        incident.outcome.process_returned_toward_baseline = None
        incident.timeline.append(IncidentTimelineEvent(timestamp=now, kind="USER", actor="Plant team", message="Incident resolved in the workflow. Physical process control was not changed."))
        self._active.pop(incident.type, None)
        self._history.appendleft(incident)
        self._last_resolved[incident.type] = incident
        return incident

    def _require_active(self, incident_id: str) -> Incident:
        incident = self.get(incident_id)
        if incident is None:
            raise KeyError(incident_id)
        if incident.status == IncidentStatus.RESOLVED:
            raise ValueError("Resolved incidents cannot be changed")
        return incident
