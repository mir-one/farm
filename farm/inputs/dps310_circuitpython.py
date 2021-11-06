# coding=utf-8
import copy

from farm.inputs.base_input import AbstractInput

measurements_dict = {
    0: {"measurement": "pressure", "unit": "hPa"},
    1: {"measurement": "temperature", "unit": "C"},
}

# Input information
INPUT_INFORMATION = {
    "input_name_unique": "DPS310_CIRCUITPYTHON",
    "input_manufacturer": "Infineon",
    "input_name": "DPS310",
    "input_library": "Adafruit-CircuitPython-DPS310",
    "measurements_name": "Pressure/Temperature",
    "measurements_dict": measurements_dict,
    "url_manufacturer": "https://www.infineon.com/cms/en/product/sensor/pressure-sensors/pressure-sensors-for-iot/dps310/",
    "url_datasheet": "https://www.infineon.com/dgdl/Infineon-DPS310-DataSheet-v01_02-EN.pdf?fileId=5546d462576f34750157750826c42242",
    "url_product_purchase": [
        "https://www.adafruit.com/product/4494",
        "https://shop.pimoroni.com/products/adafruit-dps310-precision-barometric-pressure-altitude-sensor-stemma-qt-qwiic",
        "https://www.berrybase.de/sensoren-module/luftdruck-wasserdruck/adafruit-dps310-pr-228-zisions-barometrischer-druck-und-h-246-hen-sensor",
    ],
    "options_enabled": ["i2c_location", "period", "pre_output"],
    "options_disabled": ["interface"],
    "dependencies_module": [
        ("pip-pypi", "adafruit_extended_bus", "adafruit-extended-bus==1.0.1"),
        ("pip-pypi", "adafruit_dps310", "adafruit-circuitpython-dps310==1.2.5"),
    ],
    "interfaces": ["I2C"],
    "i2c_location": ["0x77", "0x76"],
    "i2c_address_editable": False,
}


class InputModule(AbstractInput):
    """A sensor support class that monitors the DPS310's pressure and temperature"""

    def __init__(self, input_dev, testing=False):
        super(InputModule, self).__init__(input_dev, testing=testing, name=__name__)

        self.sensor = None

        if not testing:
            self.initialize_input()

    def initialize_input(self):
        import adafruit_dps310
        from adafruit_extended_bus import ExtendedI2C

        self.sensor = adafruit_dps310.DPS310(
            ExtendedI2C(self.input_dev.i2c_bus),
            address=int(str(self.input_dev.i2c_location), 16),
        )

    def get_measurement(self):
        """Gets the pressure and temperature"""
        if not self.sensor:
            self.logger.error("Input not set up")
            return

        self.return_dict = copy.deepcopy(measurements_dict)

        if self.is_enabled(0):
            self.value_set(0, self.sensor.pressure)

        if self.is_enabled(1):
            self.value_set(1, self.sensor.temperature)

        return self.return_dict
