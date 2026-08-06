from __future__ import annotations

from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    SERVICE_SET_HVAC_MODE,
    HVACMode,
)
from homeassistant.components.climate import (
    DOMAIN as CLIMATE_DOMAIN,
)
from homeassistant.components.infrared import InfraredReceivedSignal
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import State
from pytest_homeassistant_custom_component.common import mock_restore_cache

from custom_components.samsung_climate_ir.protocol import (
    SamsungAcCommand,
    SamsungAcMode,
)
from tests.conftest import (
    CLIMATE_ENTITY_ID,
    EMITTER_ENTITY_ID,
    SWITCH_ENTITY_ID,
    make_config_entry,
)


def sent_command(mock_send_command) -> SamsungAcCommand:
    assert mock_send_command.await_count >= 1
    return mock_send_command.await_args.args[2]


async def switch_call(hass, service):
    await hass.services.async_call(
        SWITCH_DOMAIN,
        service,
        {ATTR_ENTITY_ID: SWITCH_ENTITY_ID},
        blocking=True,
    )


async def test_switch_created_off(hass, setup_integration):
    assert hass.states.get(SWITCH_ENTITY_ID).state == STATE_OFF


async def test_turn_on_while_climate_off_only_stores(
    hass, setup_integration, mock_send_command
):
    await switch_call(hass, SERVICE_TURN_ON)

    assert mock_send_command.await_count == 0
    assert hass.states.get(SWITCH_ENTITY_ID).state == STATE_ON


async def test_turn_on_while_climate_on_resends_with_display(
    hass, setup_integration, mock_send_command
):
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: CLIMATE_ENTITY_ID, ATTR_HVAC_MODE: HVACMode.COOL},
        blocking=True,
    )
    await switch_call(hass, SERVICE_TURN_ON)

    command = sent_command(mock_send_command)
    assert command.display is True
    assert command.power is True
    assert command.mode is SamsungAcMode.COOL

    await switch_call(hass, SERVICE_TURN_OFF)
    assert sent_command(mock_send_command).display is False
    assert hass.states.get(SWITCH_ENTITY_ID).state == STATE_OFF


async def test_climate_frames_carry_display_state(
    hass, setup_integration, mock_send_command
):
    await switch_call(hass, SERVICE_TURN_ON)
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: CLIMATE_ENTITY_ID, ATTR_HVAC_MODE: HVACMode.HEAT},
        blocking=True,
    )

    assert sent_command(mock_send_command).display is True


async def test_restore_display_state(
    hass, mock_send_command, enable_custom_integrations
):
    mock_restore_cache(hass, [State(SWITCH_ENTITY_ID, STATE_ON)])
    hass.states.async_set(EMITTER_ENTITY_ID, "idle")
    entry = make_config_entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(SWITCH_ENTITY_ID).state == STATE_ON


async def test_receiver_signal_updates_switch(
    hass, setup_integration_with_receiver, mock_subscribe_receiver
):
    callback = mock_subscribe_receiver.subscription["callback"]
    callback(
        InfraredReceivedSignal(
            timings=SamsungAcCommand(
                power=True,
                mode=SamsungAcMode.COOL,
                temperature=22,
                display=True,
            ).get_raw_timings()
        )
    )
    await hass.async_block_till_done()

    assert hass.states.get(SWITCH_ENTITY_ID).state == STATE_ON


async def test_switch_unavailable_when_emitter_unavailable(hass, setup_integration):
    hass.states.async_set(EMITTER_ENTITY_ID, STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    assert hass.states.get(SWITCH_ENTITY_ID).state == STATE_UNAVAILABLE
