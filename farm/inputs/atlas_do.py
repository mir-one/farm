# coding=utf-8
import copy
import time

from flask_babel import lazy_gettext

from farm.databases.models import Conversion
from farm.inputs.base_input import AbstractInput
from farm.inputs.sensorutils import convert_from_x_to_y_unit
from farm.utils.atlas_calibration import AtlasScientificCommand
from farm.utils.atlas_calibration import setup_atlas_device
from farm.utils.constraints_pass import constraints_pass_positive_value
from farm.utils.database import db_retrieve_table_daemon
from farm.utils.system_pi import get_measurement
from farm.utils.system_pi import return_measurement_info
from farm.utils.system_pi import str_is_float

# Measurements
measurements_dict = {
    0: {
        'measurement': 'dissolved_oxygen',
        'unit': 'mg_L'
    }
}

# Input information
INPUT_INFORMATION = {
    'input_name_unique': 'ATLAS_DO',
    'input_manufacturer': 'Atlas Scientific',
    'input_name': 'Atlas DO',
    'input_library': 'pylibftdi/fcntl/io/serial',
    'measurements_name': 'Dissolved Oxygen',
    'measurements_dict': measurements_dict,
    'url_manufacturer': 'https://www.atlas-scientific.com/dissolved-oxygen.html',
    'url_datasheet': 'https://www.atlas-scientific.com/files/DO_EZO_Datasheet.pdf',

    'options_enabled': [
        'ftdi_location',
        'i2c_location',
        'uart_location',
        'uart_baud_rate',
        'period',
        'calibration_measurement',
        'pre_output'
    ],
    'options_disabled': ['interface'],

    'dependencies_module': [
        ('pip-pypi', 'pylibftdi', 'pylibftdi==0.19.0')
    ],

    'interfaces': ['I2C', 'UART', 'FTDI'],
    'i2c_location': ['0x66'],
    'i2c_address_editable': True,
    'uart_location': '/dev/ttyAMA0',
    'uart_baud_rate': 9600,
    'ftdi_location': '/dev/ttyUSB0',

    'custom_options': [
        {
            'id': 'temperature_comp_meas',
            'type': 'select_measurement',
            'default_value': '',
            'options_select': [
                'Input',
                'Function',
                'Math'
            ],
            'name': "{}: {}".format(lazy_gettext('Temperature Compensation'), lazy_gettext('Measurement')),
            'phrase': lazy_gettext('Select a measurement for temperature compensation')
        },
        {
            'id': 'max_age',
            'type': 'integer',
            'default_value': 120,
            'required': True,
            'constraints_pass': constraints_pass_positive_value,
            'name': "{}: {}".format(lazy_gettext('Temperature Compensation'), lazy_gettext('Max Age')),
            'phrase': lazy_gettext('The maximum age (seconds) of the measurement to use')
        }
    ],

    'custom_actions': [
        {
            'type': 'message',
            'default_value': """A one- or two-point calibration can be performed. After exposing the probe to air for 30 seconds until readings stabilize, press Calibrate (Air). If you require accuracy below 1.0 mg/L, you can place the probe in a 0 mg/L solution for 30 to 90 seconds until readings stabilize, then press Calibrate (0 mg/L). You can also clear the currently-saved calibration by pressing Clear Calibration."""
        },
        {
            'id': 'calibrate_air',
            'type': 'button',
            'name': 'Calibrate (Air)'
        },
        {
            'id': 'calibrate_0mg',
            'type': 'button',
            'name': 'Calibrate (0 mg/L)'
        },
        {
            'id': 'calibrate_clear',
            'type': 'button',
            'name': lazy_gettext('Clear Calibration')
        },
        {
            'type': 'message',
            'default_value': """The I2C address can be changed. Enter a new address in the 0xYY format (e.g. 0x22, 0x50), then press Set I2C Address. Remember to deactivate and change the I2C address option after setting the new address."""
        },
        {
            'id': 'new_i2c_address',
            'type': 'text',
            'default_value': '0x66',
            'name': lazy_gettext('New I2C Address'),
            'phrase': lazy_gettext('The new I2C to set the device to')
        },
        {
            'id': 'set_i2c_address',
            'type': 'button',
            'name': lazy_gettext('Set I2C Address')
        }
    ]
}


