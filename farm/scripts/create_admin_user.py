# -*- coding: utf-8 -*-
"""Create admin user"""
import sys
import traceback
from getpass import getpass

import bcrypt
import os

sys.path.append(os.path.abspath(os.path.join(__file__, "../../..")))

from farm.databases.models import User
from farm.databases.utils import session_scope
from farm.config import SQL_DATABASE_FARM
from farm.databases import set_uuid
from farm.utils.utils import test_username

FARM_DB_PATH = 'sqlite:///' + SQL_DATABASE_FARM

passwords_match = False
password_valid = False
user_valid = False


def set_password(new_password):
    """ saves a password hash  """
    if isinstance(new_password, str):
        new_password = new_password.encode('utf-8')
    return bcrypt.hashpw(new_password, bcrypt.gensalt())


while not user_valid:
    user_name = input("User Name: ")
    if not test_username(user_name):
        print("Invalid user name. Must be between 2 and 64 characters and "
              "only contain letters and numbers.")
    else:
        user_valid = True

email = input("Email Address: ")

while not passwords_match and not password_valid:
    password = getpass("Password: ")
    password_repeat = getpass("Repeat Password: ")

    if password != password_repeat:
        print("Password don't math. Try again.")
    else:
        passwords_match = True

try:
    with session_scope(FARM_DB_PATH) as db_session:
        new_user = User()
        new_user.unique_id = set_uuid()
        new_user.name = user_name.lower()
        new_user.password_hash = set_password(password)
        new_user.email = email
        new_user.role_id = 1
        new_user.theme = 'slate'
        new_user.landing_page = 'live'
        new_user.index_page = 'landing'
        new_user.language = 'en'
        db_session.add(new_user)

    print("Admin user '{}' successfully created.".format(user_name.lower()))
except Exception:
    print("Error creating admin user. Refer the the traceback, below, for the error.")
    traceback.print_exc()


