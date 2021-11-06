# coding=utf-8
#
#  display_ssd1306_oled_128x64_i2c.py - Function to output to LCD
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
import calendar
import datetime
import json
import math
import time
import traceback

from flask import flash
from flask_babel import lazy_gettext

from farm.config import FARM_VERSION
from farm.config_translations import TRANSLATIONS
from farm.databases.models import CustomController
from farm.databases.models import FunctionChannel
from farm.functions.base_function import AbstractFunction
from farm.farm_flask.utils.utils_general import custom_channel_options_return_json
from farm.farm_flask.utils.utils_general import delete_entry_with_id
from farm.utils.constraints_pass import constraints_pass_positive_or_zero_value
from farm.utils.constraints_pass import constraints_pass_positive_value
from farm.utils.database import db_retrieve_table_daemon
from farm.utils.functions import parse_function_information
from farm.utils.lcd import format_measurement_line
from farm.utils.system_pi import cmd_output

# Set to how many lines the LCD has
lcd_lines = 8


def execute_at_creation(error, new_func, dict_functions=None):
    try:
        dict_controllers = parse_function_information()

        for channel in range(lcd_lines):
            new_channel = FunctionChannel()
            new_channel.name = "Set 0 Line {}".format(channel)
            new_channel.function_id = new_func.unique_id
            new_channel.channel = channel

            error, custom_options = custom_channel_options_return_json(
                error, dict_controllers, None,
                new_func.unique_id, channel,
                device=new_func.device, use_defaults=True)
            custom_options_dict = json.loads(custom_options)
            custom_options_dict["name"] = new_channel.name
            new_channel.custom_options = json.dumps(custom_options_dict)
            new_channel.save()
    except Exception:
        error.append("execute_at_modification() Error: {}".format(traceback.print_exc()))

    return error, new_func


def execute_at_modification(
        messages,
        mod_function,
        request_form,
        custom_options_dict_presave,
        custom_options_channels_dict_presave,
        custom_options_dict_postsave,
        custom_options_channels_dict_postsave):
    """
    This function allows you to view and modify the output and channel settings when the user clicks
    save on the user interface. Both the output and channel settings are passed to this function, as
    dictionaries. Additionally, both the pre-saved and post-saved options are available, as it's
    sometimes useful to know what settings changed and from what values. You can modify the post-saved
    options and these will be stored in the database.
    :param mod_output: The post-saved output database entry, minus the custom_options settings
    :param request_form: The requests.form object the user submitted
    :param custom_options_dict_presave: dict of pre-saved custom output options
    :param custom_options_channels_dict_presave: dict of pre-saved custom output channel options
    :param custom_options_dict_postsave: dict of post-saved custom output options
    :param custom_options_channels_dict_postsave: dict of post-saved custom output channel options
    :return:
    """
    page_refresh = False

    try:
        dict_controllers = parse_function_information()

        channels = FunctionChannel.query.filter(
            FunctionChannel.function_id == mod_function.unique_id)

        # Ensure name doesn't get overwritten
        selector_set = 0
        selector_line = 0
        for channel in range(channels.count()):
            custom_options_channels_dict_postsave[channel]["name"] = "Set {} Line {}".format(
                selector_set, selector_line)
            selector_line += 1
            if selector_line == lcd_lines:
                selector_set += 1
                selector_line = 0

        end_channel = custom_options_dict_postsave['number_line_sets'] * lcd_lines

        # Increase number of channels
        if (custom_options_dict_postsave['number_line_sets'] >
                custom_options_dict_presave['number_line_sets']):

            page_refresh = True
            start_channel = channels.count()

            for index in range(start_channel, end_channel):
                new_channel = FunctionChannel()
                new_channel.name = "Set {} Line {}".format(
                    math.trunc(index / lcd_lines),
                    index - (math.trunc(index / lcd_lines) * lcd_lines))
                new_channel.function_id = mod_function.unique_id
                new_channel.channel = index

                messages["error"], custom_options = custom_channel_options_return_json(
                    messages["error"], dict_controllers, request_form,
                    mod_function.unique_id, index,
                    device=mod_function.device, use_defaults=False)
                custom_options_dict = json.loads(custom_options)
                custom_options_dict["name"] = new_channel.name
                new_channel.custom_options = json.dumps(custom_options_dict)

                new_channel.save()

        # Decrease number of channels
        elif (custom_options_dict_postsave['number_line_sets'] <
                custom_options_dict_presave['number_line_sets']):

            page_refresh = True
            for index, each_channel in enumerate(channels.all()):
                if index >= end_channel:
                    delete_entry_with_id(FunctionChannel, each_channel.unique_id)

    except Exception:
        messages["error"].append("execute_at_modification() Error: {}".format(traceback.print_exc()))

    return (messages,
            mod_function,
            custom_options_dict_postsave,
            custom_options_channels_dict_postsave,
            page_refresh)


