# coding=utf-8
""" collection of Admin endpoints """
import datetime
import io
import logging
import os
import socket
import subprocess
import threading
import zipfile
from collections import OrderedDict

import flask_login
from flask import Blueprint
from flask import flash
from flask import jsonify
from flask import make_response
from flask import redirect
from flask import render_template
from flask import request
from flask import send_file
from flask import url_for
from flask_babel import gettext
from pkg_resources import parse_version

from farm.config import BACKUP_LOG_FILE
from farm.config import BACKUP_PATH
from farm.config import CAMERA_INFO
from farm.config import DEPENDENCIES_GENERAL
from farm.config import DEPENDENCY_INIT_FILE
from farm.config import DEPENDENCY_LOG_FILE
from farm.config import FINAL_RELEASES
from farm.config import FORCE_UPGRADE_MASTER
from farm.config import FUNCTION_ACTION_INFO
from farm.config import FUNCTION_INFO
from farm.config import INSTALL_DIRECTORY
from farm.config import LCD_INFO
from farm.config import MATH_INFO
from farm.config import METHOD_INFO
from farm.config import FARM_VERSION
from farm.config import RESTORE_LOG_FILE
from farm.config import STATS_CSV
from farm.config import UPGRADE_INIT_FILE
from farm.config import UPGRADE_LOG_FILE
from farm.config import UPGRADE_TMP_LOG_FILE
from farm.databases.models import Misc
from farm.farm_flask.extensions import db
from farm.farm_flask.forms import forms_dependencies
from farm.farm_flask.forms import forms_misc
from farm.farm_flask.routes_static import inject_variables
from farm.farm_flask.utils import utils_general
from farm.utils.functions import parse_function_information
from farm.utils.github_release_info import FarmRelease
from farm.utils.inputs import parse_input_information
from farm.utils.outputs import parse_output_information
from farm.utils.stats import return_stat_file_dict
from farm.utils.system_pi import can_perform_backup
from farm.utils.system_pi import cmd_output
from farm.utils.system_pi import get_directory_size
from farm.utils.system_pi import internet
from farm.utils.widgets import parse_widget_information

logger = logging.getLogger('farm.farm_flask.admin')

blueprint = Blueprint(
    'routes_admin',
    __name__,
    static_folder='../static',
    template_folder='../templates'
)


@blueprint.context_processor
@flask_login.login_required
def inject_dictionary():
    return inject_variables()


