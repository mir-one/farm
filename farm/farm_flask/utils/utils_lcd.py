# -*- coding: utf-8 -*-
import logging

import sqlalchemy
from flask import current_app
from flask import flash
from flask import redirect
from flask import url_for
from flask_babel import gettext

from farm.config import LCD_INFO
from farm.config_translations import TRANSLATIONS
from farm.databases.models import DisplayOrder
from farm.databases.models import LCD
from farm.databases.models import LCDData
from farm.farm_client import DaemonControl
from farm.farm_flask.extensions import db
from farm.farm_flask.utils.utils_general import add_display_order
from farm.farm_flask.utils.utils_general import controller_activate_deactivate
from farm.farm_flask.utils.utils_general import delete_entry_with_id
from farm.farm_flask.utils.utils_general import flash_form_errors
from farm.farm_flask.utils.utils_general import flash_success_errors
from farm.farm_flask.utils.utils_general import reorder
from farm.farm_flask.utils.utils_general import return_dependencies
from farm.utils.system_pi import csv_to_list_of_str
from farm.utils.system_pi import list_to_csv

logger = logging.getLogger(__name__)

#
# LCD Manipulation
#

def lcd_add(form):
    action = '{action} {controller}'.format(
        action=TRANSLATIONS['add']['title'],
        controller=TRANSLATIONS['lcd']['title'])
    error = []

    if current_app.config['TESTING']:
        dep_unmet = False
    else:
        dep_unmet, _, _ = return_dependencies(form.lcd_type.data.split(",")[0])
        if dep_unmet:
            list_unmet_deps = []
            for each_dep in dep_unmet:
                list_unmet_deps.append(each_dep[0])
            error.append(
                "The {dev} device you're trying to add has unmet "
                "dependencies: {dep}".format(
                    dev=form.lcd_type.data, dep=', '.join(list_unmet_deps)))

    try:
        new_lcd = LCD()
        new_lcd_data = LCDData()

        try:
            from RPi import GPIO
            if GPIO.RPI_REVISION == 2 or GPIO.RPI_REVISION == 3:
                new_lcd.i2c_bus = 1
            else:
                new_lcd.i2c_bus = 0
        except:
            logger.error("RPi.GPIO and Raspberry Pi required for this action")

        lcd_id = form.lcd_type.data.split(",")[0]
        lcd_interface = form.lcd_type.data.split(",")[1]

        new_lcd.lcd_type = lcd_id
        new_lcd.interface = lcd_interface
        new_lcd.name = str(LCD_INFO[lcd_id]['name'])

        if (lcd_interface == 'I2C' and lcd_id in [
                '128x32_pioled',
                '128x64_pioled',
                '128x32_pioled_circuit_python',
                '128x64_pioled_circuit_python']):
            new_lcd.location = '0x3c'
            new_lcd.pin_reset = 19
        elif lcd_interface == 'I2C' and lcd_id in ['16x2_generic', '20x4_generic']:
            new_lcd.location = '0x27'
        elif lcd_interface == 'I2C' and lcd_id == '16x2_grove_lcd_rgb':
            new_lcd.location = '0x3e'
            new_lcd.location_backlight = '0x62'
        elif lcd_interface == 'SPI':
            new_lcd.pin_reset = 19
            new_lcd.pin_dc = 16
            new_lcd.pin_cs = 17
            new_lcd.spi_device = 0
            new_lcd.spi_bus = 0

        if lcd_id in ['28x32_pioled', '128x32_pioled_circuit_python']:
            new_lcd.x_characters = 21
            new_lcd.y_lines = 4
        elif lcd_id in ['128x64_pioled', '128x64_pioled_circuit_python']:
            new_lcd.x_characters = 21
            new_lcd.y_lines = 8
        elif lcd_id == '16x2_generic':
            new_lcd.x_characters = 16
            new_lcd.y_lines = 2
        elif lcd_id == '20x4_generic':
            new_lcd.x_characters = 20
            new_lcd.y_lines = 4
        elif lcd_id == '16x2_grove_lcd_rgb':
            new_lcd.x_characters = 16
            new_lcd.y_lines = 2

        if not error:
            new_lcd.save()
            new_lcd_data.lcd_id = new_lcd.unique_id
            new_lcd_data.save()
            display_order = csv_to_list_of_str(DisplayOrder.query.first().lcd)
            DisplayOrder.query.first().lcd = add_display_order(
                display_order, new_lcd.unique_id)
            db.session.commit()
    except sqlalchemy.exc.OperationalError as except_msg:
        error.append(except_msg)
    except sqlalchemy.exc.IntegrityError as except_msg:
        error.append(except_msg)
    flash_success_errors(error, action, url_for('routes_page.page_lcd'))

    if dep_unmet:
        return 1


