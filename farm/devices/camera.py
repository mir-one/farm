# -*- coding: utf-8 -*-
import datetime
import logging
import os
import time

from farm.config import PATH_CAMERAS
from farm.config import SQL_DATABASE_FARM
from farm.databases.models import Camera
from farm.databases.models import OutputChannel
from farm.databases.utils import session_scope
from farm.farm_client import DaemonControl
from farm.utils.database import db_retrieve_table_daemon
from farm.utils.logging_utils import set_log_level
from farm.utils.system_pi import assure_path_exists
from farm.utils.system_pi import cmd_output
from farm.utils.system_pi import set_user_grp

FARM_DB_PATH = 'sqlite:///' + SQL_DATABASE_FARM

logger = logging.getLogger(__name__)
logger.setLevel(set_log_level(logging))


#
# Camera record
#

def camera_record(record_type, unique_id, duration_sec=None, tmp_filename=None):
    """
    Record still image from cameras
    :param record_type:
    :param unique_id:
    :param duration_sec:
    :param tmp_filename:
    :return:
    """
    daemon_control = None
    settings = db_retrieve_table_daemon(Camera, unique_id=unique_id)
    timestamp_date = datetime.datetime.now()
    timestamp = timestamp_date.strftime('%Y-%m-%d_%H-%M-%S')
    assure_path_exists(PATH_CAMERAS)
    camera_path = assure_path_exists(
        os.path.join(PATH_CAMERAS, '{uid}'.format(uid=settings.unique_id)))
    if record_type == 'photo':
        if settings.path_still:
            save_path = settings.path_still
        else:
            save_path = assure_path_exists(os.path.join(camera_path, 'still'))
        # TODO: next major version, remove cam id (unique_id is already in path)
        filename = 'Still-{cam_id}-{cam}-{ts}.jpg'.format(
            cam_id=settings.id,
            cam=settings.name,
            ts=timestamp).replace(" ", "_")
    elif record_type == 'timelapse':
        if settings.path_timelapse:
            save_path = settings.path_timelapse
        else:
            save_path = assure_path_exists(os.path.join(camera_path, 'timelapse'))
        start = datetime.datetime.fromtimestamp(
            settings.timelapse_start_time).strftime("%Y-%m-%d_%H-%M-%S")
        # TODO: next major version, remove cam id (unique_id is already in path)
        filename = 'Timelapse-{cam_id}-{cam}-{st}-img-{cn:05d}.jpg'.format(
            cam_id=settings.id,
            cam=settings.name,
            st=start,
            cn=settings.timelapse_capture_number).replace(" ", "_")
    elif record_type == 'video':
        if settings.path_video:
            save_path = settings.path_video
        else:
            save_path = assure_path_exists(os.path.join(camera_path, 'video'))
        filename = 'Video-{cam}-{ts}.h264'.format(
            cam=settings.name,
            ts=timestamp).replace(" ", "_")
    else:
        return

    assure_path_exists(save_path)

    if tmp_filename:
        filename = tmp_filename

    path_file = os.path.join(save_path, filename)

    # Turn on output, if configured
    output_already_on = False
    output_id = None
    output_channel_id = None
    output_channel = None
    if settings.output_id and ',' in settings.output_id:
        output_id = settings.output_id.split(",")[0]
        output_channel_id = settings.output_id.split(",")[1]
        output_channel = db_retrieve_table_daemon(OutputChannel, unique_id=output_channel_id)

    if output_id and output_channel:
        daemon_control = DaemonControl()
        if daemon_control.output_state(output_id, output_channel=output_channel.channel) == "on":
            output_already_on = True
        else:
            daemon_control.output_on(output_id, output_channel=output_channel.channel)

    # Pause while the output remains on for the specified duration.
    # Used for instance to allow fluorescent lights to fully turn on before
    # capturing an image.
    if settings.output_duration:
        time.sleep(settings.output_duration)

    if settings.library == 'picamera':
        try:
            import picamera

            # Try 5 times to access the pi camera (in case another process is accessing it)
            for _ in range(5):
                try:
                    with picamera.PiCamera() as camera:
                        camera.resolution = (settings.width, settings.height)
                        camera.hflip = settings.hflip
                        camera.vflip = settings.vflip
                        camera.rotation = settings.rotation
                        camera.brightness = int(settings.brightness)
                        camera.contrast = int(settings.contrast)
                        camera.exposure_compensation = int(settings.exposure)
                        camera.saturation = int(settings.saturation)
                        camera.shutter_speed = settings.picamera_shutter_speed
                        camera.sharpness = settings.picamera_sharpness
                        camera.iso = settings.picamera_iso
                        camera.awb_mode = settings.picamera_awb
                        if settings.picamera_awb == 'off':
                            camera.awb_gains = (settings.picamera_awb_gain_red,
                                                settings.picamera_awb_gain_blue)
                        camera.exposure_mode = settings.picamera_exposure_mode
                        camera.meter_mode = settings.picamera_meter_mode
                        camera.image_effect = settings.picamera_image_effect

                        camera.start_preview()
                        time.sleep(2)  # Camera warm-up time

                        if record_type in ['photo', 'timelapse']:
                            camera.capture(path_file, use_video_port=False)
                        elif record_type == 'video':
                            camera.start_recording(path_file, format='h264', quality=20)
                            camera.wait_recording(duration_sec)
                            camera.stop_recording()
                        else:
                            return
                        break
                except picamera.exc.PiCameraMMALError:
                    logger.error("The camera is already open by picamera. Retrying 4 times.")
                time.sleep(1)
        except:
            logger.exception("picamera")

    elif settings.library == 'fswebcam':
        try:
            cmd = "/usr/bin/fswebcam --device {dev} --resolution {w}x{h} --set brightness={bt}% " \
                  "--no-banner --save {file}".format(dev=settings.device,
                                                     w=settings.width,
                                                     h=settings.height,
                                                     bt=settings.brightness,
                                                     file=path_file)
            if settings.hflip:
                cmd += " --flip h"
            if settings.vflip:
                cmd += " --flip h"
            if settings.rotation:
                cmd += " --rotat {angle}".format(angle=settings.rotation)
            if settings.custom_options:
                cmd += " {}".format(settings.custom_options)

            out, err, status = cmd_output(cmd, stdout_pipe=False, user='root')
            logger.debug(
                "Camera debug message: "
                "cmd: {}; out: {}; error: {}; status: {}".format(
                    cmd, out, err, status))
        except:
            logger.exception("fswebcam")

    elif settings.library == 'raspistill':
        try:
            cmd = "/usr/bin/raspistill -w {w} -h {h} --brightness {bt} " \
                  "-o {file}".format(w=settings.width,
                                     h=settings.height,
                                     bt=settings.brightness,
                                     file=path_file)

            if settings.contrast is not None:
                cmd += " --contrast {}".format(int(settings.contrast))
            if settings.saturation is not None:
                cmd += " --saturation {}".format(int(settings.saturation))
            if settings.picamera_sharpness is not None:
                cmd += " --sharpness {}".format(int(settings.picamera_sharpness))
            if settings.picamera_iso not in [0, None]:
                cmd += " --ISO {}".format(int(settings.picamera_iso))
            if settings.picamera_awb not in ["off", None]:
                cmd += " --awb {}".format(settings.picamera_awb)
            elif (settings.picamera_awb == "off" and
                  settings.picamera_awb_gain_blue is not None and
                  settings.picamera_awb_gain_red is not None):
                cmd += " --awb {}".format(settings.picamera_awb)
                cmd += " --awbgains {red:.1f},{blue:.1f}".format(
                    red=settings.picamera_awb_gain_red,
                    blue=settings.picamera_awb_gain_blue)
            if settings.hflip:
                cmd += " --hflip"
            if settings.vflip:
                cmd += " --vflip"
            if settings.rotation:
                cmd += " --rotation {angle}".format(angle=settings.rotation)
            if settings.custom_options:
                cmd += " {}".format(settings.custom_options)

            out, err, status = cmd_output(cmd, stdout_pipe=False, user='root')
            logger.debug(
                "Camera debug message: "
                "cmd: {}; out: {}; error: {}; status: {}".format(
                    cmd, out, err, status))
        except:
            logger.exception("raspistill")

    elif settings.library == 'opencv':
        try:
            import cv2
            import imutils

            cap = cv2.VideoCapture(settings.opencv_device)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.height)
            cap.set(cv2.CAP_PROP_EXPOSURE, settings.exposure)
            cap.set(cv2.CAP_PROP_GAIN, settings.gain)
            cap.set(cv2.CAP_PROP_BRIGHTNESS, settings.brightness)
            cap.set(cv2.CAP_PROP_CONTRAST, settings.contrast)
            cap.set(cv2.CAP_PROP_HUE, settings.hue)
            cap.set(cv2.CAP_PROP_SATURATION, settings.saturation)

            # Check if image can be read
            status, _ = cap.read()
            if not status:
                logger.error(
                    "Cannot detect USB camera with device '{dev}'".format(
                        dev=settings.opencv_device))
                return

            # Discard a few frames to allow camera to adjust to settings
            for _ in range(2):
                cap.read()

            if record_type in ['photo', 'timelapse']:
                edited = False
                status, img_orig = cap.read()
                cap.release()

                if not status:
                    logger.error("Could not acquire image")
                    return

                img_edited = img_orig.copy()

                if any((settings.hflip, settings.vflip, settings.rotation)):
                    edited = True

                if settings.hflip and settings.vflip:
                    img_edited = cv2.flip(img_orig, -1)
                elif settings.hflip:
                    img_edited = cv2.flip(img_orig, 1)
                elif settings.vflip:
                    img_edited = cv2.flip(img_orig, 0)

                if settings.rotation:
                    img_edited = imutils.rotate_bound(img_orig, settings.rotation)

                if edited:
                    cv2.imwrite(path_file, img_edited)
                else:
                    cv2.imwrite(path_file, img_orig)

            elif record_type == 'video':
                # TODO: opencv video recording is currently not working. No idea why. Try to fix later.
                try:
                    cap = cv2.VideoCapture(settings.opencv_device)
                    fourcc = cv2.CV_FOURCC('X', 'V', 'I', 'D')
                    resolution = (settings.width, settings.height)
                    out = cv2.VideoWriter(path_file, fourcc, 20.0, resolution)

                    time_end = time.time() + duration_sec
                    while cap.isOpened() and time.time() < time_end:
                        ret, frame = cap.read()
                        if ret:
                            # write the frame
                            out.write(frame)
                            if cv2.waitKey(1) & 0xFF == ord('q'):
                                break
                        else:
                            break
                    cap.release()
                    out.release()
                    cv2.destroyAllWindows()
                except Exception as e:
                    logger.exception(
                        "Exception raised while recording video: "
                        "{err}".format(err=e))
            else:
                return
        except:
            logger.exception("opencv")

    elif settings.library == 'http_address':
        try:
            import cv2
            import imutils
            from urllib.error import HTTPError
            from urllib.parse import urlparse
            from urllib.request import urlretrieve

            if record_type in ['photo', 'timelapse']:
                path_tmp = "/tmp/tmpimg.jpg"

                # Get filename and extension, if available
                a = urlparse(settings.url_still)
                filename = os.path.basename(a.path)
                if filename:
                    path_tmp = "/tmp/{}".format(filename)

                try:
                    os.remove(path_tmp)
                except FileNotFoundError:
                    pass

                try:
                    urlretrieve(settings.url_still, path_tmp)
                except HTTPError as err:
                    logger.error(err)
                except Exception as err:
                    logger.exception(err)

                try:
                    img_orig = cv2.imread(path_tmp)

                    if img_orig is not None and img_orig.shape is not None:
                        if any((settings.hflip, settings.vflip, settings.rotation)):
                            img_edited = None
                            if settings.hflip and settings.vflip:
                                img_edited = cv2.flip(img_orig, -1)
                            elif settings.hflip:
                                img_edited = cv2.flip(img_orig, 1)
                            elif settings.vflip:
                                img_edited = cv2.flip(img_orig, 0)

                            if settings.rotation:
                                img_edited = imutils.rotate_bound(img_orig, settings.rotation)

                            if img_edited:
                                cv2.imwrite(path_file, img_edited)
                        else:
                            cv2.imwrite(path_file, img_orig)
                    else:
                        os.rename(path_tmp, path_file)
                except Exception as err:
                    logger.error("Could not convert, rotate, or invert image: {}".format(err))
                    try:
                        os.rename(path_tmp, path_file)
                    except FileNotFoundError:
                        logger.error("Camera image not found")

            elif record_type == 'video':
                pass  # No video (yet)
        except:
            logger.exception("http:address")

    elif settings.library == 'http_address_requests':
        try:
            import cv2
            import imutils
            import requests

            if record_type in ['photo', 'timelapse']:
                path_tmp = "/tmp/tmpimg.jpg"
                try:
                    os.remove(path_tmp)
                except FileNotFoundError:
                    pass

                try:
                    r = requests.get(settings.url_still)
                    if r.status_code == 200:
                        open(path_tmp, 'wb').write(r.content)
                    else:
                        logger.error("Could not download image. Status code: {}".format(r.status_code))
                except requests.HTTPError as err:
                    logger.error("HTTPError: {}".format(err))
                except Exception as err:
                    logger.exception(err)

                try:
                    img_orig = cv2.imread(path_tmp)

                    if img_orig is not None and img_orig.shape is not None:
                        if any((settings.hflip, settings.vflip, settings.rotation)):
                            if settings.hflip and settings.vflip:
                                img_edited = cv2.flip(img_orig, -1)
                            elif settings.hflip:
                                img_edited = cv2.flip(img_orig, 1)
                            elif settings.vflip:
                                img_edited = cv2.flip(img_orig, 0)

                            if settings.rotation:
                                img_edited = imutils.rotate_bound(img_orig, settings.rotation)

                            cv2.imwrite(path_file, img_edited)
                        else:
                            cv2.imwrite(path_file, img_orig)
                    else:
                        os.rename(path_tmp, path_file)
                except Exception as err:
                    logger.error("Could not convert, rotate, or invert image: {}".format(err))
                    try:
                        os.rename(path_tmp, path_file)
                    except FileNotFoundError:
                        logger.error("Camera image not found")

            elif record_type == 'video':
                pass  # No video (yet)
        except:
            logger.exception("http_address_requests")

    try:
        set_user_grp(path_file, 'farm', 'farm')
    except Exception as e:
        logger.exception(
            "Exception raised in 'camera_record' when setting user grp: "
            "{err}".format(err=e))

    # Turn off output, if configured
    if output_id and output_channel and daemon_control and not output_already_on:
        daemon_control.output_off(output_id, output_channel=output_channel.channel)

    if record_type in ['photo', 'timelapse']:
        # Store the filename and timestamp in the database for photos and timestamps
        with session_scope(FARM_DB_PATH) as new_session:
            mod_camera = new_session.query(Camera).filter(Camera.unique_id == unique_id).first()
            if record_type == 'photo':
                mod_camera.still_last_file = filename
                mod_camera.still_last_ts = timestamp_date.timestamp()
            elif record_type == 'timelapse':
                mod_camera.timelapse_last_file = filename
                mod_camera.timelapse_last_ts = timestamp_date.timestamp()
            new_session.commit()

    try:
        set_user_grp(path_file, 'farm', 'farm')
        return save_path, filename
    except Exception as e:
        logger.exception(
            "Exception raised in 'camera_record' when setting user grp: "
            "{err}".format(err=e))


def count_cameras_opencv():
    """ Returns how many cameras are detected with opencv (cv2) """
    import cv2
    camera_ids = []
    max_tested = 10
    for i in range(max_tested):
        temp_camera = cv2.VideoCapture(i)
        if temp_camera.isOpened():
            temp_camera.release()
            camera_ids.append(i)
    return camera_ids
