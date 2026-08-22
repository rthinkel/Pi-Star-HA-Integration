"""Config flow for the Pi-Star integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .client import (
    PiStarAuthenticationError,
    PiStarClient,
    PiStarError,
    normalize_base_url,
)
from .const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_HOST,
    DEFAULT_PASSWORD,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USERNAME,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

PASSWORD_SELECTOR = TextSelector(
    TextSelectorConfig(
        type=TextSelectorType.PASSWORD,
        autocomplete="current-password",
    )
)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Required(CONF_PASSWORD, default=DEFAULT_PASSWORD): PASSWORD_SELECTOR,
    }
)


class PiStarConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Pi-Star config flow."""

    VERSION = 2

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> PiStarOptionsFlow:
        """Return the Pi-Star options flow."""
        return PiStarOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle initial setup."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                data = self._normalize_connection_data(user_input)
                if self._host_is_configured(data[CONF_HOST]):
                    return self.async_abort(reason="already_configured")
                await self._async_validate(data)
            except ValueError:
                errors["base"] = "invalid_host"
            except PiStarAuthenticationError:
                errors["base"] = "invalid_auth"
            except PiStarError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Pi-Star setup")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"Pi-Star ({self._display_host(data[CONF_HOST])})",
                    data=data,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                USER_SCHEMA, user_input or {}
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle credential reauthentication."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            data = {
                CONF_HOST: entry.data[CONF_HOST],
                CONF_USERNAME: username,
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }
            try:
                if not username:
                    raise ValueError
                await self._async_validate(data)
            except ValueError:
                errors["base"] = "invalid_auth"
            except PiStarAuthenticationError:
                errors["base"] = "invalid_auth"
            except PiStarError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Pi-Star reauthentication")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_USERNAME: data[CONF_USERNAME],
                        CONF_PASSWORD: data[CONF_PASSWORD],
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_USERNAME,
                    default=entry.data.get(CONF_USERNAME, DEFAULT_USERNAME),
                ): str,
                vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR,
            }
        )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                schema, user_input or {}
            ),
            errors=errors,
            description_placeholders={"host": entry.data[CONF_HOST]},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle user-initiated connection reconfiguration."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                base_url = normalize_base_url(user_input[CONF_HOST])
                if self._host_is_configured(
                    base_url, exclude_entry_id=entry.entry_id
                ):
                    return self.async_abort(reason="already_configured")

                username = user_input[CONF_USERNAME].strip()
                if not username:
                    raise ValueError
                password = user_input.get(CONF_PASSWORD) or entry.data[CONF_PASSWORD]
                data = {
                    CONF_HOST: base_url,
                    CONF_USERNAME: username,
                    CONF_PASSWORD: password,
                }
                await self._async_validate(data)
            except ValueError:
                errors["base"] = "invalid_host"
            except PiStarAuthenticationError:
                errors["base"] = "invalid_auth"
            except PiStarError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Pi-Star reconfiguration")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    title=f"Pi-Star ({self._display_host(base_url)})",
                    data=data,
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST, default=entry.data.get(CONF_HOST, DEFAULT_HOST)
                ): str,
                vol.Required(
                    CONF_USERNAME,
                    default=entry.data.get(CONF_USERNAME, DEFAULT_USERNAME),
                ): str,
                vol.Optional(CONF_PASSWORD): PASSWORD_SELECTOR,
            }
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                schema, user_input or {}
            ),
            errors=errors,
        )

    async def _async_validate(self, data: Mapping[str, Any]) -> None:
        """Validate Pi-Star connection data."""
        client = PiStarClient(
            async_get_clientsession(self.hass),
            data[CONF_HOST],
            data[CONF_USERNAME],
            data[CONF_PASSWORD],
        )
        await client.async_validate()

    def _normalize_connection_data(
        self, user_input: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Normalize config-flow input."""
        username = str(user_input[CONF_USERNAME]).strip()
        if not username:
            raise ValueError("Username cannot be empty")
        return {
            CONF_HOST: normalize_base_url(str(user_input[CONF_HOST])),
            CONF_USERNAME: username,
            CONF_PASSWORD: str(user_input[CONF_PASSWORD]),
        }

    def _host_is_configured(
        self, base_url: str, *, exclude_entry_id: str | None = None
    ) -> bool:
        """Return whether a normalized Pi-Star URL is already configured."""
        target = normalize_base_url(base_url).casefold()
        for entry in self._async_current_entries():
            if entry.entry_id == exclude_entry_id:
                continue
            try:
                existing = normalize_base_url(
                    str(entry.data.get(CONF_HOST, ""))
                ).casefold()
            except ValueError:
                continue
            if existing == target:
                return True
        return False

    @staticmethod
    def _display_host(base_url: str) -> str:
        """Return a compact host label for the config entry title."""
        return base_url.removeprefix("http://").removeprefix("https://")


class PiStarOptionsFlow(OptionsFlowWithReload):
    """Handle Pi-Star options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure polling options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=current_interval
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    )
                }
            ),
        )