@blueprint.route('/admin/backup', methods=('GET', 'POST'))
@flask_login.login_required
def admin_backup():
    """ Load the backup management page """
    if not utils_general.user_has_permission('edit_settings'):
        return redirect(url_for('routes_general.home'))

    form_backup = forms_misc.Backup()

    backup_dirs_tmp = []
    if not os.path.isdir('/var/Farm-backups'):
        flash("Error: Backup directory doesn't exist.", "error")
    else:
        backup_dirs_tmp = sorted(next(os.walk(BACKUP_PATH))[1])
        backup_dirs_tmp.reverse()

    backup_dirs = []
    full_paths = []
    for each_dir in backup_dirs_tmp:
        if each_dir.startswith("Farm-backup-"):
            full_path = os.path.join(BACKUP_PATH, each_dir)
            backup_dirs.append((each_dir, get_directory_size(full_path) / 1000000.0))
            full_paths.append(full_path)

    if request.method == 'POST':
        if form_backup.backup.data:
            backup_size, free_before, free_after = can_perform_backup()
            if free_after / 1000000 > 50:
                cmd = "{pth}/farm/scripts/farm_wrapper backup-create" \
                      " | ts '[%Y-%m-%d %H:%M:%S]'" \
                      " >> {log} 2>&1".format(pth=INSTALL_DIRECTORY,
                                              log=BACKUP_LOG_FILE)
                subprocess.Popen(cmd, shell=True)
                flash(gettext("Backup in progress"), "success")
            else:
                flash(
                    "Not enough free space to perform a backup. A backup "
                    "requires {size_bu:.1f} MB but there is only "
                    "{size_free:.1f} MB available, which would leave "
                    "{size_after:.1f} MB after the backup. If the free space "
                    "after a backup is less than 50 MB, the backup cannot "
                    "proceed. Free up space by deleting current "
                    "backups.".format(size_bu=backup_size / 1000000,
                                      size_free=free_before / 1000000,
                                      size_after=free_after / 1000000),
                    'error')

        elif form_backup.download.data:
            def get_all_file_paths(directory):
                file_paths = []
                for root, directories, files in os.walk(directory):
                    for filename in files:
                        # join the two strings in order to form the full filepath
                        filepath = os.path.join(root, filename)
                        file_paths.append(filepath)
                return file_paths

            try:
                backup_date_version = form_backup.selected_dir.data
                download_dir = os.path.join(BACKUP_PATH, 'Farm-backup-{}'.format(backup_date_version))
                save_file = "Farm_Backup_{dv}_{host}_.zip".format(
                    dv=backup_date_version, host=socket.gethostname().replace(' ', ''))
                file_paths = get_all_file_paths(download_dir)
                string_remove = "{}".format(os.path.join(BACKUP_PATH, download_dir))

                if not os.path.isdir(download_dir):
                    flash("Directory not found: {}".format(download_dir), "error")
                else:
                    # Zip all files in the_backup directory
                    data = io.BytesIO()
                    with zipfile.ZipFile(data, 'w') as zip:
                        # writing each file one by one
                        for file in file_paths:
                            # Remove first two directory names from zip file, so the Farm root is the zip root
                            zip.write(file, file.replace(string_remove, ""))
                    data.seek(0)

                    # Send zip file to user
                    return send_file(
                        data,
                        mimetype='application/zip',
                        as_attachment=True,
                        attachment_filename=save_file
                    )
            except Exception as err:
                flash("Error: {}".format(err), "error")

        elif form_backup.delete.data:
            cmd = "{pth}/farm/scripts/farm_wrapper backup-delete {dir}" \
                  " 2>&1".format(pth=INSTALL_DIRECTORY,
                                 dir=form_backup.selected_dir.data)
            subprocess.Popen(cmd, shell=True)
            flash(gettext("Deletion of backup in progress"),
                  "success")

        elif form_backup.restore.data:
            cmd = "{pth}/farm/scripts/farm_wrapper backup-restore {backup}" \
                  " | ts '[%Y-%m-%d %H:%M:%S]'" \
                  " >> {log} 2>&1".format(pth=INSTALL_DIRECTORY,
                                          backup=form_backup.full_path.data,
                                          log=RESTORE_LOG_FILE)
            subprocess.Popen(cmd, shell=True)
            flash(gettext("Restore in progress"),
                  "success")

    return render_template('admin/backup.html',
                           form_backup=form_backup,
                           backup_dirs=backup_dirs,
                           full_paths=full_paths)


def install_dependencies(dependencies):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dependency_list = []
    for each_dependency in dependencies:
        if each_dependency[0] not in dependency_list:
            dependency_list.append(each_dependency[0])
    with open(DEPENDENCY_LOG_FILE, 'a') as f:
        f.write("\n[{time}] Dependency installation beginning. Installing: {deps}\n\n".format(
            time=now, deps=", ".join(dependency_list)))

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
            cmd = "{pth}/farm/scripts/farm_wrapper install_dependency {dep}" \
                  " | ts '[%Y-%m-%d %H:%M:%S]' >> {log} 2>&1".format(
                    pth=INSTALL_DIRECTORY,
                    log=DEPENDENCY_LOG_FILE,
                    dep=each_dep[1])
            dep = subprocess.Popen(cmd, shell=True)
            dep.wait()
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(DEPENDENCY_LOG_FILE, 'a') as f:
                f.write("\n[{time}] End install of {dep}\n\n".format(
                    time=now, dep=each_dep[0]))

    cmd = "{pth}/farm/scripts/farm_wrapper update_permissions" \
          " | ts '[%Y-%m-%d %H:%M:%S]' >> {log}  2>&1".format(
            pth=INSTALL_DIRECTORY,
            log=DEPENDENCY_LOG_FILE)
    init = subprocess.Popen(cmd, shell=True)
    init.wait()

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(DEPENDENCY_LOG_FILE, 'a') as f:
        f.write("\n[{time}] #### Dependencies installed. Restarting frontend and backend...".format(time=now))

    with open(DEPENDENCY_INIT_FILE, 'w') as f:
        f.write('0')

    cmd = "{pth}/farm/scripts/farm_wrapper daemon_restart" \
          " | ts '[%Y-%m-%d %H:%M:%S]' >> {log}  2>&1".format(
            pth=INSTALL_DIRECTORY,
            log=DEPENDENCY_LOG_FILE)
    init = subprocess.Popen(cmd, shell=True)
    init.wait()

    cmd = "{pth}/farm/scripts/farm_wrapper frontend_reload" \
          " | ts '[%Y-%m-%d %H:%M:%S]' >> {log}  2>&1".format(
            pth=INSTALL_DIRECTORY,
            log=DEPENDENCY_LOG_FILE)
    init = subprocess.Popen(cmd, shell=True)
    init.wait()

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(DEPENDENCY_LOG_FILE, 'a') as f:
        f.write("\n\n[{time}] #### Dependency install complete.\n\n".format(time=now))


