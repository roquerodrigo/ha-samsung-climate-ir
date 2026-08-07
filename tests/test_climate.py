from __future__ import annotations

import pytest
from homeassistant.components.climate import (
    ATTR_FAN_MODE,
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    ATTR_SWING_MODE,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_SWING_MODE,
    SERVICE_SET_TEMPERATURE,
    HVACMode,
)
from homeassistant.components.climate import (
    DOMAIN as CLIMATE_DOMAIN,
)
from homeassistant.components.infrared import InfraredReceivedSignal
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import State
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import mock_restore_cache

from custom_components.samsung_climate_ir.protocol import (
    SamsungAcCommand,
    SamsungAcFanSpecial,
    SamsungAcFanSpeed,
    SamsungAcMode,
    SamsungAcSwing,
)
from tests.conftest import CLIMATE_ENTITY_ID, EMITTER_ENTITY_ID, make_config_entry


def sent_command(mock_send_command) -> SamsungAcCommand:
    assert mock_send_command.await_count >= 1
    return mock_send_command.await_args.args[2]


async def call(hass, service, **data):
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        service,
        {ATTR_ENTITY_ID: CLIMATE_ENTITY_ID, **data},
        blocking=True,
    )


async def test_initial_state_is_off(hass, setup_integration):
    state = hass.states.get(CLIMATE_ENTITY_ID)
    assert state.state == HVACMode.OFF
    assert state.attributes[ATTR_TEMPERATURE] == 22.0


async def test_hvac_modes_come_from_config(hass, setup_integration):
    state = hass.states.get(CLIMATE_ENTITY_ID)
    assert state.attributes["hvac_modes"] == [
        HVACMode.OFF,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
    ]


async def test_set_hvac_mode_sends_power_on_frame(
    hass, setup_integration, mock_send_command
):
    await call(hass, SERVICE_SET_HVAC_MODE, **{ATTR_HVAC_MODE: HVACMode.COOL})

    command = sent_command(mock_send_command)
    assert command.power is True
    assert command.mode is SamsungAcMode.COOL
    assert command.temperature == 22
    assert mock_send_command.await_args.args[1] == EMITTER_ENTITY_ID
    assert hass.states.get(CLIMATE_ENTITY_ID).state == HVACMode.COOL


async def test_turn_off_sends_power_off_with_last_mode(
    hass, setup_integration, mock_send_command
):
    await call(hass, SERVICE_SET_HVAC_MODE, **{ATTR_HVAC_MODE: HVACMode.HEAT})
    await call(hass, SERVICE_TURN_OFF)

    command = sent_command(mock_send_command)
    assert command.power is False
    assert command.mode is SamsungAcMode.HEAT
    assert hass.states.get(CLIMATE_ENTITY_ID).state == HVACMode.OFF


async def test_turn_on_restores_last_mode(hass, setup_integration, mock_send_command):
    await call(hass, SERVICE_SET_HVAC_MODE, **{ATTR_HVAC_MODE: HVACMode.DRY})
    await call(hass, SERVICE_TURN_OFF)
    await call(hass, SERVICE_TURN_ON)

    command = sent_command(mock_send_command)
    assert command.power is True
    assert command.mode is SamsungAcMode.DRY
    assert hass.states.get(CLIMATE_ENTITY_ID).state == HVACMode.DRY


async def test_set_temperature_sends_frame_while_on(
    hass, setup_integration, mock_send_command
):
    await call(hass, SERVICE_SET_HVAC_MODE, **{ATTR_HVAC_MODE: HVACMode.COOL})
    await call(hass, SERVICE_SET_TEMPERATURE, **{ATTR_TEMPERATURE: 18})

    command = sent_command(mock_send_command)
    assert command.temperature == 18
    state = hass.states.get(CLIMATE_ENTITY_ID)
    assert state.attributes[ATTR_TEMPERATURE] == 18.0


