# coding=utf-8
#
# dc_motor_l298n.py - Output for L298N DC motor controller
#
import threading
import time

import copy
from flask_babel import lazy_gettext

from farm.config_translations import TRANSLATIONS
from farm.databases.models import OutputChannel
from farm.outputs.base_output import AbstractOutput
from farm.utils.constraints_pass import constraints_pass_percent
from farm.utils.constraints_pass import constraints_pass_positive_or_zero_value
from farm.utils.constraints_pass import constraints_pass_positive_value
from farm.utils.database import db_retrieve_table_daemon
from farm.utils.influx import add_measurements_influxdb

# Measurements
measurements_dict = {
    0: {
        'measurement': 'duration_time',
        'unit': 's'
    },
    1: {
        'measurement': 'volume',
        'unit': 'ml'
    },
    2: {
        'measurement': 'duration_time',
        'unit': 's'
    },
    3: {
        'measurement': 'volume',
        'unit': 'ml'
    }
}

channels_dict = {
    0: {
        'name': 'Motor A',
        'types': ['volume', 'on_off'],
        'measurements': [0, 1]
    },
    1: {
        'name': 'Motor B',
        'types': ['volume', 'on_off'],
        'measurements': [2, 3]
    }
}

# Output information
OUTPUT_INFORMATION = {
    'output_name_unique': 'DC_MOTOR_L298N',
    'output_name': "{}: L298N".format(lazy_gettext("DC Motor Controller")),
    'output_manufacturer': 'STMicroelectronics',
    'output_library': 'RPi.GPIO',
    'measurements_dict': measurements_dict,
    'channels_dict': channels_dict,
    'output_types': ['volume', 'on_off'],

    'url_additional': 'https://www.electronicshub.org/raspberry-pi-l298n-interface-tutorial-control-dc-motor-l298n-raspberry-pi/',

    'message': 'The L298N can control 2 DC motors. If these motors control peristaltic pumps, set the Flow Rate '
               'and the output can can be instructed to dispense volumes accurately in addition to being turned on for durations.',

    'options_enabled': [
        'button_on',
        'button_send_duration',
        'button_send_volume'
    ],
    'options_disabled': ['interface'],

    'dependencies_module': [
        ('pip-pypi', 'RPi.GPIO', 'RPi.GPIO==0.7.0')
    ],

    'interfaces': ['GPIO'],

    'custom_channel_options': [
        {
            'id': 'name',
            'type': 'text',
            'default_value': '',
            'required': False,
            'name': TRANSLATIONS['name']['title'],
            'phrase': TRANSLATIONS['name']['phrase']
        },
        {
            'id': 'pin_1',
            'type': 'integer',
            'default_value': None,
            'required': False,
            'constraints_pass': constraints_pass_positive_or_zero_value,
            'name': 'Input Pin 1',
            'phrase': 'The Input Pin 1 of the controller (BCM numbering)'
        },
        {
            'id': 'pin_2',
            'type': 'integer',
            'default_value': None,
            'required': False,
            'constraints_pass': constraints_pass_positive_or_zero_value,
            'name': 'Input Pin 2',
            'phrase': 'The Input Pin 2 of the controller (BCM numbering)'
        },
        {
            'id': 'use_enable',
            'type': 'bool',
            'default_value': True,
            'name': 'Use Enable Pin',
            'phrase': 'Enable the use of the Enable Pin'
        },
        {
            'id': 'pin_enable',
            'type': 'integer',
            'default_value': None,
            'required': False,
            'constraints_pass': constraints_pass_positive_or_zero_value,
            'name': 'Enable Pin',
            'phrase': 'The Enable pin of the controller (BCM numbering)'
        },
        {
            'id': 'duty_cycle',
            'type': 'integer',
            'default_value': 50,
            'constraints_pass': constraints_pass_percent,
            'name': 'Enable Pin Duty Cycle',
            'phrase': 'The duty cycle to apply to the Enable Pin (percent, 1 - 100)'
        },
        {
            'id': 'direction',
            'type': 'select',
            'default_value': 1,
            'options_select': [
                (1, 'Forward'),
                (0, 'Backward')
            ],
            'name': lazy_gettext('Direction'),
            'phrase': 'The direction to turn the motor'
        },
        {
            'id': 'flow_rate_ml_min',
            'type': 'float',
            'default_value': 150.0,
            'constraints_pass': constraints_pass_positive_value,
            'name': 'Volume Rate (ml/min)',
            'phrase': 'If a pump, the measured flow rate (ml/min) at the set Duty Cycle'
        },
    ]
}


