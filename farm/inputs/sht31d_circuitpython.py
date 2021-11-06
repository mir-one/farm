# coding=utf-8
import copy

from farm.inputs.base_input import AbstractInput
from farm.inputs.sensorutils import calculate_dewpoint
from farm.inputs.sensorutils import calculate_vapor_pressure_deficit

# Measurements
measurements_dict = {
    0: {
        'measurement': 'temperature',
        'unit': 'C'
    },
    1: {
        'measurement': 'humidity',
        'unit': 'percent'
    },
    2: {
        'measurement': 'dewpoint',
        'unit': 'C'
    },
    3: {
        'measurement': 'vapor_pressure_deficit',
        'unit': 'Pa'
    }
}

# Input information
INPUT_INFORMATION = {
    'input_name_unique': 'SHT31D_CP',
    'input_manufacturer': 'Sensirion',
    'input_name': 'SHT31-D',
    'input_library': 'Adafruit_CircuitPython_SHT31',
    'measurements_name': 'Humidity/Temperature',
    'measurements_dict': measurements_dict,
    'url_manufacturer': 'https://www.sensirion.com/en/environmental-sensors/humidity-sensors/digital-humidity-sensors-for-various-applications/',

    'options_enabled': [
        'i2c_location',
        'measurements_select',
        'period',
        'pre_output'
    ],
    'options_disabled': ['interface'],

    'dependencies_module': [
        ('pip-pypi', 'usb.core', 'pyusb==1.1.1'),
        ('pip-pypi', 'adafruit_extended_bus', 'Adafruit-extended-bus==1.0.1'),
        ('pip-pypi', 'adafruit_sht31d', 'adafruit-circuitpython-sht31d==2.3.5')
    ],

    'interfaces': ['I2C'],
    'i2c_location': ['0x44', '0x45'],
    'i2c_address_editable': False
}


class InputModule(AbstractInput):
    """ A sensor support class that measures the SHT31-D """
    def __init__(self, input_dev, testing=False):
        super(InputModule, self).__init__(input_dev, testing=testing, name=__name__)

        self.sensor = None

        if not testing:
            self.initialize_input()

    def initialize_input(self):
        import adafruit_sht31d
        from adafruit_extended_bus import ExtendedI2C

        try:
            self.sensor = adafruit_sht31d.SHT31D(
                ExtendedI2C(self.input_dev.i2c_bus),
                address=int(str(self.input_dev.i2c_location), 16))
        except:
            self.logger.exception("Setting up sensor")

    def get_measurement(self):
        if not self.sensor:
            self.logger.error("Input not set up")
            return

        self.return_dict = copy.deepcopy(measurements_dict)

        if self.is_enabled(0):
            self.value_set(0, self.sensor.temperature)

        if self.is_enabled(1):
            self.value_set(1, self.sensor.relative_humidity)

        if self.is_enabled(2) and self.is_enabled(0) and self.is_enabled(1):
            self.value_set(2, calculate_dewpoint(self.value_get(0), self.value_get(1)))

        if self.is_enabled(3) and self.is_enabled(0) and self.is_enabled(1):
            self.value_set(3, calculate_vapor_pressure_deficit(self.value_get(0), self.value_get(1)))

        return self.return_dict
