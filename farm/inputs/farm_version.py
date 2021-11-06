# coding=utf-8
import copy

from farm.config import FARM_VERSION
from farm.inputs.base_input import AbstractInput
from farm.farm_client import DaemonControl

# Measurements
measurements_dict = {
    0: {
        'measurement': 'version',
        'unit': 'unitless',
        'name': 'Major'
    },
    1: {
        'measurement': 'version',
        'unit': 'unitless',
        'name': 'Minor'
    },
    2: {
        'measurement': 'version',
        'unit': 'unitless',
        'name': 'Revision'
    }
}

# Input information
INPUT_INFORMATION = {
    'input_name': 'Farm Version',
    'input_name_unique': 'FARM_VERSION',
    'input_manufacturer': 'Farm',
    'measurements_name': 'Version as Major.Minor.Revision',
    'measurements_dict': measurements_dict,

    'options_enabled': [
        'period',
        'measurements_select'
    ],
    'options_disabled': ['interface'],

    'interfaces': ['Farm']
}


class InputModule(AbstractInput):
    """
    A sensor support class that measures ram used by the Farm daemon
    """
    def __init__(self, input_dev, testing=False):
        super(InputModule, self).__init__(input_dev, testing=testing, name=__name__)

        self.control = None

        if not testing:
            self.initialize_input()

    def initialize_input(self):
        self.control = DaemonControl()

    def get_measurement(self):
        """ Gets the measurement in units by reading resource """
        self.return_dict = copy.deepcopy(measurements_dict)

        try:
            version = FARM_VERSION.split('.')
            self.value_set(0, int(version[0]))
            self.value_set(1, int(version[1]))
            self.value_set(2, int(version[2]))

            return self.return_dict
        except Exception:
            pass
