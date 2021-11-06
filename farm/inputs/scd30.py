# coding=utf-8
import copy

from farm.inputs.base_input import AbstractInput
from farm.inputs.sensorutils import calculate_dewpoint
from farm.inputs.sensorutils import calculate_vapor_pressure_deficit

# Measurements
measurements_dict = {
    0: {
        'measurement': 'co2',
        'unit': 'ppm'
    },
    1: {
        'measurement': 'temperature',
        'unit': 'C'
    },
    2: {
        'measurement': 'humidity',
        'unit': 'percent'
    },
    3: {
        'measurement': 'dewpoint',
        'unit': 'C'
    },
    4: {
        'measurement': 'vapor_pressure_deficit',
        'unit': 'Pa'
    }
}

# Input information
# See the inputs directory for examples of working modules.
# The following link provides the full list of options with descriptions:
# https://github.com/mir-one/Farm/blob/single_file_input_modules/farm/inputs/examples/example_all_options_temperature.py
INPUT_INFORMATION = {
    'input_name_unique': 'SCD30',
    'input_manufacturer': 'Sensirion',
    'input_name': 'SCD30',
    'input_library': 'scd30_i2c',
    'measurements_name': 'CO2/Humidity/Temperature',
    'measurements_dict': measurements_dict,
    'measurements_use_same_timestamp': True,

    'url_manufacturer': 'https://www.sensirion.com/en/environmental-sensors/carbon-dioxide-sensors/carbon-dioxide-sensors-co2/',
    'url_datasheet': 'https://www.sensirion.com/fileadmin/user_upload/customers/sensirion/Dokumente/9.5_CO2/Sensirion_CO2_Sensors_SCD30_Datasheet.pdf',
    'url_product_purchase': [
        'https://www.sparkfun.com/products/15112',
        'https://www.futureelectronics.com/p/4115766'
    ],

    'options_enabled': [
        'i2c_location',
        'period',
        'pre_output'
    ],
    'options_disabled': ['interface'],

    'dependencies_module': [
        ('pip-pypi', 'scd30_i2c', 'scd30-i2c==0.0.6')
    ],

    'interfaces': ['I2C'],
    'i2c_location': ['0x61'],
    'i2c_address_editable': False
}

class InputModule(AbstractInput):
    """ Input support class """
    def __init__(self, input_dev, testing=False):
        super(InputModule, self).__init__(input_dev, testing=testing, name=__name__)

        self.scd = None

        if not testing:
            self.initialize_input()

    def initialize_input(self):
        from scd30_i2c import SCD30

        self.scd = SCD30()

    def get_measurement(self):
        """ Measures CO2, temperature and humidity """
        self.return_dict = copy.deepcopy(measurements_dict)

        if self.scd.get_data_ready():
            m = self.scd.read_measurement()
            if m is not None:
                co2 = m[0]
                temperature = m[1]
                humidity = m[2]

                if self.is_enabled(0):
                    self.value_set(0, co2)

                if self.is_enabled(1):
                    self.value_set(1, temperature)

                if self.is_enabled(2):
                    self.value_set(2, humidity)

                if self.is_enabled(3) and self.is_enabled(1) and self.is_enabled(2):
                    self.value_set(3, calculate_dewpoint(self.value_get(1), self.value_get(2)))

                if self.is_enabled(4) and self.is_enabled(1) and self.is_enabled(2):
                    self.value_set(4, calculate_vapor_pressure_deficit(self.value_get(1), self.value_get(2)))

        return self.return_dict
