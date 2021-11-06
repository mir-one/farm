# coding=utf-8
""" collection of Page endpoints """
import calendar
import datetime
import glob
import logging
import os
import resource
import socket
import subprocess
import sys
import time
from collections import OrderedDict
from importlib import import_module

import flask_login
from flask import current_app
from flask import flash
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import send_file
from flask import url_for
from flask.blueprints import Blueprint
from flask_babel import gettext
from sqlalchemy import and_

from farm.config import ALEMBIC_VERSION
from farm.config import BACKUP_LOG_FILE
from farm.config import CAMERA_INFO
from farm.config import DAEMON_LOG_FILE
from farm.config import DAEMON_PID_FILE
from farm.config import DEPENDENCY_LOG_FILE
from farm.config import FRONTEND_PID_FILE
from farm.config import HTTP_ACCESS_LOG_FILE
from farm.config import HTTP_ERROR_LOG_FILE
from farm.config import KEEPUP_LOG_FILE
from farm.config import LCD_INFO
from farm.config import LOGIN_LOG_FILE
from farm.config import FARM_VERSION
from farm.config import RESTORE_LOG_FILE
from farm.config import THEMES_DARK
from farm.config import UPGRADE_LOG_FILE
from farm.config import USAGE_REPORTS_PATH
from farm.config_devices_units import MEASUREMENTS
from farm.databases.models import AlembicVersion
from farm.databases.models import Camera
from farm.databases.models import Conversion
from farm.databases.models import CustomController
from farm.databases.models import DeviceMeasurements
from farm.databases.models import DisplayOrder
from farm.databases.models import EnergyUsage
from farm.databases.models import Input
from farm.databases.models import LCD
from farm.databases.models import LCDData
from farm.databases.models import Math
from farm.databases.models import Measurement
from farm.databases.models import Misc
from farm.databases.models import NoteTags
from farm.databases.models import Notes
from farm.databases.models import Output
from farm.databases.models import OutputChannel
from farm.databases.models import PID
from farm.databases.models import Unit
from farm.databases.models import Widget
from farm.devices.camera import camera_record
from farm.farm_client import DaemonControl
from farm.farm_client import daemon_active
from farm.farm_flask.extensions import db
from farm.farm_flask.forms import forms_camera
from farm.farm_flask.forms import forms_lcd
from farm.farm_flask.forms import forms_misc
from farm.farm_flask.forms import forms_notes
from farm.farm_flask.routes_static import inject_variables
from farm.farm_flask.utils import utils_camera
from farm.farm_flask.utils import utils_dashboard
from farm.farm_flask.utils import utils_export
from farm.farm_flask.utils import utils_general
from farm.farm_flask.utils import utils_lcd
from farm.farm_flask.utils import utils_misc
from farm.farm_flask.utils import utils_notes
from farm.farm_flask.utils.utils_general import return_dependencies
from farm.utils.functions import parse_function_information
from farm.utils.inputs import list_analog_to_digital_converters
from farm.utils.inputs import parse_input_information
from farm.utils.outputs import output_types
from farm.utils.outputs import parse_output_information
from farm.utils.system_pi import add_custom_measurements
from farm.utils.system_pi import add_custom_units
from farm.utils.system_pi import csv_to_list_of_str
from farm.utils.system_pi import parse_custom_option_values
from farm.utils.system_pi import parse_custom_option_values_output_channels_json
from farm.utils.system_pi import return_measurement_info
from farm.utils.tools import calc_energy_usage
from farm.utils.tools import return_energy_usage
from farm.utils.tools import return_output_usage

logger = logging.getLogger('farm.farm_flask.routes_page')

blueprint = Blueprint('routes_page',
                      __name__,
                      static_folder='../static',
                      template_folder='../templates')


@blueprint.context_processor
@flask_login.login_required
def inject_dictionary():
    return inject_variables()


@blueprint.context_processor
def inject_functions():
    def epoch_to_time_string(epoch):
        return datetime.datetime.fromtimestamp(epoch).strftime(
            "%Y-%m-%d %H:%M:%S")

    def get_note_tag_from_unique_id(tag_unique_id):
        tag = NoteTags.query.filter(NoteTags.unique_id == tag_unique_id).first()
        if tag and tag.name:
            return tag.name
        else:
            return 'TAG ERROR'

    def utc_to_local_time(utc_dt):
        utc_timestamp = calendar.timegm(utc_dt.timetuple())
        return str(datetime.datetime.fromtimestamp(utc_timestamp))

    return dict(epoch_to_time_string=epoch_to_time_string,
                get_note_tag_from_unique_id=get_note_tag_from_unique_id,
                utc_to_local_time=utc_to_local_time)


@blueprint.route('/camera_submit', methods=['POST'])
@flask_login.login_required
def page_camera_submit():
    messages = {
        "success": [],
        "info": [],
        "warning": [],
        "error": []
    }
    page_refresh = False
    dep_unmet = None

    form_camera = forms_camera.Camera()

    if not utils_general.user_has_permission('edit_controllers'):
        messages["error"].append("Your permissions do not allow this action")

    if not messages["error"]:
        if form_camera.camera_mod.data:
            messages = utils_camera.camera_mod(form_camera)
        elif form_camera.camera_del.data:
            messages = utils_camera.camera_del(form_camera)
        elif form_camera.timelapse_generate.data:
            messages = utils_camera.camera_timelapse_video(form_camera)
        else:
            messages["error"].append("Unknown camera directive")

    if page_refresh:
        for each_error in messages["error"]:
            flash(each_error, "error")
        for each_warn in messages["warning"]:
            flash(each_warn, "warning")
        for each_info in messages["info"]:
            flash(each_info, "info")
        for each_success in messages["success"]:
            flash(each_success, "success")

    return jsonify(data={
        'camera_id': form_camera.camera_id.data,
        'dep_unmet': dep_unmet,
        'messages': messages,
        'page_refresh': page_refresh
    })


