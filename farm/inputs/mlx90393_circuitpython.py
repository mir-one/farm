# coding=utf-8
import copy

from farm.inputs.base_input import AbstractInput

measurements_dict = {
    0: {"measurement": "magnetic_flux_density", "unit": "uT", "name": "x"},
    1: {"measurement": "magnetic_flux_density", "unit": "uT", "name": "y"},
    2: {"measurement": "magnetic_flux_density", "unit": "uT", "name": "z"},
}

# Input information
INPUT_INFORMATION = {
    "input_name_unique": "MLX90393_CIRCUITPYTHON",
    "input_manufacturer": "Melexis",
    "input_name": "MLX90393",
    "input_library": "Adafruit-CircuitPython-MLX90393",
    "measurements_name": "Magnetic Flux",
    "measurements_dict": measurements_dict,
    "url_manufacturer": "https://www.melexis.com/en/product/MLX90393/Triaxis-Micropower-Magnetometer",
    "url_datasheet": "https://cdn-learn.adafruit.com/assets/assets/000/069/600/original/MLX90393-Datasheet-Melexis.pdf",
    "url_product_purchase": [
        "https://www.adafruit.com/product/4022",
        "https://shop.pimoroni.com/products/adafruit-wide-range-triple-axis-magnetometer-mlx90393",
        "https://www.berrybase.de/sensoren-module/bewegung-distanz/adafruit-wide-range-drei-achsen-magnetometer-mlx90393",
    ],
    "options_enabled": ["i2c_location", "period", "pre_output"],
    "options_disabled": ["interface"],
    "dependencies_module": [
        ("pip-pypi", "adafruit_extended_bus", "adafruit-extended-bus==1.0.1"),
        ("pip-pypi", "adafruit_mlx90393", "adafruit-circuitpython-mlx90393==2.0.6"),
    ],
    "interfaces": ["I2C"],
    "i2c_location": ["0x0C", "0x0D", "0x0E", "0x0F"],
    "i2c_address_editable": False,
}


class InputModule(AbstractInput):
    """A sensor support class that monitors the MLX90393's magnetic flux"""

    def __init__(self, input_dev, testing=False):
        super(InputModule, self).__init__(input_dev, testing=testing, name=__name__)

        self.sensor = None

        if not testing:
            self.initialize_input()

    def initialize_input(self):
        import adafruit_mlx90393
        from adafruit_extended_bus import ExtendedI2C

        self.sensor = adafruit_mlx90393.MLX90393(
            ExtendedI2C(self.input_dev.i2c_bus),
            address=int(str(self.input_dev.i2c_location), 16),
        )

    def get_measurement(self):
        """Gets the x, y, and z components of the magnetic flux"""
        if not self.sensor:
            self.logger.error("Input not set up")
            return

        mx, my, mz = self.sensor.magnetic

        self.return_dict = copy.deepcopy(measurements_dict)

        if self.is_enabled(0):
            self.value_set(0, mx)

        if self.is_enabled(1):
            self.value_set(1, my)

        if self.is_enabled(2):
            self.value_set(2, mz)

        return self.return_dict
