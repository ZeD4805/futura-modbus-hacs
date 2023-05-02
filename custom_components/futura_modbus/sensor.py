from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.components.sensor import SensorEntity
import logging
from typing import Optional


from .const import (
    ATTR_MANUFACTURER,
    DOMAIN,
    SENSOR_TYPES,
    FuturaModbusSensorEntityDescription,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    hub_name = entry.data[CONF_NAME]
    hub = hass.data[DOMAIN][hub_name]["hub"]

    device_info = {
        "identifiers": {(DOMAIN, hub_name)},
        "name": hub_name,
        "manufacturer": ATTR_MANUFACTURER,
        "model": "Futura",
    }

    entities = []
    for sensor_description in SENSOR_TYPES.values():
        sensor = FuturaModbusSensor(hub_name, hub, device_info, sensor_description)
        entities.append(sensor)

    async_add_entities(entities)
    return True


class FuturaModbusSensor(SensorEntity):
    """Class for a Futura Modbus Sensor"""

    def __init__(
        self,
        platform_name,
        hub,
        device_info,
        description: FuturaModbusSensorEntityDescription,
    ):
        """Initialize the sensor."""
        self._platform_name = platform_name
        self._attr_device_info = device_info
        self._hub = hub
        self.entity_description = description

    async def async_added_to_hass(self) -> None:
        """Register the update callback."""
        self._hub.async_add_futura_modbus_sensor(self._modbus_data_updated)

    async def async_will_remove_from_hass(self) -> None:
        """Remove the sensor callback"""
        self._hub.async_remove_futura_modbus_sensor(self._modbus_data_updated)

    @callback
    def _modbus_data_updated(self):
        self.async_write_ha_state()

    @callback
    def _update_state(self):
        if self.entity_description.key in self._hub.data:
            self._state = self._hub.data[self.entity_description.key]

    @property
    def name(self):
        """Return the name."""
        return f"{self._platform_name} {self.entity_description.name}"

    @property
    def unique_id(self) -> Optional[str]:
        return f"{self._platform_name}_{self.entity_description.key}"

    @property
    def native_value(self):
        """Return sensor state."""
        return (
            self._hub.data[self.entity_description.key]
            if self.entity_description.key in self._hub.data
            else None
        )
