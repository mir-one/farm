# coding=utf-8
#
# pwm_pca9685.py - Output for PCA9685
#
import copy

from flask_babel import lazy_gettext
from sqlalchemy import and_

from farm.config_translations import TRANSLATIONS
from farm.databases.models import DeviceMeasurements
from farm.databases.models import OutputChannel
from farm.outputs.base_output import AbstractOutput
from farm.utils.constraints_pass import constraints_pass_percent
from farm.utils.database import db_retrieve_table_daemon
from farm.utils.influx import add_measurements_influxdb
from farm.utils.influx import read_last_influxdb
from farm.utils.system_pi import return_measurement_info


def constraints_pass_hertz(mod_dev, value):
    """
    Check if the user input is acceptable
    :param mod_dev: SQL object with user-saved Input options
    :param value: float or int
    :return: tuple: (bool, list of strings)
    """
    errors = []
    all_passed = True
    if 1600 < value < 40:
        all_passed = False
        errors.append("Must be a value between 40 and 1600")
    return all_passed, errors, mod_dev


# Measurements
measurements_dict = {
    0: {
        'measurement': 'duty_cycle',
        'unit': 'percent'
    },
    1: {
        'measurement': 'duty_cycle',
        'unit': 'percent'
    },
    2: {
        'measurement': 'duty_cycle',
        'unit': 'percent'
    },
    3: {
        'measurement': 'duty_cycle',
        'unit': 'percent'
    },
    4: {
        'measurement': 'duty_cycle',
        'unit': 'percent'
    },
    5: {
        'measurement': 'duty_cycle',
        'unit': 'percent'
    },
    6: {
        'measurement': 'duty_cycle',
        'unit': 'percent'
    },
    7: {
        'measurement': 'duty_cycle',
        'unit': 'percent'
    },
    8: {
        'measurement': 'duty_cycle',
        'unit': 'percent'
    },
    9: {
        'measurement': 'duty_cycle',
        'unit': 'percent'
    },
    10: {
        'measurement': 'duty_cycle',
        'unit': 'percent'
    },
    11: {
        'measurement': 'duty_cycle',
        'unit': 'percent'
    },
    12: {
        'measurement': 'duty_cycle',
        'unit': 'percent'
    },
    13: {
        'measurement': 'duty_cycle',
        'unit': 'percent'
    },
    14: {
        'measurement': 'duty_cycle',
        'unit': 'percent'
    },
    15: {
        'measurement': 'duty_cycle',
        'unit': 'percent'
    }
}

channels_dict = {
    0: {
        'name': 'Channel 0',
        'types': ['pwm'],
        'measurements': [0]
    },
    1: {
        'name': 'Channel 1',
        'types': ['pwm'],
        'measurements': [1]
    },
    2: {
        'name': 'Channel 2',
        'types': ['pwm'],
        'measurements': [2]
    },
    3: {
        'name': 'Channel 3',
        'types': ['pwm'],
        'measurements': [3]
    },
    4: {
        'name': 'Channel 4',
        'types': ['pwm'],
        'measurements': [4]
    },
    5: {
        'name': 'Channel 5',
        'types': ['pwm'],
        'measurements': [5]
    },
    6: {
        'name': 'Channel 6',
        'types': ['pwm'],
        'measurements': [6]
    },
    7: {
        'name': 'Channel 7',
        'types': ['pwm'],
        'measurements': [7]
    },
    8: {
        'name': 'Channel 8',
        'types': ['pwm'],
        'measurements': [8]
    },
    9: {
        'name': 'Channel 9',
        'types': ['pwm'],
        'measurements': [9]
    },
    10: {
        'name': 'Channel 10',
        'types': ['pwm'],
        'measurements': [10]
    },
    11: {
        'name': 'Channel 11',
        'types': ['pwm'],
        'measurements': [11]
    },
    12: {
        'name': 'Channel 12',
        'types': ['pwm'],
        'measurements': [12]
    },
    13: {
        'name': 'Channel 13',
        'types': ['pwm'],
        'measurements': [13]
    },
    14: {
        'name': 'Channel 14',
        'types': ['pwm'],
        'measurements': [14]
    },
    15: {
        'name': 'Channel 15',
        'types': ['pwm'],
        'measurements': [15]
    }
}

