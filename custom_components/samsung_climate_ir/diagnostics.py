"""Diagnostics support for samsung_climate_ir."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import (
        JsonObject,
        SamsungClimateIrConfigData,
        SamsungClimateIrConfigEntry,
        SamsungClimateIrDiagnosticsPayload,
    )


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: SamsungClimateIrConfigEntry,
) -> SamsungClimateIrDiagnosticsPayload:
    """Return diagnostics for a config entry."""
    registry = er.async_get(hass)
    climate_states = [
        cast("JsonObject", state.as_dict())
        for registry_entry in er.async_entries_for_config_entry(
            registry,
            entry.entry_id,
        )
        if registry_entry.platform == DOMAIN
        and (state := hass.states.get(registry_entry.entity_id)) is not None
    ]
    return {
        "entry_data": cast("SamsungClimateIrConfigData", dict(entry.data)),
        "climate_states": climate_states,
    }
