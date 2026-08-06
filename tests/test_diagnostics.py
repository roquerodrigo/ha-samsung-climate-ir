from __future__ import annotations

from custom_components.samsung_climate_ir.diagnostics import (
    async_get_config_entry_diagnostics,
)
from tests.conftest import CLIMATE_ENTITY_ID, EMITTER_ENTITY_ID


async def test_diagnostics_payload(hass, setup_integration):
    payload = await async_get_config_entry_diagnostics(hass, setup_integration)

    assert payload["entry_data"]["emitter_entity_id"] == EMITTER_ENTITY_ID
    assert len(payload["climate_states"]) == 1
    assert payload["climate_states"][0]["entity_id"] == CLIMATE_ENTITY_ID
