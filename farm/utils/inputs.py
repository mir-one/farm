# -*- coding: utf-8 -*-
#
#  inputs.py - Farm core utils
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
import logging

import os

from farm.config import PATH_INPUTS
from farm.config import PATH_INPUTS_CUSTOM
from farm.utils.modules import load_module_from_file
from farm.utils.logging_utils import set_log_level

logger = logging.getLogger("farm.utils.inputs")
logger.setLevel(set_log_level(logging))


def list_devices_using_interface(interface):
    """
    Generates a list of input devices that use a particular interface
    :param interface: string, can be 'GPIO', 'I2C', 'UART', 'BT', '1WIRE', 'Farm', 'RPi'
    :return: list of strings
    """
    def check(check_input, dict_all_inputs, check_interface):
        if ('interfaces' in dict_all_inputs[check_input] and
                check_interface in dict_all_inputs[check_input]['interfaces']):
            return True

    list_devices = []
    dict_inputs = parse_input_information()

    for each_input in dict_inputs:
        if (check(each_input, dict_inputs, interface) and
                each_input not in list_devices):
            list_devices.append(each_input)

    return list_devices


def list_analog_to_digital_converters():
    """Generates a list of input devices that are analog-to-digital converters"""
    list_adc = []
    dict_inputs = parse_input_information()
    for each_input in dict_inputs:
        if ('analog_to_digital_converter' in dict_inputs[each_input] and
                dict_inputs[each_input]['analog_to_digital_converter'] and
                each_input not in list_adc):
            list_adc.append(each_input)
    return list_adc


def parse_input_information(exclude_custom=False):
    """Parses the variables assigned in each Input and return a dictionary of IDs and values"""
    def dict_has_value(dict_inp, input_cus, key, force_type=None):
        if (key in input_cus.INPUT_INFORMATION and
                (input_cus.INPUT_INFORMATION[key] or
                 input_cus.INPUT_INFORMATION[key] == 0)):
            if force_type == 'list':
                if isinstance(input_cus.INPUT_INFORMATION[key], list):
                    dict_inp[input_cus.INPUT_INFORMATION['input_name_unique']][key] = \
                        input_cus.INPUT_INFORMATION[key]
                else:
                    dict_inp[input_cus.INPUT_INFORMATION['input_name_unique']][key] = \
                        [input_cus.INPUT_INFORMATION[key]]
            else:
                dict_inp[input_cus.INPUT_INFORMATION['input_name_unique']][key] = \
                    input_cus.INPUT_INFORMATION[key]
        return dict_inp

    excluded_files = [
        '__init__.py', '__pycache__', 'base_input.py', 'custom_inputs',
        'examples', 'scripts', 'tmp_inputs', 'sensorutils.py'
    ]

    input_paths = [PATH_INPUTS]

    if not exclude_custom:
        input_paths.append(PATH_INPUTS_CUSTOM)

    dict_inputs = {}

    for each_path in input_paths:

        real_path = os.path.realpath(each_path)

        for each_file in os.listdir(real_path):
            if each_file in excluded_files:
                continue

            full_path = "{}/{}".format(real_path, each_file)
            input_custom = load_module_from_file(full_path, 'inputs')

            if not input_custom or not hasattr(input_custom, 'INPUT_INFORMATION'):
                continue

            # Populate dictionary of input information
            if input_custom.INPUT_INFORMATION['input_name_unique'] in dict_inputs:
                logger.error("Error: Cannot add input modules because it does not have a unique name: {name}".format(
                    name=input_custom.INPUT_INFORMATION['input_name_unique']))
            else:
                dict_inputs[input_custom.INPUT_INFORMATION['input_name_unique']] = {}

            dict_inputs[input_custom.INPUT_INFORMATION['input_name_unique']]['file_path'] = full_path

            dict_inputs = dict_has_value(dict_inputs, input_custom, 'input_manufacturer')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'input_name')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'input_library')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'measurements_name')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'measurements_dict')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'channels_dict')

            dict_inputs = dict_has_value(dict_inputs, input_custom, 'measurements_variable_amount')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'channel_quantity_same_as_measurements')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'measurements_use_same_timestamp')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'measurements_rescale')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'listener')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'message')

            dict_inputs = dict_has_value(dict_inputs, input_custom, 'url_datasheet', force_type='list')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'url_manufacturer', force_type='list')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'url_product_purchase', force_type='list')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'url_additional', force_type='list')

            # Dependencies
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'dependencies_module')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'dependencies_message')

            dict_inputs = dict_has_value(dict_inputs, input_custom, 'enable_channel_unit_select')

            # Interfaces
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'interfaces')

            # Nonstandard (I2C, UART, etc.) location
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'location')

            # I2C
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'i2c_location')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'i2c_address_editable')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'i2c_address_default')

            # FTDI
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'ftdi_location')

            # UART
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'uart_location')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'uart_baud_rate')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'pin_cs')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'pin_miso')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'pin_mosi')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'pin_clock')

            # Bluetooth (BT)
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'bt_location')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'bt_adapter')

            # Which form options to display and whether each option is enabled
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'options_enabled')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'options_disabled')

            # Host options
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'times_check')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'deadline')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'port')

            # Signal options
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'weighting')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'sample_time')

            # Analog-to-digital converter
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'adc_gain')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'adc_resolution')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'adc_sample_speed')

            # Misc
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'period')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'sht_voltage')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'cmd_command')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'resolution')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'resolution_2')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'sensitivity')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'thermocouple_type')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'ref_ohm')

            dict_inputs = dict_has_value(dict_inputs, input_custom, 'execute_at_creation')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'execute_at_modification')

            dict_inputs = dict_has_value(dict_inputs, input_custom, 'custom_options_message')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'custom_options')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'custom_channel_options')

            dict_inputs = dict_has_value(dict_inputs, input_custom, 'custom_actions_message')
            dict_inputs = dict_has_value(dict_inputs, input_custom, 'custom_actions')

    return dict_inputs
