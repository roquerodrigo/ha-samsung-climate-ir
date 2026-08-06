"""Custom types for samsung_climate_ir."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from .config_data import SamsungClimateIrConfigData
from .diagnostics_payload import SamsungClimateIrDiagnosticsPayload

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry


type JsonPrimitive = str | int | float | bool | None
type JsonValue = JsonPrimitive | list[JsonValue] | Mapping[str, JsonValue]
type JsonObject = Mapping[str, JsonValue]

type SamsungClimateIrConfigEntry = ConfigEntry[None]

__all__ = [
    "JsonObject",
    "JsonPrimitive",
    "JsonValue",
    "SamsungClimateIrConfigData",
    "SamsungClimateIrConfigEntry",
    "SamsungClimateIrDiagnosticsPayload",
]
