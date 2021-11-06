# coding=utf-8
#
# controller_math.py - Math controller that performs math on other controllers
#                      to create new values
#
#  Copyright (C) 2015-2020 Roman Inozemtsev <dao@mir.one>
#
#  This file is part of Farm
#
#  Farm is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Farm is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Farm. If not, see <http://www.gnu.org/licenses/>.
#
#  Contact at mir.one
#
import threading
import time
from statistics import median
from statistics import stdev

import urllib3

import farm.utils.psypy as SI
from farm.controllers.base_controller import AbstractController
from farm.databases.models import Conversion
from farm.databases.models import DeviceMeasurements
from farm.databases.models import Math
from farm.databases.models import Misc
from farm.inputs.sensorutils import calculate_vapor_pressure_deficit
from farm.inputs.sensorutils import convert_units
from farm.farm_client import DaemonControl
from farm.utils.database import db_retrieve_table_daemon
from farm.utils.influx import add_measurements_influxdb
from farm.utils.influx import average_past_seconds
from farm.utils.influx import read_last_influxdb
from farm.utils.influx import sum_past_seconds
from farm.utils.system_pi import get_measurement
from farm.utils.system_pi import return_measurement_info


class Measurement:
    """
    Class for holding all measurement values in a dictionary.
    The dictionary is formatted in the following way:

    {'measurement type':measurement value}

    Measurement type: The environmental or physical condition
    being measured, such as 'temperature', or 'pressure'.

    Measurement value: The actual measurement of the condition.
    """

    def __init__(self, raw_data):
        self.rawData = raw_data

    @property
    def values(self):
        return self.rawData