# Output information
OUTPUT_INFORMATION = {
    'output_name_unique': 'pwm_pca9685',
    'output_name': "{}: PCA9685 (16 channels): {}".format(
        lazy_gettext("LED Controller"), lazy_gettext('PWM')),
    'output_manufacturer': 'NXP Semiconductors',
    'output_library': 'adafruit-pca9685',
    'measurements_dict': measurements_dict,
    'channels_dict': channels_dict,
    'output_types': ['pwm'],

    'url_manufacturer': 'https://www.nxp.com/products/power-management/lighting-driver-and-controller-ics/ic-led-controllers/16-channel-12-bit-pwm-fm-plus-ic-bus-led-controller:PCA9685',
    'url_datasheet': 'https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf',
    'url_product_purchase': 'https://www.adafruit.com/product/815',

    'message': 'The PCA9685 can output a PWM signal to 16 channels at a frequency between 40 and 1600 Hz.',

    'options_enabled': [
        'i2c_location',
        'button_send_duty_cycle'
    ],
    'options_disabled': ['interface'],

    'dependencies_module': [
        ('pip-pypi', 'Adafruit_PCA9685', 'adafruit-pca9685==1.0.1')
    ],

    'interfaces': ['I2C'],
    'i2c_location': [
        '0x40', '0x41', '0x42', '0x43', '0x44', '0x45', '0x46', '0x47',
        '0x48', '0x49', '0x4a', '0x4b', '0x4c', '0x4d', '0x4e', '0x4f'
    ],
    'i2c_address_editable': False,
    'i2c_address_default': '0x40',

    'custom_options': [
        {
            'id': 'pwm_hertz',
            'type': 'integer',
            'default_value': 1600,
            'required': True,
            'constraints_pass': constraints_pass_hertz,
            'name': lazy_gettext('Frequency (Hertz)'),
            'phrase': 'The Herts to output the PWM signal (40 - 1600)'
        },
    ],

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
            'id': 'state_startup',
            'type': 'select',
            'default_value': 0,
            'options_select': [
                (0, 'Off'),
                ('set_duty_cycle', 'User Set Value'),
                ('last_duty_cycle', 'Last Known Value')
            ],
            'name': lazy_gettext('Startup State'),
            'phrase': 'Set the state when Farm starts'
        },
        {
            'id': 'startup_value',
            'type': 'float',
            'default_value': 0.0,
            'required': True,
            'constraints_pass': constraints_pass_percent,
            'name': lazy_gettext('Startup Value'),
            'phrase': 'The value when Farm starts'
        },
        {
            'id': 'state_shutdown',
            'type': 'select',
            'default_value': 0,
            'options_select': [
                (-1, 'Do Nothing'),
                (0, 'Off'),
                ('set_duty_cycle', 'User Set Value')
            ],
            'name': lazy_gettext('Shutdown State'),
            'phrase': 'Set the state when Farm shuts down'
        },
        {
            'id': 'shutdown_value',
            'type': 'float',
            'default_value': 0.0,
            'required': True,
            'constraints_pass': constraints_pass_percent,
            'name': lazy_gettext('Shutdown Value'),
            'phrase': 'The value when Farm shuts down'
        },
        {
            'id': 'pwm_invert_signal',
            'type': 'bool',
            'default_value': False,
            'name': lazy_gettext('Invert Signal'),
            'phrase': 'Invert the PWM signal'
        },
        {
            'id': 'trigger_functions_startup',
            'type': 'bool',
            'default_value': False,
            'name': lazy_gettext('Trigger Functions at Startup'),
            'phrase': 'Whether to trigger functions when the output switches at startup'
        },
        {
            'id': 'amps',
            'type': 'float',
            'default_value': 0.0,
            'required': True,
            'name': '{} ({})'.format(lazy_gettext('Current'), lazy_gettext('Amps')),
            'phrase': 'The current draw of the device being controlled'
        }
    ]
}


