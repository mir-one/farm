# coding=utf-8
#
# pwm_shell.py - Output for executing linux commands with PWM
#
import copy

from flask_babel import lazy_gettext
from sqlalchemy import and_

from farm.databases.models import DeviceMeasurements
from farm.databases.models import OutputChannel
from farm.outputs.base_output import AbstractOutput
from farm.utils.database import db_retrieve_table_daemon
from farm.utils.influx import add_measurements_influxdb
from farm.utils.influx import read_last_influxdb
from farm.utils.system_pi import cmd_output
from farm.utils.system_pi import return_measurement_info

# Measurements
measurements_dict = {
    0: {
        'measurement': 'duty_cycle',
        'unit': 'percent'
    }
}

channels_dict = {
    0: {
        'types': ['pwm'],
        'measurements': [0]
    }
}

# Output information
OUTPUT_INFORMATION = {
    'output_name_unique': 'command_pwm',
    'output_name': "Shell Script: {}".format(lazy_gettext('PWM')),
    'output_library': 'subprocess.Popen',
    'measurements_dict': measurements_dict,
    'channels_dict': channels_dict,
    'output_types': ['pwm'],

    'message': 'Commands will be executed in the Linux shell by the specified user when the duty cycle '
               'is set for this output. The string "((duty_cycle))" in the command will be replaced with '
               'the duty cycle being set prior to execution.',

    'options_enabled': [
        'button_send_duty_cycle'
    ],
    'options_disabled': ['interface'],

    'interfaces': ['SHELL'],

    'custom_channel_options': [
        {
            'id': 'pwm_command',
            'type': 'text',
            'default_value': '/home/pi/script_pwm.sh ((duty_cycle))',
            'required': True,
            'col_width': 12,
            'name': lazy_gettext('Bash Command'),
            'phrase': lazy_gettext('Command to execute to set the PWM duty cycle (%)')
        },
        {
            'id': 'linux_command_user',
            'type': 'text',
            'default_value': 'farm',
            'name': lazy_gettext('User'),
            'phrase': lazy_gettext('The user to execute the command')
        },
        {
            'id': 'state_startup',
            'type': 'select',
            'default_value': '',
            'options_select': [
                (-1, 'Do Nothing'),
                (0, 'Off'),
                ('set_duty_cycle', 'User Set Value'),
                ('last_duty_cycle', 'Last Known Value')
            ],
            'name': lazy_gettext('Startup State'),
            'phrase': lazy_gettext('Set the state when Farm starts')
        },
        {
            'id': 'startup_value',
            'type': 'float',
            'default_value': 0.0,
            'required': True,
            'name': lazy_gettext('Startup Value'),
            'phrase': lazy_gettext('The value when Farm starts')
        },
        {
            'id': 'state_shutdown',
            'type': 'select',
            'default_value': '',
            'options_select': [
                (-1, 'Do Nothing'),
                (0, 'Off'),
                ('set_duty_cycle', 'User Set Value')
            ],
            'name': lazy_gettext('Shutdown State'),
            'phrase': lazy_gettext('Set the state when Farm shuts down')
        },
        {
            'id': 'shutdown_value',
            'type': 'float',
            'default_value': 0.0,
            'required': True,
            'name': lazy_gettext('Shutdown Value'),
            'phrase': lazy_gettext('The value when Farm shuts down')
        },
        {
            'id': 'pwm_invert_signal',
            'type': 'bool',
            'default_value': False,
            'name': lazy_gettext('Invert Signal'),
            'phrase': lazy_gettext('Invert the PWM signal')
        },
        {
            'id': 'trigger_functions_startup',
            'type': 'bool',
            'default_value': False,
            'name': lazy_gettext('Trigger Functions at Startup'),
            'phrase': lazy_gettext('Whether to trigger functions when the output switches at startup')
        },
        {
            'id': 'command_force',
            'type': 'bool',
            'default_value': False,
            'name': lazy_gettext('Force Command'),
            'phrase': lazy_gettext('Always send the commad if instructed, regardless of the current state')
        },
        {
            'id': 'amps',
            'type': 'float',
            'default_value': 0.0,
            'required': True,
            'name': lazy_gettext('Current (Amps)'),
            'phrase': lazy_gettext('The current draw of the device being controlled')
        }
    ]
}


class OutputModule(AbstractOutput):
    """
    An output support class that operates an output
    """
    def __init__(self, output, testing=False):
        super(OutputModule, self).__init__(output, testing=testing, name=__name__)

        output_channels = db_retrieve_table_daemon(
            OutputChannel).filter(OutputChannel.output_id == self.output.unique_id).all()
        self.options_channels = self.setup_custom_channel_options_json(
            OUTPUT_INFORMATION['custom_channel_options'], output_channels)

    def setup_output(self):
        self.setup_output_variables(OUTPUT_INFORMATION)

        if self.options_channels['pwm_command'][0]:
            self.output_setup = True

            if self.options_channels['state_startup'][0] == 0:
                self.output_switch('off')
            elif self.options_channels['state_startup'][0] == 'set_duty_cycle':
                self.output_switch('on', amount=self.options_channels['startup_value'][0])
            elif self.options_channels['state_startup'][0] == 'last_duty_cycle':
                device_measurement = db_retrieve_table_daemon(DeviceMeasurements).filter(
                    and_(DeviceMeasurements.device_id == self.unique_id,
                         DeviceMeasurements.channel == 0)).first()

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
                    self.logger.info(
                        "Setting startup duty cycle to last known value of {dc} %".format(
                            dc=last_measurement[1]))
                    self.output_switch('on', amount=last_measurement[1])
                else:
                    self.logger.error(
                        "Output instructed at startup to be set to "
                        "the last known duty cycle, but a last known "
                        "duty cycle could not be found in the measurement "
                        "database")
        else:
            self.logger.error("Output must have command set")

    def output_switch(self, state, output_type=None, amount=None, output_channel=None):
        measure_dict = copy.deepcopy(measurements_dict)

        if self.options_channels['pwm_command'][0]:
            if state == 'on' and 0 <= amount <= 100:
                if self.options_channels['pwm_invert_signal'][0]:
                    amount = 100.0 - abs(amount)
            elif state == 'off':
                if self.options_channels['pwm_invert_signal'][0]:
                    amount = 100
                else:
                    amount = 0
            else:
                return

            self.output_states[0] = amount

            cmd = self.options_channels['pwm_command'][0].replace('((duty_cycle))', str(amount))
            cmd_return, cmd_error, cmd_status = cmd_output(
                cmd, user=self.options_channels['linux_command_user'][0])

            measure_dict[0]['value'] = self.output_states[0]
            add_measurements_influxdb(self.unique_id, measure_dict)

            self.logger.debug("Duty cycle set to {dc:.2f} %".format(dc=amount))
            self.logger.debug(
                "Output duty cycle {duty_cycle} command returned: "
                "Status: {stat}, "
                "Output: '{ret}', "
                "Error: '{err}'".format(
                    duty_cycle=amount,
                    stat=cmd_status,
                    ret=cmd_return,
                    err=cmd_error))

    def is_on(self, output_channel=None):
        if self.is_setup():
            if self.output_states[0]:
                return self.output_states[0]
            return False

    def is_setup(self):
        return self.output_setup

    def stop_output(self):
        """ Called when Output is stopped """
        if self.is_setup():
            if self.options_channels['state_shutdown'][0] == 0:
                self.output_switch('off')
            elif self.options_channels['state_shutdown'][0] == 'set_duty_cycle':
                self.output_switch('on', amount=self.options_channels['shutdown_value'][0])
        self.running = False
