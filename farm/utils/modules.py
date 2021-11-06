# coding=utf-8
import importlib.util
import logging
import os

from farm.utils.logging_utils import set_log_level

logger = logging.getLogger("farm.modules")
logger.setLevel(set_log_level(logging))


def load_module_from_file(path_file, module_type):
    try:
        module_name = "farm.{}.{}".format(
            module_type, os.path.basename(path_file).split('.')[0])
        spec = importlib.util.spec_from_file_location(module_name, path_file)
        module_custom = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module_custom)
        return module_custom
    except Exception as err:
        logger.error("Could not load module: {}".format(err))
