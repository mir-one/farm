# coding=utf-8
import copy
import resource

from farm.inputs.base_input import AbstractInput
from farm.farm_client import DaemonControl

# Measurements
measurements_dict = {
    0: {
        'measurement': 'disk_space',
        'unit': 'MB'
    }
}

# Input information
INPUT_INFORMATION = {
    'input_name': 'Farm RAM',
    'input_name_unique': 'FARM_RAM',
    'input_manufacturer': 'Farm',
    'input_library': 'resource.getrusage()',
    'measurements_name': 'Size RAM in Use',
    'measurements_dict': measurements_dict,

    'options_enabled': [
        'period'
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
            self.value_set(0, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / float(1000))
            return self.return_dict
        except Exception:
            pass