@blueprint.route('/admin/dependency_install/<device>', methods=('GET', 'POST'))
@flask_login.login_required
def admin_dependency_install(device):
    """ Install Dependencies """
    messages = {
        "success": [],
        "info": [],
        "warning": [],
        "error": []
    }

    try:
        device_unmet_dependencies, _, _ = utils_general.return_dependencies(device)
        with open(DEPENDENCY_INIT_FILE, 'w') as f:
            f.write('1')
        install_deps = threading.Thread(
            target=install_dependencies,
            args=(device_unmet_dependencies,))
        install_deps.start()
        messages["success"].append("Dependency install initiated")
    except Exception as err:
        messages["error"].append("Error: {}".format(err))

    return jsonify(data={
        'messages': messages
    })


@blueprint.route('/admin/dependencies', methods=('GET', 'POST'))
@flask_login.login_required
def admin_dependencies_main():
    return redirect(url_for('routes_admin.admin_dependencies', device='0'))


@blueprint.route('/admin/dependencies/<device>', methods=('GET', 'POST'))
@flask_login.login_required
def admin_dependencies(device):
    """ Display Dependency page """
    form_dependencies = forms_dependencies.Dependencies()

    if device != '0':
        # Only loading a single dependency page
        device_unmet_dependencies, _, _ = utils_general.return_dependencies(device)
    elif form_dependencies.device.data:
        device_unmet_dependencies, _, _ = utils_general.return_dependencies(form_dependencies.device.data)
    else:
        device_unmet_dependencies = []

    unmet_dependencies = OrderedDict()
    unmet_exist = False
    met_dependencies = []
    met_exist = False
    unmet_list = {}
    install_in_progress = False
    device_name = None
    dependencies_message = ""

    # Read from the dependency status file created by the upgrade script
    # to indicate if the upgrade is running.
    try:
        with open(DEPENDENCY_INIT_FILE) as f:
            dep = int(f.read(1))
    except (IOError, ValueError):
        try:
            with open(DEPENDENCY_INIT_FILE, 'w') as f:
                f.write('0')
        finally:
            dep = 0

    if dep:
        install_in_progress = True

    list_dependencies = [
        parse_function_information(),
        parse_input_information(),
        parse_output_information(),
        parse_widget_information(),
        CAMERA_INFO,
        FUNCTION_ACTION_INFO,
        FUNCTION_INFO,
        LCD_INFO,
        MATH_INFO,
        METHOD_INFO,
        DEPENDENCIES_GENERAL
    ]
    for each_section in list_dependencies:
        for each_device in each_section:

            if device in each_section:
                # Determine if a message for the dependencies exists
                if "dependencies_message" in each_section[device]:
                    dependencies_message = each_section[device]["dependencies_message"]

                # Find friendly name for device
                for each_device_, each_val in each_section[device].items():
                    if each_device_ in ['name',
                                        'input_name',
                                        'output_name',
                                        'function_name',
                                        'widget_name']:
                        device_name = each_val
                        break

            # Only get all dependencies when not loading a single dependency page
            if device == '0':
                # Determine if there are any unmet dependencies for every device
                dep_unmet, dep_met, _ = utils_general.return_dependencies(each_device)

                unmet_dependencies.update({
                    each_device: dep_unmet
                })
                if dep_unmet:
                    unmet_exist = True

                # Determine if there are any met dependencies
                if dep_met:
                    if each_device not in met_dependencies:
                        met_dependencies.append(each_device)
                        met_exist = True

                # Find all the devices that use each unmet dependency
                if unmet_dependencies[each_device]:
                    for each_dep in unmet_dependencies[each_device]:
                        # Determine if the third element of the tuple is a list, convert it to a tuple
                        if (type(each_dep) == tuple and
                                len(each_dep) == 3 and
                                type(each_dep[2]) == list):
                            each_dep = list(each_dep)
                            each_dep[2] = tuple(each_dep[2])
                            each_dep = tuple(each_dep)

                        if each_dep not in unmet_list:
                            unmet_list[each_dep] = []
                        if each_device not in unmet_list[each_dep]:
                            unmet_list[each_dep].append(each_device)

    if request.method == 'POST':
        if not utils_general.user_has_permission('edit_controllers'):
            return redirect(url_for('routes_admin.admin_dependencies', device=device))

        if form_dependencies.install.data:
            with open(DEPENDENCY_INIT_FILE, 'w') as f:
                f.write('1')
            install_deps = threading.Thread(
                target=install_dependencies,
                args=(device_unmet_dependencies,))
            install_deps.start()

        return redirect(url_for('routes_admin.admin_dependencies', device=device))

    return render_template('admin/dependencies.html',
                           measurements=parse_input_information(),
                           unmet_list=unmet_list,
                           dependencies_message=dependencies_message,
                           device=device,
                           device_name=device_name,
                           install_in_progress=install_in_progress,
                           unmet_dependencies=unmet_dependencies,
                           unmet_exist=unmet_exist,
                           met_dependencies=met_dependencies,
                           met_exist=met_exist,
                           form_dependencies=form_dependencies,
                           device_unmet_dependencies=device_unmet_dependencies)