class MathController(AbstractController, threading.Thread):
    """
    Class to operate discrete PID controller
    """
    def __init__(self, ready, unique_id):
        threading.Thread.__init__(self)
        super(MathController, self).__init__(ready, unique_id=unique_id, name=__name__)

        self.unique_id = unique_id
        self.sample_rate = None

        self.control = DaemonControl()

        self.measurements = None
        self.pause_loop = False
        self.verify_pause_loop = True
        self.device_measurements = None

        # General variables
        self.name = ''
        self.math_type = None
        self.is_activated = None
        self.period = None
        self.start_offset = None
        self.max_measure_age = None
        self.log_level_debug = None

        # Inputs to calculate with
        self.inputs = None

        # Difference variables
        self.difference_reverse_order = None
        self.difference_absolute = None

        # Equation variables
        self.equation_input = None
        self.equation = None

        # Redundancy variables
        self.order_of_use = None

        # Verification variables
        self.max_difference = None

        # Humidity variables
        self.dry_bulb_t_id = None
        self.dry_bulb_t_measure_id = None
        self.wet_bulb_t_id = None
        self.wet_bulb_t_measure_id = None
        self.pressure_pa_id = None
        self.pressure_pa_measure_id = None

        # Misc ids
        self.unique_id_1 = None
        self.unique_measurement_id_1 = None
        self.unique_id_2 = None
        self.unique_measurement_id_2 = None

        self.timer = None

    def loop(self):
        # Pause loop to modify conditional statements.
        # Prevents execution of conditional while variables are
        # being modified.
        if self.pause_loop:
            self.verify_pause_loop = True
            while self.pause_loop:
                time.sleep(0.1)

        if self.is_activated and time.time() > self.timer:
            # Ensure the next timer ends in the future
            while time.time() > self.timer:
                self.timer += self.period
            self.attempt_execute(self.calculate_math)

    def initialize_variables(self):
        self.sample_rate = db_retrieve_table_daemon(
            Misc, entry='first').sample_rate_controller_math

        math = db_retrieve_table_daemon(Math, unique_id=self.unique_id)

        self.device_measurements = db_retrieve_table_daemon(
            DeviceMeasurements).filter(
            DeviceMeasurements.device_id == self.unique_id)

        # General variables
        self.unique_id = math.unique_id
        self.name = math.name
        self.math_type = math.math_type
        self.is_activated = math.is_activated
        self.period = math.period
        self.start_offset = math.start_offset
        self.max_measure_age = math.max_measure_age
        self.log_level_debug = math.log_level_debug

        self.set_log_level_debug(self.log_level_debug)

        # Inputs to calculate with
        self.inputs = math.inputs

        # Difference variables
        self.difference_reverse_order = math.difference_reverse_order
        self.difference_absolute = math.difference_absolute

        # Equation variables
        self.equation_input = math.equation_input
        self.equation = math.equation

        # Redundancy variables
        self.order_of_use = math.order_of_use

        # Verification variables
        self.max_difference = math.max_difference

        # Humidity variables
        self.dry_bulb_t_id = math.dry_bulb_t_id
        self.dry_bulb_t_measure_id = math.dry_bulb_t_measure_id
        self.wet_bulb_t_id = math.wet_bulb_t_id
        self.wet_bulb_t_measure_id = math.wet_bulb_t_measure_id
        self.pressure_pa_id = math.pressure_pa_id
        self.pressure_pa_measure_id = math.pressure_pa_measure_id

        # Misc ids
        self.unique_id_1 = math.unique_id_1
        self.unique_measurement_id_1 = math.unique_measurement_id_1
        self.unique_id_2 = math.unique_id_2
        self.unique_measurement_id_2 = math.unique_measurement_id_2

        self.timer = time.time() + self.start_offset

        self.set_log_level_debug(self.log_level_debug)

    def calculate_math(self):
        measurement_dict = {}

        # Average (multiple channels)
        if self.math_type == 'average':
            measurement_dict = self.math_average(measurement_dict)
        # Average (single channel)
        elif self.math_type == 'average_single':
            measurement_dict = self.math_average_single(measurement_dict)
        # Sum (multiple channels)
        elif self.math_type == 'sum':
            measurement_dict = self.math_sum(measurement_dict)
        # Sum (single channel)
        elif self.math_type == 'sum_single':
            measurement_dict = self.math_sum_single(measurement_dict)
        # Difference between two channels
        elif self.math_type == 'difference':
            measurement_dict = self.math_difference(measurement_dict)
        # Equation (math performed on measurement)
        elif self.math_type == 'equation':
            measurement_dict = self.math_equation(measurement_dict)
        # Redundancy (Use next measurement if one isn't currently available)
        elif self.math_type == 'redundancy':
            measurement_dict = self.math_redundancy(measurement_dict)
        # Statistical analysis on all measurements from a period of time
        elif self.math_type == 'statistics':
            measurement_dict = self.math_statistics(measurement_dict)
        # Verification (only use measurement if it's close to another measurement)
        elif self.math_type == 'verification':
            measurement_dict = self.math_verification(measurement_dict)
        # Calculate humidity from wet- and dry-bulb temperatures
        elif self.math_type == 'humidity':
            measurement_dict = self.math_humidity(measurement_dict)
        # Calculate vapor pressure deficit from temperature and humidity
        elif self.math_type == 'vapor_pressure_deficit':
            measurement_dict = self.math_vapor_pressure_deficit(measurement_dict)
        else:
            self.logger.error("Unknown math type: {type}".format(type=self.math_type))

        # Add measurement(s) to influxdb
        if measurement_dict:
            self.logger.debug(
                "Adding measurements to InfluxDB with ID {}: {}".format(
                    self.unique_id, measurement_dict))
            add_measurements_influxdb(self.unique_id, measurement_dict)
        else:
            self.logger.debug(
                "No measurements to add to InfluxDB with ID {}".format(
                    self.unique_id))

    def math_average(self, measurement_dict):
        math_dev_measurement = self.device_measurements.filter(
            DeviceMeasurements.channel == 0).first()
        channel, unit, measurement = return_measurement_info(
            math_dev_measurement, None)

        success, measure = self.get_measurements_from_str(self.inputs)
        if success:
            average = float(sum(measure) / float(len(measure)))

            measurement_dict = {
                channel: {
                    'measurement': measurement,
                    'unit': unit,
                    'value': average
                }
            }
        elif measure:
            self.logger.error(measure)
        else:
            self.error_not_within_max_age()
        return measurement_dict

    def math_average_single(self, measurement_dict):
        (device_id,
         math_dev_measurement,
         math_unit,
         measure_channel,
         measure_unit,
         measure_measurement) = self.return_single_measure_info()

        try:
            return_value = average_past_seconds(
                device_id,
                measure_unit,
                measure_channel,
                self.max_measure_age,
                measure=measure_measurement)

            if math_dev_measurement.conversion_id:
                return_value = convert_units(
                    math_dev_measurement.conversion_id,
                    return_value)

            if return_value:
                measurement_dict = {
                    math_dev_measurement.channel: {
                        'measurement': measure_measurement,
                        'unit': math_unit,
                        'value': return_value
                    }
                }
            else:
                self.error_not_within_max_age()
        except Exception as msg:
            self.logger.exception(
                "average_single Error: {err}".format(err=msg))
        return measurement_dict

    def math_sum(self, measurement_dict):
        channel, unit, measurement = self.return_single_conversion_info()

        success, measure = self.get_measurements_from_str(self.inputs)
        if success:
            sum_value = float(sum(measure))

            measurement_dict = {
                channel: {
                    'measurement': measurement,
                    'unit': unit,
                    'value': sum_value
                }
            }
        elif measure:
            self.logger.error(measure)
        else:
            self.error_not_within_max_age()
        return measurement_dict

    def math_sum_single(self, measurement_dict):
        (device_id,
         math_dev_measurement,
         math_unit,
         measure_channel,
         measure_unit,
         measure_measurement) = self.return_single_measure_info()

        try:
            return_value = sum_past_seconds(
                device_id,
                measure_unit,
                measure_channel,
                self.max_measure_age,
                measure=measure_measurement)

            if math_dev_measurement.conversion_id:
                return_value = convert_units(
                    math_dev_measurement.conversion_id,
                    return_value)

            if return_value:
                measurement_dict = {
                    math_dev_measurement.channel: {
                        'measurement': measure_measurement,
                        'unit': math_unit,
                        'value': return_value
                    }
                }
            else:
                self.error_not_within_max_age()
        except Exception as msg:
            self.logger.exception(
                "sum_single Error: {err}".format(err=msg))
        return measurement_dict

    def math_difference(self, measurement_dict):
        channel, unit, measurement = self.return_single_conversion_info()

        success, measure = self.get_measurements_from_str(self.inputs)
        if success:
            if self.difference_reverse_order:
                difference = measure[1] - measure[0]
            else:
                difference = measure[0] - measure[1]
            if self.difference_absolute:
                difference = abs(difference)

            measurement_dict = {
                channel: {
                    'measurement': measurement,
                    'unit': unit,
                    'value': difference
                }
            }
        elif measure:
            self.logger.error(measure)
        else:
            self.error_not_within_max_age()
        return measurement_dict

    def math_equation(self, measurement_dict):
        channel, unit, measurement = self.return_single_conversion_info()

        success, measure = self.get_measurements_from_str(
            self.equation_input)
        if success:
            if 'x' in self.equation:
                replaced_str = self.equation.replace('x', str(measure[0]))
            else:
                replaced_str = self.equation
            equation_output = eval(replaced_str)

            measurement_dict = {
                channel: {
                    'measurement': measurement,
                    'unit': unit,
                    'value': float(equation_output)
                }
            }
        elif measure:
            self.logger.error(measure)
        else:
            self.error_not_within_max_age()
        return measurement_dict

    def math_redundancy(self, measurement_dict):
        list_order = self.order_of_use.split(';')
        measurement_success = False

        for each_id_measurement_id in list_order:
            device_id = each_id_measurement_id.split(',')[0]
            measurement_id = each_id_measurement_id.split(',')[1]

            math_dev_measurement = self.device_measurements.filter(
                DeviceMeasurements.channel == 0).first()
            if math_dev_measurement:
                conversion = db_retrieve_table_daemon(
                    Conversion,
                    unique_id=math_dev_measurement.conversion_id)
            else:
                conversion = None
            channel, unit, measurement = return_measurement_info(
                math_dev_measurement, conversion)

            try:
                success_measure, measure = self.get_measurements_from_id(
                    device_id, measurement_id)

                if success_measure:
                    measurement_dict = {
                        channel: {
                            'measurement': measurement,
                            'unit': unit,
                            'value': float(measure[1]),
                            'timestamp_utc': measure[0],
                        }
                    }
                    measurement_success = True
                    break

            except Exception as msg:
                self.logger.exception(
                    "redundancy Error: {err}".format(err=msg))
        if not measurement_success:
            self.error_not_within_max_age()
        return measurement_dict

    def math_statistics(self, measurement_dict):
        success, measure = self.get_measurements_from_str(self.inputs)
        if success:
            # Perform some math
            stat_mean = float(sum(measure) / float(len(measure)))
            stat_median = median(measure)
            stat_minimum = min(measure)
            stat_maximum = max(measure)
            stdev_ = stdev(measure)
            stdev_mean_upper = stat_mean + stdev_
            stdev_mean_lower = stat_mean - stdev_

            list_measurement = [
                stat_mean,
                stat_median,
                stat_minimum,
                stat_maximum,
                stdev_,
                stdev_mean_upper,
                stdev_mean_lower
            ]

            for each_measurement in self.device_measurements.all():
                if each_measurement.is_enabled:
                    conversion = db_retrieve_table_daemon(
                        Conversion, unique_id=each_measurement.conversion_id)
                    channel, unit, measurement = return_measurement_info(
                        each_measurement, conversion)

                    measurement_dict[channel] = {
                        'measurement': measurement,
                        'unit': unit,
                        'value': list_measurement[channel]
                    }

        elif measure:
            self.logger.error(measure)
        else:
            self.error_not_within_max_age()
        return measurement_dict

    def math_verification(self, measurement_dict):
        channel, unit, measurement = self.return_single_conversion_info()

        success, measure = self.get_measurements_from_str(self.inputs)
        if (success and
                max(measure) - min(measure) <
                self.max_difference):
            difference = max(measure) - min(measure)

            measurement_dict = {
                channel: {
                    'measurement': measurement,
                    'unit': unit,
                    'value': difference
                }
            }
        elif measure:
            self.logger.error(measure)
        else:
            self.error_not_within_max_age()
        return measurement_dict

    def math_humidity(self, measurement_dict):
        pressure_pa = 101325
        critical_error = False

        if self.pressure_pa_id and self.pressure_pa_measure_id:

            success_pa, pressure = self.get_measurements_from_id(
                self.pressure_pa_id, self.pressure_pa_measure_id)

            if success_pa:
                pressure_pa = int(pressure[1])
                # Pressure must be in Pa, convert if not

                measurement_press = db_retrieve_table_daemon(
                    DeviceMeasurements,
                    unique_id=self.pressure_pa_measure_id)
                if not measurement_press:
                    self.logger.error(
                        "Could not find pressure measurement")
                    measurement_press = None
                    critical_error = True

                if measurement_press and measurement_press.unit != 'Pa':
                    pressure_pa, status = self.is_measurement_unit(
                        measurement_press.unit, 'Pa', pressure_pa)
                    if status == 'error':
                        critical_error = True

        success_dbt, dry_bulb_t = self.get_measurements_from_id(
            self.dry_bulb_t_id, self.dry_bulb_t_measure_id)
        success_wbt, wet_bulb_t = self.get_measurements_from_id(
            self.wet_bulb_t_id, self.wet_bulb_t_measure_id)

        if success_dbt and success_wbt:
            dbt_kelvin = float(dry_bulb_t[1])
            wbt_kelvin = float(wet_bulb_t[1])

            measurement_db_temp = db_retrieve_table_daemon(
                DeviceMeasurements,
                unique_id=self.dry_bulb_t_measure_id)
            if not measurement_db_temp:
                self.logger.error(
                    "Could not find dry bulb temperature measurement")
                measurement_db_temp = None
                critical_error = True

            if measurement_db_temp and measurement_db_temp.unit != 'K':
                dbt_kelvin, status = self.is_measurement_unit(
                    measurement_db_temp.unit, 'K', dbt_kelvin)
                if status == 'error':
                    critical_error = True

            measurement_wb_temp = db_retrieve_table_daemon(
                DeviceMeasurements,
                unique_id=self.wet_bulb_t_measure_id)
            if not measurement_wb_temp:
                self.logger.error(
                    "Could not find wet bulb temperature measurement")
                measurement_wb_temp = None
                critical_error = True

            if measurement_wb_temp and measurement_wb_temp.unit != 'K':
                wbt_kelvin, status = self.is_measurement_unit(
                    measurement_wb_temp.unit, 'K', wbt_kelvin)
                if status == 'error':
                    critical_error = True

            # Convert temperatures to Kelvin (already done above)
            # dbt_kelvin = celsius_to_kelvin(dry_bulb_t_c)
            # wbt_kelvin = celsius_to_kelvin(wet_bulb_t_c)
            psypi = None

            try:
                if not critical_error:
                    psypi = SI.state(
                        "DBT", dbt_kelvin, "WBT", wbt_kelvin, pressure_pa)
                else:
                    self.logger.error(
                        "One or more critical errors prevented the "
                        "humidity from being calculated")
            except TypeError as err:
                self.logger.error("TypeError: {msg}".format(msg=err))

            if psypi:
                percent_relative_humidity = psypi[2] * 100

                # Ensure percent humidity stays within 0 - 100 % range
                if percent_relative_humidity > 100:
                    percent_relative_humidity = 100
                elif percent_relative_humidity < 0:
                    percent_relative_humidity = 0

                # Dry bulb temperature: psypi[0])
                # Wet bulb temperature: psypi[5])

                specific_enthalpy = float(psypi[1])
                humidity = float(percent_relative_humidity)
                specific_volume = float(psypi[3])
                humidity_ratio = float(psypi[4])

                self.logger.debug(
                    "Dry Temp: ({dtu}: {dtv}, K: {dtk}), "
                    "Wet Temp: ({wtu}: {wtv}, K: {wtk}), "
                    "Pressure: {pres},"
                    "Humidity: {rh}".format(
                        dtu=measurement_db_temp.unit,
                        dtv=float(dry_bulb_t[1]),
                        dtk=dbt_kelvin,
                        wtu=measurement_wb_temp.unit,
                        wtv=float(wet_bulb_t[1]),
                        wtk=wbt_kelvin,
                        pres=pressure_pa,
                        rh=humidity))

                list_measurement = [
                    humidity,
                    humidity_ratio,
                    specific_enthalpy,
                    specific_volume
                ]

                for each_measurement in self.device_measurements.all():
                    if each_measurement.is_enabled:
                        conversion = db_retrieve_table_daemon(
                            Conversion,
                            unique_id=each_measurement.conversion_id)
                        channel, unit, measurement = return_measurement_info(
                            each_measurement, conversion)

                        measurement_dict[channel] = {
                            'measurement': measurement,
                            'unit': unit,
                            'value': list_measurement[channel]
                        }
        else:
            self.error_not_within_max_age()
        return measurement_dict

    def math_vapor_pressure_deficit(self, measurement_dict):
        vpd_pa = None
        critical_error = False

        success_temp, temperature = self.get_measurements_from_id(
            self.unique_id_1, self.unique_measurement_id_1)
        success_hum, humidity = self.get_measurements_from_id(
            self.unique_id_2, self.unique_measurement_id_2)

        if success_temp and success_hum:
            vpd_temperature_celsius = float(temperature[1])
            vpd_humidity_percent = float(humidity[1])

            measurement_temp = db_retrieve_table_daemon(
                DeviceMeasurements,
                unique_id=self.unique_measurement_id_1)
            if not measurement_temp:
                self.logger.error("Could not find temperature measurement")
                measurement_temp = None
                critical_error = True

            if measurement_temp and measurement_temp.unit != 'C':
                vpd_temperature_celsius, status = self.is_measurement_unit(
                    measurement_temp.unit, 'C', vpd_temperature_celsius)
                if status == 'error':
                    critical_error = True

            measurement_hum = db_retrieve_table_daemon(
                DeviceMeasurements,
                unique_id=self.unique_measurement_id_2)
            if not measurement_hum:
                self.logger.error("Could not find humidity measurement")
                measurement_hum = None
                critical_error = True

            if measurement_hum and measurement_hum.unit != 'percent':
                vpd_humidity_percent, status = self.is_measurement_unit(
                    measurement_hum.unit, 'percent', vpd_humidity_percent)
                if status == 'error':
                    critical_error = True

            try:
                if not critical_error:
                    vpd_pa = calculate_vapor_pressure_deficit(
                        vpd_temperature_celsius, vpd_humidity_percent)
                else:
                    self.logger.error(
                        "One or more critical errors prevented the "
                        "vapor pressure deficit from being calculated")
            except TypeError as err:
                self.logger.error("TypeError: {msg}".format(msg=err))

            if vpd_pa:
                math_dev_measurement = self.device_measurements.first()
                conversion = db_retrieve_table_daemon(
                    Conversion, unique_id=math_dev_measurement.conversion_id)
                channel, unit, measurement = return_measurement_info(
                    math_dev_measurement, conversion)

                measurement_dict[channel] = {
                    'measurement': measurement,
                    'unit': unit,
                    'value': vpd_pa
                }
        else:
            self.error_not_within_max_age()
        return measurement_dict

    def is_measurement_unit(self, unit_from, unit_to, value):
        """ Converts value from one measurement to another """
        if unit_from != unit_to:
            conversion_id = None
            for each_conv in db_retrieve_table_daemon(Conversion, entry='all'):
                if (each_conv.convert_unit_from == unit_from and
                        each_conv.convert_unit_to == unit_to):
                    conversion_id = each_conv.unique_id

            if conversion_id:
                return_value = convert_units(
                    conversion_id, value)
                return return_value, 'success'
            else:
                self.logger.error(
                    "Could not find conversion for unit "
                    "{unit_from} to {unit_to}".format(
                        unit_from=unit_from,
                        unit_to=unit_to))
                return None, 'error'

    def error_not_within_max_age(self):
        self.logger.debug(
            "One or more inputs were not within the Max Age that has been "
            "set. Ensure all Inputs are operating properly.")

    def get_measurements_from_str(self, device):
        try:
            measurements = []
            device_list = device.split(';')
            for each_device_set in device_list:
                device_id = each_device_set.split(',')[0]
                device_measure_id = each_device_set.split(',')[1]

                device_measurement = get_measurement(
                    device_measure_id)
                if not device_measurement:
                    return False, None

                conversion = db_retrieve_table_daemon(
                    Conversion, unique_id=device_measurement.conversion_id)
                channel, unit, measurement = return_measurement_info(
                    device_measurement, conversion)

                last_measurement = read_last_influxdb(
                    device_id,
                    unit,
                    channel,
                    measure=measurement,
                    duration_sec=self.max_measure_age)

                if not last_measurement:
                    return False, None
                else:
                    measurements.append(last_measurement[1])
            return True, measurements
        except urllib3.exceptions.NewConnectionError:
            return False, "Influxdb: urllib3.exceptions.NewConnectionError"
        except Exception as msg:
            return False, "Influxdb: Unknown Error: {err}".format(err=msg)

    def get_measurements_from_id(self, device_id, measure_id):
        device_measurement = get_measurement(measure_id)
        if not device_measurement:
            return False, None

        conversion = db_retrieve_table_daemon(
            Conversion, unique_id=device_measurement.conversion_id)
        channel, unit, measurement = return_measurement_info(
            device_measurement, conversion)

        measure = read_last_influxdb(
            device_id,
            unit,
            channel,
            measure=measurement,
            duration_sec=self.max_measure_age)
        if not measure:
            return False, None
        return True, measure

    def return_single_conversion_info(self):
        """ Return channel, unit, and measurement of a math device measurement """
        math_dev_measurement = self.device_measurements.filter(
            DeviceMeasurements.channel == 0).first()
        if math_dev_measurement:
            conversion = db_retrieve_table_daemon(
                Conversion, unique_id=math_dev_measurement.conversion_id)
        else:
            conversion = None
        channel, unit, measurement = return_measurement_info(
            math_dev_measurement, conversion)

        return channel, unit, measurement

    def return_single_measure_info(self):
        math_dev_measurement = self.device_measurements.filter(
            DeviceMeasurements.channel == 0).first()
        math_conversion = db_retrieve_table_daemon(
            Conversion, unique_id=math_dev_measurement.conversion_id)
        _, math_unit, _ = return_measurement_info(
            math_dev_measurement, math_conversion)

        device_id = self.inputs.split(',')[0]
        measurement_id = self.inputs.split(',')[1]

        device_measurement = db_retrieve_table_daemon(
            DeviceMeasurements, unique_id=measurement_id)
        if device_measurement:
            measure_conversion = db_retrieve_table_daemon(
                Conversion,
                unique_id=device_measurement.conversion_id)
        else:
            measure_conversion = None
        (measure_channel,
         measure_unit,
         measure_measurement) = return_measurement_info(
            device_measurement, measure_conversion)

        return (device_id,
                math_dev_measurement,
                math_unit,
                measure_channel,
                measure_unit,
                measure_measurement)
