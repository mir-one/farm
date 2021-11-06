# coding=utf-8
""" collection of Page endpoints """
import logging
import os

import flask_login
from flask import current_app
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from flask.blueprints import Blueprint

from farm.config import INSTALL_DIRECTORY
from farm.databases.models import Camera
from farm.databases.models import CustomController
from farm.databases.models import DisplayOrder
from farm.databases.models import Input
from farm.databases.models import LCD
from farm.databases.models import Math
from farm.databases.models import Measurement
from farm.databases.models import Method
from farm.databases.models import Misc
from farm.databases.models import Output
from farm.databases.models import OutputChannel
from farm.databases.models import PID
from farm.databases.models import Unit
from farm.databases.models import User
from farm.farm_flask.extensions import db
from farm.farm_flask.forms import forms_output
from farm.farm_flask.routes_static import inject_variables
from farm.farm_flask.utils import utils_general
from farm.farm_flask.utils import utils_output
from farm.utils.outputs import output_types
from farm.utils.outputs import parse_output_information
from farm.utils.system_pi import add_custom_measurements
from farm.utils.system_pi import add_custom_units
from farm.utils.system_pi import csv_to_list_of_str
from farm.utils.system_pi import parse_custom_option_values_json
from farm.utils.system_pi import parse_custom_option_values_output_channels_json

logger = logging.getLogger('farm.farm_flask.routes_output')

blueprint = Blueprint('routes_output',
                      __name__,
                      static_folder='../static',
                      template_folder='../templates')


@blueprint.context_processor
@flask_login.login_required
def inject_dictionary():
    return inject_variables()


@blueprint.route('/output_submit', methods=['POST'])
@flask_login.login_required
def page_output_submit():
    """ Submit form for Output page """
    messages = {
        "success": [],
        "info": [],
        "warning": [],
        "error": []
    }
    page_refresh = False
    output_id = None
    dep_unmet = ''
    dep_name = ''
    dep_list = []
    dep_message = ''
    size_y = None

    form_add_output = forms_output.OutputAdd()
    form_mod_output = forms_output.OutputMod()

    if not utils_general.user_has_permission('edit_controllers'):
        messages["error"].append("Your permissions do not allow this action")

    if not messages["error"]:
        if form_add_output.output_add.data:
            (messages,
             dep_name,
             dep_list,
             dep_message,
             output_id,
             size_y) = utils_output.output_add(
                form_add_output, request.form)
            if dep_list:
                dep_unmet = form_add_output.output_type.data.split(',')[0]
        elif form_mod_output.output_mod.data:
            messages, page_refresh = utils_output.output_mod(
                form_mod_output, request.form)
            output_id = form_mod_output.output_id.data
        elif form_mod_output.output_delete.data:
            messages = utils_output.output_del(form_mod_output)
            output_id = form_mod_output.output_id.data

        # Custom action
        else:
            custom_button = False
            for key in request.form.keys():
                if key.startswith('custom_button_'):
                    custom_button = True
                    break
            if custom_button:
                messages = utils_general.custom_action(
                    "Output",
                    parse_output_information(),
                    form_mod_output.output_id.data,
                    request.form)
            else:
                messages["error"].append("Unknown output directive")

    return jsonify(data={
        'output_id': output_id,
        'dep_name': dep_name,
        'dep_list': dep_list,
        'dep_unmet': dep_unmet,
        'dep_message': dep_message,
        'size_y': size_y,
        'messages': messages,
        "page_refresh": page_refresh
    })


@blueprint.route('/save_output_layout', methods=['POST'])
def save_output_layout():
    """Save positions of outputs"""
    if not utils_general.user_has_permission('edit_controllers'):
        return redirect(url_for('routes_general.home'))
    data = request.get_json()
    keys = ('id', 'y')
    for each_output in data:
        if all(k in each_output for k in keys):
            output_mod = Output.query.filter(
                Output.unique_id == each_output['id']).first()
            if output_mod:
                output_mod.position_y = each_output['y']
    db.session.commit()
    return "success"