FUNCTION_INFORMATION = {
    'function_name_unique': 'display_ssd1306_oled_128x64_i2c',
    'function_name': 'Display: SSD1306 OLED 128x64 [8 Lines] (I2C)',
    'function_library': 'Adafruit-Circuitpython-SSD1306',
    'execute_at_creation': execute_at_creation,
    'execute_at_modification': execute_at_modification,

    'message': 'This Function outputs to a 128x64 SSD1306 OLED display via I2C. This display Function will show 8 lines at a time, so channels are added in sets of 8 when Number of Line Sets is modified. Every Period, the LCD will refresh and display the next set of lines. Therefore, the first set of lines that are displayed are channels 0 - 7, then 8 - 15, and so on. After all channels have been displayed, it will cycle back to the beginning.',

    'options_disabled': [
        'measurements_select',
        'measurements_configure'
    ],

    'dependencies_module': [
        ('apt', 'libjpeg-dev', 'libjpeg-dev'),
        ('pip-pypi', 'PIL', 'Pillow==8.1.2'),
        ('pip-pypi', 'usb.core', 'pyusb==1.1.1'),
        ('pip-pypi', 'adafruit_extended_bus', 'adafruit-extended-bus==1.0.1'),
        ('pip-pypi', 'adafruit_framebuf', 'adafruit-circuitpython-framebuf'),
        ('pip-pypi', 'adafruit_ssd1306', 'Adafruit-Circuitpython-SSD1306')
    ],

    'interface': 'I2C',

    'custom_options': [
        {
            'id': 'period',
            'type': 'float',
            'default_value': 10,
            'required': True,
            'constraints_pass': constraints_pass_positive_value,
            'name': lazy_gettext('Period (seconds)'),
            'phrase': lazy_gettext('The duration (seconds) between measurements or actions')
        },
        {
            'id': 'i2c_address',
            'type': 'text',
            'default_value': '0x3c',
            'required': True,
            'name': TRANSLATIONS['i2c_location']['title'],
            'phrase': TRANSLATIONS['i2c_location']['phrase']
        },
        {
            'id': 'i2c_bus',
            'type': 'integer',
            'default_value': 1,
            'required': True,
            'name': TRANSLATIONS['i2c_bus']['title'],
            'phrase': TRANSLATIONS['i2c_bus']['phrase']
        },
        {
            'id': 'number_line_sets',
            'type': 'integer',
            'default_value': 1,
            'required': True,
            'constraints_pass': constraints_pass_positive_value,
            'name': 'Number of Line Sets',
            'phrase': 'How many sets of lines to cycle on the LCD'
        },
        {
            'id': 'pin_reset',
            'type': 'integer',
            'default_value': 17,
            'required': True,
            'name': 'Reset Pin',
            'phrase': 'The pin (BCM numbering) connected to RST of the display'
        },
        {
            'id': 'characters_x',
            'type': 'integer',
            'default_value': 21,
            'required': True,
            'name': 'Characters Per Line',
            'phrase': 'The maximum number of characters to display per line'
        },
        {
            'id': 'use_non_default_font',
            'type': 'bool',
            'default_value': False,
            'required': True,
            'name': 'Use Non-Default Font',
            'phrase': "Don't use the default font. Enable to specify the path to a font to use."
        },
        {
            'id': 'non_default_font',
            'type': 'text',
            'default_value': '/usr/share/fonts/truetype/dejavu//DejaVuSans.ttf',
            'name': 'Non-Default Font Path',
            'phrase': 'The path to the non-default font to use'
        },
        {
            'id': 'font_size',
            'type': 'integer',
            'default_value': 10,
            'required': True,
            'constraints_pass': constraints_pass_positive_value,
            'name': 'Font Size (pt)',
            'phrase': 'The size of the font, in points'
        }
    ],

    'custom_channel_options': [
        {
            'id': 'line_display_type',
            'type': 'select',
            'default_value': '',
            'required': True,
            'options_select': [
                ('measurement_value', 'Last Measurement Value'),
                ('measurement_ts', 'Last Measurement Timestamp'),
                ('blank_line', 'Blank Line'),
                ('ip_address', 'IP Address'),
                ('current_time', 'Current Time'),
                ('text', 'Text')
            ],
            'name': 'Line Display Type',
            'phrase': 'What to display on the line'
        },
        {
            'id': 'select_measurement',
            'type': 'select_measurement',
            'default_value': '',
            'options_select': [
                'Input',
                'Math',
                'Function',
                'Output',
                'PID'
            ],
            'name': 'Measurement',
            'phrase': 'Measurement to display on the line'
        },
        {
            'id': 'measure_max_age',
            'type': 'float',
            'default_value': 360,
            'required': True,
            'constraints_pass': constraints_pass_positive_value,
            'name': lazy_gettext('Max Age'),
            'phrase': lazy_gettext('The maximum age (seconds) of the measurement to use')
        },
        {
            'id': 'measure_decimal',
            'type': 'integer',
            'default_value': 1,
            'required': True,
            'constraints_pass': constraints_pass_positive_or_zero_value,
            'name': 'Measurement Decimal',
            'phrase': 'The number of digits after the decimal'
        },
        {
            'id': 'text',
            'type': 'text',
            'default_value': 'Text',
            'required': True,
            'name': TRANSLATIONS['text']['title'],
            'phrase': "Text to display"
        },
        {
            'id': 'display_unit',
            'type': 'bool',
            'default_value': True,
            'required': True,
            'name': 'Display Unit',
            'phrase': "Display the measurement unit (if available)"
        }
    ]
}


