"""Switch platform for samsung_climate_ir — the AC panel display."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast, override

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_ON, EntityCategory
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import signal_display_updated
from .entity import SamsungClimateIrEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .data import SamsungClimateIrConfigData, SamsungClimateIrConfigEntry

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 — HA platform setup signature
    entry: SamsungClimateIrConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the display switch from a config entry."""
    config = cast("SamsungClimateIrConfigData", entry.data)
    async_add_entities(
        [SamsungClimateIrDisplaySwitch(entry, config["emitter_entity_id"])],
    )


class SamsungClimateIrDisplaySwitch(
    SamsungClimateIrEntity,
    SwitchEntity,
):
    """
    Panel display (light) of the Samsung AC.

    The IR protocol has no display-only command: every frame carries the whole
    AC state, display bit included. Toggling therefore stores the wish in the
    shared runtime state and asks the climate entity to re-send its current
    state; while the AC is assumed off, the bit simply rides along with the
    next power-on frame.
    """

    _attr_translation_key = "display"
    _attr_entity_category = EntityCategory.CONFIG
    _unique_id_suffix = "display"

    @property
    @override
    def is_on(self) -> bool:
        """Return whether the panel display is assumed on."""
        return self._runtime.display_on

    @override
    async def async_added_to_hass(self) -> None:
        """Restore the assumed display state and follow remote updates."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._runtime.display_on = last_state.state == STATE_ON

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                signal_display_updated(self._entry_id),
                self.async_write_ha_state,
            ),
        )

    @override
    async def async_turn_on(self, **_kwargs: object) -> None:
        """Turn the panel display on."""
        await self._async_set_display(display_on=True)

    @override
    async def async_turn_off(self, **_kwargs: object) -> None:
        """Turn the panel display off."""
        await self._async_set_display(display_on=False)

    async def _async_set_display(self, *, display_on: bool) -> None:
        """Store the display state and re-send the AC state while it is on."""
        self._runtime.display_on = display_on
        if (resend := self._runtime.resend_state_when_on) is not None:
            await resend()
        self.async_write_ha_state()
