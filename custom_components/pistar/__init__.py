"""Pi-Star Home Assistant integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import PiStarClient
from .const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_SCAN_INTERVAL,
)
from .coordinator import PiStarCoordinator

PLATFORMS: tuple[Platform, ...] = (Platform.SENSOR,)

type PiStarConfigEntry = ConfigEntry[PiStarCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: PiStarConfigEntry) -> bool:
    """Set up Pi-Star from a config entry."""
    client = PiStarClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )

    coordinator = PiStarCoordinator(hass, client, scan_interval)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PiStarConfigEntry) -> bool:
    """Unload a Pi-Star config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate older Pi-Star config entries."""
    if entry.version == 1:
        data = dict(entry.data)
        options = dict(entry.options)
        if CONF_SCAN_INTERVAL in data:
            options.setdefault(CONF_SCAN_INTERVAL, data.pop(CONF_SCAN_INTERVAL))

        hass.config_entries.async_update_entry(
            entry,
            data=data,
            options=options,
            unique_id=None,
            version=2,
        )

    return True
