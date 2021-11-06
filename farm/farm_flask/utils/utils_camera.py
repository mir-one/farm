# -*- coding: utf-8 -*-
import datetime
import logging
import os
import subprocess

import sqlalchemy
from flask import flash
from flask import url_for

from farm.config import PATH_CAMERAS
from farm.config_translations import TRANSLATIONS
from farm.databases.models import Camera
from farm.farm_client import DaemonControl
from farm.farm_flask.extensions import db
from farm.farm_flask.utils.utils_general import delete_entry_with_id
from farm.farm_flask.utils.utils_general import flash_success_errors
from farm.farm_flask.utils.utils_general import return_dependencies
from farm.utils.database import db_retrieve_table
from farm.utils.system_pi import assure_path_exists

logger = logging.getLogger(__name__)


def camera_add(form_camera):
    action = '{action} {controller}'.format(
        action=TRANSLATIONS['add']['title'],
        controller=TRANSLATIONS['camera']['title'])
    error = []

    dep_unmet, _, _ = return_dependencies(form_camera.library.data)
    if dep_unmet:
        list_unmet_deps = []
        for each_dep in dep_unmet:
            list_unmet_deps.append(each_dep[0])
        error.append(
            "The {dev} device you're trying to add has unmet dependencies: "
            "{dep}".format(dev=form_camera.library.data,
                           dep=', '.join(list_unmet_deps)))

    new_camera = Camera()
    if Camera.query.filter(Camera.name == form_camera.name.data).count():
        flash("You must choose a unique name", "error")
    new_camera.name = form_camera.name.data
    new_camera.library = form_camera.library.data
    if form_camera.library.data == 'fswebcam':
        new_camera.device = '/dev/video0'
        new_camera.brightness = 50
    elif form_camera.library.data == 'raspistill':
        new_camera.brightness = 50
        new_camera.contrast = 0.0
        new_camera.saturation = 0.0
        new_camera.picamera_sharpness = 0
        new_camera.picamera_iso = 0
        new_camera.picamera_awb = "auto"
        new_camera.picamera_awb_gain_blue = 3.0
        new_camera.picamera_awb_gain_red = 2.0
    elif form_camera.library.data == 'picamera':
        new_camera.brightness = 50
        new_camera.contrast = 0.0
        new_camera.exposure = 0.0
        new_camera.saturation = 0.0
    elif form_camera.library.data == 'opencv':
        new_camera.device = '0'
        new_camera.brightness = 0.6
        new_camera.contrast = 0.15
        new_camera.exposure = 0.0
        new_camera.gain = 0
        new_camera.hue = -1.0
        new_camera.saturation = 0.1
        new_camera.white_balance = 0.0
    elif form_camera.library.data == 'http_address':
        new_camera.url_still = 'http://s.w-x.co/staticmaps/wu/wu/wxtype1200_cur/uscsg/current.png'
        new_camera.url_stream = ''
    if not error:
        try:
            new_camera.save()
        except sqlalchemy.exc.OperationalError as except_msg:
            error.append(except_msg)
        except sqlalchemy.exc.IntegrityError as except_msg:
            error.append(except_msg)

    flash_success_errors(error, action, url_for('routes_page.page_camera'))

    if dep_unmet:
        return 1