class InputModule(AbstractInput):
    """A sensor support class that monitors the Atlas Scientific sensor DO"""
    def __init__(self, input_dev, testing=False):
        super(InputModule, self).__init__(input_dev, testing=testing, name=__name__)

        self.atlas_device = None
        self.interface = None
        self.atlas_command = None

        self.temperature_comp_meas_device_id = None
        self.temperature_comp_meas_measurement_id = None
        self.max_age = None

        if not testing:
            self.setup_custom_options(
                INPUT_INFORMATION['custom_options'], input_dev)
            self.initialize_input()

    def initialize_input(self):
        self.interface = self.input_dev.interface

        try:
            self.atlas_device = setup_atlas_device(self.input_dev)

            # Enabling DO, disabling % saturation
            self.atlas_device.atlas_write("O,mg,1")
            self.atlas_device.atlas_write("O,%,0")
            ret_val = self.atlas_device.atlas_write("O,?")
            self.logger.info("Parameters enabled: {}".format(ret_val))

            if self.temperature_comp_meas_measurement_id:
                self.atlas_command = AtlasScientificCommand(
                    self.input_dev, sensor=self.atlas_device)
        except Exception:
            self.logger.exception("Exception while initializing sensor")

        # Throw out first measurement of Atlas Scientific sensor, as it may be prone to error
        self.get_measurement()

    def get_measurement(self):
        """ Gets the sensor's DO measurement """
        if not self.atlas_device.setup:
            self.logger.error("Input not set up")
            return

        do = None
        self.return_dict = copy.deepcopy(measurements_dict)

        # Compensate measurement based on a temperature measurement
        if self.temperature_comp_meas_measurement_id and self.atlas_command:
            self.logger.debug("DO sensor set to calibrate temperature")

            last_measurement = self.get_last_measurement(
                self.temperature_comp_meas_device_id,
                self.temperature_comp_meas_measurement_id,
                max_age=self.max_age)

            if last_measurement:
                device_measurement = get_measurement(
                    self.temperature_comp_meas_measurement_id)
                conversion = db_retrieve_table_daemon(
                    Conversion, unique_id=device_measurement.conversion_id)
                _, unit, _ = return_measurement_info(
                    device_measurement, conversion)

                if unit != "C":
                    out_value = convert_from_x_to_y_unit(
                        unit, "C", last_measurement[1])
                else:
                    out_value = last_measurement[1]

                self.logger.debug(
                    "Latest temperature used to calibrate: {temp}".format(
                        temp=out_value))
                ret_value, ret_msg = self.atlas_command.calibrate(
                    'temperature', set_amount=out_value)
                time.sleep(0.5)
                self.logger.debug("Calibration returned: {val}, {msg}".format(
                    val=ret_value, msg=ret_msg))
            else:
                self.logger.error(
                    "Calibration measurement not found within the past {} seconds".format(
                        self.max_age))

        # Read sensor via FTDI or UART
        if self.interface in ['FTDI', 'UART']:
            do_status, do_list = self.atlas_device.query('R')
            if do_list:
                self.logger.debug("Returned list: {lines}".format(lines=do_list))

            # Find float value in list
            float_value = None
            for each_split in do_list:
                if str_is_float(each_split):
                    float_value = each_split
                    break

            if 'check probe' in do_list:
                self.logger.error('"check probe" returned from sensor')
            elif str_is_float(float_value):
                do = float(float_value)
                self.logger.debug('Found float value: {val}'.format(val=do))
            else:
                self.logger.error('Value or "check probe" not found in list: {val}'.format(val=do_list))

        # Read sensor via I2C
        elif self.interface == 'I2C':
            ec_status, ec_str = self.atlas_device.query('R')
            if ec_status == 'error':
                self.logger.error("Sensor read unsuccessful: {err}".format(err=ec_str))
            elif ec_status == 'success':
                do = float(ec_str)

        self.value_set(0, do)

        return self.return_dict

    def calibrate_air(self, args_dict):
        try:
            write_cmd = "Cal"
            self.logger.debug("Command to send: {}".format(write_cmd))
            ret_val = self.atlas_device.atlas_write(write_cmd)
            self.logger.info("Command returned: {}".format(ret_val))
            # Verify calibration saved
            write_cmd = "Cal,?"
            self.logger.info("Device Calibrated?: {}".format(
                self.atlas_device.atlas_write(write_cmd)))
        except:
            self.logger.exception("Exception calibrating sensor")

    def calibrate_0mg(self, args_dict):
        try:
            write_cmd = "Cal,0"
            self.logger.debug("Command to send: {}".format(write_cmd))
            ret_val = self.atlas_device.atlas_write(write_cmd)
            self.logger.info("Command returned: {}".format(ret_val))
            # Verify calibration saved
            write_cmd = "Cal,?"
            self.logger.info("Device Calibrated?: {}".format(
                self.atlas_device.atlas_write(write_cmd)))
        except:
            self.logger.exception("Exception calibrating sensor")

    def calibrate_clear(self, args_dict):
        try:
            write_cmd = "Cal,clear"
            self.logger.debug("Calibration command: {}".format(write_cmd))
            ret_val = self.atlas_device.atlas_write(write_cmd)
            self.logger.info("Command returned: {}".format(ret_val))
        except:
            self.logger.exception("Exception clearing calibration")

    def set_i2c_address(self, args_dict):
        if 'new_i2c_address' not in args_dict:
            self.logger.error("Cannot set new I2C address without an I2C address")
            return
        try:
            i2c_address = int(str(args_dict['new_i2c_address']), 16)
            write_cmd = "I2C,{}".format(i2c_address)
            self.logger.debug("I2C Change command: {}".format(write_cmd))
            self.atlas_device.atlas_write(write_cmd)
        except:
            self.logger.exception("Exception changing I2C address")