@blueprint.route('/admin/dependency_status', methods=('GET', 'POST'))
@flask_login.login_required
def admin_dependency_status():
    """ Return the last 30 lines of the dependency log """
    if os.path.isfile(DEPENDENCY_LOG_FILE):
        command = 'tail -n 40 {log}'.format(log=DEPENDENCY_LOG_FILE)
        log = subprocess.Popen(
            command, stdout=subprocess.PIPE, shell=True)
        (log_output, _) = log.communicate()
        log.wait()
        log_output = log_output.decode("utf-8")
    else:
        log_output = 'Dependency log not found. If a dependency install was ' \
                     'just initialized, please wait...'
    response = make_response(log_output)
    response.headers["content-type"] = "text/plain"
    return response


@blueprint.route('/admin/statistics', methods=('GET', 'POST'))
@flask_login.login_required
def admin_statistics():
    """ Display collected statistics """
    if not utils_general.user_has_permission('view_stats'):
        return redirect(url_for('routes_general.home'))

    try:
        statistics = return_stat_file_dict(STATS_CSV)
    except IOError:
        statistics = {}
    return render_template('admin/statistics.html',
                           statistics=statistics)


@blueprint.route('/admin/upgrade_status', methods=('GET', 'POST'))
@flask_login.login_required
def admin_upgrade_status():
    """ Return the last 30 lines of the upgrade log """
    if os.path.isfile(UPGRADE_TMP_LOG_FILE):
        command = 'cat {log}'.format(log=UPGRADE_TMP_LOG_FILE)
        log = subprocess.Popen(
            command, stdout=subprocess.PIPE, shell=True)
        (log_output, _) = log.communicate()
        log.wait()
        log_output = log_output.decode("utf-8")
    else:
        log_output = 'Upgrade log not found. If an upgrade was just ' \
                     'initialized, please wait...'
    response = make_response(log_output)
    response.headers["content-type"] = "text/plain"
    return response


