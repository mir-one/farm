# coding=utf-8
#
# on_off_gpio.py - Output for simple GPIO switching
#
from flask_babel import lazy_gettext

from farm.databases.models import OutputChannel
from farm.outputs.base_output import AbstractOutput
from farm.utils.constraints_pass import constraints_pass_positive_or_zero_value
from farm.utils.database import db_retrieve_table_daemon

# Measurements
measurements_dict = {
    0: {
        'measurement': 'duration_time',
        'unit': 's'
    }
}

channels_dict = {
    0: {
        'types': ['on_off'],
        'measurements': [0]
    }
}

# Output information
OUTPUT_INFORMATION = {
    'output_name_unique': 'wired',
    'output_name': "GPIO: {}".format(lazy_gettext('On/Off')),
    'output_library': 'RPi.GPIO',
    'measurements_dict': measurements_dict,
    'channels_dict': channels_dict,
    'output_types': ['on_off'],

    'message': 'The specified GPIO pin will be set HIGH (3.3 volts) or LOW (0 volts) when turned '
               'on or off, depending on the On State option.',

    'options_enabled': [
        'button_on',
        'button_send_duration'
    ],
    'options_disabled': ['interface'],

    'dependencies_module': [
        ('pip-pypi', 'RPi.GPIO', 'RPi.GPIO==0.7.0')
    ],

    'interfaces': ['GPIO'],

    'custom_channel_options': [
        {
            'id': 'pin',
            'type': 'integer',
            'default_value': None,
            'required': False,
            'constraints_pass': constraints_pass_positive_or_zero_value,
            'name': lazy_gettext('GPIO Pin (BCM)'),
            'phrase': 'The pin to control the state of'
        },
        {
            'id': 'state_startup',
            'type': 'select',
            'default_value': 0,
            'options_select': [
                (0, 'Off'),
                (1, 'On')
            ],
            'name': lazy_gettext('Startup State'),
            'phrase': 'Set the state when Farm starts'
        },
        {
            'id': 'state_shutdown',
            'type': 'select',
            'default_value': 0,
            'options_select': [
                (0, 'Off'),
                (1, 'On')
            ],
            'name': lazy_gettext('Shutdown State'),
            'phrase': 'Set the state when Farm shuts down'
        },
        {
            'id': 'on_state',
            'type': 'select',
            'default_value': 1,
            'options_select': [
                (1, 'HIGH'),
                (0, 'LOW')
            ],
            'name': lazy_gettext('On State'),
            'phrase': 'The state of the GPIO that corresponds to an On state'
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

        self.GPIO = None

        output_channels = db_retrieve_table_daemon(
            OutputChannel).filter(OutputChannel.output_id == self.output.unique_id).all()
        self.options_channels = self.setup_custom_channel_options_json(
            OUTPUT_INFORMATION['custom_channel_options'], output_channels)

    def setup_output(self):
        import RPi.GPIO as GPIO

        self.GPIO = GPIO

        self.setup_output_variables(OUTPUT_INFORMATION)

        if self.options_channels['pin'][0] is None:
            self.logger.error("Pin must be set")
        else:

            try:
                if self.options_channels['state_startup'][0]:
                    startup_state = self.options_channels['on_state'][0]
                else:
                    startup_state = not self.options_channels['on_state'][0]

                self.GPIO.setmode(self.GPIO.BCM)
                self.GPIO.setwarnings(True)
                self.GPIO.setup(self.options_channels['pin'][0], self.GPIO.OUT)
                self.GPIO.output(self.options_channels['pin'][0], startup_state)
                self.output_setup = True

                if self.options_channels['trigger_functions_startup'][0]:
                    try:
                        self.check_triggers(self.unique_id, output_channel=0)
                    except Exception as err:
                        self.logger.error(
                            "Could not check Trigger for channel 0 of output {}: {}".format(
                                self.unique_id, err))

                startup = 'ON' if self.options_channels['state_startup'][0] else 'OFF'
                state = 'HIGH' if self.options_channels['on_state'][0] else 'LOW'
                self.logger.info(
                    "Output setup on pin {pin} and turned {startup} (ON={state})".format(
                        pin=self.options_channels['pin'][0], startup=startup, state=state))
            except Exception as except_msg:
                self.logger.exception(
                    "Output was unable to be setup on pin {pin} with trigger={trigger}: {err}".format(
                        pin=self.options_channels['pin'][0],
                        trigger=self.options_channels['on_state'][0],
                        err=except_msg))

    def output_switch(self, state, output_type=None, amount=None, output_channel=0):
        try:
            if state == 'on':
                self.GPIO.output(self.options_channels['pin'][output_channel],
                                 self.options_channels['on_state'][output_channel])
            elif state == 'off':
                self.GPIO.output(self.options_channels['pin'][output_channel],
                                 not self.options_channels['on_state'][output_channel])
            msg = "success"
        except Exception as e:
            msg = "State change error: {}".format(e)
            self.logger.exception(msg)
        return msg

    def is_on(self, output_channel=0):
        if self.is_setup():
            try:
                return self.options_channels['on_state'][output_channel] == self.GPIO.input(
                    self.options_channels['pin'][output_channel])
            except Exception as e:
                self.logger.error("Status check error: {}".format(e))

    def is_setup(self):
        return self.output_setup

    def stop_output(self):
        """ Called when Output is stopped """
        if self.is_setup():
            if self.options_channels['state_shutdown'][0] == 1:
                self.output_switch('on', output_channel=0)
            elif self.options_channels['state_shutdown'][0] == 0:
                self.output_switch('off', output_channel=0)
        self.running = False
