import logging
from homeassistant.components.number import NumberEntity
from homeassistant.core import callback
from homeassistant.const import CONF_NAME
from typing import Optional

from .const import (
    DOMAIN,
    ATTR_MANUFACTURER,
    NUMBER_TYPES,
    FuturaModbusNumberEntityDescription,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Setting up the number entities."""
    hub_name = entry.data[CONF_NAME]
    hub = hass.data[DOMAIN][hub_name]["hub"]

    device_info = {
        "identifiers": {(DOMAIN, hub_name)},
        "name": hub_name,
        "manufacturer": ATTR_MANUFACTURER,
        "model": "Futura",
    }

    entities = []
    for number_description in NUMBER_TYPES.values():
        sensor = FuturaModbusNumber(hub_name, hub, device_info, number_description)
        entities.append(sensor)

    async_add_entities(entities)
    return True


class FuturaModbusNumber(NumberEntity):
    """Class for Futura Modbus Number"""

    def __init__(
        self,
        platform_name,
        hub,
        device_info,
        description: FuturaModbusNumberEntityDescription,
    ):
        """Initialize the number entity."""
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
    def native_value(self):
        """Return sensor state."""
        return (
            self._hub.data[self.entity_description.key]
            if self.entity_description.key in self._hub.data
            else None
        )

    @property
    def name(self):
        """Return the name."""
        return f"{self._platform_name} {self.entity_description.name}"

    @property
    def unique_id(self) -> Optional[str]:
        return f"{self._platform_name}_{self.entity_description.key}"

    @property
    def native_step(self) -> Optional[float]:
        if hasattr(self.entity_description, "native_step"):
            return self.entity_description.native_step

    @property
    def native_min_value(self) -> float:
        if hasattr(self.entity_description, "native_min_value"):
            return self.entity_description.native_min_value

    @property
    def native_max_value(self) -> float:
        if hasattr(self.entity_description, "native_max_value"):
            return self.entity_description.native_max_value

    @property
    def icon(self) -> Optional[str]:
        if hasattr(self.entity_description, "icon"):
            return self.entity_description.icon

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""

        if hasattr(self.entity_description, "address"):
            self._attr_native_value = value

            val = round(self._attr_native_value * 60, 1)
            val = int(val)
            self.hass.async_add_executor_job(
                self._hub.write_register,
                self.entity_description.address,
                val,
            )
