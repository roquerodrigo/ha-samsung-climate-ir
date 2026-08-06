"""Typed shape of the diagnostics payload."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from . import JsonObject
    from .config_data import SamsungClimateIrConfigData


class SamsungClimateIrDiagnosticsPayload(TypedDict):
    """Shape of the payload returned by the diagnostics handler."""

    entry_data: SamsungClimateIrConfigData
    entity_states: list[JsonObject]