class OutputModule(AbstractOutput):
    """
    An output support class that operates an output
    """
    def __init__(self, output, testing=False):
        super(OutputModule, self).__init__(output, testing=testing, name=__name__)

        self.driver = {}
        self.currently_dispensing = False
        self.output_setup = False
        self.channel_setup = {}
        self.gpio = None

        output_channels = db_retrieve_table_daemon(
            OutputChannel).filter(OutputChannel.output_id == self.output.unique_id).all()
        self.options_channels = self.setup_custom_channel_options_json(
            OUTPUT_INFORMATION['custom_channel_options'], output_channels)

    def setup_output(self):
        self.setup_output_variables(OUTPUT_INFORMATION)

        import RPi.GPIO as GPIO
        self.gpio = GPIO

        for channel in channels_dict:
            if (not self.options_channels['pin_1'][channel] or
                    not self.options_channels['pin_2'][channel] or
                    (self.options_channels['use_enable'][channel] and
                     not self.options_channels['pin_enable'][channel]) or
                    not self.options_channels['duty_cycle'][channel]):
                self.logger.error("Cannot initialize Output channel {} until all options are set. "
                                  "Check your configuration.".format(channel))
                self.channel_setup[channel] = False
            else:
                self.gpio.setmode(self.gpio.BCM)
                self.gpio.setup(self.options_channels['pin_1'][channel], self.gpio.OUT)
                self.gpio.setup(self.options_channels['pin_2'][channel], self.gpio.OUT)
                self.stop(channel)
                if self.options_channels['use_enable'][channel]:
                    self.gpio.setup(self.options_channels['pin_enable'][channel], self.gpio.OUT)
                    self.driver[channel] = self.gpio.PWM(self.options_channels['pin_enable'][channel], 1000)
                    self.driver[channel].start(self.options_channels['duty_cycle'][channel])
                self.channel_setup[channel] = True
                self.output_setup = True
                self.output_states[channel] = False

    def output_switch(self, state, output_type=None, amount=None, output_channel=None):
        if not self.running:
            msg = "Output is not running, cannot turn it on or off."
            self.logger.error(msg)
            return msg

        if not self.channel_setup[output_channel]:
            msg = "Output channel {} not set up, cannot turn it on or off.".format(output_channel)
            self.logger.error(msg)
            return msg

        if amount is not None and amount < 0:
            self.logger.error("Amount cannot be less than 0")
            return

        if state == 'on' and output_type == 'vol' and amount:
            if self.currently_dispensing:
                self.logger.debug("DC motor instructed to dispense volume while it's already dispensing a volume. "
                                  "Overriding current dispense with new instruction.")

            total_dispense_seconds = amount / self.options_channels['flow_rate_ml_min'][0] * 60
            msg = "Turning pump on for {sec:.1f} seconds to dispense {ml:.1f} ml (at {rate:.1f} ml/min).".format(
                sec=total_dispense_seconds,
                ml=amount,
                rate=self.options_channels['flow_rate_ml_min'][0])
            self.logger.debug(msg)

            write_db = threading.Thread(
                target=self.dispense_volume,
                args=(output_channel, amount, total_dispense_seconds,))
            write_db.start()
            return
        if state == 'on' and output_type == 'sec':
            if self.currently_dispensing:
                self.logger.debug(
                    "DC motor instructed to turn on while it's already dispensing a volume. "
                    "Overriding current dispense with new instruction.")
            self.run(output_channel)
        elif state == 'off':
            if self.currently_dispensing:
                self.currently_dispensing = False
            self.stop(output_channel)

    def dispense_volume(self, channel, amount, total_dispense_seconds):
        """ Dispense at flow rate """
        self.currently_dispensing = True
        self.logger.debug("Output turned on")
        self.run(channel)
        timer_dispense = time.time() + total_dispense_seconds

        while time.time() < timer_dispense and self.currently_dispensing:
            time.sleep(0.01)

        self.stop(channel)
        self.currently_dispensing = False
        self.logger.debug("Output turned off")
        self.record_dispersal(channel, amount, total_dispense_seconds)

    def record_dispersal(self, channel, amount, total_on_seconds):
        measure_dict = copy.deepcopy(measurements_dict)
        measure = channels_dict[channel]['measurements']
        measure_dict[measure[0]]['value'] = total_on_seconds
        measure_dict[measure[1]]['value'] = amount
        add_measurements_influxdb(self.unique_id, measure_dict)

    def run(self, channel):
        if self.options_channels['direction'][channel]:
            self.gpio.output(self.options_channels['pin_1'][channel], self.gpio.HIGH)
            self.gpio.output(self.options_channels['pin_2'][channel], self.gpio.LOW)
            self.output_states[channel] = True
        else:
            self.gpio.output(self.options_channels['pin_1'][channel], self.gpio.LOW)
            self.gpio.output(self.options_channels['pin_2'][channel], self.gpio.HIGH)
            self.output_states[channel] = True

    def stop(self, channel):
        self.gpio.output(self.options_channels['pin_1'][channel], self.gpio.LOW)
        self.gpio.output(self.options_channels['pin_2'][channel], self.gpio.LOW)
        self.output_states[channel] = False

    def is_on(self, output_channel=None):
        if self.is_setup(channel=output_channel):
            return self.output_states[output_channel]

    def is_setup(self, channel=None):
        if channel:
            return self.channel_setup[channel]
        if True in self.channel_setup.values():
            return True

    def stop_output(self):
        """ Called when Output is stopped """
        self.running = False
        for channel in channels_dict:
            if self.is_setup(channel=channel):
                self.stop(channel)
