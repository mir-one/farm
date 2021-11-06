# -*- coding: utf-8 -*-
# From https://github.com/miguelgrinberg/flask-video-streaming
import logging
import time

import cv2

from farm.farm_flask.camera.base_camera import BaseCamera

logger = logging.getLogger(__name__)


class Camera(BaseCamera):
    camera_options = None

    @staticmethod
    def set_camera_options(camera_options):
        logger.info("Setting camera options")
        Camera.camera_options = camera_options

    @staticmethod
    def frames():
        settings = Camera.camera_options

        camera = cv2.VideoCapture(settings.url_stream)

        if not camera.isOpened():
            raise RuntimeError('Could not start camera.')

        wait_period = float(1 / settings.stream_fps)

        while True:
            # read current frame
            _, img = camera.read()

            # encode as a jpeg image and return it
            time.sleep(wait_period)
            yield cv2.imencode('.jpg', img)[1].tobytes()
