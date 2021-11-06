# coding=utf-8
""" flask views that deal with user authentication """

import datetime
import logging
import socket
import time

import flask_login
from flask import flash
from flask import jsonify
from flask import make_response
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from flask.blueprints import Blueprint
from flask_babel import gettext
from sqlalchemy import func

from farm.config import LOGIN_ATTEMPTS
from farm.config import LOGIN_BAN_SECONDS
from farm.config import LOGIN_LOG_FILE
from farm.config_translations import TRANSLATIONS
from farm.databases.models import AlembicVersion
from farm.databases.models import Misc
from farm.databases.models import Role
from farm.databases.models import User
from farm.farm_flask.extensions import db
from farm.farm_flask.forms import forms_authentication
from farm.farm_flask.utils import utils_general
from farm.utils.utils import test_password
from farm.utils.utils import test_username

logger = logging.getLogger(__name__)

blueprint = Blueprint(
    'routes_authentication',
    __name__,
    static_folder='../static',
    template_folder='../templates'
)


@blueprint.route('/create_admin', methods=('GET', 'POST'))
def create_admin():
    if admin_exists():
        flash(gettext(
            "Cannot access admin creation form if an admin user "
            "already exists."), "error")
        return redirect(url_for('routes_general.home'))

    # If login token cookie from previous session exists, delete
    if request.cookies.get('remember_token'):
        response = clear_cookie_auth()
        return response

    form_create_admin = forms_authentication.CreateAdmin()
    form_notice = forms_authentication.InstallNotice()

    if request.method == 'POST':
        form_name = request.form['form-name']
        if form_name == 'acknowledge':
            mod_misc = Misc.query.first()
            mod_misc.dismiss_notification = 1
            db.session.commit()
        elif form_create_admin.validate():
            username = form_create_admin.username.data.lower()
            error = False
            if form_create_admin.password.data != form_create_admin.password_repeat.data:
                flash(gettext("Passwords do not match. Please try again."),
                      "error")
                error = True
            if not test_username(username):
                flash(gettext(
                    "Invalid user name. Must be between 2 and 64 characters "
                    "and only contain letters and numbers."),
                    "error")
                error = True
            if not test_password(form_create_admin.password.data):
                flash(gettext(
                    "Invalid password. Must be between 6 and 64 characters "
                    "and only contain letters, numbers, and symbols."),
                      "error")
                error = True
            if error:
                return redirect(url_for('routes_general.home'))

            new_user = User()
            new_user.name = username
            new_user.email = form_create_admin.email.data
            new_user.set_password(form_create_admin.password.data)
            new_user.role_id = 1  # Admin
            new_user.theme = 'spacelab'
            try:
                db.session.add(new_user)
                db.session.commit()
                flash(gettext("User '%(user)s' successfully created. Please "
                              "log in below.", user=username),
                      "success")
                return redirect(url_for('routes_authentication.login_check'))
            except Exception as except_msg:
                flash(gettext("Failed to create user '%(user)s': %(err)s",
                              user=username,
                              err=except_msg), "error")
        else:
            utils_general.flash_form_errors(form_create_admin)

    dismiss_notification = Misc.query.first().dismiss_notification

    return render_template('create_admin.html',
                           dict_translation=TRANSLATIONS,
                           dismiss_notification=dismiss_notification,
                           form_create_admin=form_create_admin,
                           form_notice=form_notice)


@blueprint.route('/login', methods=('GET', 'POST'))
def login_check():
    """Authenticate users of the web-UI"""
    if not admin_exists():
        return redirect('/create_admin')
    elif flask_login.current_user.is_authenticated:
        flash(gettext("Cannot access login page if you're already logged in"),
              "error")
        return redirect(url_for('routes_general.home'))

    settings = Misc.query.first()
    if settings.default_login_page == "password":
        return redirect(url_for('routes_authentication.login_password'))
    elif settings.default_login_page == "keypad":
        return redirect(url_for('routes_authentication.login_keypad'))
    return redirect(url_for('routes_authentication.login_password'))


