# -*- coding: utf-8 -*-
import importlib
import logging
import sys

import os

sys.path.append(
    os.path.abspath(os.path.join(
        os.path.dirname(__file__), os.path.pardir) + '/..'))

from farm.config import CAMERA_INFO
from farm.config import DEPENDENCIES_GENERAL
from farm.config import FUNCTION_ACTION_INFO
from farm.config import FUNCTION_INFO
from farm.config import INSTALL_DIRECTORY
from farm.config import DEPENDENCY_LOG_FILE
from farm.config import LCD_INFO
from farm.config import METHOD_INFO
from farm.databases.models import Actions
from farm.databases.models import Widget
from farm.databases.models import Camera
from farm.databases.models import CustomController
from farm.databases.models import EnergyUsage
from farm.databases.models import Function
from farm.databases.models import Input
from farm.databases.models import LCD
from farm.databases.models import Math
from farm.databases.models import Method
from farm.databases.models import Output
from farm.farm_flask.utils.utils_general import return_dependencies
from farm.utils.functions import parse_function_information
from farm.utils.database import db_retrieve_table_daemon
from farm.utils.outputs import parse_output_information
from farm.utils.inputs import parse_input_information
from farm.utils.system_pi import cmd_output

logger = logging.getLogger("farm.update_dependencies")


def get_installed_dependencies():
    met_deps = []

    list_dependencies = [
        parse_function_information(),
        parse_input_information(),
        parse_output_information(),
        CAMERA_INFO,
        FUNCTION_ACTION_INFO,
        FUNCTION_INFO,
        LCD_INFO,
        METHOD_INFO,
        DEPENDENCIES_GENERAL
    ]

    for each_section in list_dependencies:
        for device_type in each_section:
            if 'dependencies_module' in each_section[device_type]:
                dep_mod = each_section[device_type]['dependencies_module']
                for (install_type, package, install_id) in dep_mod:
                    entry = '{0} {1}'.format(install_type, install_id)
                    if install_type in ['pip-pypi', 'pip-git']:
                        try:
                            module = importlib.util.find_spec(package)
                            if module is not None and entry not in met_deps:
                                met_deps.append(entry)
                        except Exception:
                            logger.error(
                                'Exception checking python dependency: '
                                '{dep}'.format(dep=package))
                    elif install_type == 'apt':
                        start = "dpkg-query -W -f='${Status}'"
                        end = '2>/dev/null | grep -c "ok installed"'
                        cmd = "{} {} {}".format(start, package, end)
                        _, _, status = cmd_output(cmd, user='root')
                        if not status and entry not in met_deps:
                            met_deps.append(entry)

    return met_deps


if __name__ == "__main__":
    dependencies = []
    devices = []

    input_dev = db_retrieve_table_daemon(Input)
    for each_dev in input_dev:
        if each_dev.device not in devices:
            devices.append(each_dev.device)

    output = db_retrieve_table_daemon(Output)
    for each_dev in output:
        if each_dev.output_type not in devices:
            devices.append(each_dev.output_type)

    camera = db_retrieve_table_daemon(Camera)
    for each_dev in camera:
        if each_dev.library not in devices:
            devices.append(each_dev.library)

    lcd = db_retrieve_table_daemon(LCD)
    for each_dev in lcd:
        if each_dev.lcd_type not in devices:
            devices.append(each_dev.lcd_type)

    math = db_retrieve_table_daemon(Math)
    for each_dev in math:
        if each_dev.math_type not in devices:
            devices.append(each_dev.math_type)

    method = db_retrieve_table_daemon(Method)
    for each_dev in method:
        if each_dev.method_type not in devices:
            devices.append(each_dev.method_type)

    function = db_retrieve_table_daemon(Function)
    for each_dev in function:
        if each_dev.function_type not in devices:
            devices.append(each_dev.function_type)

    actions = db_retrieve_table_daemon(Actions)
    for each_dev in actions:
        if each_dev.action_type not in devices:
            devices.append(each_dev.action_type)

    custom = db_retrieve_table_daemon(CustomController)
    for each_dev in custom:
        if each_dev.device not in devices:
            devices.append(each_dev.device)

    widget = db_retrieve_table_daemon(Widget)
    for each_dev in widget:
        if each_dev.graph_type not in devices:
            devices.append(each_dev.graph_type)

    energy_usage = db_retrieve_table_daemon(EnergyUsage)
    for each_dev in energy_usage:
        if 'highstock' not in devices:
            devices.append('highstock')

    for each_device in devices:
        device_unmet_dependencies, _, _ = return_dependencies(each_device)
        for each_dep in device_unmet_dependencies:
            if each_dep not in dependencies:
                dependencies.append(each_dep)

    if dependencies:
        print("Unmet dependencies found: {}".format(dependencies))

        for each_dep in dependencies:
            if each_dep[1] == 'bash-commands':
                for each_command in each_dep[2]:
                    command = "{cmd} | ts '[%Y-%m-%d %H:%M:%S]' >> {log} 2>&1".format(
                        cmd=each_command,
                        log=DEPENDENCY_LOG_FILE)
                    cmd_out, cmd_err, cmd_status = cmd_output(
                        command, timeout=600, cwd="/tmp")
                    logger.info("Command returned: out: {}, error: {}, status: {}".format(
                        cmd_out, cmd_err, cmd_status))
            else:
                install_cmd = "{pth}/farm/scripts/dependencies.sh {dep}".format(
                    pth=INSTALL_DIRECTORY,
                    dep=each_dep[1])
                output, err, stat = cmd_output(install_cmd, user='root')
                formatted_output = output.decode("utf-8").replace('\\n', '\n')

    # Update installed dependencies
    installed_deps = get_installed_dependencies()
    apt_deps = ''
    for each_dep in installed_deps:
        if each_dep.split(' ')[0] == 'apt':
            apt_deps += ' {}'.format(each_dep.split(' ')[1])

    if apt_deps:
        update_cmd = 'apt-get install -y {dep}'.format(
            home=INSTALL_DIRECTORY, dep=apt_deps)
        output, err, stat = cmd_output(update_cmd, user='root')
        formatted_output = output.decode("utf-8").replace('\\n', '\n')
        print("{}".format(formatted_output))

    tmp_req_file = '{home}/install/requirements-generated.txt'.format(home=INSTALL_DIRECTORY)
    with open(tmp_req_file, "w") as f:
        for each_dep in installed_deps:
            if each_dep.split(' ')[0] == 'pip-pypi':
                f.write('{dep}\n'.format(dep=each_dep.split(' ')[1]))
            elif each_dep.split(' ')[0] == 'pip-git':
                f.write('-e {dep}\n'.format(dep=each_dep.split(' ')[1]))

    pip_req_update = '{home}/env/bin/python -m pip install --upgrade -r {home}/install/requirements-generated.txt'.format(
        home=INSTALL_DIRECTORY)
    output, err, stat = cmd_output(pip_req_update, user='root')
    formatted_output = output.decode("utf-8").replace('\\n', '\n')
    print("{}".format(formatted_output))
    os.remove(tmp_req_file)
