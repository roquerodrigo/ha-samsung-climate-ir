from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

pytest_plugins = "pytest_homeassistant_custom_component"

EMITTER_ENTITY_ID = "infrared.test_emitter"
RECEIVER_ENTITY_ID = "infrared.test_receiver"
CLIMATE_ENTITY_ID = "climate.samsung_ac_ir"
SWITCH_ENTITY_ID = "switch.samsung_ac_ir_display"

CONFIG_DATA = {
    "emitter_entity_id": EMITTER_ENTITY_ID,
    "hvac_modes": ["cool", "heat", "dry", "fan_only"],
}


@pytest.fixture
def enable_custom_integrations(hass) -> None:
    from homeassistant.loader import DATA_CUSTOM_COMPONENTS

    hass.data.pop(DATA_CUSTOM_COMPONENTS, None)


@pytest.fixture
def mock_send_command() -> Generator[AsyncMock]:
    with patch(
        "homeassistant.components.infrared.helpers.async_send_command",
        new_callable=AsyncMock,
    ) as mock:
        yield mock


@pytest.fixture
def mock_subscribe_receiver() -> Generator:
    subscription = {}

    def fake_subscribe(hass, entity_id, signal_callback):
        subscription["callback"] = signal_callback
        return lambda: subscription.pop("callback", None)

    with patch(
        "homeassistant.components.infrared.helpers.async_subscribe_receiver",
        side_effect=fake_subscribe,
    ) as mock:
        mock.subscription = subscription
        yield mock


def make_config_entry(**overrides):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.samsung_climate_ir.const import DOMAIN

    return MockConfigEntry(domain=DOMAIN, data={**CONFIG_DATA, **overrides})


@pytest.fixture
async def setup_integration(hass, mock_send_command, enable_custom_integrations):
    hass.states.async_set(EMITTER_ENTITY_ID, "idle")
    entry = make_config_entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.fixture
async def setup_integration_with_receiver(
    hass, mock_send_command, mock_subscribe_receiver, enable_custom_integrations
):
    hass.states.async_set(EMITTER_ENTITY_ID, "idle")
    hass.states.async_set(RECEIVER_ENTITY_ID, "idle")
    entry = make_config_entry(receiver_entity_id=RECEIVER_ENTITY_ID)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