def camera_mod(form_camera):
    messages = {
        "success": [],
        "info": [],
        "warning": [],
        "error": []
    }

    try:
        if (Camera.query
                .filter(Camera.unique_id != form_camera.camera_id.data)
                .filter(Camera.name == form_camera.name.data).count()):
            messages["error"].append("You must choose a unique name")
        if not 0 <= form_camera.rotation.data <= 360:
            messages["error"].append("Rotation must be between 0 and 360 degrees")

        mod_camera = Camera.query.filter(
            Camera.unique_id == form_camera.camera_id.data).first()
        mod_camera.name = form_camera.name.data

        mod_camera.width = form_camera.width.data
        mod_camera.height = form_camera.height.data
        mod_camera.hflip = form_camera.hflip.data
        mod_camera.vflip = form_camera.vflip.data
        mod_camera.rotation = form_camera.rotation.data
        mod_camera.brightness = form_camera.brightness.data
        mod_camera.hide_still = form_camera.hide_still.data
        mod_camera.hide_timelapse = form_camera.hide_timelapse.data
        mod_camera.path_still = form_camera.path_still.data
        mod_camera.path_timelapse = form_camera.path_timelapse.data
        mod_camera.path_video = form_camera.path_video.data

        if form_camera.stream_fps.data:
            if form_camera.stream_fps.data < 1:
                messages["error"].append("Stream FPS cannot be less than 1")
            mod_camera.stream_fps = form_camera.stream_fps.data

        if mod_camera.library == 'fswebcam':
            mod_camera.device = form_camera.device.data
            mod_camera.custom_options = form_camera.custom_options.data
        elif mod_camera.library == 'raspistill':
            mod_camera.brightness = form_camera.brightness.data
            mod_camera.contrast = form_camera.contrast.data
            mod_camera.saturation = form_camera.saturation.data
            mod_camera.picamera_sharpness = form_camera.picamera_sharpness.data
            mod_camera.picamera_iso = int(form_camera.picamera_iso.data)
            mod_camera.picamera_awb = form_camera.picamera_awb.data
            mod_camera.picamera_awb_gain_red = form_camera.picamera_awb_gain_red.data
            mod_camera.picamera_awb_gain_blue = form_camera.picamera_awb_gain_blue.data
            mod_camera.custom_options = form_camera.custom_options.data
        elif mod_camera.library == 'picamera':
            mod_camera.resolution_stream_width = form_camera.resolution_stream_width.data
            mod_camera.resolution_stream_height = form_camera.resolution_stream_height.data
            mod_camera.contrast = form_camera.contrast.data
            mod_camera.exposure = form_camera.exposure.data
            mod_camera.saturation = form_camera.saturation.data
            mod_camera.picamera_shutter_speed = form_camera.picamera_shutter_speed.data
            mod_camera.picamera_sharpness = form_camera.picamera_sharpness.data
            mod_camera.picamera_iso = int(form_camera.picamera_iso.data)
            mod_camera.picamera_awb = form_camera.picamera_awb.data
            mod_camera.picamera_awb_gain_red = form_camera.picamera_awb_gain_red.data
            mod_camera.picamera_awb_gain_blue = form_camera.picamera_awb_gain_blue.data
            mod_camera.picamera_exposure_mode = form_camera.picamera_exposure_mode.data
            mod_camera.picamera_meter_mode = form_camera.picamera_meter_mode.data
            mod_camera.picamera_image_effect = form_camera.picamera_image_effect.data
        elif mod_camera.library == 'opencv':
            mod_camera.opencv_device = form_camera.opencv_device.data
            mod_camera.resolution_stream_width = form_camera.resolution_stream_width.data
            mod_camera.resolution_stream_height = form_camera.resolution_stream_height.data
            mod_camera.hflip = form_camera.hflip.data
            mod_camera.vflip = form_camera.vflip.data
            mod_camera.rotation = form_camera.rotation.data
            mod_camera.height = form_camera.height.data
            mod_camera.width = form_camera.width.data
            mod_camera.brightness = form_camera.brightness.data
            mod_camera.contrast = form_camera.contrast.data
            mod_camera.exposure = form_camera.exposure.data
            mod_camera.gain = form_camera.gain.data
            mod_camera.hue = form_camera.hue.data
            mod_camera.saturation = form_camera.saturation.data
            mod_camera.white_balance = form_camera.white_balance.data
        elif mod_camera.library == 'http_address':
            mod_camera.url_still = form_camera.url_still.data
            mod_camera.url_stream = form_camera.url_stream.data
        elif mod_camera.library == 'http_address_requests':
            mod_camera.url_still = form_camera.url_still.data
            mod_camera.url_stream = form_camera.url_stream.data
        else:
            messages["error"].append("Unknown camera library")

        if form_camera.output_id.data:
            mod_camera.output_id = form_camera.output_id.data
        else:
            mod_camera.output_id = None
        mod_camera.output_duration = form_camera.output_duration.data
        mod_camera.cmd_pre_camera = form_camera.cmd_pre_camera.data
        mod_camera.cmd_post_camera = form_camera.cmd_post_camera.data

        if not messages["error"]:
            db.session.commit()
            control = DaemonControl()
            control.refresh_daemon_camera_settings()
            messages["success"].append("Camera settings saved")
    except Exception as except_msg:
        logger.exception(1)
        messages["error"].append(except_msg)

    return messages


def camera_del(form_camera):
    messages = {
        "success": [],
        "info": [],
        "warning": [],
        "error": []
    }

    camera = db_retrieve_table(
        Camera, unique_id=form_camera.camera_id.data)
    if camera.timelapse_started:
        messages["error"].append("Cannot delete camera if a time-lapse is currently "
                     "active. Stop the time-lapse and try again.")

    if not messages["error"]:
        try:
            delete_entry_with_id(
                Camera, form_camera.camera_id.data)
            messages["success"].append("Camera deleted")
        except Exception as except_msg:
            messages["error"].append(except_msg)

    return messages


def camera_timelapse_video(form_camera):
    messages = {
        "success": [],
        "info": [],
        "warning": [],
        "error": []
    }

    if not os.path.exists("/usr/bin/ffmpeg"):
        messages["error"].append("ffmpeg not found. Install with 'sudo apt install ffmpeg'")

    if not messages["error"]:
        try:
            camera = db_retrieve_table(
                Camera, unique_id=form_camera.camera_id.data)
            camera_path = assure_path_exists(
                os.path.join(PATH_CAMERAS, '{uid}'.format(uid=camera.unique_id)))
            timelapse_path = assure_path_exists(os.path.join(camera_path, 'timelapse'))
            video_path = assure_path_exists(os.path.join(camera_path, 'timelapse_video'))
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            path_file = os.path.join(
                video_path, "Video_{name}_{ts}.mp4".format(
                    name=form_camera.timelapse_image_set.data, ts=timestamp))

            cmd =  "/usr/bin/ffmpeg " \
                   "-f image2 " \
                   "-r {fps} " \
                   "-i {path}/{seq}-%05d.jpg " \
                   "-vcodec {codec} " \
                   "-y {save}".format(
                        seq=form_camera.timelapse_image_set.data,
                        fps=form_camera.timelapse_fps.data,
                        path=timelapse_path,
                        codec=form_camera.timelapse_codec.data,
                        save=path_file)
            subprocess.Popen(cmd, shell=True)
            messages["success"].append(
                "The time-lapse video is being generated in the background with the command: {}."
                " The video will be saved at {}".format(cmd, path_file))
        except Exception as except_msg:
            messages["error"].append(except_msg)

    return messages
