"""Config flow for Chameleon integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    CONF_ANIMATION_ENABLED,
    CONF_ANIMATION_SPEED,
    CONF_LIGHT_ENTITIES,
    CONF_MEDIA_PLAYER,
    DEFAULT_ANIMATION_ENABLED,
    DEFAULT_ANIMATION_SPEED,
    DOMAIN,
    MAX_ANIMATION_SPEED,
    MIN_ANIMATION_SPEED,
)
from .helpers import get_entry_title


class ChameleonConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Chameleon."""

    VERSION = 3  # Bumped for media player support

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> ChameleonOptionsFlow:
        """Get the options flow for this handler."""
        return ChameleonOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            light_entities: list[str] = user_input[CONF_LIGHT_ENTITIES]

            # Create a unique ID from sorted light entities
            unique_id = "_".join(sorted(light_entities))
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            # Create the config entry with area-aware naming
            title = get_entry_title(self.hass, light_entities)
            return self.async_create_entry(
                title=title,
                data=user_input,
            )

        # Show the form
        data_schema = vol.Schema(
            {
                vol.Required(CONF_LIGHT_ENTITIES): EntitySelector(
                    EntitySelectorConfig(
                        domain="light",
                        multiple=True,
                    )
                ),
                vol.Optional(CONF_MEDIA_PLAYER): EntitySelector(
                    EntitySelectorConfig(
                        domain="media_player",
                        multiple=False,
                    )
                ),
                vol.Required(CONF_ANIMATION_ENABLED, default=DEFAULT_ANIMATION_ENABLED): BooleanSelector(),
                vol.Required(CONF_ANIMATION_SPEED, default=DEFAULT_ANIMATION_SPEED): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_ANIMATION_SPEED,
                        max=MAX_ANIMATION_SPEED,
                        step=0.1,
                        unit_of_measurement="seconds",
                        mode=NumberSelectorMode.SLIDER,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )


class ChameleonOptionsFlow(OptionsFlow):
    """Handle options flow for Chameleon - modify entities after setup."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the options step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            new_light_entities: list[str] = user_input[CONF_LIGHT_ENTITIES]

            # Build updated data dict - start from current data, overlay changes
            new_data = {**self._config_entry.data}
            new_data[CONF_LIGHT_ENTITIES] = new_light_entities

            # Handle optional media player (remove key if cleared)
            if CONF_MEDIA_PLAYER in user_input and user_input[CONF_MEDIA_PLAYER]:
                new_data[CONF_MEDIA_PLAYER] = user_input[CONF_MEDIA_PLAYER]
            else:
                new_data.pop(CONF_MEDIA_PLAYER, None)

            # Update unique ID if lights changed
            new_unique_id = "_".join(sorted(new_light_entities))
            if new_unique_id != self._config_entry.unique_id:
                # Check if another entry already uses these lights
                for entry in self.hass.config_entries.async_entries(DOMAIN):
                    if entry.entry_id != self._config_entry.entry_id and entry.unique_id == new_unique_id:
                        errors["base"] = "already_configured"
                        break

            if not errors:
                # Update the entry title based on new lights
                new_title = get_entry_title(self.hass, new_light_entities)

                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    title=new_title,
                    data=new_data,
                    unique_id="_".join(sorted(new_light_entities)),
                )

                # Reload the entry so all entities get recreated with new config
                await self.hass.config_entries.async_reload(self._config_entry.entry_id)

                return self.async_create_entry(data={})

        # Pre-fill form with current values
        current_lights = self._config_entry.data.get(CONF_LIGHT_ENTITIES, [])
        current_media_player = self._config_entry.data.get(CONF_MEDIA_PLAYER)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_LIGHT_ENTITIES, default=current_lights): EntitySelector(
                    EntitySelectorConfig(
                        domain="light",
                        multiple=True,
                    )
                ),
                vol.Optional(
                    CONF_MEDIA_PLAYER,
                    description={"suggested_value": current_media_player},
                ): EntitySelector(
                    EntitySelectorConfig(
                        domain="media_player",
                        multiple=False,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
        )