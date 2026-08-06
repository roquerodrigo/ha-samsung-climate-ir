from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState

from tests.conftest import CLIMATE_ENTITY_ID


async def test_setup_entry_loads_successfully(hass, setup_integration):
    assert setup_integration.state == ConfigEntryState.LOADED


async def test_setup_entry_creates_climate_entity(hass, setup_integration):
    assert hass.states.get(CLIMATE_ENTITY_ID) is not None


async def test_unload_entry_succeeds(hass, setup_integration):
    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    assert setup_integration.state == ConfigEntryState.NOT_LOADED


async def test_unload_entry_makes_entity_unavailable(hass, setup_integration):
    await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(CLIMATE_ENTITY_ID).state == "unavailable"