@blueprint.route('/login_password', methods=('GET', 'POST'))
def login_password():
    """Authenticate users of the web-UI"""
    if not admin_exists():
        return redirect('/create_admin')
    elif flask_login.current_user.is_authenticated:
        flash(gettext("Cannot access login page if you're already logged in"),
              "error")
        return redirect(url_for('routes_general.home'))

    form_login = forms_authentication.Login()

    # Check if the user is banned from logging in (too many incorrect attempts)
    if banned_from_login():
        flash(gettext(
            "Too many failed login attempts. Please wait %(min)s "
            "minutes before attempting to log in again",
            min=int((LOGIN_BAN_SECONDS - session['ban_time_left']) / 60) + 1),
                "info")
    else:
        if request.method == 'POST':
            username = form_login.username.data.lower()
            user_ip = request.environ.get('HTTP_X_FORWARDED_FOR', 'unknown address')
            user = User.query.filter(
                func.lower(User.name) == username).first()

            if not user:
                login_log(username, 'NA', user_ip, 'NOUSER')
                failed_login()
            elif form_login.validate_on_submit():
                matched_hash = User().check_password(
                    form_login.password.data, user.password_hash)

                # Encode stored password hash if it's a str
                password_hash = user.password_hash
                if isinstance(user.password_hash, str):
                    password_hash = user.password_hash.encode('utf-8')

                if matched_hash == password_hash:
                    user = User.query.filter(User.name == username).first()
                    role_name = Role.query.filter(Role.id == user.role_id).first().name
                    login_log(username, role_name, user_ip, 'LOGIN')

                    # flask-login user
                    login_user = User()
                    login_user.id = user.id
                    remember_me = True if form_login.remember.data else False
                    flask_login.login_user(login_user, remember=remember_me)

                    return redirect(url_for('routes_general.home'))
                else:
                    user = User.query.filter(User.name == username).first()
                    role_name = Role.query.filter(Role.id == user.role_id).first().name
                    login_log(username, role_name, user_ip, 'FAIL')
                    failed_login()
            else:
                login_log(username, 'NA', user_ip, 'FAIL')
                failed_login()

            return redirect('/login')

    return render_template('login_password.html',
                           dict_translation=TRANSLATIONS,
                           form_login=form_login,
                           host=socket.gethostname())


@blueprint.route('/login_keypad', methods=('GET', 'POST'))
def login_keypad():
    """Authenticate users of the web-UI (with keypad)"""
    if not admin_exists():
        return redirect('/create_admin')

    elif flask_login.current_user.is_authenticated:
        flash(gettext("Cannot access login page if you're already logged in"),
              "error")
        return redirect(url_for('routes_general.home'))

    # Check if the user is banned from logging in (too many incorrect attempts)
    if banned_from_login():
        flash(gettext(
            "Too many failed login attempts. Please wait %(min)s "
            "minutes before attempting to log in again",
            min=int((LOGIN_BAN_SECONDS - session['ban_time_left']) / 60) + 1),
                "info")

    return render_template('login_keypad.html',
                           dict_translation=TRANSLATIONS,
                           host=socket.gethostname())


@blueprint.route('/login_keypad_code/', methods=('GET', 'POST'))
def login_keypad_code_empty():
    """Forward to keypad when no code entered"""
    time.sleep(2)
    flash("Please enter a code", "error")
    return redirect('/login_keypad')


@blueprint.route('/login_keypad_code/<code>', methods=('GET', 'POST'))
def login_keypad_code(code):
    """Check code from keypad"""
    if not admin_exists():
        return redirect('/create_admin')

    elif flask_login.current_user.is_authenticated:
        flash(gettext("Cannot access login page if you're already logged in"),
              "error")
        return redirect(url_for('routes_general.home'))

    # Check if the user is banned from logging in (too many incorrect attempts)
    if banned_from_login():
        flash(gettext(
            "Too many failed login attempts. Please wait %(min)s "
            "minutes before attempting to log in again",
            min=int((LOGIN_BAN_SECONDS - session['ban_time_left']) / 60) + 1),
                "info")
    else:
        user = User.query.filter(User.code == code).first()
        user_ip = request.environ.get('HTTP_X_FORWARDED_FOR', 'unknown address')

        if not user:
            login_log(code, 'NA', user_ip, 'FAIL')
            failed_login()
            flash("Invalid Code", "error")
            time.sleep(2)
        else:
            role_name = Role.query.filter(Role.id == user.role_id).first().name
            login_log(user.name, role_name, user_ip, 'LOGIN')

            # flask-login user
            login_user = User()
            login_user.id = user.id
            remember_me = True
            flask_login.login_user(login_user, remember=remember_me)

            return redirect(url_for('routes_general.home'))

    return render_template('login_keypad.html',
                           dict_translation=TRANSLATIONS,
                           host=socket.gethostname())


