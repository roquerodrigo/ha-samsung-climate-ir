"""Samsung Climate IR integration for Home Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import Platform

from .data import SamsungClimateIrRuntime

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import SamsungClimateIrConfigEntry

PLATFORMS: list[Platform] = [Platform.CLIMATE, Platform.SWITCH]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SamsungClimateIrConfigEntry,
) -> bool:
    """Set up Samsung Climate IR from a config entry."""
    entry.runtime_data = SamsungClimateIrRuntime()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: SamsungClimateIrConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
