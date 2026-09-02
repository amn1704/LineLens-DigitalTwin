from __future__ import annotations

from dataclasses import dataclass

from .models import IncidentType


@dataclass(frozen=True)
class IncidentPlaybook:
    incident_type: IncidentType
    owner_role: str
    checks: tuple[str, ...]
    escalation_rule: str


PLAYBOOKS: dict[IncidentType, IncidentPlaybook] = {
    IncidentType.PRODUCTION: IncidentPlaybook(
        incident_type=IncidentType.PRODUCTION,
        owner_role="Final Assembly Supervisor",
        checks=(
            "Check fixture alignment.",
            "Check lift and locator condition.",
            "Review recent station fault history.",
            "Send a line-support engineer to the station.",
            "Watch the incoming queue for the next few cycles.",
            "Escalate if cycle time remains above the response threshold.",
        ),
        escalation_rule="Escalate when the cycle remains above the response threshold after the next few cycles.",
    ),
    IncidentType.QUALITY: IncidentPlaybook(
        incident_type=IncidentType.QUALITY,
        owner_role="Body Shop Quality Supervisor",
        checks=(
            "Inspect the suspected weld gun.",
            "Check electrode-cap condition.",
            "Review the exposed vehicle group.",
            "Send eligible bodies to Body Shop Exit geometry inspection.",
            "Stop using the suspected tool only if engineering inspection confirms the problem.",
        ),
        escalation_rule="Escalate to engineering if inspection confirms the shared production pattern.",
    ),
}
