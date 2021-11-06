# coding=utf-8
import copy
import importlib.util
import os
import textwrap

from flask import Markup
from flask import current_app
from flask import flash

from farm.config import PATH_PYTHON_CODE_USER
from farm.databases.models import DeviceMeasurements
from farm.inputs.base_input import AbstractInput
from farm.utils.database import db_retrieve_table_daemon
from farm.utils.system_pi import assure_path_exists
from farm.utils.system_pi import cmd_output
from farm.utils.system_pi import set_user_grp


def generate_code(new_input):
    error = []
    pre_statement_run = """import os
import sys
sys.path.append(os.path.abspath('/var/farm-root'))
from farm.farm_client import DaemonControl
from farm.utils.influx import add_measurements_influxdb
control = DaemonControl()

class PythonInputRun:
    def __init__(self, logger, input_id, measurement_info):
        self.logger = logger
        self.input_id = input_id
        self.measurement_info = measurement_info

    def store_measurement(self, channel=None, measurement=None, timestamp=None):
        if None in [channel, measurement]:
            return
        measure = {channel: {}}
        measure[channel]['measurement'] = self.measurement_info[channel]['measurement']
        measure[channel]['unit'] = self.measurement_info[channel]['unit']
        measure[channel]['value'] = measurement
        if timestamp:
            measure[channel]['timestamp_utc'] = timestamp
        add_measurements_influxdb(self.input_id, measure)

    def python_code_run(self):
"""
    indented_code = textwrap.indent(new_input.cmd_command, ' ' * 8)
    input_python_code_run = pre_statement_run + indented_code

    assure_path_exists(PATH_PYTHON_CODE_USER)
    file_run = '{}/input_python_code_{}.py'.format(
        PATH_PYTHON_CODE_USER, new_input.unique_id)
    with open(file_run, 'w') as fw:
        fw.write('{}\n'.format(input_python_code_run))
        fw.close()
    set_user_grp(file_run, 'farm', 'farm')

    for each_error in error:
        flash(each_error, 'error')

    return input_python_code_run, file_run


def execute_at_creation(error, new_input, dict_inputs=None):
    generate_code(new_input)
    return error, new_input

def execute_at_modification(
        messages,
        mod_input,
        request_form,
        custom_options_dict_presave,
        custom_options_channels_dict_presave,
        custom_options_dict_postsave,
        custom_options_channels_dict_postsave):
    """
    Function to run when the Input is saved to evaluate the Python 3 code using pylint3
    :param messages: dict of info, warning, error, success messages as well as other variables
    :param mod_input: The WTForms object containing the form data submitted by the web GUI
    :param request_form: The custom_options form input data (if it exists)
    :param custom_options_dict_presave:
    :param custom_options_channels_dict_presave:
    :param custom_options_dict_postsave:
    :param custom_options_channels_dict_postsave:
    :return: tuple of (all_passed, error, mod_input) variables
    """
    messages["page_refresh"] = True
    pylint_message = None

    if current_app.config['TESTING']:
        return (messages,
                mod_input,
                custom_options_dict_postsave,
                custom_options_channels_dict_postsave)

    try:
        input_python_code_run, file_run = generate_code(mod_input)

        lines_code = ''
        for line_num, each_line in enumerate(input_python_code_run.splitlines(), 1):
            if len(str(line_num)) == 3:
                line_spacing = ''
            elif len(str(line_num)) == 2:
                line_spacing = ' '
            else:
                line_spacing = '  '
            lines_code += '{sp}{ln}: {line}\n'.format(
                sp=line_spacing,
                ln=line_num,
                line=each_line)

        cmd_test = 'mkdir -p /var/farm-root/.pylint.d && ' \
                   'export PYTHONPATH=$PYTHONPATH:/var/farm-root && ' \
                   'export PYLINTHOME=/var/farm-root/.pylint.d && ' \
                   'pylint3 -d I,W0621,C0103,C0111,C0301,C0327,C0410,C0413 {path}'.format(
                       path=file_run)
        cmd_out, cmd_error, cmd_status = cmd_output(cmd_test)
        pylint_message = Markup(
            '<pre>\n\n'
            'Full Python Code Input code:\n\n{code}\n\n'
            'Python Code Input code analysis:\n\n{report}'
            '</pre>'.format(
                code=lines_code, report=cmd_out.decode("utf-8")))
    except Exception as err:
        cmd_status = None
        messages["error"].append("Error running pylint: {}".format(err))

    if cmd_status:
        messages["warning"].append("pylint returned with status: {}".format(cmd_status))

    if pylint_message:
        messages["info"].append("Review your code for issues and test your Input "
              "before putting it into a production environment.")
        messages["return_text"].append(pylint_message)

    return (messages,
            mod_input,
            custom_options_dict_postsave,
            custom_options_channels_dict_postsave)


