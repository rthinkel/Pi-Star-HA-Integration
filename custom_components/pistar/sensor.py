"""Pi-Star sensors."""
import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SENSOR_DEFINITIONS = [
    # --- Hotspot health ---
    {"key": "status",        "name": "Pi-Star Status",       "icon": "mdi:radio-tower",    "unit": None},
    {"key": "dmr_network",   "name": "Pi-Star DMR Network",  "icon": "mdi:network",        "unit": None},
    {"key": "trx_status",    "name": "Pi-Star TRX Status",   "icon": "mdi:radio",          "unit": None},
    {"key": "firmware",      "name": "Pi-Star Firmware",     "icon": "mdi:chip",           "unit": None},

    # --- Radio info ---
    {"key": "tx_frequency",  "name": "Pi-Star TX Frequency", "icon": "mdi:sine-wave",      "unit": None},
    {"key": "rx_frequency",  "name": "Pi-Star RX Frequency", "icon": "mdi:sine-wave",      "unit": None},

    # --- DMR repeater info ---
    {"key": "dmr_id",        "name": "Pi-Star DMR ID",       "icon": "mdi:identifier",     "unit": None},
    {"key": "dmr_cc",        "name": "Pi-Star Color Code",   "icon": "mdi:palette",        "unit": None},
    {"key": "ts1_status",    "name": "Pi-Star TS1 Status",   "icon": "mdi:numeric-1-box",  "unit": None},
    {"key": "ts2_status",    "name": "Pi-Star TS2 Status",   "icon": "mdi:numeric-2-box",  "unit": None},
    {"key": "dmr_master",    "name": "Pi-Star DMR Master",   "icon": "mdi:server",         "unit": None},

    # --- Gateway last heard ---
    {"key": "last_time",      "name": "Pi-Star Last Heard Time",     "icon": "mdi:clock-outline",  "unit": None},
    {"key": "last_callsign",  "name": "Pi-Star Last Heard Callsign", "icon": "mdi:account-voice",  "unit": None},
    {"key": "last_tg",        "name": "Pi-Star Last Heard TG",       "icon": "mdi:pound",          "unit": None},
    {"key": "last_mode",      "name": "Pi-Star Last Heard Mode",     "icon": "mdi:radio",          "unit": None},
    {"key": "last_source",    "name": "Pi-Star Last Heard Source",   "icon": "mdi:antenna",        "unit": None},
    {"key": "last_duration",  "name": "Pi-Star Last Heard Duration", "icon": "mdi:timer-outline",  "unit": "s"},
    {"key": "last_loss",      "name": "Pi-Star Last Heard Loss",     "icon": "mdi:signal-off",     "unit": "%"},
    {"key": "last_ber",       "name": "Pi-Star Last Heard BER",      "icon": "mdi:percent",        "unit": "%"},
    {"key": "currently_tx",   "name": "Pi-Star Currently TX",        "icon": "mdi:broadcast",      "unit": None},

    # --- Local RF last heard ---
    {"key": "local_last_callsign", "name": "Pi-Star Local Last Callsign", "icon": "mdi:account-voice", "unit": None},
    {"key": "local_last_tg",       "name": "Pi-Star Local Last TG",       "icon": "mdi:pound",         "unit": None},
    {"key": "local_last_mode",     "name": "Pi-Star Local Last Mode",     "icon": "mdi:radio",         "unit": None},
    {"key": "local_last_duration", "name": "Pi-Star Local Last Duration", "icon": "mdi:timer-outline", "unit": "s"},
    {"key": "local_last_ber",      "name": "Pi-Star Local Last BER",      "icon": "mdi:percent",       "unit": "%"},
    {"key": "local_last_rssi",     "name": "Pi-Star Local Last RSSI",     "icon": "mdi:signal",        "unit": None},
]


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Pi-Star sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        PiStarSensor(coordinator, entry, defn)
        for defn in SENSOR_DEFINITIONS
    ]
    async_add_entities(entities)


class PiStarSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Pi-Star sensor."""

    def __init__(self, coordinator, entry, definition):
        super().__init__(coordinator)
        self._key = definition["key"]
        self._attr_name = definition["name"]
        self._attr_icon = definition["icon"]
        self._attr_native_unit_of_measurement = definition["unit"]
        self._attr_unique_id = f"{entry.entry_id}_{self._key}"
        self._entry = entry

    @property
    def native_value(self):
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._key)

    @property
    def available(self):
        """Return True if the coordinator has data."""
        return self.coordinator.last_update_success

    @property
    def device_info(self):
        """Return device information for the Pi-Star hotspot."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": f"Pi-Star ({self._entry.data.get('host', 'pi-star.local')})",
            "manufacturer": "Andy Taylor (MW0MWZ)",
            "model": "Pi-Star Digital Voice",
        }