async def test_set_temperature_while_off_only_stores(
    hass, setup_integration, mock_send_command
):
    await call(hass, SERVICE_SET_TEMPERATURE, **{ATTR_TEMPERATURE: 25})

    assert mock_send_command.await_count == 0
    assert hass.states.get(CLIMATE_ENTITY_ID).attributes[ATTR_TEMPERATURE] == 25.0


async def test_set_temperature_with_hvac_mode_switches_mode(
    hass, setup_integration, mock_send_command
):
    await call(
        hass,
        SERVICE_SET_TEMPERATURE,
        **{ATTR_TEMPERATURE: 26, ATTR_HVAC_MODE: HVACMode.HEAT},
    )

    command = sent_command(mock_send_command)
    assert command.power is True
    assert command.mode is SamsungAcMode.HEAT
    assert command.temperature == 26
    assert hass.states.get(CLIMATE_ENTITY_ID).state == HVACMode.HEAT


async def test_set_fan_mode_while_on_sends_frame(
    hass, setup_integration, mock_send_command
):
    await call(hass, SERVICE_SET_HVAC_MODE, **{ATTR_HVAC_MODE: HVACMode.COOL})
    await call(hass, SERVICE_SET_FAN_MODE, **{ATTR_FAN_MODE: "high"})

    command = sent_command(mock_send_command)
    assert command.fan is SamsungAcFanSpeed.HIGH
    assert command.fan_special is SamsungAcFanSpecial.OFF


async def test_set_fan_mode_while_off_only_stores(
    hass, setup_integration, mock_send_command
):
    await call(hass, SERVICE_SET_FAN_MODE, **{ATTR_FAN_MODE: "low"})

    assert mock_send_command.await_count == 0
    assert hass.states.get(CLIMATE_ENTITY_ID).attributes[ATTR_FAN_MODE] == "low"


async def test_turbo_fan_sets_powerful_feature(
    hass, setup_integration, mock_send_command
):
    await call(hass, SERVICE_SET_HVAC_MODE, **{ATTR_HVAC_MODE: HVACMode.COOL})
    await call(hass, SERVICE_SET_FAN_MODE, **{ATTR_FAN_MODE: "turbo"})

    command = sent_command(mock_send_command)
    assert command.fan is SamsungAcFanSpeed.TURBO
    assert command.fan_special is SamsungAcFanSpecial.POWERFUL


async def test_swing_on_sends_both(hass, setup_integration, mock_send_command):
    await call(hass, SERVICE_SET_HVAC_MODE, **{ATTR_HVAC_MODE: HVACMode.COOL})
    await call(hass, SERVICE_SET_SWING_MODE, **{ATTR_SWING_MODE: "on"})

    command = sent_command(mock_send_command)
    assert command.swing is SamsungAcSwing.BOTH


async def test_wind_free_preset_forces_auto_fan_and_swing_off(
    hass, setup_integration, mock_send_command
):
    await call(hass, SERVICE_SET_HVAC_MODE, **{ATTR_HVAC_MODE: HVACMode.COOL})
    await call(hass, SERVICE_SET_SWING_MODE, **{ATTR_SWING_MODE: "on"})
    await call(hass, SERVICE_SET_FAN_MODE, **{ATTR_FAN_MODE: "high"})
    await call(hass, SERVICE_SET_PRESET_MODE, **{ATTR_PRESET_MODE: "wind_free"})

    command = sent_command(mock_send_command)
    assert command.fan_special is SamsungAcFanSpecial.WIND_FREE
    assert command.fan is SamsungAcFanSpeed.AUTO
    assert command.swing is SamsungAcSwing.OFF
    state = hass.states.get(CLIMATE_ENTITY_ID)
    assert state.attributes[ATTR_FAN_MODE] == "auto"
    assert state.attributes[ATTR_SWING_MODE] == "off"


async def test_non_auto_fan_drops_wind_free(hass, setup_integration, mock_send_command):
    await call(hass, SERVICE_SET_HVAC_MODE, **{ATTR_HVAC_MODE: HVACMode.COOL})
    await call(hass, SERVICE_SET_PRESET_MODE, **{ATTR_PRESET_MODE: "wind_free"})
    await call(hass, SERVICE_SET_FAN_MODE, **{ATTR_FAN_MODE: "medium"})

    command = sent_command(mock_send_command)
    assert command.fan is SamsungAcFanSpeed.MEDIUM
    assert command.fan_special is SamsungAcFanSpecial.OFF
    assert hass.states.get(CLIMATE_ENTITY_ID).attributes[ATTR_PRESET_MODE] == "none"