def lcd_mod(form_mod_lcd):
    action = '{action} {controller}'.format(
        action=TRANSLATIONS['modify']['title'],
        controller=TRANSLATIONS['lcd']['title'])
    error = []

    mod_lcd = LCD.query.filter(
        LCD.unique_id == form_mod_lcd.lcd_id.data).first()
    if mod_lcd.is_activated:
        error.append(gettext(
            "Deactivate LCD controller before modifying its settings."))

    if not error:
        if form_mod_lcd.validate():
            try:
                mod_lcd.name = form_mod_lcd.name.data

                if mod_lcd.interface == 'I2C':
                    mod_lcd.location = form_mod_lcd.location.data
                    mod_lcd.i2c_bus = form_mod_lcd.i2c_bus.data
                elif mod_lcd.interface == 'SPI':
                    mod_lcd.pin_reset = form_mod_lcd.pin_reset.data
                    mod_lcd.pin_dc = form_mod_lcd.pin_dc.data
                    mod_lcd.spi_device = form_mod_lcd.spi_device.data
                    mod_lcd.spi_bus = form_mod_lcd.spi_bus.data
                    if form_mod_lcd.pin_cs.data:
                        mod_lcd.pin_cs = form_mod_lcd.pin_cs.data

                if mod_lcd.lcd_type == '16x2_grove_lcd_rgb':
                    mod_lcd.location_backlight = form_mod_lcd.location_backlight.data

                if form_mod_lcd.pin_reset.data is not None:
                    mod_lcd.pin_reset = form_mod_lcd.pin_reset.data
                else:
                    mod_lcd.pin_reset = None
                mod_lcd.period = form_mod_lcd.period.data
                mod_lcd.log_level_debug = form_mod_lcd.log_level_debug.data
                db.session.commit()
            except Exception as except_msg:
                error.append(except_msg)
        else:
            flash_form_errors(form_mod_lcd)
    flash_success_errors(error, action, url_for('routes_page.page_lcd'))


def lcd_del(lcd_id):
    action = '{action} {controller}'.format(
        action=TRANSLATIONS['delete']['title'],
        controller=TRANSLATIONS['lcd']['title'])
    error = []

    lcd = LCD.query.filter(LCD.unique_id == lcd_id).first()
    if lcd.is_activated:
        error.append(gettext(
            "Deactivate LCD controller before modifying its settings."))

    if not error:
        try:
            # Delete all LCD Displays
            lcd_displays = LCDData.query.filter(LCDData.lcd_id == lcd_id).all()
            for each_lcd_display in lcd_displays:
                lcd_display_del(each_lcd_display.unique_id, delete_last=True)

            # Delete LCD
            delete_entry_with_id(LCD, lcd_id)
            display_order = csv_to_list_of_str(DisplayOrder.query.first().lcd)
            display_order.remove(lcd_id)
            DisplayOrder.query.first().lcd = list_to_csv(display_order)
            db.session.commit()
        except Exception as except_msg:
            error.append(except_msg)
    flash_success_errors(error, action, url_for('routes_page.page_lcd'))


def lcd_reorder(lcd_id, display_order, direction):
    action = '{action} {controller}'.format(
        action=TRANSLATIONS['reorder']['title'],
        controller=TRANSLATIONS['lcd']['title'])
    error = []
    try:
        status, reord_list = reorder(display_order, lcd_id, direction)
        if status == 'success':
            DisplayOrder.query.first().lcd = ','.join(map(str, reord_list))
            db.session.commit()
        else:
            error.append(reord_list)
    except Exception as except_msg:
        error.append(except_msg)
    flash_success_errors(error, action, url_for('routes_page.page_lcd'))


