"""Climate platform for samsung_climate_ir."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast, override

from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    ATTR_SWING_MODE,
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    PRESET_NONE,
    SWING_OFF,
    SWING_ON,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate.const import ATTR_FAN_MODE
from homeassistant.components.infrared import (
    InfraredEmitterConsumerEntity,
    InfraredReceiverConsumerEntity,
)
from homeassistant.const import ATTR_TEMPERATURE, STATE_UNAVAILABLE, UnitOfTemperature
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DOMAIN,
)
from .protocol import (
    MAX_TEMPERATURE,
    MIN_TEMPERATURE,
    SamsungAcCommand,
    SamsungAcFanSpecial,
    SamsungAcFanSpeed,
    SamsungAcMode,
    SamsungAcSwing,
)

if TYPE_CHECKING:
    from homeassistant.components.infrared import InfraredReceivedSignal
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .data import SamsungClimateIrConfigData, SamsungClimateIrConfigEntry

PARALLEL_UPDATES = 1

FAN_TURBO = "turbo"
PRESET_WIND_FREE = "wind_free"

DEFAULT_TARGET_TEMPERATURE = 22.0

_HA_FAN_TO_PROTOCOL: dict[str, SamsungAcFanSpeed] = {
    FAN_AUTO: SamsungAcFanSpeed.AUTO,
    FAN_LOW: SamsungAcFanSpeed.LOW,
    FAN_MEDIUM: SamsungAcFanSpeed.MEDIUM,
    FAN_HIGH: SamsungAcFanSpeed.HIGH,
    FAN_TURBO: SamsungAcFanSpeed.TURBO,
}
_PROTOCOL_FAN_TO_HA: dict[SamsungAcFanSpeed, str] = {
    value: key for key, value in _HA_FAN_TO_PROTOCOL.items()
} | {SamsungAcFanSpeed.AUTO_ALTERNATE: FAN_AUTO}

_HA_MODE_TO_PROTOCOL: dict[HVACMode, SamsungAcMode] = {
    HVACMode.AUTO: SamsungAcMode.AUTO,
    HVACMode.COOL: SamsungAcMode.COOL,
    HVACMode.DRY: SamsungAcMode.DRY,
    HVACMode.FAN_ONLY: SamsungAcMode.FAN,
    HVACMode.HEAT: SamsungAcMode.HEAT,
}
_PROTOCOL_MODE_TO_HA: dict[SamsungAcMode, HVACMode] = {
    value: key for key, value in _HA_MODE_TO_PROTOCOL.items()
}

# WindFree closes the louver to diffuse air, which only makes sense while
# cooling or drying; entering these modes drops the preset.
_WIND_FREE_INCOMPATIBLE_MODES = (HVACMode.HEAT, HVACMode.FAN_ONLY)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 — HA platform setup signature
    entry: SamsungClimateIrConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Samsung AC climate entity from a config entry."""
    config = cast("SamsungClimateIrConfigData", entry.data)
    if receiver_entity_id := config.get("receiver_entity_id"):
        async_add_entities(
            [
                SamsungClimateIrClimateWithReceiver(
                    entry,
                    config["emitter_entity_id"],
                    receiver_entity_id,
                ),
            ],
        )
    else:
        async_add_entities(
            [SamsungClimateIrClimate(entry, config["emitter_entity_id"])],
        )


