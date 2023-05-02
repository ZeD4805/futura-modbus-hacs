"""Jablotron Futura Modbus integration."""
import asyncio
from datetime import timedelta
import logging
import threading
from typing import Optional, Any

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_track_time_interval
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    Platform,
)
from homeassistant.core import HomeAssistant, callback

from pyModbusTCP.client import ModbusClient

from .const import (
    DEFAULT_NAME,
    DEFAULT_PORT,
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    UNKNOWN_MODEL,
    AlfaFields,
    ExtButtonFields,
    ExtSensorFields,
    UIFields,
    SensorFields,
    DEVICE_MODEL,
)

_LOGGER = logging.getLogger(__name__)

FUTURA_MODBUS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.string,
        vol.Optional(
            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
        ): cv.positive_int,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({cv.slug: FUTURA_MODBUS_SCHEMA})}, extra=vol.ALLOW_EXTRA
)

PLATFORMS = [Platform.SENSOR, Platform.NUMBER, Platform.SWITCH]


async def async_setup(hass, config):
    """Setup the Jablotron Futura modbus component."""
    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Setup modbus."""
    host = entry.data[CONF_HOST]
    name = entry.data[CONF_NAME]
    port = entry.data[CONF_PORT]
    scan_interval = entry.data[CONF_SCAN_INTERVAL]

    _LOGGER.debug("Setup %s.%s", DOMAIN, name)

    hub = FuturaModbusHub(hass, name, host, port, scan_interval)
    hass.data[DOMAIN][name] = {"hub": hub}

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )
    return True


async def async_unload_entry(hass, entry):
    """Unload Futura modbus entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entry.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if not unload_ok:
        return False

    hass.data[DOMAIN].pop(entry.data["name"])
    return True