class CustomModule(AbstractFunction):
    """
    Class to operate custom controller
    """
    def __init__(self, function, testing=False):
        super(CustomModule, self).__init__(function, testing=testing, name=__name__)

        self.options_channels = {}
        self.device = None
        self.timer_loop = time.time()
        self.line_sets = []
        self.current_line_set = 0
        self.line_y_dimensions = [0, 8, 16, 24, 32, 40, 48, 56]
        self.pad = -2

        # Initialize custom options
        self.period = None
        self.i2c_address = None
        self.i2c_bus = None
        self.number_line_sets = None
        self.pin_reset = None
        self.characters_x = None
        self.use_non_default_font = None
        self.non_default_font = None
        self.font_size = None

        # Set custom options
        custom_function = db_retrieve_table_daemon(
            CustomController, unique_id=self.unique_id)
        self.setup_custom_options(
            FUNCTION_INFORMATION['custom_options'], custom_function)

        if not testing:
            self.initialize_variables()

    def initialize_variables(self):
        from farm.devices.lcd_pioled_circuitpython import PiOLEDCircuitpython

        try:
            function_channels = db_retrieve_table_daemon(
                FunctionChannel).filter(FunctionChannel.function_id == self.unique_id).all()
            self.options_channels = self.setup_custom_channel_options_json(
                FUNCTION_INFORMATION['custom_channel_options'], function_channels)

            for each_set in range(self.number_line_sets):
                self.line_sets.append([])
                for each_line in range(lcd_lines):
                    self.line_sets[each_set].append(each_line)

            self.logger.debug("Line sets: {}".format(self.line_sets))

            lcd_settings_dict = {
                "unique_id": self.unique_id,
                "interface": "I2C",
                "i2c_address": self.i2c_address,
                "i2c_bus": self.i2c_bus,
                "x_characters": self.characters_x,
                "line_y_dimensions": self.line_y_dimensions,
                "lcd_type": "128x64_pioled_circuit_python",
                "font_size": self.font_size
            }

            font = None
            if self.use_non_default_font:
                font = self.non_default_font

            self.device = PiOLEDCircuitpython(lcd_settings_dict=lcd_settings_dict, font=font)
            self.device.lcd_init()

            self.logger.debug("LCD Function started")
        except:
            self.logger.exception("Starting LCD Function")

    def loop(self):
        if self.timer_loop > time.time():
            return

        while self.timer_loop < time.time():
            self.timer_loop += self.period

        if not self.device:
            self.logger.error("LCD not set up")
            return

        # Generate lines to display
        lines_display = {}
        for line in range(lcd_lines):
            lines_display[line] = ""

        for current_line in self.line_sets[self.current_line_set]:
            current_channel = (self.current_line_set * lcd_lines) + current_line
            self.logger.debug("Channel: {}, Set: {} Line: {}, ".format(
                current_channel, self.current_line_set, current_line))

            try:
                # Get measurement value and timestamp
                if self.options_channels['line_display_type'][current_channel] in [
                    'measurement_value', 'measurement_ts']:
                    lines_display[current_line] = "NONE"
                    measure_ts = None
                    measure_value = None

                    last_measurement = self.get_last_measurement(
                        self.options_channels['select_measurement'][current_channel]['device_id'],
                        self.options_channels['select_measurement'][current_channel]['measurement_id'],
                        max_age=self.options_channels['measure_max_age'][current_channel])

                    if last_measurement:
                        measure_ts = last_measurement[0]
                        measure_value = last_measurement[1]

                    if self.options_channels['line_display_type'][current_channel] == 'measurement_value':
                        if measure_value:
                            if self.options_channels['measure_decimal'][current_channel] == 0:
                                val_rounded = int(self.options_channels['measure_decimal'][current_channel])
                            else:
                                val_rounded = round(
                                    measure_value,
                                    self.options_channels['measure_decimal'][current_channel])

                            lines_display[current_line] = format_measurement_line(
                                self.options_channels['select_measurement'][current_channel]['device_id'],
                                self.options_channels['select_measurement'][current_channel]['measurement_id'],
                                val_rounded,
                                self.characters_x,
                                display_unit=self.options_channels['display_unit'][current_channel])

                    elif self.options_channels['line_display_type'][current_channel] == 'measurement_ts':
                        if measure_ts:
                            # Convert UTC timestamp to local timezone
                            utc_dt = datetime.datetime.strptime(
                                measure_ts.split(".")[0], '%Y-%m-%dT%H:%M:%S')
                            utc_timestamp = calendar.timegm(utc_dt.timetuple())
                            lines_display[current_line] = str(
                                datetime.datetime.fromtimestamp(utc_timestamp))

                elif self.options_channels['line_display_type'][current_channel] == 'current_time':
                    lines_display[current_line] = time.strftime('%Y-%m-%d %H:%M:%S')

                elif self.options_channels['line_display_type'][current_channel] == 'text':
                    lines_display[current_line] = self.options_channels['text'][current_channel]

                elif self.options_channels['line_display_type'][current_channel] == 'blank_line':
                    lines_display[current_line] = ""

                elif self.options_channels['line_display_type'][current_channel] == 'ip_address':
                    str_ip_cmd = "ip addr | " \
                                 "grep 'state UP' -A2 | " \
                                 "tail -n1 | " \
                                 "awk '{print $2}' | " \
                                 "cut -f1  -d'/'"
                    ip_out, _, _ = cmd_output(str_ip_cmd)
                    lines_display[current_line] = ip_out.rstrip().decode("utf-8")
            except Exception as err:
                # self.logger.exception("Generating line")
                self.logger.error("Error generating channel {} line: {}".format(current_channel, err))
                lines_display[current_line] = "ERROR"

        if self.current_line_set == len(self.line_sets) - 1:
            self.current_line_set = 0
        else:
            self.current_line_set += 1

        self.logger.debug("Displaying: {}".format(lines_display))

        # Display lines
        self.device.lcd_init()
        self.device.lcd_write_lines(
            lines_display[0],
            lines_display[1],
            lines_display[2],
            lines_display[3],
            lines_display[4],
            lines_display[5],
            lines_display[6],
            lines_display[7])

    def stop_function(self):
        self.device.lcd_write_lines(
            "Farm {}".format(FARM_VERSION), "Display Deactivated", "", "")