@blueprint.route('/admin/upgrade', methods=('GET', 'POST'))
@flask_login.login_required
def admin_upgrade():
    """ Display any available upgrades and option to upgrade """
    if not utils_general.user_has_permission('edit_settings'):
        return redirect(url_for('routes_general.home'))

    misc = Misc.query.first()
    if not internet(host=misc.net_test_ip,
                    port=misc.net_test_port,
                    timeout=misc.net_test_timeout):
        return render_template('admin/upgrade.html',
                               is_internet=False)

    is_internet = True

    # Read from the upgrade status file created by the upgrade script
    # to indicate if the upgrade is running.
    try:
        with open(UPGRADE_INIT_FILE) as f:
            upgrade = int(f.read(1))
    except Exception:
        try:
            with open(UPGRADE_INIT_FILE, 'w') as f:
                f.write('0')
        finally:
            upgrade = 0

    if upgrade:
        if upgrade == 2:
            flash(gettext("There was an error encountered during the upgrade"
                          " process. Check the upgrade log for details."),
                  "error")
        return render_template('admin/upgrade.html',
                               current_release=FARM_VERSION,
                               is_internet=is_internet,
                               upgrade=upgrade)

    form_backup = forms_misc.Backup()
    form_upgrade = forms_misc.Upgrade()

    upgrade_available = False

    # Check for any new Farm releases on github
    farm_releases = FarmRelease()
    (upgrade_exists,
     releases,
     farm_releases,
     current_latest_release,
     errors) = farm_releases.github_upgrade_exists()

    if errors:
        for each_error in errors:
            flash(each_error, 'error')

    if releases:
        current_latest_major_version = current_latest_release.split('.')[0]
        current_major_release = releases[0]
        current_releases = []
        releases_behind = None
        for index, each_release in enumerate(releases):
            if parse_version(each_release) >= parse_version(FARM_VERSION):
                current_releases.append(each_release)
            if parse_version(each_release) == parse_version(FARM_VERSION):
                releases_behind = index
        if upgrade_exists:
            upgrade_available = True
    else:
        current_releases = []
        current_latest_major_version = '0'
        current_major_release = '0.0.0'
        releases_behind = 0

    # Update database to reflect the current upgrade status
    mod_misc = Misc.query.first()
    if mod_misc.farm_upgrade_available != upgrade_available:
        mod_misc.farm_upgrade_available = upgrade_available
        db.session.commit()

    def not_enough_space_upgrade():
        backup_size, free_before, free_after = can_perform_backup()
        if free_after / 1000000 < 50:
            flash(
                "A backup must be performed during an upgrade and there is "
                "not enough free space to perform a backup. A backup "
                "requires {size_bu:.1f} MB but there is only {size_free:.1f} "
                "MB available, which would leave {size_after:.1f} MB after "
                "the backup. If the free space after a backup is less than 50"
                " MB, the backup cannot proceed. Free up space by deleting "
                "current backups.".format(size_bu=backup_size / 1000000,
                                          size_free=free_before / 1000000,
                                          size_after=free_after / 1000000),
                'error')
            return True
        else:
            return False

    if request.method == 'POST':
        if (form_upgrade.upgrade.data and
                (upgrade_available or FORCE_UPGRADE_MASTER)):
            if not_enough_space_upgrade():
                pass
            elif FORCE_UPGRADE_MASTER:
                try:
                    os.remove(UPGRADE_TMP_LOG_FILE)
                except FileNotFoundError:
                    pass
                cmd = "{pth}/farm/scripts/farm_wrapper upgrade-master" \
                      " | ts '[%Y-%m-%d %H:%M:%S]' 2>&1 | tee -a {log} {tmp_log}".format(
                    pth=INSTALL_DIRECTORY,
                    log=UPGRADE_LOG_FILE,
                    tmp_log=UPGRADE_TMP_LOG_FILE)
                subprocess.Popen(cmd, shell=True)

                upgrade = 1
                flash(gettext("The upgrade (from master branch) has started"), "success")
            else:
                try:
                    os.remove(UPGRADE_TMP_LOG_FILE)
                except FileNotFoundError:
                    pass
                cmd = "{pth}/farm/scripts/farm_wrapper upgrade-release-major {current_maj_version}" \
                      " | ts '[%Y-%m-%d %H:%M:%S]' 2>&1 | tee -a {log} {tmp_log}".format(
                    current_maj_version=FARM_VERSION.split('.')[0],
                    pth=INSTALL_DIRECTORY,
                    log=UPGRADE_LOG_FILE,
                    tmp_log=UPGRADE_TMP_LOG_FILE)
                subprocess.Popen(cmd, shell=True)

                upgrade = 1
                mod_misc = Misc.query.first()
                mod_misc.farm_upgrade_available = False
                db.session.commit()
                flash(gettext("The upgrade has started"), "success")
        elif (form_upgrade.upgrade_next_major_version.data and
                upgrade_available):
            if not not_enough_space_upgrade():
                try:
                    os.remove(UPGRADE_TMP_LOG_FILE)
                except FileNotFoundError:
                    pass
                cmd = "{pth}/farm/scripts/farm_wrapper upgrade-release-wipe {ver}" \
                      " | ts '[%Y-%m-%d %H:%M:%S]' 2>&1 | tee -a {log} {tmp_log}".format(
                    pth=INSTALL_DIRECTORY,
                    ver=current_latest_major_version,
                    log=UPGRADE_LOG_FILE,
                    tmp_log=UPGRADE_TMP_LOG_FILE)
                subprocess.Popen(cmd, shell=True)

                upgrade = 1
                mod_misc = Misc.query.first()
                mod_misc.farm_upgrade_available = False
                db.session.commit()
                flash(gettext(
                    "The major version upgrade has started"), "success")
        else:
            flash(gettext(
                "You cannot upgrade if an upgrade is not available"),
                "error")

    return render_template('admin/upgrade.html',
                           final_releases=FINAL_RELEASES,
                           force_upgrade_master=FORCE_UPGRADE_MASTER,
                           form_backup=form_backup,
                           form_upgrade=form_upgrade,
                           current_release=FARM_VERSION,
                           current_releases=current_releases,
                           current_major_release=current_major_release,
                           current_latest_release=current_latest_release,
                           current_latest_major_version=current_latest_major_version,
                           releases_behind=releases_behind,
                           upgrade_available=upgrade_available,
                           upgrade=upgrade,
                           is_internet=is_internet)
