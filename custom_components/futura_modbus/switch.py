import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.const import CONF_NAME
from typing import Any, Optional

from .const import (
    DOMAIN,
    ATTR_MANUFACTURER,
    SWITCH_TYPES,
    FuturaModbusSwitchEntityDescription,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Setting up the switch entities."""
    hub_name = entry.data[CONF_NAME]
    hub = hass.data[DOMAIN][hub_name]["hub"]

    device_info = {
        "identifiers": {(DOMAIN, hub_name)},
        "name": hub_name,
        "manufacturer": ATTR_MANUFACTURER,
        "model": "Futura",
    }

    entities = []
    for switch_description in SWITCH_TYPES.values():
        sensor = FuturaModbusSwitch(hub_name, hub, device_info, switch_description)
        entities.append(sensor)

    async_add_entities(entities)
    return True


class FuturaModbusSwitch(SwitchEntity):
    """Class for Futura Modbus switch"""

    def __init__(
        self,
        platform_name,
        hub,
        device_info,
        description: FuturaModbusSwitchEntityDescription,
    ) -> None:
        """Initialize the switch entity."""
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
            self._state = self._hub.data[self.entity_description.key] != 0

    @property
    def is_on(self):
        """Return sensor state."""
        return (
            self._hub.data[self.entity_description.key] != 0
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
    def icon(self) -> Optional[str]:
        if hasattr(self.entity_description, "icon"):
            return self.entity_description.icon

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch entity."""

        if hasattr(self.entity_description, "address"):
            self.hass.async_add_executor_job(
                self._hub.write_register,
                self.entity_description.address,
                1,
            )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch entity."""

        if hasattr(self.entity_description, "address"):
            self.hass.async_add_executor_job(
                self._hub.write_register,
                self.entity_description.address,
                0,
            )