class OutputModule(AbstractOutput):
    """
    An output support class that operates an output
    """
    def __init__(self, output, testing=False):
        super(OutputModule, self).__init__(output, testing=testing, name=__name__)

        self.pwm_duty_cycles = {}
        for i in range(16):
            self.pwm_duty_cycles[i] = 0
        self.pwm_output = None
        self.pwm_hertz = None

        self.setup_custom_options(
            OUTPUT_INFORMATION['custom_options'], output)

        output_channels = db_retrieve_table_daemon(
            OutputChannel).filter(OutputChannel.output_id == self.output.unique_id).all()
        self.options_channels = self.setup_custom_channel_options_json(
            OUTPUT_INFORMATION['custom_channel_options'], output_channels)

    def setup_output(self):
        import Adafruit_PCA9685

        self.setup_output_variables(OUTPUT_INFORMATION)

        error = []
        if self.pwm_hertz < 40:
            error.append("PWM Hertz must be a value between 40 and 1600")
        if error:
            for each_error in error:
                self.logger.error(each_error)
            return

        try:
            self.pwm_output = Adafruit_PCA9685.PCA9685(
                address=int(str(self.output.i2c_location), 16),
                busnum=self.output.i2c_bus)
 
            self.pwm_output.set_pwm_freq(self.pwm_hertz)

            self.output_setup = True
            self.logger.debug("Output setup on bus {} at {}".format(
                self.output.i2c_bus, self.output.i2c_location))

            for i in range(16):
                if self.options_channels['state_startup'][i] == 0:
                    self.logger.debug("Startup state channel {ch}: off".format(ch=i))
                    self.output_switch('off', output_channel=i)
                elif self.options_channels['state_startup'][i] == 'set_duty_cycle':
                    self.logger.debug("Startup state channel {ch}: on ({dc:.2f} %)".format(
                        ch=i, dc=self.options_channels['startup_value'][i]))
                    self.output_switch('on', output_channel=i, amount=self.options_channels['startup_value'][i])
                elif self.options_channels['state_startup'][i] == 'last_duty_cycle':
                    self.logger.debug("Startup state channel {ch}: last".format(ch=i))
                    device_measurement = db_retrieve_table_daemon(DeviceMeasurements).filter(
                        and_(DeviceMeasurements.device_id == self.unique_id,
                             DeviceMeasurements.channel == i)).first()

                    last_measurement = None
                    if device_measurement:
                        channel, unit, measurement = return_measurement_info(device_measurement, None)
                        last_measurement = read_last_influxdb(
                            self.unique_id,
                            unit,
                            channel,
                            measure=measurement,
                            duration_sec=None)

                    if last_measurement:
                        self.logger.debug("Setting channel {ch} startup duty cycle to last known value of {dc} %".format(
                            ch=i, dc=last_measurement[1]))
                        self.output_switch('on', amount=last_measurement[1])
                    else:
                        self.logger.error(
                            "Output channel {} instructed at startup to be set to "
                            "the last known duty cycle, but a last known "
                            "duty cycle could not be found in the measurement "
                            "database".format(i))
                else:
                    self.logger.debug("Startup state channel {ch}: no change".format(ch=i))
        except Exception as except_msg:
            self.logger.exception("Output was unable to be setup: {err}".format(err=except_msg))

    def output_switch(self, state, output_type=None, amount=0, output_channel=None):
        measure_dict = copy.deepcopy(measurements_dict)

        output_amount = 0

        if state == 'on':
            if self.options_channels['pwm_invert_signal'][output_channel]:
                output_amount = 100.0 - abs(amount)
            else:
                output_amount = abs(amount)
        elif state == 'off':
            if self.options_channels['pwm_invert_signal'][output_channel]:
                output_amount = 100
            else:
                output_amount = 0

        off_at_tick = round(output_amount * 4095. / 100.)
        self.pwm_output.set_pwm(output_channel, 0, off_at_tick)

        self.pwm_duty_cycles[output_channel] = amount
        measure_dict[output_channel]['value'] = amount
        add_measurements_influxdb(self.unique_id, measure_dict)

        self.logger.debug(
            "Duty cycle of channel {ch} set to {dc:.2f} % (switched off for {off_at_tick:d} of 4095 ticks)".format(
                ch=output_channel, dc=amount, off_at_tick=off_at_tick))
        return "success"

    def is_on(self, output_channel=None):
        if self.is_setup():
            duty_cycle = self.pwm_duty_cycles[output_channel]
            if duty_cycle:
                return duty_cycle

            return False

    def is_setup(self):
        return self.output_setup

    def stop_output(self):
        """ Called when Output is stopped """
        if self.is_setup():
            for i in range(16):
                if self.options_channels['state_shutdown'][i] == 0:
                    self.output_switch('off')
                elif self.options_channels['state_shutdown'][i] == 'set_duty_cycle':
                    self.output_switch('on', amount=self.options_channels['shutdown_value'][i])
        self.running = False