def lcd_activate(lcd_id):
    action = '{action} {controller}'.format(
        action=TRANSLATIONS['activate']['title'],
        controller=TRANSLATIONS['lcd']['title'])
    messages = {
        "success": [],
        "info": [],
        "warning": [],
        "error": []
    }

    try:
        # All display lines must be filled to activate display
        lcd = LCD.query.filter(LCD.unique_id == lcd_id).first()
        lcd_data = LCDData.query.filter(LCDData.lcd_id == lcd_id).all()
        blank_line_detected = False

        for each_lcd_data in lcd_data:
            if (
                    (lcd.y_lines in [2, 4, 8] and
                        (not each_lcd_data.line_1_id or
                         not each_lcd_data.line_2_id)
                     ) or
                    (lcd.y_lines in [4, 8] and
                        (not each_lcd_data.line_3_id or
                         not each_lcd_data.line_4_id)
                    ) or
                    (lcd.y_lines == 8 and
                        (not each_lcd_data.line_5_id or
                         not each_lcd_data.line_6_id or
                         not each_lcd_data.line_7_id or
                         not each_lcd_data.line_8_id))
                    ):
                blank_line_detected = True

        def check_display_set(error, display_num, measurement, max_age, decimal_places):
            if measurement not in ["BLANK", "IP", "TEXT"]:
                if max_age is None:
                    error.append(
                        "Display Set {n}: {set}: {opt}".format(
                            n=display_num, set=gettext("Must be set"), opt=TRANSLATIONS['max_age']['title']))
                if decimal_places is None:
                    error.append("Display Set {n}: {set}: {opt}".format(
                        n=display_num, set=gettext("Must be set"), opt=gettext("Decimal Places")))
            return error

        for each_lcd_data in lcd_data:
            if lcd.y_lines in [2, 4, 8]:
                messages["error"] = check_display_set(
                    messages["error"], 1,
                    each_lcd_data.line_1_measurement,
                    each_lcd_data.line_1_max_age,
                    each_lcd_data.line_1_decimal_places)
                messages["error"] = check_display_set(
                    messages["error"], 2,
                    each_lcd_data.line_2_measurement,
                    each_lcd_data.line_2_max_age,
                    each_lcd_data.line_2_decimal_places)
            if lcd.y_lines in [4, 8]:
                messages["error"] = check_display_set(
                    messages["error"], 3,
                    each_lcd_data.line_3_measurement,
                    each_lcd_data.line_3_max_age,
                    each_lcd_data.line_3_decimal_places)
                messages["error"] = check_display_set(
                    messages["error"], 4,
                    each_lcd_data.line_4_measurement,
                    each_lcd_data.line_4_max_age,
                    each_lcd_data.line_4_decimal_places)
            if lcd.y_lines == 8:
                messages["error"] = check_display_set(
                    messages["error"], 5,
                    each_lcd_data.line_5_measurement,
                    each_lcd_data.line_5_max_age,
                    each_lcd_data.line_5_decimal_places)
                messages["error"] = check_display_set(
                    messages["error"], 6,
                    each_lcd_data.line_6_measurement,
                    each_lcd_data.line_6_max_age,
                    each_lcd_data.line_6_decimal_places)
                messages["error"] = check_display_set(
                    messages["error"], 7,
                    each_lcd_data.line_7_measurement,
                    each_lcd_data.line_7_max_age,
                    each_lcd_data.line_7_decimal_places)
                messages["error"] = check_display_set(
                    messages["error"], 8,
                    each_lcd_data.line_8_measurement,
                    each_lcd_data.line_8_max_age,
                    each_lcd_data.line_8_decimal_places)

        if blank_line_detected:
            messages["error"].append(gettext(
                'Detected at least one "Line" unset. '
                'Cannot activate LCD if there are unconfigured lines.'))

        if not messages["error"]:
            messages = controller_activate_deactivate(
                messages, 'activate', 'LCD', lcd_id)
    except Exception as except_msg:
        messages["error"].append(str(except_msg))

    flash_success_errors(
        messages["error"], action, url_for('routes_page.page_lcd'))


