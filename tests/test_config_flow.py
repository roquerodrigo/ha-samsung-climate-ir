from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.samsung_climate_ir.const import DOMAIN
from tests.conftest import EMITTER_ENTITY_ID, RECEIVER_ENTITY_ID, make_config_entry


@pytest.fixture
def mock_infrared_entities():
    with (
        patch(
            "custom_components.samsung_climate_ir.config_flow.async_get_emitters",
            return_value=[EMITTER_ENTITY_ID],
        ),
        patch(
            "custom_components.samsung_climate_ir.config_flow.async_get_receivers",
            return_value=[RECEIVER_ENTITY_ID],
        ),
    ):
        yield


async def test_user_flow_aborts_without_emitters(hass, enable_custom_integrations):
    with patch(
        "custom_components.samsung_climate_ir.config_flow.async_get_emitters",
        return_value=[],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_emitter_entities"


async def test_user_flow_creates_entry(
    hass, enable_custom_integrations, mock_infrared_entities
):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "emitter_entity_id": EMITTER_ENTITY_ID,
            "hvac_modes": ["cool", "heat"],
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"Samsung AC via {EMITTER_ENTITY_ID}"
    assert result["data"] == {
        "emitter_entity_id": EMITTER_ENTITY_ID,
        "hvac_modes": ["cool", "heat"],
    }


async def test_user_flow_creates_entry_with_receiver(
    hass, enable_custom_integrations, mock_infrared_entities
):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "emitter_entity_id": EMITTER_ENTITY_ID,
            "receiver_entity_id": RECEIVER_ENTITY_ID,
            "hvac_modes": ["cool"],
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["receiver_entity_id"] == RECEIVER_ENTITY_ID


async def test_user_flow_aborts_on_duplicate_emitter(
    hass, enable_custom_integrations, mock_infrared_entities
):
    make_config_entry().add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "emitter_entity_id": EMITTER_ENTITY_ID,
            "hvac_modes": ["cool"],
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_flow_title_uses_registry_name(
    hass, enable_custom_integrations, mock_infrared_entities
):
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    registry.async_get_or_create(
        "infrared",
        "mqtt",
        "emitter-unique-id",
        suggested_object_id="test_emitter",
        original_name="Living Room Blaster",
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "emitter_entity_id": EMITTER_ENTITY_ID,
            "hvac_modes": ["cool"],
        },
    )
    assert result["title"] == "Samsung AC via Living Room Blaster"


async def test_reconfigure_updates_data_and_reloads(
    hass, enable_custom_integrations, mock_infrared_entities
):
    entry = make_config_entry()
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "emitter_entity_id": EMITTER_ENTITY_ID,
            "hvac_modes": ["cool", "heat"],
        },
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {
        "emitter_entity_id": EMITTER_ENTITY_ID,
        "hvac_modes": ["cool", "heat"],
    }


async def test_reconfigure_can_drop_the_receiver(
    hass, enable_custom_integrations, mock_infrared_entities
):
    entry = make_config_entry(receiver_entity_id=RECEIVER_ENTITY_ID)
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "emitter_entity_id": EMITTER_ENTITY_ID,
            "hvac_modes": ["cool"],
        },
    )
    await hass.async_block_till_done()
    assert result["reason"] == "reconfigure_successful"
    assert "receiver_entity_id" not in entry.data


async def test_reconfigure_aborts_on_another_entries_emitter(
    hass, enable_custom_integrations, mock_infrared_entities
):
    make_config_entry().add_to_hass(hass)
    other_emitter_entry = make_config_entry(emitter_entity_id="infrared.other_emitter")
    other_emitter_entry.add_to_hass(hass)

    result = await other_emitter_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "emitter_entity_id": EMITTER_ENTITY_ID,
            "hvac_modes": ["cool"],
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert other_emitter_entry.data["emitter_entity_id"] == "infrared.other_emitter"


async def test_reconfigure_aborts_without_emitters(hass, enable_custom_integrations):
    entry = make_config_entry()
    entry.add_to_hass(hass)

    with patch(
        "custom_components.samsung_climate_ir.config_flow.async_get_emitters",
        return_value=[],
    ):
        result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_emitter_entities"
