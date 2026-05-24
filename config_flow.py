"""Config flow for Pi-Star integration."""
import logging
import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    DEFAULT_HOST,
    DEFAULT_USERNAME,
    DEFAULT_PASSWORD,
    DEFAULT_SCAN_INTERVAL,
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
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


async def validate_connection(host: str, username: str, password: str) -> None:
    """Try connecting to Pi-Star and raise on failure."""
    auth = aiohttp.BasicAuth(username, password)
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"http://{host}/",
            auth=auth,
            timeout=timeout,
        ) as response:
            if response.status not in (200, 401):
                raise CannotConnect(f"HTTP {response.status}")
            if response.status == 401:
                raise InvalidAuth


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Pi-Star config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            try:
                await validate_connection(
                    user_input[CONF_HOST],
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected error during Pi-Star config flow")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"Pi-Star ({user_input[CONF_HOST]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(Exception):
    pass


class InvalidAuth(Exception):
    pass