@blueprint.route('/output', methods=('GET', 'POST'))
@flask_login.login_required
def page_output():
    """ Display Output page options """
    output_type = request.args.get('output_type', None)
    output_id = request.args.get('output_id', None)
    each_output = None
    if output_type in ['entry', 'options'] and output_id != '0':
        each_output = Output.query.filter(Output.unique_id == output_id).first()

    camera = Camera.query.all()
    function = CustomController.query.all()
    input_dev = Input.query.all()
    lcd = LCD.query.all()
    math = Math.query.all()
    method = Method.query.all()
    misc = Misc.query.first()
    output = Output.query.all()
    output_channel = OutputChannel.query.all()
    pid = PID.query.all()
    user = User.query.all()

    dict_outputs = parse_output_information()

    form_add_output = forms_output.OutputAdd()
    form_mod_output = forms_output.OutputMod()

    # Generate all measurement and units used
    dict_measurements = add_custom_measurements(Measurement.query.all())
    dict_units = add_custom_units(Unit.query.all())

    choices_function = utils_general.choices_functions(
        function, dict_units, dict_measurements)
    choices_input = utils_general.choices_inputs(
        input_dev, dict_units, dict_measurements)
    choices_input_devices = utils_general.choices_input_devices(input_dev)
    choices_math = utils_general.choices_maths(
        math, dict_units, dict_measurements)
    choices_method = utils_general.choices_methods(method)
    choices_output = utils_general.choices_outputs(
        output, dict_units, dict_measurements)
    choices_output_channels = utils_general.choices_outputs_channels(
        output, output_channel, dict_outputs)
    choices_pid = utils_general.choices_pids(
        pid, dict_units, dict_measurements)

    custom_options_values_outputs = parse_custom_option_values_json(
        output, dict_controller=dict_outputs)
    custom_options_values_output_channels = parse_custom_option_values_output_channels_json(
        output_channel, dict_controller=dict_outputs, key_name='custom_channel_options')

    custom_actions = {}
    for each_output in output:
        if 'custom_actions' in dict_outputs[each_output.output_type]:
            custom_actions[each_output.output_type] = True

    # Create dict of Input names
    names_output = {}
    all_elements = output
    for each_element in all_elements:
        names_output[each_element.unique_id] = '[{id}] {name}'.format(
            id=each_element.unique_id.split('-')[0], name=each_element.name)

    # Create list of file names from the output_options directory
    # Used in generating the correct options for each output/device
    output_templates = []
    output_path = os.path.join(
        INSTALL_DIRECTORY,
        'farm/farm_flask/templates/pages/output_options')
    for (_, _, file_names) in os.walk(output_path):
        output_templates.extend(file_names)
        break

    display_order_output = csv_to_list_of_str(DisplayOrder.query.first().output)

    output_variables = {}
    for each_output in output:
        output_variables[each_output.unique_id] = {}
        for each_channel in dict_outputs[each_output.output_type]['channels_dict']:
            output_variables[each_output.unique_id][each_channel] = {}
            output_variables[each_output.unique_id][each_channel]['amps'] = None
            output_variables[each_output.unique_id][each_channel]['trigger_startup'] = None

    # Find FTDI devices
    ftdi_devices = []
    if not current_app.config['TESTING']:
        for each_output in output:
            if each_output.interface == "FTDI":
                from farm.devices.atlas_scientific_ftdi import get_ftdi_device_list
                ftdi_devices = get_ftdi_device_list()
                break

    if not output_type:
        return render_template('pages/output.html',
                               camera=camera,
                               choices_function=choices_function,
                               choices_input=choices_input,
                               choices_input_devices=choices_input_devices,
                               choices_math=choices_math,
                               choices_method=choices_method,
                               choices_output=choices_output,
                               choices_output_channels=choices_output_channels,
                               choices_pid=choices_pid,
                               custom_actions=custom_actions,
                               custom_options_values_outputs=custom_options_values_outputs,
                               custom_options_values_output_channels=custom_options_values_output_channels,
                               dict_outputs=dict_outputs,
                               display_order_output=display_order_output,
                               form_add_output=form_add_output,
                               form_mod_output=form_mod_output,
                               ftdi_devices=ftdi_devices,
                               lcd=lcd,
                               misc=misc,
                               names_output=names_output,
                               output=output,
                               output_channel=output_channel,
                               output_types=output_types(),
                               output_templates=output_templates,
                               output_variables=output_variables,
                               user=user)
    elif output_type == 'entry':
        return render_template('pages/output_entry.html',
                               camera=camera,
                               choices_function=choices_function,
                               choices_input=choices_input,
                               choices_input_devices=choices_input_devices,
                               choices_math=choices_math,
                               choices_method=choices_method,
                               choices_output=choices_output,
                               choices_output_channels=choices_output_channels,
                               choices_pid=choices_pid,
                               custom_actions=custom_actions,
                               custom_options_values_outputs=custom_options_values_outputs,
                               custom_options_values_output_channels=custom_options_values_output_channels,
                               dict_outputs=dict_outputs,
                               display_order_output=display_order_output,
                               each_output=each_output,
                               form_add_output=form_add_output,
                               form_mod_output=form_mod_output,
                               ftdi_devices=ftdi_devices,
                               lcd=lcd,
                               misc=misc,
                               names_output=names_output,
                               output=output,
                               output_channel=output_channel,
                               output_types=output_types(),
                               output_templates=output_templates,
                               output_variables=output_variables,
                               user=user)
    elif output_type == 'options':
        return render_template('pages/output_options.html',
                               camera=camera,
                               choices_function=choices_function,
                               choices_input=choices_input,
                               choices_input_devices=choices_input_devices,
                               choices_math=choices_math,
                               choices_method=choices_method,
                               choices_output=choices_output,
                               choices_output_channels=choices_output_channels,
                               choices_pid=choices_pid,
                               custom_actions=custom_actions,
                               custom_options_values_outputs=custom_options_values_outputs,
                               custom_options_values_output_channels=custom_options_values_output_channels,
                               dict_outputs=dict_outputs,
                               display_order_output=display_order_output,
                               each_output=each_output,
                               form_add_output=form_add_output,
                               form_mod_output=form_mod_output,
                               ftdi_devices=ftdi_devices,
                               lcd=lcd,
                               misc=misc,
                               names_output=names_output,
                               output=output,
                               output_channel=output_channel,
                               output_types=output_types(),
                               output_templates=output_templates,
                               output_variables=output_variables,
                               user=user)
