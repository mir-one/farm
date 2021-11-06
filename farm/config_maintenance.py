# -*- coding: utf-8 -*-
#
#  config_maintenance.py - Global Farm settings
#

# Maintenance Mode
# Prevents users from installing or upgrading Farm
# Used by the developers to test the install/upgrade system for stability prior to release
# Create ~/Farm/.maintenance to override maintenance mode and allow an install/upgrade:

MAINTENANCE_MODE = False
