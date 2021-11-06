# coding=utf-8
import datetime
import json

from flask_babel import lazy_gettext

from farm.config_translations import TRANSLATIONS
from farm.databases.models import Conversion
from farm.databases.models import InputChannel
from farm.inputs.base_input import AbstractInput
from farm.utils.constraints_pass import constraints_pass_positive_value
from farm.utils.database import db_retrieve_table_daemon
from farm.utils.influx import add_measurements_influxdb
from farm.utils.influx import parse_measurement

# Measurements
measurements_dict = {}

# Channels
channels_dict = {
    0: {}
}

# Input information
INPUT_INFORMATION = {
    'input_name_unique': 'MQTT_PAHO_JSON',
    'input_manufacturer': 'Farm',
    'input_name': 'MQTT Subscribe (JSON payload)',
    'input_library': 'paho-mqtt, jmespath',
    'measurements_name': 'Variable measurements',
    'measurements_dict': measurements_dict,
    'channels_dict': channels_dict,

    'measurements_variable_amount': True,
    'channel_quantity_same_as_measurements': True,
    'measurements_use_same_timestamp': False,
    'listener': True,

    'message': 'A single topic is subscribed to and the returned JSON payload contains one or '
               'more key/value pairs. The given JSON Key is used as a JMESPATH expression to find the '
               'corresponding value that will be stored for that channel. Be sure you select and '
               'save the Measurement Unit for each channel. Once the unit has been saved, '
               'you can convert to other units in the Convert Measurement section.'
               ' Example expressions for jmespath (https://jmespath.org) include '
               '<i>temperature</i>, <i>sensors[0].temperature</i>, and <i>bathroom.temperature</i> which refer to '
               'the temperature as a direct key within the first entry of sensors or as a subkey '
               'of bathroom, respectively. Jmespath elements and keys that contain special characters '
               'have to be enclosed in double quotes, e.g. <i>"sensor-1".temperature</i>.',

    'options_enabled': [
        'measurements_select'
    ],
    'options_disabled': ['interface'],

    'interfaces': ['Farm'],

    'dependencies_module': [
        ('pip-pypi', 'paho', 'paho-mqtt==1.5.1'),
        ('pip-pypi', 'jmespath', 'jmespath==0.10.0')
    ],

    'custom_options': [
        {
            'id': 'mqtt_hostname',
            'type': 'text',
            'default_value': 'localhost',
            'required': True,
            'name': TRANSLATIONS["host"]["title"],
            'phrase': TRANSLATIONS["host"]["phrase"]
        },
        {
            'id': 'mqtt_port',
            'type': 'integer',
            'default_value': 1883,
            'required': True,
            'name': TRANSLATIONS["port"]["title"],
            'phrase': TRANSLATIONS["port"]["phrase"]
        },
        {
            'id': 'mqtt_channel',
            'type': 'text',
            'default_value': 'mqtt/test/input',
            'required': True,
            'name': 'Topic',
            'phrase': 'The topic to subscribe to'
        },
        {
            'id': 'mqtt_keepalive',
            'type': 'integer',
            'default_value': 60,
            'required': True,
            'constraints_pass': constraints_pass_positive_value,
            'name': lazy_gettext('Keep Alive'),
            'phrase': 'Maximum amount of time between received signals. Set to 0 to disable.'
        },
        {
            'id': 'mqtt_clientid',
            'type': 'text',
            'default_value': 'farm_mqtt_client',
            'required': True,
            'name': 'Client ID',
            'phrase': 'Unique client ID for connecting to the server'
        },
        {
            'id': 'mqtt_login',
            'type': 'bool',
            'default_value': False,
            'name': 'Use Login',
            'phrase': 'Send login credentials'
        },
        {
            'id': 'mqtt_use_tls',
            'type': 'bool',
            'default_value': False,
            'name': 'Use TLS',
            'phrase': 'Send login credentials using TLS'
        },
        {
            'id': 'mqtt_username',
            'type': 'text',
            'default_value': 'user',
            'required': False,
            'name': lazy_gettext('Username'),
            'phrase': lazy_gettext('Username for connecting to the server')
        },
        {
            'id': 'mqtt_password',
            'type': 'text',
            'default_value': '',
            'required': False,
            'name': lazy_gettext('Password'),
            'phrase': 'Password for connecting to the server. Leave blank to disable.'
        }
    ],

    'custom_channel_options': [
        {
            'id': 'name',
            'type': 'text',
            'default_value': '',
            'required': False,
            'name': TRANSLATIONS['name']['title'],
            'phrase': TRANSLATIONS['name']['phrase']
        },
        {
            'id': 'json_name',
            'type': 'text',
            'default_value': '',
            'required': True,
            'name': 'JSON Key',
            'phrase': 'JMES Path expression to find value in JSON response'
        }
    ]
}


