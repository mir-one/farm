# coding=utf-8
import logging
import traceback

import flask_login
from flask_accept import accept
from flask_restx import Resource
from flask_restx import abort
from flask_restx import fields

from farm.databases.models import CustomController
from farm.databases.models import DeviceMeasurements
from farm.databases.models import FunctionChannel
from farm.databases.models.controller import FunctionChannelSchema
from farm.databases.models.controller import FunctionSchema
from farm.databases.models.measurement import DeviceMeasurementsSchema
from farm.farm_flask.api import api
from farm.farm_flask.api import default_responses
from farm.farm_flask.api.sql_schema_fields import device_measurement_fields
from farm.farm_flask.api.sql_schema_fields import function_channel_fields
from farm.farm_flask.api.sql_schema_fields import function_fields
from farm.farm_flask.api.utils import get_from_db
from farm.farm_flask.api.utils import return_list_of_dictionaries
from farm.farm_flask.utils import utils_general

logger = logging.getLogger(__name__)

ns_function = api.namespace('functions', description='Function operations')

function_single_fields = api.model('Function Status Fields', {
    'function settings': fields.Nested(function_fields),
    'function channels': fields.List(fields.Nested(function_channel_fields)),
    'device measurements': fields.List(fields.Nested(device_measurement_fields)),
})

function_list_fields = api.model('Function Fields List', {
    'function settings': fields.List(fields.Nested(function_fields)),
    'function channels': fields.List(fields.Nested(function_channel_fields))
})


@ns_function.route('/')
@ns_function.doc(security='apikey', responses=default_responses)
class Functions(Resource):
    """Function information"""

    @accept('application/vnd.farm.v1+json')
    @ns_function.marshal_with(function_list_fields)
    @flask_login.login_required
    def get(self):
        """Show all function settings"""
        if not utils_general.user_has_permission('view_settings'):
            abort(403)
        try:
            list_data = get_from_db(FunctionSchema, CustomController)
            list_channels = get_from_db(FunctionChannelSchema, FunctionChannel)
            if list_data:
                return {'function settings': list_data,
                        'function channels': list_channels}, 200
        except Exception:
            abort(500,
                  message='An exception occurred',
                  error=traceback.format_exc())


@ns_function.route('/<string:unique_id>')
@ns_function.doc(
    security='apikey',
    responses=default_responses,
    params={'unique_id': 'The unique ID of the function'}
)
class SettingsFunctionsUniqueID(Resource):
    """Interacts with function settings in the SQL database"""

    @accept('application/vnd.farm.v1+json')
    @ns_function.marshal_with(function_single_fields)
    @flask_login.login_required
    def get(self, unique_id):
        """Show the settings for an function"""
        if not utils_general.user_has_permission('view_settings'):
            abort(403)
        try:
            list_data = get_from_db(FunctionSchema, CustomController, unique_id=unique_id)

            function_channel_schema = FunctionChannelSchema()
            list_channels = return_list_of_dictionaries(
                function_channel_schema.dump(
                    FunctionChannel.query.filter_by(
                        function_id=unique_id).all(), many=True))

            measure_schema = DeviceMeasurementsSchema()
            list_measurements = return_list_of_dictionaries(
                measure_schema.dump(
                    DeviceMeasurements.query.filter_by(
                        device_id=unique_id).all(), many=True))

            return {'function settings': list_data,
                    'function channels': list_channels,
                    'device measurements': list_measurements}, 200
        except Exception:
            abort(500,
                  message='An exception occurred',
                  error=traceback.format_exc())