class FuturaModbusHub:
    """Wrapper class for pymodbus for Futura."""

    def __init__(self, hass, name, host, port, scan_interval):
        """Initialize the modbus hub."""
        self._hass = hass
        self._client = ModbusClient(host=host, port=port, timeout=5)
        self._lock = threading.Lock()
        self._name = name
        self._scan_interval = timedelta(seconds=scan_interval)
        self._unsub_interval_method = None
        self._sensors = []
        self.data = {}

    @callback
    def async_add_futura_modbus_sensor(self, update_callback):
        """Listen for data updates."""
        # This is the first sensor, set up interval.
        if not self._sensors:
            self._unsub_interval_method = async_track_time_interval(
                self._hass, self.async_refresh_modbus_data, self._scan_interval
            )

        self._sensors.append(update_callback)

    @callback
    def async_remove_futura_modbus_sensor(self, update_callback):
        """Remove data update."""
        if update_callback in self._sensors:
            self._sensors.remove(update_callback)

        if not self._sensors:
            if self._unsub_interval_method is not None:
                self._unsub_interval_method()
                self._unsub_interval_method = None
            self.close()

    async def async_refresh_modbus_data(self, _now: Optional[int] = None) -> bool:
        """Time to update."""
        if not self._sensors:
            return

        update_result = await self._hass.async_add_executor_job(self.read_modbus_data)

        if update_result:
            for update_callback in self._sensors:
                update_callback()

        return True

    @property
    def name(self):
        """Return the name of the hub."""
        return self._name

    def close(self):
        """Disconnect client."""
        with self._lock:
            self._client.close()

    def read_holding_registers(self, address, count):
        """Read holding registers."""
        with self._lock:
            return self._client.read_holding_registers(address, count)

    def read_input_registers(self, address, count):
        """Read input registers."""
        with self._lock:
            return self._client.read_input_registers(address, count)

    def read_modbus_data(self):
        """Read data from modbus."""
        return self.read_modbus_info()

    def write_register(self, address: int, value: int):
        """Write modbus register."""
        with self._lock:
            ret = self._client.write_single_register(
                address,
                value,
            )

            return ret

    def read_modbus_info(self):
        """Read the modbus registers."""
        temp_humi_data = self.read_input_registers(address=30, count=8)
        if temp_humi_data is None:
            return False

        self.data["fut_temp_ambient"] = temp_humi_data[0] * 0.1
        self.data["fut_temp_fresh"] = temp_humi_data[1] * 0.1
        self.data["fut_temp_indoor"] = temp_humi_data[2] * 0.1
        self.data["fut_temp_waste"] = temp_humi_data[3] * 0.1

        self.data["fut_humi_ambient"] = temp_humi_data[4] * 0.1
        self.data["fut_humi_fresh"] = temp_humi_data[5] * 0.1
        self.data["fut_humi_indoor"] = temp_humi_data[6] * 0.1
        self.data["fut_humi_waste"] = temp_humi_data[7] * 0.1

        power_data = self.read_input_registers(address=41, count=3)
        if power_data is None:
            return False

        self.data["fut_power_consumption"] = power_data[0]
        self.data["fut_heat_recovering"] = power_data[1]
        self.data["fut_heating_power"] = power_data[2]

        holding_regs = self.read_holding_registers(address=1, count=16)
        if holding_regs is None:
            return False

        self.data["func_boost_tm"] = round(holding_regs[0] / 60, 0)
        self.data["cfg_bypass_enable"] = round(holding_regs[13], 0)
        self.data["cfg_heating_enable"] = round(holding_regs[14], 0)
        self.data["cfg_cooling_enable"] = round(holding_regs[15], 0)

        return True

    """def read_modbus_holding_registers(self):
        global_reg_count = 24
        global_data = self.read_holding_registers(
            unit=1, address=0x0, count=global_reg_count
        )

        if global_data.isError():
            return False

        decoder = BinaryPayloadDecoder.fromRegisters(
            global_data.register, byteorder=Endian.Big
        )

        # 0
        func_ventilation = decoder.decode_16bit_uint()
        self.data["func_ventilation"] = func_ventilation

        # 1
        func_boost_tm = decoder.decode_16bit_uint()
        self.data["func_boost_tm"] = func_boost_tm

        # 2
        func_circulation_tm = decoder.decode_16bit_uint()
        self.data["func_circulation_tm"] = func_circulation_tm

        # 3
        func_overpressure_tm = decoder.decode_16bit_uint()
        self.data["func_overpressure_tm"] = func_overpressure_tm

        # 4
        func_night_tm = decoder.decode_16bit_uint()
        self.data["func_night_tm"] = func_night_tm

        # 5
        func_party_tm = decoder.decode_16bit_uint()
        self.data["func_party_tm"] = func_party_tm

        # 6-7
        func_away_begin = decoder.decode_32bit_uint()
        self.data["func_away_begin"] = func_away_begin

        # 8-9
        func_away_end = decoder.decode_32bit_uint()
        self.data["func_away_end"] = func_away_end

        # 10
        cfg_temp_set = decoder.decode_16bit_uint()
        self.data["cfg_temp_set"] = round(cfg_temp_set * 0.1, 1)

        # 11
        cfg_humi_set = decoder.decode_16bit_uint()
        self.data["cfg_humi_set"] = round(cfg_humi_set * 0.1, 1)

        # 12
        func_time_prog = decoder.decode_16bit_uint()
        self.data["func_time_prog"] = 1 if func_time_prog != 0 else 0

        # 13
        func_antiradon = decoder.decode_16bit_uint()
        self.data["func_antiradon"] = 1 if func_antiradon != 0 else 0

        # 14
        cfg_bypass_enable = decoder.decode_16bit_uint()
        self.data["cfg_bypass_enable"] = 1 if cfg_bypass_enable != 0 else 0

        # 15
        cfg_heating_enable = decoder.decode_16bit_uint()
        self.data["cfg_heating_enable"] = 1 if cfg_heating_enable != 0 else 0

        # 16
        cfg_cooling_enable = decoder.decode_16bit_uint()
        self.data["cfg_cooling_enable"] = 1 if cfg_cooling_enable != 0 else 0

        # 17
        cfg_comfort_enable = decoder.decode_16bit_uint()
        self.data["cfg_comfort_enable"] = 1 if cfg_comfort_enable != 0 else 0

        decoder.skip_bytes(2 * 2)  # 18->20

        # 20
        vzv_cb_priority_control = decoder.decode_16bit_uint()
        self.data["vzv_cb_priority_control"] = 1 if vzv_cb_priority_control != 0 else 0

        # 21
        vzv_kitchenhood_normally_open = decoder.decode_16bit_uint()
        self.data["vzv_kitchenhood_normally_open"] = (
            1 if vzv_kitchenhood_normally_open != 0 else 0
        )

        # 22
        vzv_boost_volume_per_run = decoder.decode_16bit_uint()
        self.data["vzv_boost_volume_per_run"] = (
            1 if vzv_boost_volume_per_run != 0 else 0
        )

        # 23
        vzv_kitchenhood_boost_volume_per_run = decoder.decode_16bit_uint()
        self.data["vzv_kitchenhood_boost_volume_per_run"] = (
            1 if vzv_kitchenhood_boost_volume_per_run != 0 else 0
        )

        # TODO figure this out

        # wall mounted thermostats (3)
        # 100, 105, 110
        ui_temp_corr = decoder.decode_16bit_uint()
        self.data["ui_temp_corr"] = ui_temp_corr

        # wall mounted sensors (8)
        # 115, 120, 125, 130, 135, 140, 145, 150
        se_temp_corr = decoder.decode_16bit_uint()
        self.data["se_temp_corr"] = se_temp_corr

        # alfa temperature correction
        # 160, 165, 170, 175, 180, 185, 190, 195
        alfa_temp_corr = decoder.decode_16bit_uint()
        self.data["alfa_temp_corr"] = alfa_temp_corr

        # alfa ntc temperature sensor correction
        # 162, 167, 172, 177, 182, 187, 192, 197
        alfa_ntc_temp_corr = decoder.decode_16bit_uint()
        self.data["alfa_ntc_temp_corr"] = alfa_ntc_temp_corr

        # EXT SENSORS
        ext_sensor_reg_count = 8 * 10
        ext_sensor_data = self.read_holding_registers(
            unit=1, address=0x12C, count=ext_sensor_reg_count
        )

        if ext_sensor_data.isError():
            return False

        decoder = BinaryPayloadDecoder.fromRegisters(
            ext_sensor_data.register, byteorder=Endian.Big
        )

        # 300 - 375
        sensors: list[dict[int, Any]] = []
        for i in range(8):
            sensor_data = {
                ExtSensorFields.INDEX: i,
                ExtSensorFields.PRESENT: False,
                ExtSensorFields.ERROR: 0,
                ExtSensorFields.TEMPERATURE: 0,
                ExtSensorFields.HUMIDITY: 0,
                ExtSensorFields.CO2: 0,
                ExtSensorFields.FLOOR_TEMP: 0,
            }

            # XX0
            sensor_present = decoder.decode_16bit_uint()
            sensor_data[ExtSensorFields.PRESENT] = sensor_present != 0

            # XX1
            sensor_error = decoder.decode_16bit_uint()
            sensor_data[ExtSensorFields.ERROR] = sensor_error

            # XX2
            sensor_temperature = decoder.decode_16bit_int()
            sensor_data[ExtSensorFields.TEMPERATURE] = round(
                sensor_temperature * 0.1, 1
            )

            # XX3
            sensor_humidity = decoder.decode_16bit_uint()
            sensor_data[ExtSensorFields.HUMIDITY] = sensor_humidity

            # XX4
            sensor_co2 = decoder.decode_16bit_uint()
            sensor_data[ExtSensorFields.CO2] = sensor_co2

            # XX5
            sensor_floor_temp = decoder.decode_16bit_int()
            sensor_data[ExtSensorFields.FLOOR_TEMP] = round(sensor_floor_temp * 0.1, 1)

            decoder.skip_bytes(5 * 2)  # is this correct?

            sensors.append(sensor_data)
        self.data["sensors"] = sensors

        # EXT BUTTONS
        ext_sensor_reg_count = 8 * 10
        ext_sensor_data = self.read_holding_registers(
            unit=1, address=0x190, count=ext_sensor_reg_count
        )

        if ext_sensor_data.isError():
            return False

        decoder = BinaryPayloadDecoder.fromRegisters(
            ext_sensor_data.register, byteorder=Endian.Big
        )

        # 400 - 473
        buttons: list[dict[int, Any]] = []
        for i in range(8):
            button_data = {
                ExtButtonFields.INDEX: i,
                ExtButtonFields.PRESENT: False,
                ExtButtonFields.BUTTON_MODE: 0,
                ExtButtonFields.BUTTON_TIMER: 0,
                ExtButtonFields.BUTTON_ACTIVE: 0,
            }

            # XX0
            button_present = decoder.decode_16bit_uint()
            button_data[ExtButtonFields.PRESENT] = button_present != 0

            # XX1
            button_mode = decoder.decode_16bit_uint()
            button_data[ExtButtonFields.BUTTON_MODE] = button_mode

            # XX2
            button_tm = decoder.decode_16bit_uint()
            button_data[ExtButtonFields.BUTTON_TIMER] = button_tm

            # XX3
            button_active = decoder.decode_16bit_uint()
            button_data[ExtButtonFields.BUTTON_ACTIVE] = button_active

            decoder.skip_bytes(7 * 2)  # 7 addresses for 16bits
            buttons.append(button_data)
        self.data["buttons"] = buttons

        # TODO figure this out also
        # 900
        access_code = decoder.decode_16bit_uint()
        self.data["access_code"] = access_code

        # 920
        user_password = decoder.decode_16bit_uint()
        self.data["user_password"] = user_password

        # 922
        password_timeout = decoder.decode_16bit_uint()
        self.data["password_timeout"] = password_timeout

        return True

    def read_modbus_input_registers(self):
        global_reg_count = 24
        global_data = self.read_holding_registers(
            unit=1, address=0x0, count=global_reg_count
        )

        if global_data.isError():
            return False

        decoder = BinaryPayloadDecoder.fromRegisters(
            global_data.register, byteorder=Endian.Big
        )

        # 0
        fact_device_id = decoder.decode_16bit_uint()
        self.data["fact_device_id"] = fact_device_id

        # 1-2
        fact_serial_number = decoder.decode_32bit_uint()
        self.data["fact_serial_number"] = fact_serial_number

        # 3-5
        fact_ethernet_mac_1 = decoder.decode_16bit_uint()
        fact_ethernet_mac_2 = decoder.decode_16bit_uint()
        fact_ethernet_mac_3 = decoder.decode_16bit_uint()
        self.data["fact_ethernet_mac"] = [
            fact_ethernet_mac_1,
            fact_ethernet_mac_2,
            fact_ethernet_mac_3,
        ]

        # 14
        sys_options = decoder.decode_16bit_uint()
        if sys_options in DEVICE_MODEL:
            self.data["sys_options"] = DEVICE_MODEL[sys_options]
        else:
            self.data["sys_options"] = UNKNOWN_MODEL

        # 15
        fut_config = decoder.decode_16bit_uint()
        self.data["fut_config"] = fut_config

        # 16-17
        fut_mode = decoder.decode_32bit_uint()
        self.data["fut_mode"] = fut_mode

        # 18-19
        fut_error = decoder.decode_32bit_uint()
        self.data["fut_error"] = fut_error

        # 20-21
        fut_warning = decoder.decode_32bit_uint()
        self.data["fut_warning"] = fut_warning

        decoder.skip_bytes(9 * 2)

        # 30
        fut_temp_ambient = decoder.decode_16bit_uint()
        self.data["fut_temp_ambient"] = round(fut_temp_ambient * 0.1, 1)

        # 31
        fut_temp_fresh = decoder.decode_16bit_uint()
        self.data["fut_temp_fresh"] = round(fut_temp_fresh * 0.1, 1)

        # 32
        fut_temp_indoor = decoder.decode_16bit_uint()
        self.data["fut_temp_indoor"] = round(fut_temp_indoor * 0.1, 1)

        # 33
        fut_temp_waste = decoder.decode_16bit_uint()
        self.data["fut_temp_waste"] = round(fut_temp_waste * 0.1, 1)

        # 34
        fut_humi_ambient = decoder.decode_16bit_uint()
        self.data["fut_humi_ambient"] = round(fut_humi_ambient * 0.1, 1)

        # 35
        fut_humi_fresh = decoder.decode_16bit_uint()
        self.data["fut_humi_fresh"] = round(fut_humi_fresh * 0.1, 1)

        # 36
        fut_humi_indoor = decoder.decode_16bit_uint()
        self.data["fut_humi_indoor"] = round(fut_humi_indoor * 0.1, 1)

        # 37
        fut_humi_waste = decoder.decode_16bit_uint()
        self.data["fut_humi_waste"] = round(fut_humi_waste * 0.1, 1)

        # 38
        fut_t_out = decoder.decode_16bit_uint()
        self.data["fut_t_out"] = round(fut_t_out * 0.1, 1)

        decoder.skip_bytes(2)

        # 40
        fut_filter_wear_level = decoder.decode_16bit_uint()
        self.data["fut_filter_wear_level"] = fut_filter_wear_level

        # 41
        fut_power_consumption = decoder.decode_16bit_uint()
        self.data["fut_power_consumption"] = fut_power_consumption

        # 42
        fut_heat_recovery = decoder.decode_16bit_uint()
        self.data["fut_heat_recovery"] = fut_heat_recovery

        # 43
        fut_heating_power = decoder.decode_16bit_uint()
        self.data["fut_heating_power"] = fut_heating_power

        # 44
        fut_air_flow = decoder.decode_16bit_uint()
        self.data["fut_air_flow"] = fut_air_flow

        # 45
        fut_fan_pwm_supply = decoder.decode_16bit_uint()
        self.data["fut_fan_pwm_supply"] = fut_fan_pwm_supply

        # 46
        fut_fan_pwm_exhaust = decoder.decode_16bit_uint()
        self.data["fut_fan_pwm_exhaust"] = fut_fan_pwm_exhaust

        # 47
        fut_fan_pwm_supply = decoder.decode_16bit_uint()
        self.data["fut_fan_rpm_supply"] = fut_fan_pwm_supply

        # 48
        fut_fan_pwm_exhaust = decoder.decode_16bit_uint()
        self.data["fut_fan_rpm_exhaust"] = fut_fan_pwm_exhaust

        # 49
        fut_uint1_voltage = decoder.decode_16bit_uint()
        self.data["fut_uint1_voltage"] = fut_uint1_voltage

        # 50
        fut_uint2_voltage = decoder.decode_16bit_uint()
        self.data["fut_uint2_voltage"] = fut_uint2_voltage

        # 51
        fut_dig_inputs = decoder.decode_16bit_uint()
        self.data["fut_dig_inputs"] = fut_dig_inputs

        # 52
        sys_battery_voltage = decoder.decode_16bit_uint()
        self.data["sys_battery_voltage"] = round(sys_battery_voltage * 0.001, 3)

        decoder.skip_bytes(8 * 2)

        # 60-61
        mbdev_stat_reads = decoder.decode_32bit_uint()
        self.data["mbdev_stat_reads"] = mbdev_stat_reads

        # 62-63
        mbdev_stat_writes = decoder.decode_32bit_uint()
        self.data["mbdev_stat_writes"] = mbdev_stat_writes

        # 64-65
        mbdev_stat_fails = decoder.decode_32bit_uint()
        self.data["mbdev_stat_fails"] = mbdev_stat_fails

        # 66
        mbdev_connected_mk_ui = decoder.decode_16bit_uint()
        self.data["mbdev_connected_mk_ui"] = mbdev_connected_mk_ui

        # 67-68
        mbdev_connected_mk_sens = decoder.decode_32bit_uint()
        self.data["mbdev_connected_mk_sens"] = mbdev_connected_mk_sens

        # 69
        mbdev_connected_coolbreeze = decoder.decode_16bit_uint()
        self.data["mbdev_connected_coolbreeze"] = mbdev_connected_coolbreeze != 0

        # 70-71
        mbdev_connected_valve_supply = decoder.decode_32bit_uint()
        self.data["mbdev_connected_valve_supply"] = mbdev_connected_valve_supply

        # 72-73
        mbdev_connected_valve_exhaust = decoder.decode_32bit_uint()
        self.data["mbdev_connected_valve_exhaust"] = mbdev_connected_valve_exhaust

        # 74
        mbdev_connected_button = decoder.decode_16bit_uint()
        self.data["mbdev_connected_button"] = mbdev_connected_button

        # 75
        mbdev_connected_alfa = decoder.decode_16bit_uint()
        self.data["mbdev_connected_alfa"] = mbdev_connected_alfa

        decoder.skip_bytes(5 * 2)

        # 80
        vzv_identity = decoder.decode_16bit_uint()
        self.data["vzv_identity"] = vzv_identity

        decoder.skip_bytes(20 * 2)

        # 100/.../104 -> ... 114
        # wall mounted ui
        uis: list[dict[int, Any]] = []
        for i in range(3):
            ui_data = {
                UIFields.INDEX: i,
                UIFields.ADDRESS: 0,
                UIFields.OPTIONS: 0,
                UIFields.CO2: 0,
                UIFields.TEMP: 0,
                UIFields.HUMI: 0,
            }

            ui_mb_address = decoder.decode_16bit_uint()
            ui_data[UIFields.ADDRESS] = ui_mb_address

            ui_options = decoder.decode_16bit_uint()
            ui_data[UIFields.OPTIONS] = ui_options

            ui_co2 = decoder.decode_16bit_uint()
            ui_data[UIFields.CO2] = ui_co2

            ui_temp = decoder.decode_16bit_uint()
            ui_data[UIFields.TEMP] = round(ui_temp * 0.1, 1)

            ui_humi = decoder.decode_16bit_uint()
            ui_data[UIFields.HUMI] = round(ui_humi * 0.1, 1)

            uis.append(ui_data)
        self.data["ui"] = uis

        # 115/.../119 ... 154
        sens: list[dict[int, Any]] = []
        for i in range(8):
            sens_data = {
                SensorFields.INDEX: i,
                SensorFields.ADDRESS: 0,
                SensorFields.OPTIONS: 0,
                SensorFields.CO2: 0,
                SensorFields.TEMP: 0,
                SensorFields.HUMI: 0,
            }
            sens_mb_address = decoder.decode_16bit_uint()
            sens_data[SensorFields.ADDRESS] = sens_mb_address

            sens_options = decoder.decode_16bit_uint()
            sens_data[SensorFields.OPTIONS] = sens_options

            sens_co2 = decoder.decode_16bit_uint()
            sens_data[SensorFields.CO2] = sens_co2

            sens_temp = decoder.decode_16bit_uint()
            sens_data[SensorFields.TEMP] = round(sens_temp * 0.1, 1)

            sens_humi = decoder.decode_16bit_uint()
            sens_data[SensorFields.HUMI] = round(sens_humi * 0.1, 1)

            sens.append(sens_data)
        self.data["sensor"] = sens

        decoder.skip_bytes(6 * 2)

        # 160/.../165 ... 235
        alfas: list[dict[int, Any]] = []
        for i in range(8):
            alfa_data = {
                AlfaFields.INDEX: i,
                AlfaFields.ADDRESS: 0,
                AlfaFields.OPTIONS: 0,
                AlfaFields.CO2: 0,
                AlfaFields.TEMP: 0,
                AlfaFields.HUMI: 0,
                AlfaFields.NTC_TEMP: 0,
            }

            alfa_mb_address = decoder.decode_16bit_uint()
            alfa_data[AlfaFields.INDEX] = alfa_mb_address

            alfa_options = decoder.decode_16bit_uint()
            alfa_data[AlfaFields.OPTIONS] = alfa_options

            alfa_co2 = decoder.decode_16bit_uint()
            alfa_data[AlfaFields.CO2] = alfa_co2

            alfa_temp = decoder.decode_16bit_uint()
            alfa_data[AlfaFields.TEMP] = round(alfa_temp * 0.1, 1)

            alfa_humi = decoder.decode_16bit_uint()
            alfa_data[AlfaFields.HUMI] = round(alfa_humi * 0.1, 1)

            alfa_ntc_temp = decoder.decode_16bit_uint()
            alfa_data[AlfaFields.NTC_TEMP] = round(alfa_ntc_temp * 0.1, 1)

            alfas.append(sens_data)

            decoder.skip_bytes(5 * 2)
        self.data["alfa"] = alfas"""