# Measurements
measurements_dict = {}

# Input information
INPUT_INFORMATION = {
    'input_name_unique': 'PythonCode',
    'input_manufacturer': 'Linux',
    'input_name': 'Python 3 Code',
    'measurements_name': 'Store Value(s)',
    'measurements_dict': measurements_dict,
    'measurements_variable_amount': True,
    'channel_quantity_same_as_measurements': False,
    'execute_at_creation': execute_at_creation,
    'execute_at_modification': execute_at_modification,

    'message': 'All channels require a Measurement Unit to be selected and saved in order to store values to the '
               'database.',

    'options_enabled': [
        'measurements_select',
        'period',
        'cmd_command',
        'pre_output'
    ],
    'options_disabled': ['interface'],

    'interfaces': ['Farm'],
    'cmd_command': """import random  # Import any external libraries

# Get measurements/values (for example, these are randomly-generated numbers)
random_value_channel_0 = random.uniform(10.0, 100.0)

# Store measurements in database (must specify the channel and measurement)
self.store_measurement(channel=0, measurement=random_value_channel_0)"""
}


class InputModule(AbstractInput):
    """ A sensor support class that returns a value from a command """

    def __init__(self, input_dev, testing=False):
        super(InputModule, self).__init__(input_dev, testing=testing, name=__name__)

        self.input_dev = input_dev
        self.python_code = None

        if not testing:
            self.initialize_input()

    def initialize_input(self):
        self.unique_id = self.input_dev.unique_id

        self.measure_info = {}
        self.device_measurements = db_retrieve_table_daemon(
            DeviceMeasurements).filter(
            DeviceMeasurements.device_id == self.input_dev.unique_id)
        for each_measure in self.device_measurements.all():
            self.measure_info[each_measure.channel] = {}
            self.measure_info[each_measure.channel]['unit'] = each_measure.unit
            self.measure_info[each_measure.channel]['measurement'] = each_measure.measurement

        self.python_code = self.input_dev.cmd_command

    def get_measurement(self):
        """ Determine if the return value of the command is a number """
        if not self.python_code:
            self.logger.error("Input not set up")
            return

        self.return_dict = copy.deepcopy(measurements_dict)

        file_run = '{}/input_python_code_{}.py'.format(PATH_PYTHON_CODE_USER, self.unique_id)

        # If the file to execute doesn't exist, generate it
        if not os.path.exists(file_run):
            execute_at_creation([], self.input_dev)

        with open(file_run, 'r') as file:
            self.logger.debug("Python Code:\n{}".format(file.read()))

        module_name = "farm.input.python_code_exec_{}".format(os.path.basename(file_run).split('.')[0])
        spec = importlib.util.spec_from_file_location(module_name, file_run)
        conditional_run = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(conditional_run)
        run = conditional_run.PythonInputRun(self.logger, self.unique_id, self.measure_info)
        try:
            run.python_code_run()
        except Exception:
            self.logger.exception(1)
