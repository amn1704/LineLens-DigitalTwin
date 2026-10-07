from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..sustainability.energy import DEFAULT_GRID_EMISSION_FACTOR, EMISSION_FACTOR_NOTE


class ImpactAssumptions(BaseModel):
    """Illustrative placeholders for turning synthetic line evidence into ₹, vehicles and kWh.

    None of these values come from Maruti Suzuki or any real plant.  They exist so
    a reviewer can replace them with their own figures and see how sensitive the
    estimate is.
    """

    model_config = ConfigDict(extra="forbid")

    shift_hours: float = Field(
        8.0, ge=0, le=24,
        description="Illustrative production hours per shift used to extrapolate a forecast to one shift.",
    )
    contribution_margin_per_vehicle_inr: float = Field(
        50_000.0, ge=0,
        description="Illustrative placeholder contribution margin per vehicle (₹); not a real OEM figure.",
    )
    inline_rework_cost_inr: float = Field(
        1_500.0, ge=0,
        description="Illustrative placeholder cost to fix a body in the Body Shop (₹).",
    )
    eol_rework_cost_inr: float = Field(
        6_000.0, ge=0,
        description="Illustrative placeholder cost to fix the same issue after End-of-Line inspection (₹).",
    )
    electricity_tariff_inr_per_kwh: float = Field(
        8.0, ge=0,
        description="Illustrative placeholder industrial electricity tariff (₹/kWh).",
    )
    grid_emission_factor_kg_per_kwh: float = Field(
        DEFAULT_GRID_EMISSION_FACTOR, ge=0,
        description=f"Illustrative grid emission factor (kg CO2/kWh); {EMISSION_FACTOR_NOTE}.",
    )
