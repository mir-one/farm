# coding=utf-8
#
# controller_lcd.py - Farm LCD controller that outputs measurements and other
#                     information to I2C-interfaced LCDs
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
#  LCD Code used in part from:
#
# Copyright (c) 2010 cnr437@gmail.com
#
# Licensed under the MIT License <http://opensource.org/licenses/MIT>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# <http://code.activestate.com/recipes/577231-discrete-lcd-controller/>
#
import calendar
import datetime
import threading
import time

from farm.controllers.base_controller import AbstractController
from farm.config import FARM_VERSION
from farm.databases.models import Conversion
from farm.databases.models import DeviceMeasurements
from farm.databases.models import Input
from farm.databases.models import LCD
from farm.databases.models import LCDData
from farm.databases.models import Math
from farm.databases.models import Measurement
from farm.databases.models import Output
from farm.databases.models import PID
from farm.databases.models import Unit
from farm.utils.database import db_retrieve_table_daemon
from farm.utils.influx import read_last_influxdb
from farm.utils.system_pi import add_custom_measurements
from farm.utils.system_pi import add_custom_units
from farm.utils.system_pi import cmd_output
from farm.utils.system_pi import return_measurement_info


class LCDController(AbstractController, threading.Thread):
    """
    Class to operate LCD controller
    """
    def __init__(self, ready, unique_id):
        threading.Thread.__init__(self)
        super(LCDController, self).__init__(ready, unique_id=unique_id, name=__name__)

        self.unique_id = unique_id
        self.sample_rate = 1

        self.flash_lcd_on = False
        self.lcd_initialized = False
        self.lcd_is_on = False

        self.display_sets = []
        self.display_set_count = 0

        self.lcd_out = None
        self.lcd_type = None
        self.lcd_name = None
        self.lcd_period = None
        self.lcd_x_characters = None
        self.lcd_y_lines = None
        self.timer = None
        self.backlight_timer = None
        self.log_level_debug = None

        self.list_inputs = None
        self.dict_units = None

        self.lcd_string_line = {}
        self.lcd_line = {}
        self.lcd_text = {}
        self.lcd_max_age = {}
        self.lcd_decimal_places = {}

    def loop(self):
        if not self.lcd_initialized:
            self.stop_controller()
        elif (self.lcd_is_on and
                self.lcd_initialized and
                time.time() > self.timer):
            try:
                # Acquire all measurements to be displayed on the LCD
                display_id = self.display_sets[self.display_set_count]
                for line in range(1, self.lcd_y_lines + 1):
                    if not self.running:
                        break
                    if self.lcd_line[display_id][line]['id'] and self.lcd_line[display_id][line]['setup']:
                        self.create_lcd_line(
                            self.get_measurement(display_id, line),
                            display_id,
                            line)
                    else:
                        self.lcd_string_line[display_id][line] = 'LCD LINE ERROR'
                # Output lines to the LCD
                if self.running:
                    self.output_lcds()
            except KeyError:
                self.logger.exception(
                    "KeyError: Unable to output to LCD.")
            except IOError:
                self.logger.exception(
                    "IOError: Unable to output to LCD.")
            except Exception:
                self.logger.exception(
                    "Exception: Unable to output to LCD.")

            # Increment display counter to show the next display
            if len(self.display_sets) > 1:
                if self.display_set_count < len(self.display_sets) - 1:
                    self.display_set_count += 1
                else:
                    self.display_set_count = 0

            self.timer = time.time() + self.lcd_period

        elif not self.lcd_is_on:
            # Turn backlight off
            self.lcd_out.lcd_backlight(0)

        if self.flash_lcd_on:
            if time.time() > self.backlight_timer:
                if self.lcd_is_on:
                    self.lcd_backlight(0)
                    seconds = 0.2
                else:
                    self.output_lcds()
                    seconds = 1.1
                self.backlight_timer = time.time() + seconds

    def run_finally(self):
        self.lcd_out.lcd_init()  # Blank LCD
        line_1 = 'Farm {}'.format(FARM_VERSION)
        line_2 = 'Stop {}'.format(self.lcd_name)
        self.lcd_out.lcd_write_lines(line_1, line_2, '', '')

    def initialize_variables(self):
        lcd_dev = db_retrieve_table_daemon(LCD, unique_id=self.unique_id)
        self.lcd_type = lcd_dev.lcd_type
        self.lcd_name = lcd_dev.name
        self.lcd_period = lcd_dev.period
        self.lcd_x_characters = lcd_dev.x_characters
        self.lcd_y_lines = lcd_dev.y_lines
        self.timer = time.time() + self.lcd_period
        self.backlight_timer = time.time()
        self.log_level_debug = lcd_dev.log_level_debug

        self.set_log_level_debug(self.log_level_debug)

        # Add custom measurement and units to list
        self.list_inputs = add_custom_measurements(
            db_retrieve_table_daemon(Measurement, entry='all'))

        self.list_inputs.update(
            {'input_time': {'unit': None, 'name': 'Time'}})
        self.list_inputs.update(
            {'pid_time': {'unit': None, 'name': 'Time'}})

        self.dict_units = add_custom_units(
            db_retrieve_table_daemon(Unit, entry='all'))

        lcd_data = db_retrieve_table_daemon(
            LCDData).filter(LCDData.lcd_id == lcd_dev.unique_id).all()

        for each_lcd_display in lcd_data:
            self.display_sets.append(each_lcd_display.unique_id)
            self.lcd_string_line[each_lcd_display.unique_id] = {}
            self.lcd_line[each_lcd_display.unique_id] = {}
            self.lcd_text[each_lcd_display.unique_id] = {}
            self.lcd_max_age[each_lcd_display.unique_id] = {}
            self.lcd_decimal_places[each_lcd_display.unique_id] = {}

            for i in range(1, self.lcd_y_lines + 1):
                self.lcd_string_line[each_lcd_display.unique_id][i] = ''
                self.lcd_line[each_lcd_display.unique_id][i] = {}
                if i == 1:
                    self.lcd_text[each_lcd_display.unique_id][i] = each_lcd_display.line_1_text
                    self.lcd_max_age[each_lcd_display.unique_id][i] = each_lcd_display.line_1_max_age
                    self.lcd_decimal_places[each_lcd_display.unique_id][i] = each_lcd_display.line_1_decimal_places
                elif i == 2:
                    self.lcd_text[each_lcd_display.unique_id][i] = each_lcd_display.line_2_text
                    self.lcd_max_age[each_lcd_display.unique_id][i] = each_lcd_display.line_2_max_age
                    self.lcd_decimal_places[each_lcd_display.unique_id][i] = each_lcd_display.line_2_decimal_places
                elif i == 3:
                    self.lcd_text[each_lcd_display.unique_id][i] = each_lcd_display.line_3_text
                    self.lcd_max_age[each_lcd_display.unique_id][i] = each_lcd_display.line_3_max_age
                    self.lcd_decimal_places[each_lcd_display.unique_id][i] = each_lcd_display.line_3_decimal_places
                elif i == 4:
                    self.lcd_text[each_lcd_display.unique_id][i] = each_lcd_display.line_4_text
                    self.lcd_max_age[each_lcd_display.unique_id][i] = each_lcd_display.line_4_max_age
                    self.lcd_decimal_places[each_lcd_display.unique_id][i] = each_lcd_display.line_4_decimal_places
                elif i == 5:
                    self.lcd_text[each_lcd_display.unique_id][i] = each_lcd_display.line_5_text
                    self.lcd_max_age[each_lcd_display.unique_id][i] = each_lcd_display.line_5_max_age
                    self.lcd_decimal_places[each_lcd_display.unique_id][i] = each_lcd_display.line_5_decimal_places
                elif i == 6:
                    self.lcd_text[each_lcd_display.unique_id][i] = each_lcd_display.line_6_text
                    self.lcd_max_age[each_lcd_display.unique_id][i] = each_lcd_display.line_6_max_age
                    self.lcd_decimal_places[each_lcd_display.unique_id][i] = each_lcd_display.line_6_decimal_places
                elif i == 7:
                    self.lcd_text[each_lcd_display.unique_id][i] = each_lcd_display.line_7_text
                    self.lcd_max_age[each_lcd_display.unique_id][i] = each_lcd_display.line_7_max_age
                    self.lcd_decimal_places[each_lcd_display.unique_id][i] = each_lcd_display.line_7_decimal_places
                elif i == 8:
                    self.lcd_text[each_lcd_display.unique_id][i] = each_lcd_display.line_8_text
                    self.lcd_max_age[each_lcd_display.unique_id][i] = each_lcd_display.line_8_max_age
                    self.lcd_decimal_places[each_lcd_display.unique_id][i] = each_lcd_display.line_8_decimal_places

            if self.lcd_y_lines in [2, 4, 8]:
                self.setup_lcd_line(
                    each_lcd_display.unique_id, 1,
                    each_lcd_display.line_1_id,
                    each_lcd_display.line_1_measurement)
                self.setup_lcd_line(
                    each_lcd_display.unique_id, 2,
                    each_lcd_display.line_2_id,
                    each_lcd_display.line_2_measurement)

            if self.lcd_y_lines in [4, 8]:
                self.setup_lcd_line(
                    each_lcd_display.unique_id, 3,
                    each_lcd_display.line_3_id,
                    each_lcd_display.line_3_measurement)
                self.setup_lcd_line(
                    each_lcd_display.unique_id, 4,
                    each_lcd_display.line_4_id,
                    each_lcd_display.line_4_measurement)

            if self.lcd_y_lines == 8:
                self.setup_lcd_line(
                    each_lcd_display.unique_id, 5,
                    each_lcd_display.line_5_id,
                    each_lcd_display.line_5_measurement)
                self.setup_lcd_line(
                    each_lcd_display.unique_id, 6,
                    each_lcd_display.line_6_id,
                    each_lcd_display.line_6_measurement)
                self.setup_lcd_line(
                    each_lcd_display.unique_id, 7,
                    each_lcd_display.line_7_id,
                    each_lcd_display.line_7_measurement)
                self.setup_lcd_line(
                    each_lcd_display.unique_id, 8,
                    each_lcd_display.line_8_id,
                    each_lcd_display.line_8_measurement)

        if self.lcd_type in ['16x2_generic',
                             '20x4_generic']:
            from farm.devices.lcd_generic import LCD_Generic
            self.lcd_out = LCD_Generic(lcd_dev)
            self.lcd_init()
        elif self.lcd_type in ['16x2_grove_lcd_rgb']:
            from farm.devices.lcd_grove_lcd_rgb import LCD_Grove_LCD_RGB
            self.lcd_out = LCD_Grove_LCD_RGB(lcd_dev)
            self.lcd_init()
        elif self.lcd_type in ['128x32_pioled',
                               '128x64_pioled']:
            from farm.devices.lcd_pioled import LCD_Pioled
            self.lcd_out = LCD_Pioled(lcd_dev)
            self.lcd_init()
        elif self.lcd_type in ['128x32_pioled_circuit_python',
                               '128x64_pioled_circuit_python']:
            from farm.devices.lcd_pioled_circuitpython import PiOLEDCircuitpython
            self.lcd_out = PiOLEDCircuitpython(lcd_dev)
            self.lcd_init()
        else:
            self.logger.error("Unknown LCD type: {}".format(self.lcd_type))

        if self.lcd_initialized:
            line_1 = 'Farm {}'.format(FARM_VERSION)
            line_2 = 'Start {}'.format(self.lcd_name)
            self.lcd_out.lcd_write_lines(line_1, line_2, '', '')

    def lcd_init(self):
        self.lcd_out.lcd_init()
        self.lcd_initialized = True
        self.lcd_is_on = True

    def get_measurement(self, display_id, i):
        try:
            if self.lcd_line[display_id][i]['measure'] == 'TEXT':
                # Display custom, user-entered text
                self.lcd_line[display_id][i]['name'] = ''
                self.lcd_line[display_id][i]['unit'] = ''
                if len(self.lcd_text[display_id][i]) > self.lcd_x_characters:
                    self.lcd_line[display_id][i]['measure_val'] = self.lcd_text[display_id][i][:self.lcd_x_characters]
                else:
                    self.lcd_line[display_id][i]['measure_val'] = self.lcd_text[display_id][i]
                return True
            elif self.lcd_line[display_id][i]['measure'] == 'BLANK':
                # Display an empty line
                self.lcd_line[display_id][i]['name'] = ''
                self.lcd_line[display_id][i]['unit'] = ''
                self.lcd_line[display_id][i]['measure_val'] = ''
                return True
            elif self.lcd_line[display_id][i]['measure'] == 'IP':
                # Display the device's IP address
                str_ip_cmd = "ip addr | grep 'state UP' -A2 | tail -n1 | awk '{print $2}' | cut -f1  -d'/'"
                ip_out, _, _ = cmd_output(str_ip_cmd)
                self.lcd_line[display_id][i]['name'] = ''
                self.lcd_line[display_id][i]['unit'] = ''
                self.lcd_line[display_id][i]['measure_val'] = ip_out.rstrip().decode("utf-8")
                return True
            elif self.lcd_line[display_id][i]['measure'] == 'output_state':
                # Display the GPIO state
                # TODO: Currently not a selectable option in the LCD Line dropdown
                self.lcd_line[display_id][i]['measure_val'] = self.output_state(
                    self.lcd_line[display_id][i]['id'])
                return True
            else:
                if self.lcd_line[display_id][i]['measure'] == 'time':
                    # Display the time of the last measurement
                    last_measurement = read_last_influxdb(
                        self.lcd_line[display_id][i]['id'],
                        '/.*/',
                        None,
                        duration_sec=self.lcd_max_age[display_id][i])
                else:
                    last_measurement = read_last_influxdb(
                        self.lcd_line[display_id][i]['id'],
                        self.lcd_line[display_id][i]['unit'],
                        self.lcd_line[display_id][i]['channel'],
                        measure=self.lcd_line[display_id][i]['measure'],
                        duration_sec=self.lcd_max_age[display_id][i])

                if last_measurement:
                    self.lcd_line[display_id][i]['time'] = last_measurement[0]
                    if self.lcd_decimal_places[display_id][i] == 0:
                        self.lcd_line[display_id][i]['measure_val'] = int(last_measurement[1])
                    else:
                        self.lcd_line[display_id][i]['measure_val'] = round(
                            last_measurement[1], self.lcd_decimal_places[display_id][i])
                    utc_dt = datetime.datetime.strptime(
                        self.lcd_line[display_id][i]['time'].split(".")[0],
                        '%Y-%m-%dT%H:%M:%S')
                    utc_timestamp = calendar.timegm(utc_dt.timetuple())
                    local_timestamp = str(datetime.datetime.fromtimestamp(utc_timestamp))
                    self.logger.debug("Latest {}: {} @ {}".format(
                        self.lcd_line[display_id][i]['measure'],
                        self.lcd_line[display_id][i]['measure_val'], local_timestamp))
                    return True

                else:
                    self.lcd_line[display_id][i]['time'] = None
                    self.lcd_line[display_id][i]['measure_val'] = None
                    self.logger.debug("No data returned from influxdb")
            return False
        except Exception as except_msg:
            self.logger.debug(
                "Failed to read measurement from the influxdb database: "
                "{err}".format(err=except_msg))
            return False

    def create_lcd_line(self, last_measurement_success, display_id, i):
        try:
            if last_measurement_success:
                if self.lcd_line[display_id][i]['unit'] in self.dict_units:
                    unit_display = self.dict_units[self.lcd_line[display_id][i]['unit']]['unit']
                else:
                    unit_display = ''

                if unit_display:
                    unit_length = len(unit_display.replace('°', u''))
                else:
                    unit_length = 0

                # Produce the line that will be displayed on the LCD
                if self.lcd_line[display_id][i]['measure'] == 'time':
                    # Convert UTC timestamp to local timezone
                    utc_dt = datetime.datetime.strptime(
                        self.lcd_line[display_id][i]['time'].split(".")[0],
                        '%Y-%m-%dT%H:%M:%S')
                    utc_timestamp = calendar.timegm(utc_dt.timetuple())
                    self.lcd_string_line[display_id][i] = str(
                        datetime.datetime.fromtimestamp(utc_timestamp))
                elif unit_length > 0:
                    value_length = len(str(
                        self.lcd_line[display_id][i]['measure_val']))
                    name_length = self.lcd_x_characters - value_length - unit_length - 2
                    name_cropped = self.lcd_line[display_id][i]['name'].ljust(name_length)[:name_length]
                    self.lcd_string_line[display_id][i] = '{name} {value} {unit}'.format(
                        name=name_cropped,
                        value=self.lcd_line[display_id][i]['measure_val'],
                        unit=unit_display.replace('°', u''))
                else:
                    value_length = len(str(
                        self.lcd_line[display_id][i]['measure_val']))
                    name_length = self.lcd_x_characters - value_length - 1
                    name_cropped = self.lcd_line[display_id][i]['name'][:name_length]
                    if name_cropped != '':
                        line_str = '{name} {value}'.format(
                            name=name_cropped,
                            value=self.lcd_line[display_id][i]['measure_val'])
                    else:
                        line_str = self.lcd_line[display_id][i]['measure_val']
                    self.lcd_string_line[display_id][i] = line_str

            else:
                error = 'NO DATA'
                name_length = self.lcd_x_characters - len(error) - 1
                name_cropped = self.lcd_line[display_id][i]['name'].ljust(name_length)[:name_length]
                self.lcd_string_line[display_id][i] = '{name} {error}'.format(
                    name=name_cropped, error=error)

        except Exception as except_msg:
            self.logger.exception("Error: {err}".format(err=except_msg))

    def output_lcds(self):
        """ Output to all LCDs all at once """
        line_1 = ''
        line_2 = ''
        line_3 = ''
        line_4 = ''
        line_5 = ''
        line_6 = ''
        line_7 = ''
        line_8 = ''

        self.lcd_out.lcd_init()
        display_id = self.display_sets[self.display_set_count]

        if 1 in self.lcd_string_line[display_id] and self.lcd_string_line[display_id][1]:
            line_1 = self.lcd_string_line[display_id][1]
        if 2 in self.lcd_string_line[display_id] and self.lcd_string_line[display_id][2]:
            line_2 = self.lcd_string_line[display_id][2]
        if 3 in self.lcd_string_line[display_id] and self.lcd_string_line[display_id][3]:
            line_3 = self.lcd_string_line[display_id][3]
        if 4 in self.lcd_string_line[display_id] and self.lcd_string_line[display_id][4]:
            line_4 = self.lcd_string_line[display_id][4]
        if 5 in self.lcd_string_line[display_id] and self.lcd_string_line[display_id][5]:
            line_5 = self.lcd_string_line[display_id][5]
        if 6 in self.lcd_string_line[display_id] and self.lcd_string_line[display_id][6]:
            line_6 = self.lcd_string_line[display_id][6]
        if 7 in self.lcd_string_line[display_id] and self.lcd_string_line[display_id][7]:
            line_7 = self.lcd_string_line[display_id][7]
        if 8 in self.lcd_string_line[display_id] and self.lcd_string_line[display_id][8]:
            line_8 = self.lcd_string_line[display_id][8]

        if self.lcd_type in ['128x32_pioled',
                             '128x32_pioled_circuit_python',
                             '16x2_generic',
                             '20x4_generic',
                             '16x2_grove_lcd_rgb']:
            self.lcd_out.lcd_write_lines(line_1, line_2, line_3, line_4)

        elif self.lcd_type in ['128x64_pioled', '128x64_pioled_circuit_python']:
            self.lcd_out.lcd_write_lines(line_1, line_2, line_3, line_4,
                                         message_line_5=line_5,
                                         message_line_6=line_6,
                                         message_line_7=line_7,
                                         message_line_8=line_8)

    def output_state(self, output_id):
        output = db_retrieve_table_daemon(Output, unique_id=output_id)
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            if GPIO.input(output.pin) == output.on_state:
                gpio_state = 'On'
            else:
                gpio_state = 'Off'
            return gpio_state
        except:
            self.logger.error(
                "RPi.GPIO and Raspberry Pi required for this action")

    def setup_lcd_line(self, display_id, line, device_id, measurement_id):
        if measurement_id == 'output':
            device_measurement = db_retrieve_table_daemon(
                Output, unique_id=device_id)
        elif measurement_id in ['BLANK', 'IP', 'TEXT']:
            device_measurement = None
        else:
            device_measurement = db_retrieve_table_daemon(
                DeviceMeasurements, unique_id=measurement_id)

        if device_measurement:
            conversion = db_retrieve_table_daemon(
                Conversion, unique_id=device_measurement.conversion_id)
            channel, unit, measurement = return_measurement_info(
                device_measurement, conversion)
        else:
            channel = None
            unit = None
            measurement = None

        self.lcd_line[display_id][line]['setup'] = False
        self.lcd_line[display_id][line]['id'] = device_id
        self.lcd_line[display_id][line]['name'] = None
        self.lcd_line[display_id][line]['unit'] = unit
        self.lcd_line[display_id][line]['measure'] = measurement
        self.lcd_line[display_id][line]['channel'] = channel

        if 'time' in measurement_id:
            self.lcd_line[display_id][line]['measure'] = 'time'
        elif measurement_id in ['BLANK', 'IP', 'TEXT']:
            self.lcd_line[display_id][line]['measure'] = measurement_id
            self.lcd_line[display_id][line]['name'] = ''

        if not device_id:
            return

        if unit in self.dict_units:
            self.lcd_line[display_id][line]['unit'] = unit
        else:
            self.lcd_line[display_id][line]['unit'] = ''

        # Determine the name
        controllers = [
            Output,
            PID,
            Input,
            Math
        ]
        for each_controller in controllers:
            controller_found = db_retrieve_table_daemon(each_controller, unique_id=device_id)
            if controller_found:
                self.lcd_line[display_id][line]['name'] = controller_found.name

        if (self.lcd_line[display_id][line]['measure'] in ['BLANK', 'IP', 'TEXT', 'time'] or
                None not in [self.lcd_line[display_id][line]['name'],
                             self.lcd_line[display_id][line]['unit']]):
            self.lcd_line[display_id][line]['setup'] = True

    def lcd_backlight(self, state):
        """ Turn the backlight on or off """
        if state:
            self.lcd_out.lcd_backlight(state)
            self.lcd_is_on = True
            self.timer = time.time() - 1  # Induce LCD to update after turning backlight on
        else:
            self.lcd_is_on = False  # Instruct LCD backlight to turn off

    def lcd_backlight_color(self, color):
        """ Set backlight color """
        self.lcd_out.lcd_backlight_color(color)
        self.timer = time.time() - 1  # Induce LCD to update after turning backlight on

    def lcd_flash(self, state):
        """ Enable the LCD to begin or end flashing """
        if state:
            self.flash_lcd_on = True
            return 1, "LCD {} Flashing Turned On".format(self.unique_id)
        else:
            self.flash_lcd_on = False
            self.lcd_backlight(True)
            return 1, "LCD {} Reset".format(self.unique_id)
