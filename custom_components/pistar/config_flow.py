"""Config flow for Pi-Star integration."""
import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Required(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
    }
)


async def validate_connection(hass, host: str, username: str, password: str) -> None:
    """Verify that the Pi-Star MMDVM dashboard can be reached."""
    client = PiStarClient(
        async_get_clientsession(hass),
        host,
        username,
        password,
    )
    await client.async_get_text("/mmdvmhost/repeaterinfo.php")


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Pi-Star config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial configuration step."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            try:
                await validate_connection(
                    self.hass,
                    host,
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
            except PiStarAuthenticationError:
                errors["base"] = "invalid_auth"
            except (PiStarError, ValueError):
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Pi-Star config flow")
                errors["base"] = "unknown"
            else:
                normalized_url = normalize_base_url(host)
                await self.async_set_unique_id(normalized_url.casefold())
                self._abort_if_unique_id_configured()
                user_input[CONF_HOST] = host
                return self.async_create_entry(
                    title=f"Pi-Star ({host})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
