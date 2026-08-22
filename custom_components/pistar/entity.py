"""Base entities for the Pi-Star integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PiStarCoordinator


class PiStarEntity(CoordinatorEntity[PiStarCoordinator]):
    """Base class for Pi-Star entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PiStarCoordinator, entry_id: str, title: str) -> None:
        """Initialize the Pi-Star entity."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=title,
            manufacturer="Pi-Star",
            model="Digital Voice Hotspot",
            configuration_url=coordinator.client.configuration_url,
        )