@blueprint.route("/logout")
@flask_login.login_required
def logout():
    """Log out of the web-ui"""
    user = User.query.filter(User.name == flask_login.current_user.name).first()
    role_name = Role.query.filter(Role.id == user.role_id).first().name
    login_log(user.name,
              role_name,
              request.environ.get('REMOTE_ADDR', 'unknown address'),
              'LOGOUT')
    # flask-login logout
    flask_login.logout_user()

    response = clear_cookie_auth()

    flash(gettext("Successfully logged out"), 'success')
    return response


@blueprint.route('/newremote/')
def newremote():
    """Verify authentication as a client computer to the remote admin"""
    username = request.args.get('user')
    pass_word = request.args.get('passw')

    user = User.query.filter(
        User.name == username).first()

    if user:
        if User().check_password(
                pass_word, user.password_hash) == user.password_hash:
            try:
                with open('/var/farm-root/farm/farm_flask/ssl_certs/cert.pem', 'r') as cert:
                    certificate_data = cert.read()
            except Exception:
                certificate_data = None
            return jsonify(status=0,
                           error_msg=None,
                           hash=str(user.password_hash),
                           certificate=certificate_data)
    return jsonify(status=1,
                   error_msg="Unable to authenticate with user and password.",
                   hash=None,
                   certificate=None)


@blueprint.route('/remote_login', methods=('GET', 'POST'))
def remote_admin_login():
    """Authenticate Remote Admin login"""
    password_hash = request.form.get('password_hash', None)
    username = request.form.get('username', None)

    if username and password_hash:
        user = User.query.filter(
            func.lower(User.name) == username).first()
    else:
        user = None

    if user and str(user.password_hash) == str(password_hash):
        login_user = User()
        login_user.id = user.id
        flask_login.login_user(login_user, remember=False)
        return "Logged in via Remote Admin"
    else:
        return "ERROR"


@blueprint.route('/auth/')
@flask_login.login_required
def remote_auth():
    """Checks authentication for remote admin"""
    return "authenticated"


def admin_exists():
    """Verify that at least one admin user exists"""
    return User.query.filter_by(role_id=1).count()


def check_database_version_issue():
    if len(AlembicVersion.query.all()) > 1:
        flash("A check of your database indicates there is an issue with your"
              " database version number. To resolve this issue, move"
              " your farm.db from ~/Farm/databases/farm.db to a "
              "different location (or delete it) and a new database will be "
              "generated in its place.", "error")


def banned_from_login():
    """Check if the person at the login prompt is banned form logging in"""
    if not session.get('failed_login_count'):
        session['failed_login_count'] = 0
    if not session.get('failed_login_ban_time'):
        session['failed_login_ban_time'] = 0
    elif session['failed_login_ban_time']:
        session['ban_time_left'] = time.time() - session['failed_login_ban_time']
        if session['ban_time_left'] < LOGIN_BAN_SECONDS:
            return 1
        else:
            session['failed_login_ban_time'] = 0
    return 0


def failed_login():
    """Count the number of failed login attempts"""
    try:
        session['failed_login_count'] += 1
    except KeyError:
        session['failed_login_count'] = 1

    if session['failed_login_count'] > LOGIN_ATTEMPTS - 1:
        session['failed_login_ban_time'] = time.time()
        session['failed_login_count'] = 0
    else:
        flash('Failed Login ({}/{})'.format(
            session['failed_login_count'], LOGIN_ATTEMPTS), "error")


def login_log(user, group, ip, status):
    """Write to login log"""
    with open(LOGIN_LOG_FILE, 'a') as log_file:
        log_file.write(
            '{dt:%Y-%m-%d %H:%M:%S}: {stat} {user} ({grp}), {ip}\n'.format(
                dt=datetime.datetime.now(), stat=status,
                user=user, grp=group, ip=ip))


def clear_cookie_auth():
    """Delete authentication cookies"""
    response = make_response(redirect('/login'))
    session.clear()
    response.set_cookie('remember_token', '', expires=0)
    return response