async def test_swing_on_drops_wind_free(hass, setup_integration, mock_send_command):
    await call(hass, SERVICE_SET_HVAC_MODE, **{ATTR_HVAC_MODE: HVACMode.COOL})
    await call(hass, SERVICE_SET_PRESET_MODE, **{ATTR_PRESET_MODE: "wind_free"})
    await call(hass, SERVICE_SET_SWING_MODE, **{ATTR_SWING_MODE: "on"})

    command = sent_command(mock_send_command)
    assert command.swing is SamsungAcSwing.BOTH
    assert command.fan_special is SamsungAcFanSpecial.OFF
    assert hass.states.get(CLIMATE_ENTITY_ID).attributes[ATTR_PRESET_MODE] == "none"


async def test_heat_mode_drops_wind_free(hass, setup_integration, mock_send_command):
    await call(hass, SERVICE_SET_HVAC_MODE, **{ATTR_HVAC_MODE: HVACMode.COOL})
    await call(hass, SERVICE_SET_PRESET_MODE, **{ATTR_PRESET_MODE: "wind_free"})
    await call(hass, SERVICE_SET_HVAC_MODE, **{ATTR_HVAC_MODE: HVACMode.HEAT})

    command = sent_command(mock_send_command)
    assert command.fan_special is SamsungAcFanSpecial.OFF
    assert hass.states.get(CLIMATE_ENTITY_ID).attributes[ATTR_PRESET_MODE] == "none"