def lcd_deactivate(lcd_id):
    messages = {
        "success": [],
        "info": [],
        "warning": [],
        "error": []
    }
    messages = controller_activate_deactivate(
        messages, 'deactivate', 'LCD', lcd_id)


def lcd_reset_flashing(lcd_id):
    control = DaemonControl()
    return_value, return_msg = control.lcd_flash(lcd_id, False)
    if return_value:
        flash(gettext("%(msg)s", msg=return_msg), "success")
    else:
        flash(gettext("%(msg)s", msg=return_msg), "error")


def lcd_display_add(form):
    action = '{action} {controller}'.format(
        action=TRANSLATIONS['add']['title'],
        controller=TRANSLATIONS['display']['title'])
    error = []

    lcd = LCD.query.filter(LCD.unique_id == form.lcd_id.data).first()
    if lcd.is_activated:
        error.append(gettext(
            "Deactivate LCD controller before modifying its settings."))

    if not error:
        try:
            new_lcd_data = LCDData()
            new_lcd_data.lcd_id = form.lcd_id.data
            new_lcd_data.save()
            db.session.commit()
        except sqlalchemy.exc.OperationalError as except_msg:
            error.append(except_msg)
        except sqlalchemy.exc.IntegrityError as except_msg:
            error.append(except_msg)
    flash_success_errors(error, action, url_for('routes_page.page_lcd'))


