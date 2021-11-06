# coding=utf-8
import fcntl
import logging
import os
import sys
import time

import io

sys.path.append(os.path.abspath(os.path.join(os.path.realpath(__file__), '../../..')))

from farm.devices.base_atlas import AbstractBaseAtlasScientific


class AtlasScientificI2C(AbstractBaseAtlasScientific):
    """Class for Atlas Scientific sensor communication via I2C"""

    long_timeout = 1.5  # the timeout needed to query readings and calibrations
    short_timeout = .5  # timeout for regular commands
    default_bus = 1  # the default bus for I2C on the newer Raspberry Pis, certain older boards use bus 0
    default_address = 98  # the default address for the sensor

    def __init__(self, i2c_address=default_address, i2c_bus=default_bus):
        super(AtlasScientificI2C, self).__init__(interface='I2C', name="_{}_{}".format(i2c_address, i2c_bus))

        # open two file streams, one for reading and one for writing
        # the specific I2C channel is selected with bus
        # it is usually 1, except for older revisions where its 0
        # wb and rb indicate binary read and write
        self.logger = logging.getLogger(
            "{}_{}_{}".format(__name__, i2c_address, i2c_bus))
        self.current_addr = i2c_address
        self.setup = False
        try:
            self.file_read = io.open("/dev/i2c-" + str(i2c_bus), "rb", buffering=0)
            self.file_write = io.open("/dev/i2c-" + str(i2c_bus), "wb", buffering=0)

            # initializes I2C to either a user specified or default address
            self.set_i2c_address(i2c_address)
            self.setup = True

            (board,
             revision,
             firmware_version) = self.get_board_version()

            self.logger.info(
                "Atlas Scientific Board: {brd}, Rev: {rev}, Firmware: {fw}".format(
                    brd=board,
                    rev=revision,
                    fw=firmware_version))
        except Exception as err:
            self.logger.exception(
                "{cls} raised an exception when initializing: "
                "{err}".format(cls=type(self).__name__, err=err))

    def set_i2c_address(self, addr):
        # set the I2C communications to the slave specified by the address
        # The commands for I2C dev using the ioctl functions are specified in
        # the i2c-dev.h file from i2c-tools
        i2c_slave = 0x703
        fcntl.ioctl(self.file_read, i2c_slave, addr)
        fcntl.ioctl(self.file_write, i2c_slave, addr)
        self.current_addr = addr

    def atlas_write(self, cmd):
        self.write(cmd)

    def write(self, cmd):
        """ Append the null character and send the command over I2C"""
        cmd += "\00"
        # self.logger.error("Atlas Scientific command being sent: '{}'".format(cmd))
        self.file_write.write(cmd.encode('latin-1'))

    def read(self, num_of_bytes=50):
        """ Read a specified number of bytes from I2C, then parse and display the result """
        res = self.file_read.read(num_of_bytes)  # read from the board
        if res[0] == 1:  # if the response isn't an error
            response = list(filter(lambda x: x != '\x00', res.decode()))  # remove the null characters
            # change MSB to 0 for all received characters except the first and get a list of characters
            char_list = map(lambda x: chr(ord(x) & ~0x80), list(response[1:]))
            # NOTE: having to change the MSB to 0 is a glitch in the raspberry pi, and you shouldn't have to do this!
            return "success", ''.join(char_list)  # convert the char list to a string and returns it
        else:
            return "error", str(res[0])

    def query(self, query_str):
        """ Send command to board and read response """
        try:
            # write a command to the board, wait the correct timeout,
            # and read the response
            self.write(query_str)

            # the read and calibration commands require a longer timeout
            if ((query_str.upper().startswith("R")) or
                    (query_str.upper().startswith("CAL"))):
                time.sleep(self.long_timeout)
            elif query_str.upper().startswith("SLEEP"):
                return "sleep mode"
            else:
                time.sleep(self.short_timeout)

            return self.read()
        except Exception as err:
            self.logger.debug(
                "{cls} raised an exception when taking a reading: "
                "{err}".format(cls=type(self).__name__, err=err))
            return "error", err

    def close(self):
        self.file_read.close()
        self.file_write.close()

    def list_i2c_devices(self):
        """ Determine the addresses of connected I2C devices """
        prev_addr = self.current_addr  # save the current address so we can restore it after
        i2c_devices = []
        for i in range(0, 128):
            try:
                self.set_i2c_address(i)
                self.read()
                i2c_devices.append(i)
            except IOError:
                pass
        self.set_i2c_address(prev_addr)  # restore the address we were using
        return i2c_devices


def main():
    device = AtlasScientificI2C()

    print(">> Atlas Scientific sample code")
    print(">> Any commands entered are passed to the board via I2C except:")
    print(">>   List_addr lists the available I2C addresses.")
    print(">>   Address,xx changes the I2C address the Raspberry Pi communicates with.")
    print(">>   Poll,xx.x command continuously polls the board every xx.x seconds")
    print(" where xx.x is longer than the {to:.2f} second timeout.".format(
        to=device.long_timeout))
    print(">> Pressing ctrl-c will stop the polling")

    while True:
        input_str = input("Enter command: ")

        if input_str.upper().startswith("LIST_ADDR"):
            devices = device.list_i2c_devices()
            for line in devices:
                print(line)

        # address command lets you change which address the Raspberry Pi will poll
        elif input_str.upper().startswith("ADDRESS"):
            addr = int(input_str.split(',')[1])
            device.set_i2c_address(addr)
            print("I2C address set to " + str(addr))

        # continuous polling command automatically polls the board
        elif input_str.upper().startswith("POLL"):
            delay_time = float(input_str.split(',')[1])

            # check for polling time being too short, change it to the minimum timeout if too short
            if delay_time < device.long_timeout:
                print("Polling time is shorter than timeout, setting polling "
                      "time to {to:.2f}".format(to=device.long_timeout))
                delay_time = device.long_timeout

            # get the information of the board you're polling
            info = device.query("I").split(",")[1]
            print("Polling {sen} sensor every {sec:.2f} seconds, "
                  "press ctrl-c to stop polling".format(
                    sen=info, sec=delay_time))

            try:
                while True:
                    print(device.query("R"))
                    time.sleep(delay_time - device.long_timeout)
            except KeyboardInterrupt:  # catch ctrl-c
                print("Continuous polling stopped")

        # if not a special keyword, pass commands straight to board
        else:
            if len(input_str) == 0:
                print("Please input valid command.")
            else:
                try:
                    print(device.query(input_str))
                except IOError:
                    print("Query failed \n - Address may be invalid, use "
                          "List_addr command to see available addresses")


if __name__ == "__main__":
    main()