class InputModule(AbstractInput):
    """ A sensor support class that retrieves stored data from MQTT """

    def __init__(self, input_dev, testing=False):
        super(InputModule, self).__init__(input_dev, testing=testing, name=__name__)

        self.client = None
        self.jmespath = None
        self.options_channels = None

        self.mqtt_hostname = None
        self.mqtt_port = None
        self.mqtt_channel = None
        self.mqtt_keepalive = None
        self.mqtt_clientid = None
        self.mqtt_login = None
        self.mqtt_use_tls = None
        self.mqtt_username = None
        self.mqtt_password = None

        if not testing:
            self.setup_custom_options(
                INPUT_INFORMATION['custom_options'], input_dev)
            self.initialize_input()

    def initialize_input(self):
        import paho.mqtt.client as mqtt
        import jmespath

        self.jmespath = jmespath

        input_channels = db_retrieve_table_daemon(
            InputChannel).filter(InputChannel.input_id == self.input_dev.unique_id).all()
        self.options_channels = self.setup_custom_channel_options_json(
            INPUT_INFORMATION['custom_channel_options'], input_channels)

        self.client = mqtt.Client(self.mqtt_clientid)
        self.logger.debug("Client created with ID {}".format(self.mqtt_clientid))
        if self.mqtt_login:
            if not self.mqtt_password:
                self.mqtt_password = None
            self.logger.debug("Sending username and password credentials")
            self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
        if self.mqtt_use_tls:
            self.client.tls_set()

    def listener(self):
        self.callbacks_connect()
        self.connect()
        self.subscribe()
        self.client.loop_start()

    def callbacks_connect(self):
        """ Connect the callback functions """
        try:
            self.logger.debug("Connecting MQTT callback functions")
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.on_subscribe = self.on_subscribe
            self.client.on_disconnect = self.on_disconnect
            self.logger.debug("MQTT callback functions connected")
        except:
            self.logger.error("Unable to connect mqtt callback functions")

    def connect(self):
        """ Set up the connection to the MQTT Server """
        try:
            self.client.connect(
                self.mqtt_hostname,
                port=self.mqtt_port,
                keepalive=self.mqtt_keepalive)
            self.logger.info("Connected to {} as {}".format(
                self.mqtt_hostname, self.mqtt_clientid))
        except:
            self.logger.error("Could not connect to mqtt host: {}:{}".format(
                self.mqtt_hostname, self.mqtt_port))

    def subscribe(self):
        """ Subscribe to the proper MQTT channel to listen to """
        try:
            self.logger.debug("Subscribing to MQTT topic '{}'".format(
                self.mqtt_channel))
            self.client.subscribe(self.mqtt_channel)
        except:
            self.logger.error("Could not subscribe to MQTT channel '{}'".format(
                self.mqtt_channel))

    def on_connect(self, client, obj, flags, rc):
        self.logger.debug("Connected to '{}'. Return code: {}".format(
            self.mqtt_channel, rc))

    def on_subscribe(self, client, obj, mid, granted_qos):
        self.logger.debug("Subscribed to mqtt topic: {}, {}, {}".format(
            self.mqtt_channel, mid, granted_qos))

    def on_log(self, mqttc, obj, level, string):
        self.logger.info("Log: {}".format(string))

    def on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode()
            self.logger.debug(
                "Received message: topic: {}, payload: {}".format(
                    msg.topic, payload))
        except Exception as exc:
            self.logger.error(
                "Payload could not be decoded: {}".format(exc))
            return

        try:
            json_values = json.loads(payload)
        except ValueError as err:
            self.logger.error(
                "Error parsing payload '{}' as JSON: {} ".format(
                    msg.payload.decode(), err))
            return

        datetime_utc = datetime.datetime.utcnow()
        measurement = {}
        for each_channel in self.channels_measurement:
            json_name = self.options_channels['json_name'][each_channel]
            self.logger.debug("Searching JSON for {}".format(json_name))

            try:
                jmesexpression = self.jmespath.compile(json_name)
                value = jmesexpression.search(json_values)
                self.logger.debug(
                    "Found key: {}, value: {}".format(json_name, value))
                measurement[each_channel] = {}
                measurement[each_channel]['measurement'] = self.channels_measurement[each_channel].measurement
                measurement[each_channel]['unit'] = self.channels_measurement[each_channel].unit
                measurement[each_channel]['value'] = value
                measurement[each_channel]['timestamp_utc'] = datetime_utc
                self.add_measurement_influxdb(each_channel, measurement)
            except Exception as err:
                self.logger.error(
                    "Error in JSON '{}' finding '{}': {}".format(
                        json_values, json_name, err))

    def add_measurement_influxdb(self, channel, measurement):
        # Convert value/unit is conversion_id present and valid
        if self.channels_conversion[channel]:
            conversion = db_retrieve_table_daemon(
                Conversion,
                unique_id=self.channels_measurement[channel].conversion_id)
            if conversion:
                meas = parse_measurement(
                    self.channels_conversion[channel],
                    self.channels_measurement[channel],
                    measurement,
                    channel,
                    measurement[channel],
                    timestamp=measurement[channel]['timestamp_utc'])

                measurement[channel]['measurement'] = meas[channel]['measurement']
                measurement[channel]['unit'] = meas[channel]['unit']
                measurement[channel]['value'] = meas[channel]['value']

        if measurement:
            self.logger.debug(
                "Adding measurement to influxdb: {}".format(measurement))
            add_measurements_influxdb(
                self.unique_id,
                measurement,
                use_same_timestamp=INPUT_INFORMATION['measurements_use_same_timestamp'])

    def on_disconnect(self, client, userdata, rc=0):
        self.logger.debug("Disconnected. Return code: {}".format(rc))

    def stop_input(self):
        """ Called when Input is deactivated """
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()