def lcd_display_mod(form):
    action = '{action} {controller}'.format(
        action=TRANSLATIONS['modify']['title'],
        controller=TRANSLATIONS['display']['title'])
    error = []

    lcd = LCD.query.filter(LCD.unique_id == form.lcd_id.data).first()
    if lcd.is_activated:
        error.append(gettext(
            "Deactivate LCD controller before modifying its settings."))

    if not error:
        try:
            mod_lcd = LCD.query.filter(
                LCD.unique_id == form.lcd_id.data).first()
            if mod_lcd.is_activated:
                flash(gettext(
                    "Deactivate LCD controller before modifying its settings."),
                    "error")
                return redirect(url_for('routes_page.page_lcd'))

            mod_lcd_data = LCDData.query.filter(
                LCDData.unique_id == form.lcd_data_id.data).first()

            if form.line_1_display.data:
                mod_lcd_data.line_1_id = form.line_1_display.data.split(",")[0]
                mod_lcd_data.line_1_measurement = form.line_1_display.data.split(",")[1]
                if form.line_1_text.data:
                    mod_lcd_data.line_1_text = form.line_1_text.data
                mod_lcd_data.line_1_max_age = form.line_1_max_age.data
                mod_lcd_data.line_1_decimal_places = form.line_1_decimal_places.data
            else:
                mod_lcd_data.line_1_id = ''
                mod_lcd_data.line_1_measurement = ''

            if form.line_2_display.data:
                mod_lcd_data.line_2_id = form.line_2_display.data.split(",")[0]
                mod_lcd_data.line_2_measurement = form.line_2_display.data.split(",")[1]
                if form.line_2_text.data:
                    mod_lcd_data.line_2_text = form.line_2_text.data
                mod_lcd_data.line_2_max_age = form.line_2_max_age.data
                mod_lcd_data.line_2_decimal_places = form.line_2_decimal_places.data
            else:
                mod_lcd_data.line_2_id = ''
                mod_lcd_data.line_2_measurement = ''

            if form.line_3_display.data:
                mod_lcd_data.line_3_id = form.line_3_display.data.split(",")[0]
                mod_lcd_data.line_3_measurement = form.line_3_display.data.split(",")[1]
                if form.line_3_text.data:
                    mod_lcd_data.line_3_text = form.line_3_text.data
                mod_lcd_data.line_3_max_age = form.line_3_max_age.data
                mod_lcd_data.line_3_decimal_places = form.line_3_decimal_places.data
            else:
                mod_lcd_data.line_3_id = ''
                mod_lcd_data.line_3_measurement = ''

            if form.line_4_display.data:
                mod_lcd_data.line_4_id = form.line_4_display.data.split(",")[0]
                mod_lcd_data.line_4_measurement = form.line_4_display.data.split(",")[1]
                if form.line_4_text.data:
                    mod_lcd_data.line_4_text = form.line_4_text.data
                mod_lcd_data.line_4_max_age = form.line_4_max_age.data
                mod_lcd_data.line_4_decimal_places = form.line_4_decimal_places.data
            else:
                mod_lcd_data.line_4_id = ''
                mod_lcd_data.line_4_measurement = ''

            if form.line_5_display.data:
                mod_lcd_data.line_5_id = form.line_5_display.data.split(",")[0]
                mod_lcd_data.line_5_measurement = form.line_5_display.data.split(",")[1]
                if form.line_5_text.data:
                    mod_lcd_data.line_5_text = form.line_5_text.data
                mod_lcd_data.line_5_max_age = form.line_5_max_age.data
                mod_lcd_data.line_5_decimal_places = form.line_5_decimal_places.data
            else:
                mod_lcd_data.line_5_id = ''
                mod_lcd_data.line_5_measurement = ''

            if form.line_6_display.data:
                mod_lcd_data.line_6_id = form.line_6_display.data.split(",")[0]
                mod_lcd_data.line_6_measurement = form.line_6_display.data.split(",")[1]
                if form.line_6_text.data:
                    mod_lcd_data.line_6_text = form.line_6_text.data
                mod_lcd_data.line_6_max_age = form.line_6_max_age.data
                mod_lcd_data.line_6_decimal_places = form.line_6_decimal_places.data
            else:
                mod_lcd_data.line_6_id = ''
                mod_lcd_data.line_6_measurement = ''

            if form.line_7_display.data:
                mod_lcd_data.line_7_id = form.line_7_display.data.split(",")[0]
                mod_lcd_data.line_7_measurement = form.line_7_display.data.split(",")[1]
                if form.line_7_text.data:
                    mod_lcd_data.line_7_text = form.line_7_text.data
                mod_lcd_data.line_7_max_age = form.line_7_max_age.data
                mod_lcd_data.line_7_decimal_places = form.line_7_decimal_places.data
            else:
                mod_lcd_data.line_7_id = ''
                mod_lcd_data.line_7_measurement = ''

            if form.line_8_display.data:
                mod_lcd_data.line_8_id = form.line_8_display.data.split(",")[0]
                mod_lcd_data.line_8_measurement = form.line_8_display.data.split(",")[1]
                if form.line_8_text.data:
                    mod_lcd_data.line_8_text = form.line_8_text.data
                mod_lcd_data.line_8_max_age = form.line_8_max_age.data
                mod_lcd_data.line_8_decimal_places = form.line_8_decimal_places.data
            else:
                mod_lcd_data.line_8_id = ''
                mod_lcd_data.line_8_measurement = ''

            db.session.commit()
        except Exception as except_msg:
            error.append(except_msg)
    flash_success_errors(error, action, url_for('routes_page.page_lcd'))


def lcd_display_del(lcd_data_id, delete_last=False):
    action = '{action} {controller}'.format(
        action=TRANSLATIONS['delete']['title'],
        controller=TRANSLATIONS['display']['title'])
    error = []

    lcd_data_this = LCDData.query.filter(
        LCDData.unique_id == lcd_data_id).first()
    lcd_data_all = LCDData.query.filter(
        LCDData.lcd_id == lcd_data_this.lcd_id).all()
    lcd = LCD.query.filter(
        LCD.unique_id == lcd_data_this.lcd_id).first()

    if lcd.is_activated:
        error.append(gettext(
            "Deactivate LCD controller before modifying its settings"))
    if not delete_last and len(lcd_data_all) < 2:
        error.append(gettext("The last display cannot be deleted"))

    if not error:
        try:
            delete_entry_with_id(LCDData, lcd_data_id)
            db.session.commit()
        except Exception as except_msg:
            error.append(except_msg)
    flash_success_errors(error, action, url_for('routes_page.page_lcd'))
