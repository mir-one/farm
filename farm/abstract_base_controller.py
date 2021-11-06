# coding=utf-8
"""
This module contains the AbstractBaseController Class which acts as a template
for all controllers.  It is not to be used directly. The AbstractBaseController Class
ensures that certain methods and instance variables are included in each
Controller template.

All Controller templates should inherit from this class

These base classes currently inherit this AbstractBaseController:
controllers/base_controller.py
inputs/base_input.py
outputs/base_output.py
"""
import json
import logging
import time
from collections import OrderedDict

from farm.config import SQL_DATABASE_FARM
from farm.databases.models import Conversion
from farm.databases.models import DeviceMeasurements
from farm.databases.models import OutputChannel
from farm.databases.utils import session_scope
from farm.utils.database import db_retrieve_table_daemon
from farm.utils.influx import get_last_measurement
from farm.utils.influx import get_past_measurements
from farm.utils.lockfile import LockFile

FARM_DB_PATH = 'sqlite:///' + SQL_DATABASE_FARM


class AbstractBaseController(object):
    """
    Base Controller class that ensures certain methods and values are present
    in controllers.
    """
    def __init__(self, unique_id=None, testing=False, name=__name__):
        logger_name = "{}".format(name)
        if not testing and unique_id:
            logger_name += "_{}".format(unique_id.split('-')[0])
        self.logger = logging.getLogger(logger_name)

        self.lockfile = LockFile()
        self.channels_conversion = {}
        self.channels_measurement = {}
        self.device_measurements = None

    def setup_custom_options(self, custom_options, custom_controller):
        if not hasattr(custom_controller, 'custom_options'):
            self.logger.error("custom_controller missing attribute custom_options")
            return
        elif custom_controller.custom_options.startswith("{"):
            return self.setup_custom_options_json(custom_options, custom_controller)
        else:
            return self.setup_custom_options_csv(custom_options, custom_controller)

    def setup_device_measurement(self, unique_id):
        for _ in range(5):  # Make 5 attempts to access database
            try:
                self.device_measurements = db_retrieve_table_daemon(
                    DeviceMeasurements).filter(
                    DeviceMeasurements.device_id == unique_id)

                for each_measure in self.device_measurements.all():
                    self.channels_measurement[each_measure.channel] = each_measure
                    self.channels_conversion[each_measure.channel] = db_retrieve_table_daemon(
                        Conversion, unique_id=each_measure.conversion_id)
                return
            except Exception as msg:
                self.logger.debug("Error: {}".format(msg))
            time.sleep(0.1)

    # TODO: Remove in place of JSON function, below, in next major version
    def setup_custom_options_csv(self, custom_options, custom_controller):
        for each_option_default in custom_options:
            try:
                required = False
                custom_option_set = False
                error = []

                if 'type' not in each_option_default:
                    error.append("'type' not found in custom_options")
                if ('id' not in each_option_default and
                        ('type' in each_option_default and
                         each_option_default['type'] not in ['new_line', 'message'])):
                    error.append("'id' not found in custom_options")
                if ('default_value' not in each_option_default and
                        ('type' in each_option_default and
                         each_option_default['type'] != 'new_line')):
                    error.append("'default_value' not found in custom_options")

                for each_error in error:
                    self.logger.error(each_error)
                if error:
                    return

                if each_option_default['type'] in ['new_line', 'message']:
                    continue

                if 'required' in each_option_default and each_option_default['required']:
                    required = True

                option_value = each_option_default['default_value']
                device_id = None
                measurement_id = None
                channel_id = None

                if not hasattr(custom_controller, 'custom_options'):
                    self.logger.error("custom_controller missing attribute custom_options")
                    return

                if custom_controller.custom_options:
                    for each_option in custom_controller.custom_options.split(';'):
                        option = each_option.split(',')[0]

                        if option == each_option_default['id']:
                            custom_option_set = True

                            if (each_option_default['type'] == 'select_measurement' and
                                    len(each_option.split(',')) > 2):
                                device_id = each_option.split(',')[1]
                                measurement_id = each_option.split(',')[2]
                            if (each_option_default['type'] == 'select_measurement_channel' and
                                    len(each_option.split(',')) > 3):
                                device_id = each_option.split(',')[1]
                                measurement_id = each_option.split(',')[2]
                                channel_id = each_option.split(',')[3]
                            else:
                                option_value = each_option.split(',')[1]

                if required and not custom_option_set:
                    self.logger.error(
                        "Option '{}' required but was not found to be set by the user. Setting to default.".format(
                            each_option_default['id']))

                if each_option_default['type'] == 'integer':
                    setattr(self, each_option_default['id'], int(option_value))

                elif each_option_default['type'] == 'float':
                    setattr(self, each_option_default['id'], float(option_value))

                elif each_option_default['type'] == 'bool':
                    setattr(self, each_option_default['id'], bool(option_value))

                elif each_option_default['type'] in ['multiline_text',
                                                     'text']:
                    setattr(self, each_option_default['id'], str(option_value))

                elif each_option_default['type'] == 'select_multi_measurement':
                    setattr(self, each_option_default['id'], str(option_value))

                elif each_option_default['type'] == 'select':
                    option_value = str(option_value)
                    if 'cast_value' in each_option_default and each_option_default['cast_value']:
                        if each_option_default['cast_value'] == 'integer':
                            option_value = int(option_value)
                        elif each_option_default['cast_value'] == 'float':
                            option_value = float(option_value)
                    setattr(self, each_option_default['id'], option_value)

                elif each_option_default['type'] == 'select_measurement':
                    setattr(self,
                            '{}_device_id'.format(each_option_default['id']),
                            device_id)
                    setattr(self,
                            '{}_measurement_id'.format(each_option_default['id']),
                            measurement_id)

                elif each_option_default['type'] == 'select_measurement_channel':
                    setattr(self,
                            '{}_device_id'.format(each_option_default['id']),
                            device_id)
                    setattr(self,
                            '{}_measurement_id'.format(each_option_default['id']),
                            measurement_id)
                    setattr(self,
                            '{}_channel_id'.format(each_option_default['id']),
                            channel_id)

                elif each_option_default['type'] in ['select_type_measurement',
                                                     'select_type_unit']:
                    setattr(self, each_option_default['id'], str(option_value))

                elif each_option_default['type'] == 'select_device':
                    setattr(self,
                            '{}_id'.format(each_option_default['id']),
                            str(option_value))

                elif each_option_default['type'] in ['message', 'new_line']:
                    pass

                else:
                    self.logger.error(
                        "setup_custom_options_csv() Unknown custom_option type '{}'".format(each_option_default['type']))
            except Exception:
                self.logger.exception("Error parsing custom_options")

    def setup_custom_options_json(self, custom_options, custom_controller):
        for each_option_default in custom_options:
            try:
                required = False
                custom_option_set = False
                error = []

                if 'type' not in each_option_default:
                    error.append("'type' not found in custom_options")
                if ('id' not in each_option_default and
                        ('type' in each_option_default and
                         each_option_default['type'] not in ['new_line', 'message'])):
                    error.append("'id' not found in custom_options")
                if ('default_value' not in each_option_default and
                        ('type' in each_option_default and
                         each_option_default['type'] != 'new_line')):
                    error.append("'default_value' not found in custom_options")

                for each_error in error:
                    self.logger.error(each_error)
                if error:
                    return

                if each_option_default['type'] in ['new_line', 'message']:
                    continue

                if 'required' in each_option_default and each_option_default['required']:
                    required = True

                # set default value
                option_value = each_option_default['default_value']
                device_id = None
                measurement_id = None
                channel_id = None

                if not hasattr(custom_controller, 'custom_options'):
                    self.logger.error("custom_controller missing attribute custom_options")
                    return

                if getattr(custom_controller, 'custom_options'):
                    for each_option, each_value in json.loads(getattr(custom_controller, 'custom_options')).items():
                        if each_option == each_option_default['id']:
                            custom_option_set = True

                            if (each_option_default['type'] == 'select_measurement' and
                                    len(each_value.split(',')) > 1):
                                device_id = each_value.split(',')[0]
                                measurement_id = each_value.split(',')[1]
                            if (each_option_default['type'] == 'select_measurement_channel' and
                                    len(each_value.split(',')) > 2):
                                device_id = each_value.split(',')[0]
                                measurement_id = each_value.split(',')[1]
                                channel_id = each_value.split(',')[2]
                            else:
                                option_value = each_value

                if required and not custom_option_set:
                    self.logger.error(
                        "Option '{}' required but was not found to be set by the user. Setting to default.".format(
                            each_option_default['id']))

                if each_option_default['type'] in ['integer',
                                                   'float',
                                                   'bool',
                                                   'multiline_text',
                                                   'select_multi_measurement',
                                                   'text',
                                                   'select']:
                    setattr(self, each_option_default['id'], option_value)

                elif each_option_default['type'] == 'select_measurement':
                    setattr(self,
                            '{}_device_id'.format(each_option_default['id']),
                            device_id)
                    setattr(self,
                            '{}_measurement_id'.format(each_option_default['id']),
                            measurement_id)

                elif each_option_default['type'] == 'select_measurement_channel':
                    setattr(self,
                            '{}_device_id'.format(each_option_default['id']),
                            device_id)
                    setattr(self,
                            '{}_measurement_id'.format(each_option_default['id']),
                            measurement_id)
                    setattr(self,
                            '{}_channel_id'.format(each_option_default['id']),
                            channel_id)

                elif each_option_default['type'] == 'select_type_measurement':
                    setattr(self, each_option_default['id'], str(option_value))

                elif each_option_default['type'] == 'select_type_unit':
                    setattr(self, each_option_default['id'], str(option_value))

                elif each_option_default['type'] == 'select_device':
                    setattr(self,
                            '{}_id'.format(each_option_default['id']),
                            str(option_value))

                elif each_option_default['type'] in ['message', 'new_line']:
                    pass

                else:
                    self.logger.error(
                        "setup_custom_options_json() Unknown option type '{}'".format(each_option_default['type']))
            except Exception:
                self.logger.exception("Error parsing options")

    def setup_custom_channel_options_json(self, custom_options, custom_controller_channels):
        dict_values = {}
        for each_option_default in custom_options:
            try:
                dict_values[each_option_default['id']] = OrderedDict()
                required = False
                custom_option_set = False
                error = []
                if 'type' not in each_option_default:
                    error.append("'type' not found in custom_options")
                if 'id' not in each_option_default:
                    error.append("'id' not found in custom_options")
                if 'default_value' not in each_option_default:
                    error.append("'default_value' not found in custom_options")
                for each_error in error:
                    self.logger.error(each_error)
                if error:
                    return

                if 'required' in each_option_default and each_option_default['required']:
                    required = True

                for each_channel in custom_controller_channels:
                    channel = each_channel.channel

                    # set default value
                    dict_values[each_option_default['id']][channel] = each_option_default['default_value']

                    if each_option_default['type'] == 'select_measurement':
                        dict_values[each_option_default['id']][channel] = {}
                        dict_values[each_option_default['id']][channel]['device_id'] = None
                        dict_values[each_option_default['id']][channel]['measurement_id'] = None
                        dict_values[each_option_default['id']][channel]['channel_id'] = None

                    if not hasattr(each_channel, 'custom_options'):
                        self.logger.error("custom_controller missing attribute custom_options")
                        return

                    if getattr(each_channel, 'custom_options'):
                        for each_option, each_value in json.loads(getattr(each_channel, 'custom_options')).items():
                            if each_option == each_option_default['id']:
                                custom_option_set = True

                                if each_option_default['type'] == 'select_measurement':
                                    if len(each_value.split(',')) > 1:
                                        dict_values[each_option_default['id']][channel]['device_id'] = each_value.split(',')[0]
                                        dict_values[each_option_default['id']][channel]['measurement_id'] = each_value.split(',')[1]
                                    if len(each_value.split(',')) > 2:
                                        dict_values[each_option_default['id']][channel]['channel_id'] = each_value.split(',')[2]
                                else:
                                    dict_values[each_option_default['id']][channel] = each_value

                    if required and not custom_option_set:
                        self.logger.error(
                            "Option '{}' required but was not found to be set by the user".format(
                                each_option_default['id']))
            except Exception:
                self.logger.exception("Error parsing options")

        return dict_values

    def lock_acquire(self, lockfile, timeout):
        self.logger.debug("Acquiring lock")
        return self.lockfile.lock_acquire(lockfile, timeout)

    def lock_locked(self, lockfile):
        return self.lockfile.lock_locked(lockfile)

    def lock_release(self, lockfile):
        self.logger.debug("Releasing lock")
        self.lockfile.lock_release(lockfile)

    def _delete_custom_option(self, controller, unique_id, option):
        try:
            with session_scope(FARM_DB_PATH) as new_session:
                mod_function = new_session.query(controller).filter(
                    controller.unique_id == unique_id).first()
                try:
                    dict_custom_options = json.loads(mod_function.custom_options)
                except:
                    dict_custom_options = {}
                dict_custom_options.pop(option)
                mod_function.custom_options = json.dumps(dict_custom_options)
                new_session.commit()
        except Exception:
            self.logger.exception("delete_custom_option")

    def _set_custom_option(self, controller, unique_id, option, value):
        try:
            with session_scope(FARM_DB_PATH) as new_session:
                mod_function = new_session.query(controller).filter(
                    controller.unique_id == unique_id).first()
                try:
                    dict_custom_options = json.loads(mod_function.custom_options)
                except:
                    dict_custom_options = {}
                dict_custom_options[option] = value
                mod_function.custom_options = json.dumps(dict_custom_options)
                new_session.commit()
        except Exception:
            self.logger.exception("set_custom_option")

    @staticmethod
    def _get_custom_option(custom_options, option):
        try:
            dict_custom_options = json.loads(custom_options)
        except:
            dict_custom_options = {}
        if option in dict_custom_options:
            return dict_custom_options[option]

    @staticmethod
    def get_last_measurement(device_id, measurement_id, max_age=None):
        return get_last_measurement(device_id, measurement_id, max_age=max_age)

    @staticmethod
    def get_past_measurements(device_id, measurement_id, max_age=None):
        return get_past_measurements(device_id, measurement_id, max_age=max_age)

    @staticmethod
    def get_output_channel_from_channel_id(channel_id):
        """Return channel number from channel ID"""
        output_channel = db_retrieve_table_daemon(
            OutputChannel).filter(
            OutputChannel.unique_id == channel_id).first()
        if output_channel:
            return output_channel.channel