@blueprint.route('/camera', methods=('GET', 'POST'))
@flask_login.login_required
def page_camera():
    """
    Page to start/stop video stream or time-lapse, or capture a still image.
    Displays most recent still image and time-lapse image.
    """
    if not utils_general.user_has_permission('view_camera'):
        return redirect(url_for('routes_general.home'))

    form_camera = forms_camera.Camera()
    camera = Camera.query.all()
    output = Output.query.all()
    output_channel = OutputChannel.query.all()

    opencv_devices = []

    for each_cam in camera:
        if each_cam.library == 'opencv':
            try:
                from farm.devices.camera import count_cameras_opencv
                opencv_devices = count_cameras_opencv()
            except Exception:
                opencv_devices = []
            break

    pi_camera_enabled = False
    try:
        if (not current_app.config['TESTING'] and
                'start_x=1' in open('/boot/config.txt').read()):
            pi_camera_enabled = True
    except IOError as e:
        logger.error("Camera IOError raised in '/camera' endpoint: "
                     "{err}".format(err=e))

    if request.method == 'POST':
        unmet_dependencies = None
        if not utils_general.user_has_permission('edit_controllers'):
            return redirect(url_for('routes_page.page_camera'))

        control = DaemonControl()
        mod_camera = Camera.query.filter(
            Camera.unique_id == form_camera.camera_id.data).first()
        if form_camera.camera_add.data:
            unmet_dependencies = utils_camera.camera_add(form_camera)
        elif form_camera.capture_still.data:
            # If a stream is active, stop the stream to take a photo
            if mod_camera.stream_started:
                camera_stream = import_module(
                    'farm.farm_flask.camera.camera_{lib}'.format(
                        lib=mod_camera.library)).Camera
                if camera_stream(unique_id=mod_camera.unique_id).is_running(mod_camera.unique_id):
                    camera_stream(unique_id=mod_camera.unique_id).stop(mod_camera.unique_id)
                time.sleep(2)
            camera_record('photo', mod_camera.unique_id)
        elif form_camera.start_timelapse.data:
            if mod_camera.stream_started:
                flash(gettext("Cannot start time-lapse if stream is active."), "error")
                return redirect(url_for('routes_page.page_camera'))
            now = time.time()
            mod_camera.timelapse_started = True
            mod_camera.timelapse_start_time = now
            if form_camera.timelapse_runtime_sec.data:
                mod_camera.timelapse_end_time = now + float(form_camera.timelapse_runtime_sec.data)
            else:
                mod_camera.timelapse_end_time = now + 315360000
            mod_camera.timelapse_interval = form_camera.timelapse_interval.data
            mod_camera.timelapse_next_capture = now
            mod_camera.timelapse_capture_number = 0
            db.session.commit()
            control.refresh_daemon_camera_settings()
        elif form_camera.pause_timelapse.data:
            mod_camera.timelapse_paused = True
            db.session.commit()
            control.refresh_daemon_camera_settings()
        elif form_camera.resume_timelapse.data:
            mod_camera.timelapse_paused = False
            db.session.commit()
            control.refresh_daemon_camera_settings()
        elif form_camera.stop_timelapse.data:
            mod_camera.timelapse_started = False
            mod_camera.timelapse_start_time = None
            mod_camera.timelapse_end_time = None
            mod_camera.timelapse_interval = None
            mod_camera.timelapse_next_capture = None
            mod_camera.timelapse_capture_number = None
            db.session.commit()
            control.refresh_daemon_camera_settings()
        elif form_camera.start_stream.data:
            if mod_camera.timelapse_started:
                flash(gettext(
                    "Cannot start stream if time-lapse is active."), "error")
                return redirect(url_for('routes_page.page_camera'))
            else:
                mod_camera.stream_started = True
                db.session.commit()
        elif form_camera.stop_stream.data:
            camera_stream = import_module(
                'farm.farm_flask.camera.camera_{lib}'.format(
                    lib=mod_camera.library)).Camera
            if camera_stream(unique_id=mod_camera.unique_id).is_running(mod_camera.unique_id):
                camera_stream(unique_id=mod_camera.unique_id).stop(mod_camera.unique_id)
            mod_camera.stream_started = False
            db.session.commit()

        if unmet_dependencies:
            return redirect(url_for('routes_admin.admin_dependencies',
                                    device=form_camera.library.data))
        else:
            return redirect(url_for('routes_page.page_camera'))

    # Get the full path and timestamps of latest still and time-lapse images
    (latest_img_still_ts,
     latest_img_still,
     latest_img_tl_ts,
     latest_img_tl,
     time_lapse_imgs) = utils_general.get_camera_image_info()

    time_now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    dict_outputs = parse_output_information()
    choices_output_channels = utils_general.choices_outputs_channels(
        output, output_channel, dict_outputs)

    return render_template('pages/camera.html',
                           camera=camera,
                           camera_info=CAMERA_INFO,
                           choices_output_channels=choices_output_channels,
                           form_camera=form_camera,
                           latest_img_still=latest_img_still,
                           latest_img_still_ts=latest_img_still_ts,
                           latest_img_tl=latest_img_tl,
                           latest_img_tl_ts=latest_img_tl_ts,
                           opencv_devices=opencv_devices,
                           output=output,
                           pi_camera_enabled=pi_camera_enabled,
                           time_lapse_imgs=time_lapse_imgs,
                           time_now=time_now)


