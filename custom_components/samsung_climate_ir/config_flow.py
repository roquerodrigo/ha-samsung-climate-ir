"""Config flow for samsung_climate_ir."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.climate import HVACMode
from homeassistant.components.infrared import (
    DOMAIN as INFRARED_DOMAIN,
)
from homeassistant.components.infrared import (
    async_get_emitters,
    async_get_receivers,
)
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_EMITTER_ENTITY_ID,
    CONF_HVAC_MODES,
    CONF_RECEIVER_ENTITY_ID,
    DOMAIN,
)

_HVAC_MODE_OPTIONS = [
    HVACMode.AUTO,
    HVACMode.COOL,
    HVACMode.DRY,
    HVACMode.FAN_ONLY,
    HVACMode.HEAT,
]
_DEFAULT_HVAC_MODES = [
    HVACMode.COOL,
    HVACMode.DRY,
    HVACMode.FAN_ONLY,
    HVACMode.HEAT,
]


class SamsungClimateIrFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Samsung Climate IR."""

    VERSION = 1

    def _entity_name(self, entity_id: str) -> str:
        """Return the friendly name registered for an entity."""
        registry = er.async_get(self.hass)
        entry = registry.async_get(entity_id)
        return entry.name or entry.original_name or entity_id if entry else entity_id

    def _schema(self) -> vol.Schema:
        """Build the form schema from the available infrared entities."""
        return vol.Schema(
            {
                vol.Required(CONF_EMITTER_ENTITY_ID): EntitySelector(
                    EntitySelectorConfig(
                        domain=INFRARED_DOMAIN,
                        include_entities=async_get_emitters(self.hass),
                    ),
                ),
                vol.Optional(CONF_RECEIVER_ENTITY_ID): EntitySelector(
                    EntitySelectorConfig(
                        domain=INFRARED_DOMAIN,
                        include_entities=async_get_receivers(self.hass),
                    ),
                ),
                vol.Required(
                    CONF_HVAC_MODES,
                    default=[mode.value for mode in _DEFAULT_HVAC_MODES],
                ): vol.All(
                    SelectSelector(
                        SelectSelectorConfig(
                            options=[mode.value for mode in _HVAC_MODE_OPTIONS],
                            translation_key=CONF_HVAC_MODES,
                            mode=SelectSelectorMode.LIST,
                            multiple=True,
                        ),
                    ),
                    vol.Length(min=1),
                ),
            },
        )

    async def async_step_user(
        self,
        user_input: dict[str, str | list[str]] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        if not async_get_emitters(self.hass):
            return self.async_abort(reason="no_emitter_entities")

        if user_input is not None:
            emitter_entity_id = str(user_input[CONF_EMITTER_ENTITY_ID])
            self._async_abort_entries_match(
                {CONF_EMITTER_ENTITY_ID: emitter_entity_id},
            )
            return self.async_create_entry(
                title=f"Samsung AC via {self._entity_name(emitter_entity_id)}",
                data=user_input,
            )

        return self.async_show_form(step_id="user", data_schema=self._schema())

    async def async_step_reconfigure(
        self,
        user_input: dict[str, str | list[str]] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        if not async_get_emitters(self.hass):
            return self.async_abort(reason="no_emitter_entities")

        entry = self._get_reconfigure_entry()
        if user_input is not None:
            emitter_entity_id = str(user_input[CONF_EMITTER_ENTITY_ID])
            self._async_abort_entries_match(
                {CONF_EMITTER_ENTITY_ID: emitter_entity_id},
            )
            return self.async_update_reload_and_abort(
                entry,
                title=f"Samsung AC via {self._entity_name(emitter_entity_id)}",
                data=user_input,
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                self._schema(),
                entry.data,
            ),
        )
