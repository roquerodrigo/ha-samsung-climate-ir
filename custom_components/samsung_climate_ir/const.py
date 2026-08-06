"""Constants for samsung_climate_ir."""

from __future__ import annotations

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "samsung_climate_ir"

CONF_EMITTER_ENTITY_ID = "emitter_entity_id"
CONF_RECEIVER_ENTITY_ID = "receiver_entity_id"
CONF_HVAC_MODES = "hvac_modes"


def signal_display_updated(entry_id: str) -> str:
    """Return the dispatcher signal fired when a remote changes the display."""
    return f"{DOMAIN}_{entry_id}_display_updated"
