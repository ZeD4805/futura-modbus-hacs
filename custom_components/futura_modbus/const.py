from dataclasses import dataclass

from enum import Enum, auto
from typing import Optional

from homeassistant.components.sensor import SensorEntityDescription, SensorDeviceClass
from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.switch import SwitchEntityDescription, SwitchDeviceClass
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfPower,
    UnitOfTime,
    PERCENTAGE,
)

DOMAIN = "futura_modbus"
DEFAULT_NAME = "FuturaModbus"
DEFAULT_PORT = 502
DEFAULT_SCAN_INTERVAL = 2

DEVICE_ID = 39


class UIFields(Enum):
    """Fields for wall mounted UI displays."""

    INDEX = auto()
    ADDRESS = auto()  # modbus address
    OPTIONS = auto()
    CO2 = auto()
    TEMP = auto()
    HUMI = auto()


class SensorFields(Enum):
    """Fields for internal sensors."""

    INDEX = auto()
    ADDRESS = auto()  # modbus address
    OPTIONS = auto()
    CO2 = auto()
    TEMP = auto()
    HUMI = auto()


class AlfaFields(Enum):
    """Fields for Alfa."""

    INDEX = auto()
    ADDRESS = auto()  # modbus address
    OPTIONS = auto()
    CO2 = auto()
    TEMP = auto()
    HUMI = auto()
    NTC_TEMP = auto()


class ExtSensorFields(Enum):
    """Fields for external sensors."""

    INDEX = auto()
    PRESENT = auto()
    ERROR = auto()
    TEMPERATURE = auto()
    HUMIDITY = auto()
    CO2 = auto()
    FLOOR_TEMP = auto()


class ExtButtonFields(Enum):
    """Button Fields for external buttons"""

    INDEX = auto()
    PRESENT = auto()
    BUTTON_MODE = auto()
    BUTTON_TIMER = auto()
    BUTTON_ACTIVE = auto()


@dataclass
class FuturaModbusSensorEntityDescription(SensorEntityDescription):
    """Class that describes Futura sensor entities"""


SENSOR_TYPES: dict[str, list[FuturaModbusSensorEntityDescription]] = {
    "temp_ambient": FuturaModbusSensorEntityDescription(
        name="Ambient temperature",
        key="fut_temp_ambient",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,  # DEVICE_CLASS_TEMPERATURE,
    ),
    "temp_fresh": FuturaModbusSensorEntityDescription(
        name="Fresh temperature",
        key="fut_temp_fresh",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    "temp_indoor": FuturaModbusSensorEntityDescription(
        name="Indoor temperature",
        key="fut_temp_indoor",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    "temp_waste": FuturaModbusSensorEntityDescription(
        name="Waste temperature",
        key="fut_temp_waste",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    "humi_ambient": FuturaModbusSensorEntityDescription(
        name="Ambient humidity",
        key="fut_humi_ambient",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
    ),
    "humi_fresh": FuturaModbusSensorEntityDescription(
        name="Fresh humidity",
        key="fut_humi_fresh",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
    ),
    "humi_indoor": FuturaModbusSensorEntityDescription(
        name="Indoor humidity",
        key="fut_humi_indoor",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
    ),
    "humi_waste": FuturaModbusSensorEntityDescription(
        name="Waste humidity",
        key="fut_humi_waste",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
    ),
    "device_consumption": FuturaModbusSensorEntityDescription(
        name="Device consumption",
        key="fut_power_consumption",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
    ),
    "heat_recovery": FuturaModbusSensorEntityDescription(
        name="Heat recovery",
        key="fut_heat_recovering",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
    ),
    "heating_consumption": FuturaModbusSensorEntityDescription(
        name="heating consumption",
        key="fut_heating_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
    ),
}


@dataclass
class FuturaModbusNumberEntityDescription(NumberEntityDescription):
    """Class that describes Futura number entities"""

    address: Optional[int] = None


NUMBER_TYPES: dict[str, list[FuturaModbusNumberEntityDescription]] = {
    "boost_tm": FuturaModbusNumberEntityDescription(
        name="Fan boost timer",
        key="func_boost_tm",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=None,
        native_step=1,
        native_min_value=0,
        native_max_value=10,
        icon="mdi:fan",
        address=1,
    ),
}


@dataclass
class FuturaModbusSwitchEntityDescription(SwitchEntityDescription):
    """Class that describes Futura switch entities"""

    address: Optional[int] = None


SWITCH_TYPES: dict[str, list[FuturaModbusSwitchEntityDescription]] = {
    "bypass": FuturaModbusSwitchEntityDescription(
        name="Enable automatic bypass",
        key="cfg_bypass_enable",
        device_class=SwitchDeviceClass.SWITCH,
        icon="mdi:transit-skip",
        address=14,
    ),
    "heating": FuturaModbusSwitchEntityDescription(
        name="Enable heating",
        key="cfg_heating_enable",
        device_class=SwitchDeviceClass.SWITCH,
        icon="mdi:heat-wave",
        address=15,
    ),
    "cooling": FuturaModbusSwitchEntityDescription(
        name="Enable cooling",
        key="cfg_cooling_enable",
        device_class=SwitchDeviceClass.SWITCH,
        icon="mdi:snowflake",
        address=16,
    ),
}

FUTURA_L = "Futura L"
FUTURA_M = "Futura M"
UNKNOWN_MODEL = "Unknown device model"

DEVICE_MODEL = {0: FUTURA_L, 1: FUTURA_L, 2: FUTURA_M}
ATTR_MANUFACTURER = "JablotronLT"
