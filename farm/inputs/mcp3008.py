# coding=utf-8
import copy
from collections import OrderedDict

from farm.inputs.base_input import AbstractInput
from farm.utils.constraints_pass import constraints_pass_positive_value

# Measurements
measurements_dict = OrderedDict()
for each_channel in range(4):
    measurements_dict[each_channel] = {
        'measurement': 'electrical_potential',
        'unit': 'V'
    }

# Input information
INPUT_INFORMATION = {
    'input_name_unique': 'MCP3008',
    'input_manufacturer': 'Microchip',
    'input_name': 'MCP3008',
    'input_library': 'Adafruit_MCP3008',
    'measurements_name': 'Voltage (Analog-to-Digital Converter)',
    'measurements_dict': measurements_dict,
    'url_manufacturer': 'https://www.microchip.com/wwwproducts/en/en010530',
    'url_datasheet': 'http://ww1.microchip.com/downloads/en/DeviceDoc/21295d.pdf',
    'url_product_purchase': 'https://www.adafruit.com/product/856',

    'measurements_rescale': True,
    'scale_from_min': -4.096,
    'scale_from_max': 4.096,

    'options_enabled': [
        'pin_cs',
        'pin_miso',
        'pin_mosi',
        'pin_clock',
        'measurements_select',
        'channels_convert',
        'period',
        'pre_output'
    ],
    'options_disabled': ['interface'],

    'dependencies_module': [
        ('pip-pypi', 'Adafruit_MCP3008', 'Adafruit-MCP3008==1.5.6')
    ],

    'interfaces': ['UART'],
    'pin_cs': 8,
    'pin_miso': 9,
    'pin_mosi': 10,
    'pin_clock': 11,

    'custom_options': [
        {
            'id': 'vref',
            'type': 'float',
            'default_value': 3.3,
            'constraints_pass': constraints_pass_positive_value,
            'name': 'VREF (volts)',
            'phrase': 'Set the VREF voltage'
        }
    ]
}


class InputModule(AbstractInput):
    """ ADC Read """
    def __init__(self, input_dev, testing=False):
        super(InputModule, self).__init__(input_dev, testing=testing, name=__name__)

        self.sensor = None
        self.vref = None

        if not testing:
            self.setup_custom_options(
                INPUT_INFORMATION['custom_options'], input_dev)
            self.initialize_input()

    def initialize_input(self):
        import Adafruit_MCP3008

        self.sensor = Adafruit_MCP3008.MCP3008(
            clk=self.input_dev.pin_clock,
            cs=self.input_dev.pin_cs,
            miso=self.input_dev.pin_miso,
            mosi=self.input_dev.pin_mosi)

    def get_measurement(self):
        if not self.sensor:
            self.logger.error("Input not set up")
            return

        self.return_dict = copy.deepcopy(measurements_dict)

        for channel in self.channels_measurement:
            if self.is_enabled(channel):
                self.value_set(channel, ((self.sensor.read_adc(channel) / 1024.0) * self.vref))

        return self.return_dict
