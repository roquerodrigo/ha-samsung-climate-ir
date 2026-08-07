"""Base entity shared by every platform of a config entry."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from homeassistant.components.infrared import InfraredEmitterConsumerEntity
from homeassistant.helpers.restore_state import RestoreEntity

from .device import build_device_info

if TYPE_CHECKING:
    from homeassistant.helpers.device_registry import DeviceInfo

    from .data import SamsungClimateIrConfigEntry, SamsungClimateIrRuntime


class SamsungClimateIrEntity(InfraredEmitterConsumerEntity, RestoreEntity):
    """
    Base for the entities of one config entry.

    Centralizes what every entity shares: the emitter it transmits through,
    the runtime state, the device it attaches to, and the unique ID derived
    from the config entry. State is assumed (IR is one-way) and restored
    across restarts, hence ``RestoreEntity``.
    """

    _attr_has_entity_name = True
    _attr_assumed_state = True
    _unique_id_suffix: str

    def __init__(
        self,
        entry: SamsungClimateIrConfigEntry,
        emitter_entity_id: str,
    ) -> None:
        """Initialize the entry-derived identity and shared runtime state."""
        self._entry_id = entry.entry_id
        self._infrared_emitter_entity_id = emitter_entity_id
        self._runtime: SamsungClimateIrRuntime = entry.runtime_data

    @property
    @override
    def unique_id(self) -> str:
        """Return the unique ID derived from the config entry."""
        return f"{self._entry_id}_{self._unique_id_suffix}"

    @property
    @override
    def device_info(self) -> DeviceInfo:
        """Return the device every entity of the entry attaches to."""
        return build_device_info(self._entry_id)