@blueprint.route('/notes', methods=('GET', 'POST'))
@flask_login.login_required
def page_notes():
    """
    Notes page
    """
    form_note_add = forms_notes.NoteAdd()
    form_note_options = forms_notes.NoteOptions()
    form_note_mod = forms_notes.NoteMod()
    form_tag_add = forms_notes.TagAdd()
    form_tag_options = forms_notes.TagOptions()
    form_note_show = forms_notes.NotesShow()

    total_notes = Notes.query.count()

    notes = Notes.query.order_by(Notes.id.desc()).limit(10)
    tags = NoteTags.query.all()

    current_date_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if request.method == 'POST':
        if not utils_general.user_has_permission('edit_settings'):
            return redirect(url_for('routes_page.page_notes'))

        if form_note_show.notes_show.data:
            notes = utils_notes.show_notes(form_note_show)
        elif form_note_show.notes_export.data:
            notes, data = utils_notes.export_notes(form_note_show)
            if data:
                # Send zip file to user
                return send_file(
                    data,
                    mimetype='application/zip',
                    as_attachment=True,
                    attachment_filename=
                    'Farm_Notes_{mv}_{host}_{dt}.zip'.format(
                        mv=FARM_VERSION,
                        host=socket.gethostname().replace(' ', ''),
                        dt=datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
                )
        elif form_note_show.notes_import_upload.data:
            utils_notes.import_notes(form_note_show)
        else:
            if form_tag_add.tag_add.data:
                utils_notes.tag_add(form_tag_add)
            elif form_tag_options.tag_rename.data:
                utils_notes.tag_rename(form_tag_options)
            elif form_tag_options.tag_del.data:
                utils_notes.tag_del(form_tag_options)

            elif form_note_add.note_add.data:
                utils_notes.note_add(form_note_add)
            elif form_note_mod.note_save.data:
                utils_notes.note_mod(form_note_mod)
            elif form_note_options.note_del.data:
                utils_notes.note_del(form_note_options)
            elif form_note_options.note_mod.data:
                return redirect(url_for('routes_page.page_note_edit', unique_id=form_note_options.note_unique_id.data))

            return redirect(url_for('routes_page.page_notes'))

    if notes:
        note_count = notes.count()
        notes_all = notes.all()
    else:
        note_count = 0
        notes_all = None
    number_displayed_notes = (note_count, total_notes)

    return render_template('tools/notes.html',
                           form_note_add=form_note_add,
                           form_note_options=form_note_options,
                           form_note_mod=form_note_mod,
                           form_tag_add=form_tag_add,
                           form_tag_options=form_tag_options,
                           form_note_show=form_note_show,
                           notes=notes_all,
                           tags=tags,
                           current_date_time=current_date_time,
                           number_displayed_notes=number_displayed_notes)


@blueprint.route('/note_edit/<unique_id>', methods=('GET', 'POST'))
@flask_login.login_required
def page_note_edit(unique_id):
    """
    Edit note page
    """
    # Used in software tests to verify function is executing as admin
    if unique_id == '0':
        return 'admin logged in'

    this_note = Notes.query.filter(Notes.unique_id == unique_id).first()

    form_note_mod = forms_notes.NoteMod()

    tags = NoteTags.query.all()

    if request.method == 'POST':
        if not utils_general.user_has_permission('edit_settings'):
            return redirect(url_for('routes_page.page_notes'))

        if form_note_mod.note_save.data:
            utils_notes.note_mod(form_note_mod)
        if form_note_mod.file_rename.data:
            utils_notes.file_rename(form_note_mod)
        if form_note_mod.file_del.data:
            utils_notes.file_del(form_note_mod)
        if form_note_mod.note_del.data:
            utils_notes.note_del(form_note_mod)
            return redirect(url_for('routes_page.page_notes'))
        if form_note_mod.note_cancel.data:
            return redirect(url_for('routes_page.page_notes'))

        return redirect(url_for('routes_page.page_note_edit', unique_id=this_note.unique_id))

    form_note_mod.note.data = this_note.note

    return render_template('tools/note_edit.html',
                           form_note_mod=form_note_mod,
                           this_note=this_note,
                           tags=tags)


@blueprint.route('/export', methods=('GET', 'POST'))
@flask_login.login_required
def page_export():
    """
    Export/Import measurement and settings data
    """
    form_export_measurements = forms_misc.ExportMeasurements()
    form_export_settings = forms_misc.ExportSettings()
    form_import_settings = forms_misc.ImportSettings()
    form_export_influxdb = forms_misc.ExportInfluxdb()
    form_import_influxdb = forms_misc.ImportInfluxdb()

    function = CustomController.query.all()
    input_dev = Input.query.all()
    math = Math.query.all()
    output = Output.query.all()

    # Generate all measurement and units used
    dict_measurements = add_custom_measurements(Measurement.query.all())
    dict_units = add_custom_units(Unit.query.all())

    choices_function = utils_general.choices_functions(
        function, dict_units, dict_measurements)
    choices_input = utils_general.choices_inputs(
        input_dev, dict_units, dict_measurements)
    choices_math = utils_general.choices_maths(
        math, dict_units, dict_measurements)
    choices_output = utils_general.choices_outputs(
        output, dict_units, dict_measurements)

    if request.method == 'POST':
        if not utils_general.user_has_permission('edit_controllers'):
            return redirect(url_for('routes_general.home'))

        if form_export_measurements.export_data_csv.data:
            url = utils_export.export_measurements(form_export_measurements)
            if url:
                return redirect(url)
        elif form_export_settings.export_settings_zip.data:
            file_send = utils_export.export_settings(form_export_settings)
            if file_send:
                return file_send
            else:
                flash('Unknown error creating zipped settings database',
                      'error')
        elif form_import_settings.settings_import_upload.data:
            backup_file = utils_export.import_settings(form_import_settings)
            if backup_file:
                flash('The settings database import has been initialized. '
                      'This process may take an extended time to complete, '
                      'as any unmet dependencies will be installed. '
                      'Additionally, the daemon will be stopped during this '
                      'process and all users will be logged out at the '
                      'completion of the import.', 'success')
                return redirect(url_for('routes_authentication.logout'))
            else:
                flash('An error occurred during the settings database import.',
                      'error')
        elif form_export_influxdb.export_influxdb_zip.data:
            file_send = utils_export.export_influxdb(form_export_influxdb)
            if file_send:
                return file_send
            else:
                flash('Unknown error creating zipped influxdb database '
                      'and metastore', 'error')
        elif form_import_influxdb.influxdb_import_upload.data:
            restore_influxdb = utils_export.import_influxdb(
                form_import_influxdb)
            if restore_influxdb == 'success':
                flash('The influxdb database import has been initialized. '
                      'This process may take an extended time to complete '
                      'if there is a lot of data. Please allow ample time '
                      'for it to complete.',
                      'success')
            else:
                flash('Errors occurred during the influxdb database import.',
                      'error')

    # Generate start end end times for date/time picker
    end_picker = datetime.datetime.now().strftime('%m/%d/%Y %H:%M')
    start_picker = datetime.datetime.now() - datetime.timedelta(hours=6)
    start_picker = start_picker.strftime('%m/%d/%Y %H:%M')

    return render_template('tools/export.html',
                           start_picker=start_picker,
                           end_picker=end_picker,
                           form_export_influxdb=form_export_influxdb,
                           form_export_measurements=form_export_measurements,
                           form_export_settings=form_export_settings,
                           form_import_influxdb=form_import_influxdb,
                           form_import_settings=form_import_settings,
                           choices_function=choices_function,
                           choices_input=choices_input,
                           choices_math=choices_math,
                           choices_output=choices_output)


@blueprint.route('/graph-async', methods=('GET', 'POST'))
@flask_login.login_required
def page_graph_async():
    """ Generate graphs using asynchronous data retrieval """
    if not current_app.config['TESTING']:
        dep_unmet, _, _ = return_dependencies('highstock')
        if dep_unmet:
            return redirect(url_for('routes_admin.admin_dependencies',
                                    device='highstock'))

    function = CustomController.query.all()
    input_dev = Input.query.all()
    device_measurements = DeviceMeasurements.query.all()
    math = Math.query.all()
    output = Output.query.all()
    pid = PID.query.all()
    tag = NoteTags.query.all()

    # Generate all measurement and units used
    dict_measurements = add_custom_measurements(Measurement.query.all())
    dict_units = add_custom_units(Unit.query.all())

    # Get what each measurement uses for a unit
    use_unit = utils_general.use_unit_generate(
        device_measurements, input_dev, output, math, function)

    choices_function = utils_general.choices_functions(
        function, dict_units, dict_measurements)
    choices_input = utils_general.choices_inputs(
        input_dev, dict_units, dict_measurements)
    choices_math = utils_general.choices_maths(
        math, dict_units, dict_measurements)
    choices_output = utils_general.choices_outputs(
        output, dict_units, dict_measurements)
    choices_pid = utils_general.choices_pids(
        pid, dict_units, dict_measurements)
    choices_tag = utils_general.choices_tags(tag)

    selected_ids_measures = []
    start_time_epoch = 0

    device_measurements_dict = {}
    for meas in device_measurements:
        device_measurements_dict[meas.unique_id] = meas

    dict_measure_measurements = {}
    dict_measure_units = {}

    for each_measurement in device_measurements:
        conversion = Conversion.query.filter(
            Conversion.unique_id == each_measurement.conversion_id).first()
        _, unit, measurement = return_measurement_info(each_measurement, conversion)
        dict_measure_measurements[each_measurement.unique_id] = measurement
        dict_measure_units[each_measurement.unique_id] = unit

    async_height = 600

    if request.method == 'POST':
        if request.form['async_height']:
            async_height = request.form['async_height']
        seconds = 0
        if request.form['submit'] == 'All Data':
            pass
        elif request.form['submit'] == 'Year':
            seconds = 31556952
        elif request.form['submit'] == 'Month':
            seconds = 2629746
        elif request.form['submit'] == 'Week':
            seconds = 604800
        elif request.form['submit'] == 'Day':
            seconds = 86400

        if seconds:
            start_time_epoch = (datetime.datetime.now() -
                                datetime.timedelta(seconds=seconds)).strftime('%s')
        selected_ids_measures = request.form.getlist('selected_measure')

    # Generate a dictionary of lists of y-axes
    y_axes = utils_dashboard.graph_y_axes_async(dict_measurements,
                                                selected_ids_measures)

    return render_template('pages/graph-async.html',
                           conversion=Conversion,
                           async_height=async_height,
                           start_time_epoch=start_time_epoch,
                           device_measurements_dict=device_measurements_dict,
                           dict_measure_measurements=dict_measure_measurements,
                           dict_measure_units=dict_measure_units,
                           dict_measurements=dict_measurements,
                           dict_units=dict_units,
                           use_unit=use_unit,
                           input=input_dev,
                           math=math,
                           function=function,
                           output=output,
                           pid=pid,
                           tag=tag,
                           choices_input=choices_input,
                           choices_math=choices_math,
                           choices_function=choices_function,
                           choices_output=choices_output,
                           choices_pid=choices_pid,
                           choices_tag=choices_tag,
                           selected_ids_measures=selected_ids_measures,
                           y_axes=y_axes)


@blueprint.route('/info', methods=('GET', 'POST'))
@flask_login.login_required
def page_info():
    """ Display page with system information from command line tools """
    if not utils_general.user_has_permission('view_stats'):
        return redirect(url_for('routes_general.home'))

    virtualenv_flask = False
    virtualenv_daemon = False
    daemon_pid = None
    pstree_daemon_output = None
    top_daemon_output = None
    frontend_pid = None
    pstree_frontend_output = None
    top_frontend_output = None

    uptime = subprocess.Popen(
        "uptime", stdout=subprocess.PIPE, shell=True)
    (uptime_output, _) = uptime.communicate()
    uptime.wait()
    if uptime_output:
        uptime_output = uptime_output.decode("latin1")

    uname = subprocess.Popen(
        "uname -a", stdout=subprocess.PIPE, shell=True)
    (uname_output, _) = uname.communicate()
    uname.wait()
    if uname_output:
        uname_output = uname_output.decode("latin1")

    if not current_app.config['TESTING']:
        gpio = subprocess.Popen(
            "gpio readall", stdout=subprocess.PIPE, shell=True)
        (gpio_output, _) = gpio.communicate()
        gpio.wait()
        if gpio_output:
            gpio_output = gpio_output.decode("latin1")
    else:
        gpio_output = ''

        # Search for /dev/i2c- devices and compile a sorted dictionary of each
    # device's integer device number and the corresponding 'i2cdetect -y ID'
    # output for display on the info page
    i2c_devices_sorted = {}
    if not current_app.config['TESTING']:
        try:
            i2c_devices = glob.glob("/dev/i2c-*")
            i2c_devices_sorted = OrderedDict()
            for each_dev in i2c_devices:
                device_int = int(each_dev.replace("/dev/i2c-", ""))
                i2cdetect = subprocess.Popen(
                    "i2cdetect -y {dev}".format(dev=device_int),
                    stdout=subprocess.PIPE,
                    shell=True)
                (i2cdetect_out, _) = i2cdetect.communicate()
                i2cdetect.wait()
                if i2cdetect_out:
                    i2c_devices_sorted[device_int] = i2cdetect_out.decode("latin1")
        except Exception as er:
            flash("Error detecting I2C devices: {er}".format(er=er), "error")
        finally:
            i2c_devices_sorted = OrderedDict(sorted(i2c_devices_sorted.items()))

    df = subprocess.Popen(
        "df -h", stdout=subprocess.PIPE, shell=True)
    (df_output, _) = df.communicate()
    df.wait()
    if df_output:
        df_output = df_output.decode("latin1")

    free = subprocess.Popen(
        "free -h", stdout=subprocess.PIPE, shell=True)
    (free_output, _) = free.communicate()
    free.wait()
    if free_output:
        free_output = free_output.decode("latin1")

    dmesg = subprocess.Popen(
        "dmesg | tail -n 20", stdout=subprocess.PIPE, shell=True)
    (dmesg_output, _) = dmesg.communicate()
    dmesg.wait()
    if dmesg_output:
        dmesg_output = dmesg_output.decode("latin1")

    ifconfig = subprocess.Popen(
        "ifconfig -a", stdout=subprocess.PIPE, shell=True)
    (ifconfig_output, _) = ifconfig.communicate()
    ifconfig.wait()
    if ifconfig_output:
        ifconfig_output = ifconfig_output.decode("latin1")

    database_version = AlembicVersion.query.first().version_num
    correct_database_version = ALEMBIC_VERSION

    if hasattr(sys, 'real_prefix') or sys.base_prefix != sys.prefix:
        virtualenv_flask = True

    if os.path.exists(DAEMON_PID_FILE):
        with open(DAEMON_PID_FILE, 'r') as pid_file:
            daemon_pid = int(pid_file.read())

    if not current_app.config['TESTING']:
        daemon_up = daemon_active()
    else:
        daemon_up = False

    if daemon_up is True:
        control = DaemonControl()
        ram_use_daemon = control.ram_use()
        virtualenv_daemon = control.is_in_virtualenv()

        pstree_daemon_output, top_daemon_output = output_pstree_top(daemon_pid)
    else:
        ram_use_daemon = 0

    if os.path.exists(FRONTEND_PID_FILE):
        with open(FRONTEND_PID_FILE, 'r') as pid_file:
            frontend_pid = int(pid_file.read())

    if frontend_pid:
        pstree_frontend_output, top_frontend_output = output_pstree_top(frontend_pid)

    ram_use_flask = resource.getrusage(
        resource.RUSAGE_SELF).ru_maxrss / float(1000)

    python_version = sys.version

    return render_template('pages/info.html',
                           daemon_pid=daemon_pid,
                           daemon_up=daemon_up,
                           gpio_readall=gpio_output,
                           database_version=database_version,
                           correct_database_version=correct_database_version,
                           df=df_output,
                           dmesg_output=dmesg_output,
                           free=free_output,
                           frontend_pid=frontend_pid,
                           i2c_devices_sorted=i2c_devices_sorted,
                           ifconfig=ifconfig_output,
                           pstree_daemon=pstree_daemon_output,
                           pstree_frontend=pstree_frontend_output,
                           python_version=python_version,
                           ram_use_daemon=ram_use_daemon,
                           ram_use_flask=ram_use_flask,
                           top_daemon=top_daemon_output,
                           top_frontend=top_frontend_output,
                           uname=uname_output,
                           uptime=uptime_output,
                           virtualenv_daemon=virtualenv_daemon,
                           virtualenv_flask=virtualenv_flask)


def output_pstree_top(pid):
    pstree = subprocess.Popen(
        "pstree -p {pid}".format(pid=pid), stdout=subprocess.PIPE, shell=True)
    (pstree_output, _) = pstree.communicate()
    pstree.wait()
    if pstree_output:
        pstree_output = pstree_output.decode("latin1")

    top = subprocess.Popen(
        "top -bH -n 1 -p {pid}".format(pid=pid), stdout=subprocess.PIPE, shell=True)
    (top_output, _) = top.communicate()
    top.wait()
    if top_output:
        top_output = top_output.decode("latin1")

    return pstree_output, top_output


@blueprint.route('/lcd', methods=('GET', 'POST'))
@flask_login.login_required
def page_lcd():
    """ Display LCD output settings """
    lcd = LCD.query.all()
    lcd_data = LCDData.query.all()
    math = Math.query.all()
    pid = PID.query.all()
    output = Output.query.all()
    input_dev = Input.query.all()

    display_order = csv_to_list_of_str(DisplayOrder.query.first().lcd)

    dict_units = add_custom_units(Unit.query.all())
    dict_measurements = add_custom_measurements(Measurement.query.all())

    choices_lcd = utils_general.choices_lcd(
        input_dev, math, pid, output, dict_units, dict_measurements)

    form_lcd_add = forms_lcd.LCDAdd()
    form_lcd_mod = forms_lcd.LCDMod()
    form_lcd_display = forms_lcd.LCDModDisplay()

    if request.method == 'POST':
        unmet_dependencies = None
        if not utils_general.user_has_permission('edit_controllers'):
            return redirect(url_for('routes_general.home'))

        if form_lcd_add.add.data:
            unmet_dependencies = utils_lcd.lcd_add(form_lcd_add)
        elif form_lcd_mod.save.data:
            utils_lcd.lcd_mod(form_lcd_mod)
        elif form_lcd_mod.delete.data:
            utils_lcd.lcd_del(form_lcd_mod.lcd_id.data)
        elif form_lcd_mod.reorder_up.data:
            utils_lcd.lcd_reorder(form_lcd_mod.lcd_id.data,
                                  display_order, 'up')
        elif form_lcd_mod.reorder_down.data:
            utils_lcd.lcd_reorder(form_lcd_mod.lcd_id.data,
                                  display_order, 'down')
        elif form_lcd_mod.activate.data:
            utils_lcd.lcd_activate(form_lcd_mod.lcd_id.data)
        elif form_lcd_mod.deactivate.data:
            utils_lcd.lcd_deactivate(form_lcd_mod.lcd_id.data)
        elif form_lcd_mod.reset_flashing.data:
            utils_lcd.lcd_reset_flashing(form_lcd_mod.lcd_id.data)
        elif form_lcd_mod.add_display.data:
            utils_lcd.lcd_display_add(form_lcd_mod)
        elif form_lcd_display.save_display.data:
            utils_lcd.lcd_display_mod(form_lcd_display)
        elif form_lcd_display.delete_display.data:
            utils_lcd.lcd_display_del(form_lcd_display.lcd_data_id.data)

        if unmet_dependencies:
            return redirect(url_for('routes_admin.admin_dependencies',
                                    device=form_lcd_add.lcd_type.data.split(",")[0]))
        else:
            return redirect(url_for('routes_page.page_lcd'))

    return render_template('pages/lcd.html',
                           choices_lcd=choices_lcd,
                           lcd=lcd,
                           lcd_data=lcd_data,
                           lcd_info=LCD_INFO,
                           math=math,
                           measurements=parse_input_information(),
                           pid=pid,
                           output=output,
                           sensor=input_dev,
                           display_order=display_order,
                           form_lcd_add=form_lcd_add,
                           form_lcd_mod=form_lcd_mod,
                           form_lcd_display=form_lcd_display)


@blueprint.route('/live', methods=('GET', 'POST'))
@flask_login.login_required
def page_live():
    """ Page of recent and updating input data """
    # Get what each measurement uses for a unit
    function = CustomController.query.all()
    device_measurements = DeviceMeasurements.query.all()
    input_dev = Input.query.all()
    output = Output.query.all()
    math = Math.query.all()

    activated_inputs = Input.query.filter(Input.is_activated).count()
    activated_functions = CustomController.query.filter(CustomController.is_activated).count()

    use_unit = utils_general.use_unit_generate(
        device_measurements, input_dev, output, math, function)

    # Display orders
    display_order_input = csv_to_list_of_str(DisplayOrder.query.first().inputs)
    display_order_function = csv_to_list_of_str(DisplayOrder.query.first().function)

    # Generate all measurement and units used
    dict_measurements = add_custom_measurements(Measurement.query.all())
    dict_units = add_custom_units(Unit.query.all())

    dict_controllers = parse_function_information()

    custom_options_values_controllers = parse_custom_option_values(
        function, dict_controller=dict_controllers)

    dict_measure_measurements = {}
    dict_measure_units = {}

    for each_measurement in device_measurements:
        conversion = Conversion.query.filter(
            Conversion.unique_id == each_measurement.conversion_id).first()
        _, unit, measurement = return_measurement_info(each_measurement, conversion)
        dict_measure_measurements[each_measurement.unique_id] = measurement
        dict_measure_units[each_measurement.unique_id] = unit

    return render_template('pages/live.html',
                           and_=and_,
                           activated_inputs=activated_inputs,
                           activated_functions=activated_functions,
                           custom_options_values_controllers=custom_options_values_controllers,
                           table_device_measurements=DeviceMeasurements,
                           table_input=Input,
                           table_function=CustomController,
                           dict_measurements=dict_measurements,
                           dict_units=dict_units,
                           dict_measure_measurements=dict_measure_measurements,
                           dict_measure_units=dict_measure_units,
                           display_order_input=display_order_input,
                           display_order_function=display_order_function,
                           list_devices_adc=list_analog_to_digital_converters(),
                           measurement_units=MEASUREMENTS,
                           use_unit=use_unit)


@blueprint.route('/logview', methods=('GET', 'POST'))
@flask_login.login_required
def page_logview():
    """ Display the last (n) lines from a log file """
    if not utils_general.user_has_permission('view_logs'):
        return redirect(url_for('routes_general.home'))

    form_log_view = forms_misc.LogView()
    log_output = None
    lines = 30
    logfile = ''
    log_field = None
    if request.method == 'POST':
        if form_log_view.lines.data:
            lines = form_log_view.lines.data

        # Log fie requested
        if form_log_view.log_view.data:
            command = None
            log_field = form_log_view.log.data

            # Find which log file was requested, generate command to execute
            if form_log_view.log.data == 'log_pid_settings':
                logfile = DAEMON_LOG_FILE
                logrotate_file = logfile + '.1'
                if (logrotate_file and os.path.exists(logrotate_file) and
                        logfile and os.path.isfile(logfile)):
                    command = 'cat {lrlog} {log} | grep -a "PID Settings" | tail -n {lines}'.format(
                        lrlog=logrotate_file, log=logfile, lines=lines)
                else:
                    command = 'grep -a "PID Settings" {log} | tail -n {lines}'.format(
                        lines=lines, log=logfile)
            elif form_log_view.log.data == 'log_nginx':
                command = 'journalctl -u nginx | tail -n {lines}'.format(
                    lines=lines)
            elif form_log_view.log.data == 'log_flask':
                command = 'journalctl -u farmflask | tail -n {lines}'.format(
                    lines=lines)
            else:
                if form_log_view.log.data == 'log_login':
                    logfile = LOGIN_LOG_FILE
                elif form_log_view.log.data == 'log_http_access':
                    logfile = HTTP_ACCESS_LOG_FILE
                elif form_log_view.log.data == 'log_http_error':
                    logfile = HTTP_ERROR_LOG_FILE
                elif form_log_view.log.data == 'log_daemon':
                    logfile = DAEMON_LOG_FILE
                elif form_log_view.log.data == 'log_dependency':
                    logfile = DEPENDENCY_LOG_FILE
                elif form_log_view.log.data == 'log_keepup':
                    logfile = KEEPUP_LOG_FILE
                elif form_log_view.log.data == 'log_backup':
                    logfile = BACKUP_LOG_FILE
                elif form_log_view.log.data == 'log_restore':
                    logfile = RESTORE_LOG_FILE
                elif form_log_view.log.data == 'log_upgrade':
                    logfile = UPGRADE_LOG_FILE

                logrotate_file = logfile + '.1'
                if (logrotate_file and os.path.exists(logrotate_file) and
                        logfile and os.path.isfile(logfile)):
                    command = 'cat {lrlog} {log} | tail -n {lines}'.format(
                        lrlog=logrotate_file, log=logfile, lines=lines)
                elif os.path.isfile(logfile):
                    command = 'tail -n {lines} {log}'.format(lines=lines,
                                                             log=logfile)

            # Execute command and generate the output to display to the user
            if command:
                log = subprocess.Popen(
                    command, stdout=subprocess.PIPE, shell=True)
                (log_output, _) = log.communicate()
                log.wait()
                log_output = str(log_output, 'latin-1')
            else:
                log_output = 404

    return render_template('tools/logview.html',
                           form_log_view=form_log_view,
                           lines=lines,
                           log_field=log_field,
                           logfile=logfile,
                           log_output=log_output)


@blueprint.route('/usage', methods=('GET', 'POST'))
@flask_login.login_required
def page_usage():
    """ Display output usage (duration and energy usage/cost) """
    if not utils_general.user_has_permission('view_stats'):
        return redirect(url_for('routes_general.home'))

    calculate_pass = False

    form_energy_usage_add = forms_misc.EnergyUsageAdd()
    form_energy_usage_mod = forms_misc.EnergyUsageMod()

    if request.method == 'POST':
        if not utils_general.user_has_permission('edit_controllers'):
            return redirect(url_for('routes_page.page_usage'))

        if form_energy_usage_add.energy_usage_add.data:
            dep_unmet, _, _ = return_dependencies('highstock')
            if dep_unmet:
                return redirect(url_for('routes_admin.admin_dependencies',
                                        device='highstock'))
            utils_misc.energy_usage_add(form_energy_usage_add)
        elif form_energy_usage_mod.energy_usage_mod.data:
            utils_misc.energy_usage_mod(form_energy_usage_mod)
        elif form_energy_usage_mod.energy_usage_delete.data:
            utils_misc.energy_usage_delete(
                form_energy_usage_mod.energy_usage_id.data)
        elif form_energy_usage_mod.energy_usage_range_calc.data:
            calculate_pass = True

        if not calculate_pass:
            return redirect(url_for('routes_page.page_usage'))

    energy_usage = EnergyUsage.query.all()
    input_dev = Input.query.all()
    function = CustomController.query.all()
    math = Math.query.all()
    misc = Misc.query.first()
    output = Output.query.all()
    output_channel = OutputChannel.query.all()

    # Generate all measurement and units used
    dict_measurements = add_custom_measurements(Measurement.query.all())
    dict_units = add_custom_units(Unit.query.all())

    choices_function = utils_general.choices_functions(
        function, dict_units, dict_measurements)
    choices_input = utils_general.choices_inputs(
        input_dev, dict_units, dict_measurements)
    choices_math = utils_general.choices_maths(
        math, dict_units, dict_measurements)

    dict_outputs = parse_output_information()

    custom_options_values_output_channels = parse_custom_option_values_output_channels_json(
        output_channel, dict_controller=dict_outputs, key_name='custom_channel_options')

    energy_usage_stats, graph_info = return_energy_usage(
        energy_usage, DeviceMeasurements.query, Conversion.query)
    output_stats = return_output_usage(
        dict_outputs, misc, output, OutputChannel, custom_options_values_output_channels)

    day = misc.output_usage_dayofmonth
    if 4 <= day <= 20 or 24 <= day <= 30:
        date_suffix = 'th'
    else:
        date_suffix = ['st', 'nd', 'rd'][day % 10 - 1]

    display_order = csv_to_list_of_str(DisplayOrder.query.first().output)

    if calculate_pass:
        start_string = form_energy_usage_mod.energy_usage_date_range.data.split(' - ')[0]
        end_string = form_energy_usage_mod.energy_usage_date_range.data.split(' - ')[1]
        (calculate_usage,
         graph_info,
         picker_start,
         picker_end) = calc_energy_usage(
            form_energy_usage_mod.energy_usage_id.data,
            graph_info,
            start_string,
            end_string,
            EnergyUsage.query,
            DeviceMeasurements.query,
            Conversion.query,
            misc.output_usage_volts)
    else:
        calculate_usage = {}
        picker_start = {}
        picker_end = {}

    picker_end['default'] = datetime.datetime.now().strftime('%m/%d/%Y %H:%M')
    picker_start['default'] = datetime.datetime.now() - datetime.timedelta(hours=6)
    picker_start['default'] = picker_start['default'].strftime('%m/%d/%Y %H:%M')

    return render_template('pages/usage.html',
                           calculate_usage=calculate_usage,
                           choices_function=choices_function,
                           choices_input=choices_input,
                           choices_math=choices_math,
                           custom_options_values_output_channels=custom_options_values_output_channels,
                           date_suffix=date_suffix,
                           dict_outputs=dict_outputs,
                           display_order=display_order,
                           energy_usage=energy_usage,
                           energy_usage_stats=energy_usage_stats,
                           form_energy_usage_add=form_energy_usage_add,
                           form_energy_usage_mod=form_energy_usage_mod,
                           graph_info=graph_info,
                           misc=misc,
                           output=output,
                           output_stats=output_stats,
                           output_types=output_types(),
                           picker_end=picker_end,
                           picker_start=picker_start,
                           table_output_channel=OutputChannel,
                           timestamp=time.strftime("%c"))


@blueprint.route('/usage_reports')
@flask_login.login_required
def page_usage_reports():
    """ Display output usage (duration and energy usage/cost) """
    if not utils_general.user_has_permission('view_stats'):
        return redirect(url_for('routes_general.home'))

    report_location = os.path.normpath(USAGE_REPORTS_PATH)
    reports = [0, 0]

    return render_template('pages/usage_reports.html',
                           report_location=report_location,
                           reports=reports)


def dict_custom_colors():
    """
    Generate a dictionary of custom colors from CSV strings saved in the
    database. If custom colors aren't already saved, fill in with a default
    palette.

    :return: dictionary of graph_ids and lists of custom colors
    """
    if flask_login.current_user.theme in THEMES_DARK:
        default_palette = [
            '#2b908f', '#90ee7e', '#f45b5b', '#7798BF', '#aaeeee', '#ff0066',
            '#eeaaee', '#55BF3B', '#DF5353', '#7798BF', '#aaeeee'
        ]
    else:
        default_palette = [
            '#7cb5ec', '#434348', '#90ed7d', '#f7a35c', '#8085e9', '#f15c80',
            '#e4d354', '#2b908f', '#f45b5b', '#91e8e1'
        ]

    color_count = OrderedDict()
    graph = Widget.query.all()
    for each_graph in graph:
        # Only process graph widget types
        if each_graph.graph_type != 'graph':
            continue

        try:
            # Get current saved colors
            if each_graph.custom_colors:  # Split into list
                colors = each_graph.custom_colors.split(',')
            else:  # Create empty list
                colors = []
            # Fill end of list with empty strings
            while len(colors) < len(default_palette):
                colors.append('')

            # Populate empty strings with default colors
            for x, _ in enumerate(default_palette):
                if colors[x] == '':
                    colors[x] = default_palette[x]

            index = 0
            index_sum = 0
            total = []

            if each_graph.input_ids_measurements:
                for each_set in each_graph.input_ids_measurements.split(';'):
                    input_unique_id = each_set.split(',')[0]
                    input_measure_id = each_set.split(',')[1]

                    device_measurement = DeviceMeasurements.query.filter(
                        DeviceMeasurements.unique_id == input_measure_id).first()
                    if device_measurement:
                        measurement_name = device_measurement.name
                        conversion = Conversion.query.filter(
                            Conversion.unique_id == device_measurement.conversion_id).first()
                    else:
                        measurement_name = None
                        conversion = None
                    channel, unit, measurement = return_measurement_info(
                        device_measurement, conversion)

                    input_dev = Input.query.filter_by(
                        unique_id=input_unique_id).first()

                    # Custom colors
                    if (index < len(each_graph.input_ids_measurements.split(';')) and
                            len(colors) > index):
                        color = colors[index]
                    else:
                        color = '#FF00AA'

                    # Data grouping
                    disable_data_grouping = False
                    if input_measure_id in each_graph.disable_data_grouping:
                        disable_data_grouping = True

                    if None not in [input_dev, device_measurement]:
                        total.append({
                            'unique_id': input_unique_id,
                            'measure_id': input_measure_id,
                            'type': 'Input',
                            'name': input_dev.name,
                            'channel': channel,
                            'unit': unit,
                            'measure': measurement,
                            'measure_name': measurement_name,
                            'color': color,
                            'disable_data_grouping': disable_data_grouping})
                        index += 1
                index_sum += index

            if each_graph.math_ids:
                index = 0
                for each_set in each_graph.math_ids.split(';'):
                    math_unique_id = each_set.split(',')[0]
                    math_measure_id = each_set.split(',')[1]

                    device_measurement = DeviceMeasurements.query.filter(
                        DeviceMeasurements.unique_id == math_measure_id).first()
                    if device_measurement:
                        measurement_name = device_measurement.name
                        conversion = Conversion.query.filter(
                            Conversion.unique_id == device_measurement.conversion_id).first()
                    else:
                        measurement_name = None
                        conversion = None
                    channel, unit, measurement = return_measurement_info(
                        device_measurement, conversion)

                    math = Math.query.filter_by(
                        unique_id=math_unique_id).first()

                    # Custom colors
                    if (index < len(each_graph.math_ids.split(';')) and
                            len(colors) > index_sum + index):
                        color = colors[index_sum + index]
                    else:
                        color = '#FF00AA'

                    # Data grouping
                    disable_data_grouping = False
                    if math_measure_id in each_graph.disable_data_grouping:
                        disable_data_grouping = True

                    if math is not None:
                        total.append({
                            'unique_id': math_unique_id,
                            'measure_id': math_measure_id,
                            'type': 'Math',
                            'name': math.name,
                            'channel': channel,
                            'unit': unit,
                            'measure': measurement,
                            'measure_name': measurement_name,
                            'color': color,
                            'disable_data_grouping': disable_data_grouping})
                        index += 1
                index_sum += index

            if each_graph.output_ids:
                index = 0
                for each_set in each_graph.output_ids.split(';'):
                    output_unique_id = each_set.split(',')[0]
                    output_measure_id = each_set.split(',')[1]

                    device_measurement = DeviceMeasurements.query.filter(
                        DeviceMeasurements.unique_id == output_measure_id).first()
                    if device_measurement:
                        measurement_name = device_measurement.name
                        conversion = Conversion.query.filter(
                            Conversion.unique_id == device_measurement.conversion_id).first()
                    else:
                        measurement_name = None
                        conversion = None
                    channel, unit, measurement = return_measurement_info(
                        device_measurement, conversion)

                    output = Output.query.filter_by(
                        unique_id=output_unique_id).first()

                    if (index < len(each_graph.output_ids.split(';')) and
                            len(colors) > index_sum + index):
                        color = colors[index_sum + index]
                    else:
                        color = '#FF00AA'

                    # Data grouping
                    disable_data_grouping = False
                    if output_measure_id in each_graph.disable_data_grouping:
                        disable_data_grouping = True

                    if output is not None:
                        total.append({
                            'unique_id': output_unique_id,
                            'measure_id': output_measure_id,
                            'type': 'Output',
                            'name': output.name,
                            'channel': channel,
                            'unit': unit,
                            'measure': measurement,
                            'measure_name': measurement_name,
                            'color': color,
                            'disable_data_grouping': disable_data_grouping})
                        index += 1
                index_sum += index

            if each_graph.pid_ids:
                index = 0
                for each_set in each_graph.pid_ids.split(';'):
                    pid_unique_id = each_set.split(',')[0]
                    pid_measure_id = each_set.split(',')[1]

                    device_measurement = DeviceMeasurements.query.filter(
                        DeviceMeasurements.unique_id == pid_measure_id).first()
                    if device_measurement:
                        measurement_name = device_measurement.name
                        conversion = Conversion.query.filter(
                            Conversion.unique_id == device_measurement.conversion_id).first()
                    else:
                        measurement_name = None
                        conversion = None
                    channel, unit, measurement = return_measurement_info(
                        device_measurement, conversion)

                    pid = PID.query.filter_by(
                        unique_id=pid_unique_id).first()

                    # Custom colors
                    if (index < len(each_graph.pid_ids.split(';')) and
                            len(colors) > index_sum + index):
                        color = colors[index_sum + index]
                    else:
                        color = '#FF00AA'

                    # Data grouping
                    disable_data_grouping = False
                    if pid_measure_id in each_graph.disable_data_grouping:
                        disable_data_grouping = True

                    if pid is not None:
                        total.append({
                            'unique_id': pid_unique_id,
                            'measure_id': pid_measure_id,
                            'type': 'PID',
                            'name': pid.name,
                            'channel': channel,
                            'unit': unit,
                            'measure': measurement,
                            'measure_name': measurement_name,
                            'color': color,
                            'disable_data_grouping': disable_data_grouping})
                        index += 1
                index_sum += index

            if each_graph.note_tag_ids:
                index = 0
                for each_set in each_graph.note_tag_ids.split(';'):
                    tag_unique_id = each_set.split(',')[0]

                    device_measurement = NoteTags.query.filter_by(
                        unique_id=tag_unique_id).first()

                    if (index < len(each_graph.note_tag_ids.split(',')) and
                            len(colors) > index_sum + index):
                        color = colors[index_sum + index]
                    else:
                        color = '#FF00AA'
                    if device_measurement is not None:
                        total.append({
                            'unique_id': tag_unique_id,
                            'measure_id': None,
                            'type': 'Tag',
                            'name': device_measurement.name,
                            'channel': None,
                            'unit': None,
                            'measure': None,
                            'measure_name': None,
                            'color': color,
                            'disable_data_grouping': None
                        })
                        index += 1
                index_sum += index

            color_count.update({each_graph.unique_id: total})
        except IndexError:
            logger.exception("Index")
        except Exception:
            logger.exception("Exception")

    return color_count


def gen(camera):
    """ Video streaming generator function """
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