class SamsungClimateIrClimate(
    InfraredEmitterConsumerEntity,
    ClimateEntity,
    RestoreEntity,
):
    """Samsung AC climate entity controlled via an infrared emitter."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_translation_key = "samsung_ac"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1.0
    _attr_min_temp = float(MIN_TEMPERATURE)
    _attr_max_temp = float(MAX_TEMPERATURE)
    _attr_assumed_state = True
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(
        self,
        entry: SamsungClimateIrConfigEntry,
        emitter_entity_id: str,
    ) -> None:
        """Initialize the Samsung AC climate entity."""
        self._attr_unique_id = f"{entry.entry_id}_climate"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Samsung AC",
            manufacturer="Samsung",
        )
        self._infrared_emitter_entity_id = emitter_entity_id
        self._attr_fan_modes = [FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_TURBO]
        self._attr_swing_modes = [SWING_OFF, SWING_ON]
        self._attr_preset_modes = [PRESET_NONE, PRESET_WIND_FREE]

        config = cast("SamsungClimateIrConfigData", entry.data)
        self._attr_hvac_modes = [HVACMode.OFF] + [
            HVACMode(mode) for mode in config["hvac_modes"]
        ]
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_target_temperature = DEFAULT_TARGET_TEMPERATURE
        self._attr_fan_mode = FAN_AUTO
        self._attr_swing_mode = SWING_OFF
        self._attr_preset_mode = PRESET_NONE
        self._mode_for_frame = SamsungAcMode.COOL

    @override
    async def async_added_to_hass(self) -> None:
        """Restore the assumed state, as infrared cannot read it back."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is None or last_state.state in (STATE_UNAVAILABLE, None):
            return

        if last_state.state in self._attr_hvac_modes:
            self._attr_hvac_mode = HVACMode(last_state.state)
            if self._attr_hvac_mode is not HVACMode.OFF:
                self._mode_for_frame = _HA_MODE_TO_PROTOCOL[self._attr_hvac_mode]
        if (fan_mode := last_state.attributes.get(ATTR_FAN_MODE)) in (
            self._attr_fan_modes or []
        ):
            self._attr_fan_mode = fan_mode
        if (swing_mode := last_state.attributes.get(ATTR_SWING_MODE)) in (
            self._attr_swing_modes or []
        ):
            self._attr_swing_mode = swing_mode
        if (preset_mode := last_state.attributes.get(ATTR_PRESET_MODE)) in (
            self._attr_preset_modes or []
        ):
            self._attr_preset_mode = preset_mode
        if (temperature := last_state.attributes.get(ATTR_TEMPERATURE)) is not None:
            self._attr_target_temperature = float(temperature)

    @override
    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        if hvac_mode is not HVACMode.OFF:
            self._mode_for_frame = _HA_MODE_TO_PROTOCOL[hvac_mode]
            if (
                hvac_mode in _WIND_FREE_INCOMPATIBLE_MODES
                and self._attr_preset_mode == PRESET_WIND_FREE
            ):
                self._attr_preset_mode = PRESET_NONE
        self._attr_hvac_mode = hvac_mode
        await self._async_send_current_state()
        self.async_write_ha_state()

    @override
    async def async_set_temperature(self, **kwargs: float | str) -> None:
        """Set the target temperature, switching HVAC mode when one is given."""
        self._attr_target_temperature = float(kwargs[ATTR_TEMPERATURE])

        if (hvac_mode_value := kwargs.get(ATTR_HVAC_MODE)) is not None:
            hvac_mode = HVACMode(str(hvac_mode_value))
            self._valid_mode_or_raise("hvac", hvac_mode, self.hvac_modes)
            await self.async_set_hvac_mode(hvac_mode)
            return

        if self._attr_hvac_mode is not HVACMode.OFF:
            await self._async_send_current_state()
        self.async_write_ha_state()

    @override
    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode, dropping the WindFree preset it contradicts."""
        if fan_mode != FAN_AUTO and self._attr_preset_mode == PRESET_WIND_FREE:
            self._attr_preset_mode = PRESET_NONE
        self._attr_fan_mode = fan_mode
        if self._attr_hvac_mode is not HVACMode.OFF:
            await self._async_send_current_state()
        self.async_write_ha_state()

    @override
    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set swing mode, dropping the WindFree preset it contradicts."""
        if swing_mode == SWING_ON and self._attr_preset_mode == PRESET_WIND_FREE:
            self._attr_preset_mode = PRESET_NONE
        self._attr_swing_mode = swing_mode
        if self._attr_hvac_mode is not HVACMode.OFF:
            await self._async_send_current_state()
        self.async_write_ha_state()

    @override
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode; WindFree forces the fan to auto and swing off."""
        self._attr_preset_mode = preset_mode
        if preset_mode == PRESET_WIND_FREE:
            self._attr_fan_mode = FAN_AUTO
            self._attr_swing_mode = SWING_OFF
        if self._attr_hvac_mode is not HVACMode.OFF:
            await self._async_send_current_state()
        self.async_write_ha_state()

    @override
    async def async_turn_on(self) -> None:
        """Turn on into the last active HVAC mode."""
        await self.async_set_hvac_mode(_PROTOCOL_MODE_TO_HA[self._mode_for_frame])

    async def _async_send_current_state(self) -> None:
        """Encode the entity state into a frame and send it via the emitter."""
        wind_free = self._attr_preset_mode == PRESET_WIND_FREE
        fan = _HA_FAN_TO_PROTOCOL[self._attr_fan_mode or FAN_AUTO]
        if wind_free:
            fan = SamsungAcFanSpeed.AUTO

        if wind_free:
            fan_special = SamsungAcFanSpecial.WIND_FREE
        elif fan is SamsungAcFanSpeed.TURBO:
            fan_special = SamsungAcFanSpecial.POWERFUL
        else:
            fan_special = SamsungAcFanSpecial.OFF

        swing = (
            SamsungAcSwing.BOTH
            if self._attr_swing_mode == SWING_ON and not wind_free
            else SamsungAcSwing.OFF
        )

        await self._send_command(
            SamsungAcCommand(
                power=self._attr_hvac_mode is not HVACMode.OFF,
                mode=self._mode_for_frame,
                temperature=int(
                    self._attr_target_temperature or DEFAULT_TARGET_TEMPERATURE,
                ),
                fan=fan,
                swing=swing,
                fan_special=fan_special,
            ),
        )


class SamsungClimateIrClimateWithReceiver(
    SamsungClimateIrClimate,
    InfraredReceiverConsumerEntity,
):
    """Samsung AC climate entity that also tracks an infrared receiver."""

    def __init__(
        self,
        entry: SamsungClimateIrConfigEntry,
        emitter_entity_id: str,
        receiver_entity_id: str,
    ) -> None:
        """Initialize the Samsung AC climate entity with a receiver."""
        super().__init__(entry, emitter_entity_id)
        self._infrared_receiver_entity_id = receiver_entity_id

    @override
    @callback
    def _handle_signal(self, signal: InfraredReceivedSignal) -> None:
        """Update the assumed state from a physical remote signal."""
        command = SamsungAcCommand.from_raw_timings(signal.timings)
        if command is None:
            return

        if not command.power:
            self._attr_hvac_mode = HVACMode.OFF
        else:
            hvac_mode = _PROTOCOL_MODE_TO_HA[command.mode]
            if hvac_mode not in self._attr_hvac_modes:
                return
            self._attr_hvac_mode = hvac_mode
            self._mode_for_frame = command.mode

        self._attr_target_temperature = float(command.temperature)
        if command.fan_special is SamsungAcFanSpecial.POWERFUL:
            self._attr_fan_mode = FAN_TURBO
        else:
            self._attr_fan_mode = _PROTOCOL_FAN_TO_HA[command.fan]
        self._attr_swing_mode = (
            SWING_OFF if command.swing is SamsungAcSwing.OFF else SWING_ON
        )
        self._attr_preset_mode = (
            PRESET_WIND_FREE
            if command.fan_special is SamsungAcFanSpecial.WIND_FREE
            else PRESET_NONE
        )
        self.async_write_ha_state()