async def test_entity_unavailable_when_emitter_unavailable(hass, setup_integration):
    hass.states.async_set(EMITTER_ENTITY_ID, STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    assert hass.states.get(CLIMATE_ENTITY_ID).state == STATE_UNAVAILABLE

    hass.states.async_set(EMITTER_ENTITY_ID, "idle")
    await hass.async_block_till_done()
    assert hass.states.get(CLIMATE_ENTITY_ID).state != STATE_UNAVAILABLE


async def test_restore_state(hass, mock_send_command, enable_custom_integrations):
    mock_restore_cache(
        hass,
        [
            State(
                CLIMATE_ENTITY_ID,
                HVACMode.HEAT,
                {
                    ATTR_TEMPERATURE: 27,
                    ATTR_FAN_MODE: "high",
                    ATTR_SWING_MODE: "on",
                    ATTR_PRESET_MODE: "none",
                },
            )
        ],
    )
    hass.states.async_set(EMITTER_ENTITY_ID, "idle")
    entry = make_config_entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(CLIMATE_ENTITY_ID)
    assert state.state == HVACMode.HEAT
    assert state.attributes[ATTR_TEMPERATURE] == 27.0
    assert state.attributes[ATTR_FAN_MODE] == "high"
    assert state.attributes[ATTR_SWING_MODE] == "on"


@pytest.fixture
def received_signal(mock_subscribe_receiver):
    def send(command: SamsungAcCommand):
        callback = mock_subscribe_receiver.subscription["callback"]
        callback(InfraredReceivedSignal(timings=command.get_raw_timings()))

    return send


async def test_receiver_signal_updates_state(
    hass, setup_integration_with_receiver, received_signal
):
    received_signal(
        SamsungAcCommand(
            power=True,
            mode=SamsungAcMode.HEAT,
            temperature=28,
            fan=SamsungAcFanSpeed.HIGH,
            swing=SamsungAcSwing.BOTH,
        )
    )
    await hass.async_block_till_done()

    state = hass.states.get(CLIMATE_ENTITY_ID)
    assert state.state == HVACMode.HEAT
    assert state.attributes[ATTR_TEMPERATURE] == 28.0
    assert state.attributes[ATTR_FAN_MODE] == "high"
    assert state.attributes[ATTR_SWING_MODE] == "on"


async def test_receiver_power_off_signal(
    hass, setup_integration_with_receiver, received_signal
):
    received_signal(
        SamsungAcCommand(power=False, mode=SamsungAcMode.COOL, temperature=22)
    )
    await hass.async_block_till_done()
    assert hass.states.get(CLIMATE_ENTITY_ID).state == HVACMode.OFF


async def test_receiver_wind_free_signal(
    hass, setup_integration_with_receiver, received_signal
):
    received_signal(
        SamsungAcCommand(
            power=True,
            mode=SamsungAcMode.COOL,
            temperature=22,
            fan_special=SamsungAcFanSpecial.WIND_FREE,
        )
    )
    await hass.async_block_till_done()
    state = hass.states.get(CLIMATE_ENTITY_ID)
    assert state.attributes[ATTR_PRESET_MODE] == "wind_free"


async def test_receiver_powerful_signal_shows_turbo_fan(
    hass, setup_integration_with_receiver, received_signal
):
    received_signal(
        SamsungAcCommand(
            power=True,
            mode=SamsungAcMode.COOL,
            temperature=22,
            fan=SamsungAcFanSpeed.TURBO,
            fan_special=SamsungAcFanSpecial.POWERFUL,
        )
    )
    await hass.async_block_till_done()
    assert hass.states.get(CLIMATE_ENTITY_ID).attributes[ATTR_FAN_MODE] == "turbo"


async def test_receiver_ignores_undecodable_signal(
    hass, setup_integration_with_receiver, mock_subscribe_receiver
):
    callback = mock_subscribe_receiver.subscription["callback"]
    callback(InfraredReceivedSignal(timings=[100, -100, 100]))
    await hass.async_block_till_done()
    assert hass.states.get(CLIMATE_ENTITY_ID).state == HVACMode.OFF


async def test_receiver_ignores_unconfigured_mode(
    hass, mock_send_command, mock_subscribe_receiver, enable_custom_integrations
):
    hass.states.async_set(EMITTER_ENTITY_ID, "idle")
    hass.states.async_set("infrared.test_receiver", "idle")
    entry = make_config_entry(
        hvac_modes=["cool"], receiver_entity_id="infrared.test_receiver"
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    callback = mock_subscribe_receiver.subscription["callback"]
    callback(
        InfraredReceivedSignal(
            timings=SamsungAcCommand(
                power=True, mode=SamsungAcMode.HEAT, temperature=24
            ).get_raw_timings()
        )
    )
    await hass.async_block_till_done()
    assert hass.states.get(CLIMATE_ENTITY_ID).state == HVACMode.OFF


async def test_turn_on_uses_first_configured_mode_when_cool_is_excluded(
    hass, mock_send_command, enable_custom_integrations
):
    hass.states.async_set(EMITTER_ENTITY_ID, "idle")
    entry = make_config_entry(hvac_modes=["heat", "dry"])
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await call(hass, SERVICE_TURN_ON)

    command = sent_command(mock_send_command)
    assert command.power is True
    assert command.mode is SamsungAcMode.HEAT
    assert hass.states.get(CLIMATE_ENTITY_ID).state == HVACMode.HEAT


async def test_set_temperature_rejects_unconfigured_hvac_mode(
    hass, setup_integration, mock_send_command
):
    with pytest.raises(ServiceValidationError):
        await call(
            hass,
            SERVICE_SET_TEMPERATURE,
            **{ATTR_TEMPERATURE: 24, ATTR_HVAC_MODE: HVACMode.AUTO},
        )

    assert mock_send_command.await_count == 0
    assert hass.states.get(CLIMATE_ENTITY_ID).state == HVACMode.OFF


async def test_set_hvac_mode_service_rejects_unconfigured_mode(
    hass, setup_integration, mock_send_command
):
    with pytest.raises(ServiceValidationError):
        await call(hass, SERVICE_SET_HVAC_MODE, **{ATTR_HVAC_MODE: HVACMode.AUTO})

    assert mock_send_command.await_count == 0
