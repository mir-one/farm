# -*- coding: utf-8 -*-
#
# forms_pid.py - PID Flask Forms
#

from flask_babel import lazy_gettext
from flask_wtf import FlaskForm
from wtforms import BooleanField
from wtforms import DecimalField
from wtforms import SelectField
from wtforms import StringField
from wtforms import SubmitField
from wtforms import validators
from wtforms import widgets
from wtforms.validators import DataRequired
from wtforms.validators import Optional
from wtforms.widgets.html5 import NumberInput

from farm.config_translations import TRANSLATIONS


class PIDModBase(FlaskForm):
    function_id = StringField('Function ID', widget=widgets.HiddenInput())
    function_type = StringField('Function Type', widget=widgets.HiddenInput())
    name = StringField(
        TRANSLATIONS['name']['title'],
        validators=[DataRequired()])
    measurement = StringField(
        TRANSLATIONS['measurement']['title'],
        validators=[DataRequired()])
    direction = SelectField(
        lazy_gettext('Direction'),
        choices=[
            ('raise', lazy_gettext('Raise')),
            ('lower', lazy_gettext('Lower')),
            ('both', lazy_gettext('Both'))
        ],
        validators=[DataRequired()]
    )
    period = DecimalField(
        TRANSLATIONS['period']['title'],
        validators=[validators.NumberRange(
            min=1,
            max=86400
        )],
        widget=NumberInput(step='any')
    )
    log_level_debug = BooleanField(
        TRANSLATIONS['log_level_debug']['title'])
    start_offset = DecimalField(
        TRANSLATIONS['start_offset']['title'],
        widget=NumberInput(step='any'))
    max_measure_age = DecimalField(
        TRANSLATIONS['max_age']['title'],
        validators=[validators.NumberRange(
            min=1,
            max=86400
        )],
        widget=NumberInput(step='any')
    )
    setpoint = DecimalField(
        TRANSLATIONS['setpoint']['title'],
        validators=[validators.NumberRange(
            min=-1000000,
            max=1000000
        )],
        widget=NumberInput(step='any')
    )
    band = DecimalField(
        lazy_gettext('Band (+/- Setpoint)'),
        widget=NumberInput(step='any'))
    send_lower_as_negative = BooleanField(lazy_gettext('Send Lower as Negative'))
    store_lower_as_negative = BooleanField(lazy_gettext('Store Lower as Negative'))
    k_p = DecimalField(
        lazy_gettext('Kp Gain'),
        validators=[validators.NumberRange(
            min=0
        )],
        widget=NumberInput(step='any')
    )
    k_i = DecimalField(
        lazy_gettext('Ki Gain'),
        validators=[validators.NumberRange(
            min=0
        )],
        widget=NumberInput(step='any')
    )
    k_d = DecimalField(
        lazy_gettext('Kd Gain'),
        validators=[validators.NumberRange(
            min=0
        )],
        widget=NumberInput(step='any')
    )
    integrator_max = DecimalField(
        lazy_gettext('Integrator Min'),
        widget=NumberInput(step='any'))
    integrator_min = DecimalField(
        lazy_gettext('Integrator Max'),
        widget=NumberInput(step='any'))
    raise_output_id = StringField(lazy_gettext('Output (Raise)'))
    raise_output_type = StringField(lazy_gettext('Action (Raise)'))
    lower_output_id = StringField(lazy_gettext('Output (Lower)'))
    lower_output_type = StringField(lazy_gettext('Action (Lower)'))
    setpoint_tracking_type = StringField(TRANSLATIONS['setpoint_tracking_type']['title'])
    setpoint_tracking_method_id = StringField('Setpoint Tracking Method')
    setpoint_tracking_input_math_id = StringField('Setpoint Tracking Input/Math')
    setpoint_tracking_max_age = DecimalField('Max Age (seconds)',
        validators=[Optional()],
        widget=NumberInput(step='any'))
    pid_hold = SubmitField(lazy_gettext('Hold'))
    pid_pause = SubmitField(lazy_gettext('Pause'))
    pid_resume = SubmitField(lazy_gettext('Resume'))


