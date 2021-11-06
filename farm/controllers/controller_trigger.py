# coding=utf-8
#
# controller_trigger.py - Trigger controller that checks measurements
#                         and performs functions in response to events
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
import datetime
import threading
import time

from farm.controllers.base_controller import AbstractController
from farm.config import SQL_DATABASE_FARM
from farm.databases.models import Input
from farm.databases.models import Math
from farm.databases.models import Misc
from farm.databases.models import Output
from farm.databases.models import OutputChannel
from farm.databases.models import PID
from farm.databases.models import SMTP
from farm.databases.models import Trigger
from farm.databases.utils import session_scope
from farm.farm_client import DaemonControl
from farm.utils.database import db_retrieve_table_daemon
from farm.utils.function_actions import trigger_function_actions
from farm.utils.method import load_method_handler, parse_db_time
from farm.utils.sunriseset import calculate_sunrise_sunset_epoch
from farm.utils.system_pi import epoch_of_next_time
from farm.utils.system_pi import time_between_range

FARM_DB_PATH = 'sqlite:///' + SQL_DATABASE_FARM


class TriggerController(AbstractController, threading.Thread):
    """
    Class to operate Trigger controller

    Triggers are events that are used to signal when a set of actions
    should be executed.

    The main loop in this class will continually check if any timer
    Triggers have elapsed. If any have, trigger_all_actions()
    will be ran to execute all actions associated with that particular
    trigger.

    Edge and Output conditionals are triggered from
    the Input and Output controllers, respectively, and the
    trigger_all_actions() function in this class will be ran.
    """
    def __init__(self, ready, unique_id):
        threading.Thread.__init__(self)
        super(TriggerController, self).__init__(ready, unique_id=unique_id, name=__name__)

        self.unique_id = unique_id
        self.sample_rate = None

        self.control = DaemonControl()

        self.pause_loop = False
        self.verify_pause_loop = True
        self.trigger = None
        self.trigger_type = None
        self.trigger_name = None
        self.is_activated = None
        self.log_level_debug = None
        self.smtp_max_count = None
        self.email_count = None
        self.allowed_to_send_notice = None
        self.smtp_wait_timer = None
        self.timer_period = None
        self.period = None
        self.smtp_wait_timer = None
        self.timer_start_time = None
        self.timer_end_time = None
        self.unique_id_1 = None
        self.unique_id_2 = None
        self.unique_id_3 = None
        self.trigger_actions_at_period = None
        self.trigger_actions_at_start = None
        self.method_start_time = None
        self.method_end_time = None

    def loop(self):
        # Pause loop to modify trigger.
        # Prevents execution of trigger while variables are
        # being modified.
        if self.pause_loop:
            self.verify_pause_loop = True
            while self.pause_loop:
                time.sleep(0.1)

        elif (self.is_activated and self.timer_period and
                self.timer_period < time.time()):
            check_approved = False

            # Check if the trigger period has elapsed
            if self.trigger_type == 'trigger_sunrise_sunset':
                while self.running and self.timer_period < time.time():
                    self.timer_period = calculate_sunrise_sunset_epoch(self.trigger)

                check_approved = True

            elif self.trigger_type == 'trigger_run_pwm_method':

                # Only execute trigger actions when started
                # Now only set PWM output
                pwm_duty_cycle, ended = self.get_method_output(
                    self.trigger.unique_id_1)

                self.timer_period += self.trigger.period
                self.set_output_duty_cycle(pwm_duty_cycle)
                if self.trigger_actions_at_period:
                    trigger_function_actions(
                        self.unique_id,
                        debug=self.log_level_debug)
                check_approved = True

                if ended:
                    self.stop_method()

            elif (self.trigger_type in [
                    'trigger_timer_daily_time_point',
                    'trigger_timer_daily_time_span',
                    'trigger_timer_duration']):
                if self.trigger_type == 'trigger_timer_daily_time_point':
                    self.timer_period = epoch_of_next_time(
                        '{hm}:00'.format(hm=self.timer_start_time))
                elif self.trigger_type in ['trigger_timer_duration',
                                           'trigger_timer_daily_time_span']:
                    while self.running and self.timer_period < time.time():
                        self.timer_period += self.period
                check_approved = True

            if check_approved:
                self.attempt_execute(self.check_triggers)

    def run_finally(self):
        pass

    def refresh_settings(self):
        """ Signal to pause the main loop and wait for verification, the refresh settings """
        self.pause_loop = True
        while not self.verify_pause_loop:
            time.sleep(0.1)

        self.logger.info("Refreshing trigger settings")
        self.initialize_variables()

        self.pause_loop = False
        self.verify_pause_loop = False
        return "Trigger settings successfully refreshed"

    def initialize_variables(self):
        """ Define all settings """
        self.email_count = 0
        self.allowed_to_send_notice = True

        self.sample_rate = db_retrieve_table_daemon(
            Misc, entry='first').sample_rate_controller_conditional

        self.smtp_max_count = db_retrieve_table_daemon(
            SMTP, entry='first').hourly_max

        self.trigger = db_retrieve_table_daemon(
            Trigger, unique_id=self.unique_id)
        self.trigger_type = self.trigger.trigger_type
        self.trigger_name = self.trigger.name
        self.is_activated = self.trigger.is_activated
        self.log_level_debug = self.trigger.log_level_debug

        self.set_log_level_debug(self.log_level_debug)

        now = time.time()
        self.smtp_wait_timer = now + 3600
        self.timer_period = None

        # Set up trigger timer (daily time point)
        if self.trigger_type == 'trigger_timer_daily_time_point':
            self.timer_start_time = self.trigger.timer_start_time
            self.timer_period = epoch_of_next_time(
                '{hm}:00'.format(hm=self.trigger.timer_start_time))

        # Set up trigger timer (daily time span)
        elif self.trigger_type == 'trigger_timer_daily_time_span':
            self.timer_start_time = self.trigger.timer_start_time
            self.timer_end_time = self.trigger.timer_end_time
            self.period = self.trigger.period
            self.timer_period = now

        # Set up trigger timer (duration)
        elif self.trigger_type == 'trigger_timer_duration':
            self.period = self.trigger.period
            if self.trigger.timer_start_offset:
                self.timer_period = now + self.trigger.timer_start_offset
            else:
                self.timer_period = now

        # Set up trigger Run PWM Method
        elif self.trigger_type == 'trigger_run_pwm_method':
            self.unique_id_1 = self.trigger.unique_id_1
            self.unique_id_2 = self.trigger.unique_id_2
            self.unique_id_3 = self.trigger.unique_id_3
            self.period = self.trigger.period
            self.trigger_actions_at_period = self.trigger.trigger_actions_at_period
            self.trigger_actions_at_start = self.trigger.trigger_actions_at_start
            self.method_start_time = self.trigger.method_start_time
            self.method_end_time = self.trigger.method_end_time
            if self.is_activated:
                self.start_method(self.trigger.unique_id_1)
            if self.trigger_actions_at_start:
                self.timer_period = now - self.trigger.period
                if self.is_activated:
                    self.loop()
            else:
                self.timer_period = now

        # Set up trigger sunrise/sunset
        elif self.trigger_type == 'trigger_sunrise_sunset':
            self.period = 60
            # Set the next trigger at the specified sunrise/sunset time (+-offsets)
            self.timer_period = calculate_sunrise_sunset_epoch(self.trigger)

    def start_method(self, method_id):
        """ Instruct a method to start running """
        if method_id:
            this_controller = db_retrieve_table_daemon(
                Trigger, unique_id=self.unique_id)

            method = load_method_handler(method_id, self.logger)

            if parse_db_time(this_controller.method_start_time) is None:
                self.method_start_time = datetime.datetime.now()
                self.method_end_time = method.determine_end_time(self.method_start_time)

                self.logger.info("Starting method {} {}".format(self.method_start_time, self.method_end_time))

                with session_scope(FARM_DB_PATH) as db_session:
                    this_controller = db_session.query(Trigger)
                    this_controller = this_controller.filter(Trigger.unique_id == self.unique_id).first()
                    this_controller.method_start_time = self.method_start_time
                    this_controller.method_end_time = self.method_end_time
                    db_session.commit()
            else:
                # already running, potentially the daemon has been restarted
                self.method_start_time = this_controller.method_start_time
                self.method_end_time = this_controller.method_end_time

    def stop_method(self):
        self.method_start_time = None
        self.method_end_time = None
        with session_scope(FARM_DB_PATH) as db_session:
            this_controller = db_session.query(Trigger)
            this_controller = this_controller.filter(Trigger.unique_id == self.unique_id).first()
            this_controller.is_activated = False
            this_controller.method_start_time = None
            this_controller.method_end_time = None
            db_session.commit()
        self.stop_controller()
        self.is_activated = False
        self.logger.warning(
            "Method has ended. "
            "Activate the Trigger controller to start it again.")

    def get_method_output(self, method_id):
        """ Get output variable from method """
        this_controller = db_retrieve_table_daemon(
            Trigger, unique_id=self.unique_id)

        if this_controller.method_start_time is None:
            return

        now = datetime.datetime.now()

        method = load_method_handler(method_id, self.logger)
        setpoint, ended = method.calculate_setpoint(now, this_controller.method_start_time)

        if setpoint is not None:
            if setpoint > 100:
                setpoint = 100
            elif setpoint < 0:
                setpoint = 0

        return setpoint, ended

    def set_output_duty_cycle(self, duty_cycle):
        """ Set PWM Output duty cycle """
        output_channel = db_retrieve_table_daemon(OutputChannel).filter(
            OutputChannel.unique_id == self.trigger.unique_id_3).first()
        output_channel = output_channel.channel if output_channel else 0
        self.logger.debug("Set output duty cycle to {}".format(duty_cycle))
        self.control.output_on(
            self.trigger.unique_id_2, output_type='pwm', amount=duty_cycle, output_channel=output_channel)

    def check_triggers(self):
        """
        Check if any Triggers are activated and
        execute their actions if so.

        For example, if measured temperature is above 30C, notify me@gmail.com

        "if measured temperature is above 30C" is the Trigger to check.
        "notify me@gmail.com" is the Trigger Action to execute if the
        Trigger is True.
        """
        now = time.time()
        timestamp = datetime.datetime.fromtimestamp(now).strftime(
            '%Y-%m-%d %H:%M:%S')
        message = "{ts}\n[Trigger {id} ({name})]".format(
            ts=timestamp,
            name=self.trigger_name,
            id=self.unique_id)

        trigger = db_retrieve_table_daemon(
            Trigger, unique_id=self.unique_id, entry='first')

        device_id = trigger.measurement.split(',')[0]

        # if len(trigger.measurement.split(',')) > 1:
        #     device_measurement = trigger.measurement.split(',')[1]
        # else:
        #     device_measurement = None

        device = None

        input_dev = db_retrieve_table_daemon(
            Input, unique_id=device_id, entry='first')
        if input_dev:
            device = input_dev

        math = db_retrieve_table_daemon(
            Math, unique_id=device_id, entry='first')
        if math:
            device = math

        output = db_retrieve_table_daemon(
            Output, unique_id=device_id, entry='first')
        if output:
            device = output

        pid = db_retrieve_table_daemon(
            PID, unique_id=device_id, entry='first')
        if pid:
            device = pid

        if not device:
            message += " Error: Controller not Input, Math, Output, or PID"
            self.logger.error(message)
            return

        # If the edge detection variable is set, calling this function will
        # trigger an edge detection event. This will merely produce the correct
        # message based on the edge detection settings.
        elif trigger.trigger_type == 'trigger_edge':
            try:
                import RPi.GPIO as GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(int(input_dev.pin), GPIO.IN)
                gpio_state = GPIO.input(int(input_dev.pin))
            except Exception as e:
                gpio_state = None
                self.logger.error("Exception reading the GPIO pin: {}".format(e))
            if (gpio_state is not None and
                    gpio_state == trigger.if_sensor_gpio_state):
                message += " GPIO State Detected (state = {state}).".format(
                    state=trigger.if_sensor_gpio_state)
            else:
                self.logger.error("GPIO not configured correctly or GPIO state not verified")
                return

        # Calculate the sunrise/sunset times and find the next time this trigger should trigger
        elif trigger.trigger_type == 'trigger_sunrise_sunset':
            # Since the check time is the trigger time, we will only calculate and set the next trigger time
            self.timer_period = calculate_sunrise_sunset_epoch(trigger)

        # Check if the current time is between the start and end time
        elif trigger.trigger_type == 'trigger_timer_daily_time_span':
            if not time_between_range(self.timer_start_time,
                                      self.timer_end_time):
                return

        # If the code hasn't returned by now, action should be executed
        trigger_function_actions(
            self.unique_id,
            message=message,
            debug=self.log_level_debug)
