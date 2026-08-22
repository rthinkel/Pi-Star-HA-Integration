"""Diagnostics support for the Pi-Star integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_PASSWORD


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry
) -> dict[str, Any]:
    """Return diagnostics for a Pi-Star config entry."""
    coordinator = entry.runtime_data
    return {
        "entry": {
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), {CONF_PASSWORD}),
            "options": dict(entry.options),
        },
        "last_update_success": coordinator.last_update_success,
        "last_refresh_groups": coordinator.last_refresh_groups,
        "data": coordinator.data,
    }
