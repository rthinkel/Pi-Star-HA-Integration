"""Pi-Star sensors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfFrequency,
    UnitOfTime,
)

from .entity import PiStarEntity


@dataclass(frozen=True, kw_only=True)
class PiStarSensorEntityDescription(SensorEntityDescription):
    """Describe a Pi-Star sensor."""

    requires_value: bool = False


SENSORS: tuple[PiStarSensorEntityDescription, ...] = (
    PiStarSensorEntityDescription(key="status", translation_key="status"),
    PiStarSensorEntityDescription(key="dmr_network", translation_key="dmr_network"),
    PiStarSensorEntityDescription(key="trx_status", translation_key="trx_status"),
    PiStarSensorEntityDescription(
        key="firmware",
        translation_key="firmware",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    PiStarSensorEntityDescription(
        key="tx_frequency",
        translation_key="tx_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.MEGAHERTZ,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PiStarSensorEntityDescription(
        key="rx_frequency",
        translation_key="rx_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.MEGAHERTZ,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PiStarSensorEntityDescription(
        key="dmr_id",
        translation_key="dmr_id",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    PiStarSensorEntityDescription(
        key="dmr_cc",
        translation_key="dmr_cc",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    PiStarSensorEntityDescription(key="ts1_status", translation_key="ts1_status"),
    PiStarSensorEntityDescription(key="ts2_status", translation_key="ts2_status"),
    PiStarSensorEntityDescription(key="dmr_master", translation_key="dmr_master"),
    PiStarSensorEntityDescription(key="last_time", translation_key="last_time"),
    PiStarSensorEntityDescription(key="last_callsign", translation_key="last_callsign"),
    PiStarSensorEntityDescription(key="last_tg", translation_key="last_tg"),
    PiStarSensorEntityDescription(key="last_mode", translation_key="last_mode"),
    PiStarSensorEntityDescription(key="last_source", translation_key="last_source"),
    PiStarSensorEntityDescription(
        key="last_duration",
        translation_key="last_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PiStarSensorEntityDescription(
        key="last_loss",
        translation_key="last_loss",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PiStarSensorEntityDescription(
        key="last_ber",
        translation_key="last_ber",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PiStarSensorEntityDescription(
        key="last_rssi",
        translation_key="last_rssi",
        requires_value=True,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PiStarSensorEntityDescription(
        key="currently_tx", translation_key="currently_tx"
    ),
    PiStarSensorEntityDescription(
        key="local_last_callsign", translation_key="local_last_callsign"
    ),
    PiStarSensorEntityDescription(
        key="local_last_tg", translation_key="local_last_tg"
    ),
    PiStarSensorEntityDescription(
        key="local_last_mode", translation_key="local_last_mode"
    ),
    PiStarSensorEntityDescription(
        key="local_last_duration",
        translation_key="local_last_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PiStarSensorEntityDescription(
        key="local_last_ber",
        translation_key="local_last_ber",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PiStarSensorEntityDescription(
        key="local_last_rssi",
        translation_key="local_last_rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up Pi-Star sensors from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        PiStarSensor(coordinator, entry.entry_id, entry.title, description)
        for description in SENSORS
    )


class PiStarSensor(PiStarEntity, SensorEntity):
    """Representation of a Pi-Star sensor."""

    entity_description: PiStarSensorEntityDescription

    def __init__(self, coordinator, entry_id, title, description) -> None:
        """Initialize a Pi-Star sensor."""
        super().__init__(coordinator, entry_id, title)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.coordinator.data.get(self.entity_description.key)

    @property
    def available(self) -> bool:
        """Return whether the coordinator has usable data."""
        if not super().available:
            return False
        if self.entity_description.requires_value:
            return self.native_value is not None
        return True