class PIDModRelayRaise(FlaskForm):
    raise_min_duration = DecimalField(
        lazy_gettext('Min On Duration (Raise)'),
        validators=[validators.NumberRange(
            min=0,
            max=86400
        )],
        widget=NumberInput(step='any')
    )
    raise_max_duration = DecimalField(
        lazy_gettext('Max On Duration (Raise)'),
        validators=[validators.NumberRange(
            min=0,
            max=86400
        )],
        widget=NumberInput(step='any')
    )
    raise_min_off_duration = DecimalField(
        lazy_gettext('Min Off Duration (Raise)'),
        validators=[validators.NumberRange(
            min=0,
            max=86400
        )],
        widget=NumberInput(step='any')
    )


class PIDModRelayLower(FlaskForm):
    lower_min_duration = DecimalField(
        lazy_gettext('Min On Duration (Lower)'),
        validators=[validators.NumberRange(
            min=0,
            max=86400
        )],
        widget=NumberInput(step='any')
    )
    lower_max_duration = DecimalField(
        lazy_gettext('Max On Duration (Lower)'),
        validators=[validators.NumberRange(
            min=0,
            max=86400
        )],
        widget=NumberInput(step='any')
    )
    lower_min_off_duration = DecimalField(
        lazy_gettext('Min Off Duration (Lower)'),
        validators=[validators.NumberRange(
            min=0,
            max=86400
        )],
        widget=NumberInput(step='any')
    )


class PIDModValueRaise(FlaskForm):
    raise_min_amount = DecimalField(
        lazy_gettext('Min Amount (Raise)'),
        widget=NumberInput(step='any')
    )
    raise_max_amount = DecimalField(
        lazy_gettext('Max Amount (Raise)'),
        widget=NumberInput(step='any')
    )


class PIDModValueLower(FlaskForm):
    lower_min_amount = DecimalField(
        lazy_gettext('Min Amount (Lower)'),
        widget=NumberInput(step='any')
    )
    lower_max_amount = DecimalField(
        lazy_gettext('Max Amount (Lower)'),
        widget=NumberInput(step='any')
    )


class PIDModVolumeRaise(FlaskForm):
    raise_min_amount = DecimalField(
        lazy_gettext('Min On Amount (Raise)'),
        validators=[validators.NumberRange(
            min=0,
            max=86400
        )],
        widget=NumberInput(step='any')
    )
    raise_max_amount = DecimalField(
        lazy_gettext('Max On Amount (Raise)'),
        validators=[validators.NumberRange(
            min=0,
            max=86400
        )],
        widget=NumberInput(step='any')
    )


class PIDModVolumeLower(FlaskForm):
    lower_min_amount = DecimalField(
        lazy_gettext('Min On Amount (Lower)'),
        validators=[validators.NumberRange(
            min=0,
            max=86400
        )],
        widget=NumberInput(step='any')
    )
    lower_max_amount = DecimalField(
        lazy_gettext('Max On Amount (Lower)'),
        validators=[validators.NumberRange(
            min=0,
            max=86400
        )],
        widget=NumberInput(step='any')
    )


class PIDModPWMRaise(FlaskForm):
    raise_min_duty_cycle = DecimalField(
        lazy_gettext('Min Duty Cycle (Raise)'),
        validators=[validators.NumberRange(
            min=0,
            max=100
        )],
        widget=NumberInput(step='any')
    )
    raise_max_duty_cycle = DecimalField(
        lazy_gettext('Max Duty Cycle (Raise)'),
        validators=[validators.NumberRange(
            min=0,
            max=100
        )],
        widget=NumberInput(step='any')
    )
    raise_always_min_pwm = BooleanField(
        TRANSLATIONS['raise_always_min_pwm']['title'])


class PIDModPWMLower(FlaskForm):
    lower_min_duty_cycle = DecimalField(
        lazy_gettext('Min Duty Cycle (Lower)'),
        validators=[validators.NumberRange(
            min=0,
            max=100
        )],
        widget=NumberInput(step='any')
    )
    lower_max_duty_cycle = DecimalField(
        lazy_gettext('Max Duty Cycle (Lower)'),
        validators=[validators.NumberRange(
            min=0,
            max=100
        )],
        widget=NumberInput(step='any')
    )
    lower_always_min_pwm = BooleanField(
        TRANSLATIONS['lower_always_min_pwm']['title'])
