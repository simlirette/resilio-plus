"""Re-export shim — V3 SQLAlchemy models moved to app.db.models (2026-04-16).

Import from app.db.models directly. This shim exists for backwards-compat
with seed scripts and any external tooling that referenced this module path.
"""

from ..db.models import (  # noqa: F401
    AllostaticEntryModel,
    EnergySnapshotModel,
    ExternalPlanModel,
    ExternalSessionModel,
    HeadCoachMessageModel,
    HormonalProfileModel,
)
