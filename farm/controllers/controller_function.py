# coding=utf-8
#
# controller_function.py - Function controller that manages Custom Functions
#
#  Copyright (C) 2015-2020 Roman Inozemtsev <dao@mir.one>
#
#  This file is part of Farm
#
#  Farm is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Farm is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Farm. If not, see <http://www.gnu.org/licenses/>.
#
#  Contact at mir.one
#
import threading
import time

from farm.controllers.base_controller import AbstractController
from farm.databases.models import Conversion
from farm.databases.models import CustomController
from farm.databases.models import DeviceMeasurements
from farm.databases.models import Misc
from farm.farm_client import DaemonControl
from farm.utils.database import db_retrieve_table_daemon
from farm.utils.functions import parse_function_information
from farm.utils.modules import load_module_from_file


class FunctionController(AbstractController, threading.Thread):
    """
    Class for controlling the Function
    """
    def __init__(self, ready, unique_id):
        threading.Thread.__init__(self)
        super(FunctionController, self).__init__(ready, unique_id=unique_id, name=__name__)

        self.unique_id = unique_id
        self.run_function = None
        self.sample_rate = None

        self.control = DaemonControl()

        self.timer_loop = time.time()
        self.dict_function = None
        self.device_measurements = None
        self.conversions = None
        self.function = None
        self.function_name = None
        self.log_level_debug = None
        self.device = None
        self.period = None

    def __str__(self):
        return str(self.__class__)

    def loop(self):
        if self.timer_loop < time.time():
            while self.timer_loop < time.time():
                self.timer_loop += self.sample_rate

            try:
                self.run_function.loop()
            except Exception as err:
                self.logger.exception("Exception while running loop(): {}".format(err))

    def run_finally(self):
        try:
            self.run_function.stop_function()
        except:
            pass

    def initialize_variables(self):
        function = db_retrieve_table_daemon(
            CustomController, unique_id=self.unique_id)

        self.log_level_debug = function.log_level_debug
        self.set_log_level_debug(self.log_level_debug)

        self.dict_function = parse_function_information()

        self.sample_rate = db_retrieve_table_daemon(
            Misc, entry='first').sample_rate_controller_function

        self.device_measurements = db_retrieve_table_daemon(
            DeviceMeasurements).filter(
            DeviceMeasurements.device_id == self.unique_id)

        self.conversions = db_retrieve_table_daemon(Conversion)

        self.function = function
        self.unique_id = function.unique_id
        self.function_name = function.name
        self.device = function.device

        if self.device in self.dict_function:
            function_loaded = load_module_from_file(
                self.dict_function[self.device]['file_path'],
                'function')

            if function_loaded:
                self.run_function = function_loaded.CustomModule(self.function)
        else:
            self.logger.debug("Device '{device}' not recognized".format(
                device=self.device))
            raise Exception("'{device}' is not a valid device type.".format(
                device=self.device))

    def custom_button_exec_function(self, button_id, args_dict, thread=True):
        """Execute function from custom action button press"""
        try:
            run_action = getattr(self.run_function, button_id)
            if thread:
                thread_run_action = threading.Thread(
                    target=run_action,
                    args=(args_dict,))
                thread_run_action.start()
                return 0, "Command sent to Function Controller and is running in the background."
            else:
                return_val = run_action(args_dict)
                return 0, "Command sent to Function Controller. Returned: {}".format(return_val)
        except:
            self.logger.exception(
                "Error executing button press function '{}'".format(
                    button_id))

    def function_action(self, action_string, args_dict=None, thread=True):
        """Execute function action"""
        if args_dict is None:
            args_dict = {}
        try:
            run_action = getattr(self.run_function, action_string)
            if thread:
                thread_run_action = threading.Thread(
                    target=run_action,
                    args=(args_dict,))
                thread_run_action.start()
                return 0, "Command sent to Function Controller and is running in the background."
            else:
                return_val = run_action(args_dict)
                return 0, "Command sent to Function Controller. Returned: {}".format(return_val)
        except:
            self.logger.exception(
                "Error executing function action '{}'".format(action_string))

    def function_status(self):
        return self.run_function.function_status()
