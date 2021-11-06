# -*- coding: utf-8 -*-
#
#  config.py - Global Farm settings
#
import binascii
import sys
from datetime import timedelta

import os
from flask_babel import lazy_gettext

# Append proper path for other software reading this config file
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from config_translations import TRANSLATIONS

FARM_VERSION = '1.0.0'
ALEMBIC_VERSION = '0187ea22dc4b'

#  FORCE_UPGRADE_MASTER
#  Set True to enable upgrading to the master branch of the Farm repository.
#  Set False to enable upgrading to the latest Release version (default).
#  Do not use this feature unless you know what you're doing or have been
#  instructed to do so, as it can really mess up your system.
FORCE_UPGRADE_MASTER = False

# Final release for each major version number
# Used to determine proper upgrade page to display
FINAL_RELEASES = ['5.7.3', '6.4.7', '7.10.0']

# ENABLE FLASK PROFILER
# Accessed at https://127.0.0.1/farm-flask-profiler
ENABLE_FLASK_PROFILER = False

LANGUAGES = {
    'en': 'English',
    'de': 'Deutsche (German)',
    'es': 'Español (Spanish)',
    'fr': 'Français (French)',
    'it': 'Italiano (Italian)',
    'nl': 'Nederlands (Dutch)',
    'nb': 'Norsk (Norwegian)',
    'pl': 'Polski (Polish)',
    'pt': 'Português (Portuguese)',
    'ru': 'русский язык (Russian)',
    'sr': 'српски (Serbian)',
    'sv': 'Svenska (Swedish)',
    'zh': '中文 (Chinese)'
}

DASHBOARD_WIDGETS = [
    ('', "{} {} {}".format(lazy_gettext('Add'), lazy_gettext('Dashboard'), lazy_gettext('Widget'))),
    ('spacer', lazy_gettext('Spacer')),
    ('graph', lazy_gettext('Graph')),
    ('gauge', lazy_gettext('Gauge')),
    ('indicator', TRANSLATIONS['indicator']['title']),
    ('measurement', TRANSLATIONS['measurement']['title']),
    ('output', TRANSLATIONS['output']['title']),
    ('output_pwm_slider', '{}: {}'.format(
        TRANSLATIONS['output']['title'], lazy_gettext('PWM Slider'))),
    ('pid_control', lazy_gettext('PID Control')),
    ('python_code', lazy_gettext('Python Code')),
    ('camera', TRANSLATIONS['camera']['title'])
]

# Camera info
CAMERA_INFO = {
    'fswebcam': {
        'name': 'fswebcam',
        'dependencies_module': [
            ('apt', 'fswebcam', 'fswebcam')
        ],
        'capable_image': True,
        'capable_stream': False
    },
    'opencv': {
        'name': 'OpenCV',
        'dependencies_module': [
            ('pip-pypi', 'imutils', 'imutils'),
            ('apt', 'python3-opencv', 'python3-opencv'),
        ],
        'capable_image': True,
        'capable_stream': True
    },
    'picamera': {
        'name': 'PiCamera',
        'dependencies_module': [
            ('pip-pypi', 'picamera', 'picamerab==1.13b1')
        ],
        'capable_image': True,
        'capable_stream': True
    },
    'raspistill': {
        'name': 'raspistill',
        'dependencies_module': [],
        'capable_image': True,
        'capable_stream': False
    },
    'http_address': {
        'name': 'URL (urllib)',
        'dependencies_module': [
            ('pip-pypi', 'imutils', 'imutils'),
            ('apt', 'python3-opencv', 'python3-opencv'),
        ],
        'capable_image': True,
        'capable_stream': True
    },
    'http_address_requests': {
        'name': 'URL (requests)',
        'dependencies_module': [
            ('pip-pypi', 'imutils', 'imutils'),
            ('apt', 'python3-opencv', 'python3-opencv'),
        ],
        'capable_image': True,
        'capable_stream': False
    },
}

# LCD info
LCD_INFO = {
    '16x2_generic': {
        'name': '16x2 LCD',
        'dependencies_module': [],
        'interfaces': ['I2C']
    },
    '20x4_generic': {
        'name': '20x4 LCD',
        'dependencies_module': [],
        'interfaces': ['I2C']
    },
    '16x2_grove_lcd_rgb': {
        'name': '16x2 Grove LCD RGB',
        'dependencies_module': [],
        'interfaces': ['I2C']
    },
    '128x32_pioled_circuit_python': {
        'name': '128x32 OLED (SD1306, CircuitPython)',
        'message': "This module uses the newer Adafruit CircuitPython library. The older Adafruit_SSD1306 library is deprecated and not recommended to be used.",
        'dependencies_module': [
            ('apt', 'libjpeg-dev', 'libjpeg-dev'),
            ('pip-pypi', 'PIL', 'Pillow==8.1.2'),
            ('pip-pypi', 'usb.core', 'pyusb==1.1.1'),
            ('pip-pypi', 'adafruit_extended_bus', 'adafruit-extended-bus==1.0.1'),
            ('pip-pypi', 'adafruit_framebuf', 'adafruit-circuitpython-framebuf'),
            ('pip-pypi', 'adafruit_ssd1306', 'Adafruit-Circuitpython-SSD1306')
        ],
        'interfaces': ['I2C', 'SPI']
    },
    '128x64_pioled_circuit_python': {
        'name': '128x64 OLED (SD1306, CircuitPython)',
        'message': "This module uses the newer Adafruit CircuitPython library. The older Adafruit_SSD1306 library is deprecated and not recommended to be used.",
        'dependencies_module': [
            ('apt', 'libjpeg-dev', 'libjpeg-dev'),
            ('pip-pypi', 'PIL', 'Pillow==8.1.2'),
            ('pip-pypi', 'usb.core', 'pyusb==1.1.1'),
            ('pip-pypi', 'adafruit_extended_bus', 'adafruit-extended-bus==1.0.1'),
            ('pip-pypi', 'adafruit_framebuf', 'adafruit-circuitpython-framebuf'),
            ('pip-pypi', 'adafruit_ssd1306', 'Adafruit-Circuitpython-SSD1306')
        ],
        'interfaces': ['I2C', 'SPI']
    },
    '128x32_pioled': {
        'name': '128x32 OLED (SD1306, Adafruit_SSD1306)',
        'message': "This module uses the older Adafruit_SSD1306 library that is deprecated and is not recommended to be used. It is recommended to use the other module that uses the newer Adafruit CircuitPython library.",
        'dependencies_module': [
            ('apt', 'libjpeg-dev', 'libjpeg-dev'),
            ('pip-pypi', 'PIL', 'Pillow==8.1.2'),
            ('pip-pypi', 'Adafruit_GPIO', 'Adafruit-GPIO==1.0.3'),
            ('pip-pypi', 'Adafruit_PureIO', 'Adafruit-PureIO==1.1.8'),
            ('pip-pypi', 'Adafruit_SSD1306', 'git+https://github.com/adafruit/Adafruit_Python_SSD1306.git')
        ],
        'interfaces': ['I2C', 'SPI']
    },
    '128x64_pioled': {
        'name': '128x64 OLED (SD1306, Adafruit_SSD1306)',
        'message': "This module uses the older Adafruit_SSD1306 library that is deprecated and is not recommended to be used. It is recommended to use the other module that uses the newer Adafruit CircuitPython library.",
        'dependencies_module': [
            ('apt', 'libjpeg-dev', 'libjpeg-dev'),
            ('pip-pypi', 'PIL', 'Pillow==8.1.2'),
            ('pip-pypi', 'Adafruit_GPIO', 'Adafruit-GPIO==1.0.3'),
            ('pip-pypi', 'Adafruit_PureIO', 'Adafruit-PureIO==1.1.8'),
            ('pip-pypi', 'Adafruit_SSD1306', 'git+https://github.com/adafruit/Adafruit_Python_SSD1306.git')
        ],
        'interfaces': ['I2C', 'SPI']
    }
}

# Math form dropdown
LCDS = [
    ('16x2_generic', LCD_INFO['16x2_generic']['name']),
    ('20x4_generic', LCD_INFO['20x4_generic']['name']),
    ('16x2_grove_lcd_rgb', LCD_INFO['16x2_grove_lcd_rgb']['name']),
    ('128x32_pioled', LCD_INFO['128x32_pioled']['name']),
    ('128x64_pioled', LCD_INFO['128x64_pioled']['name']),
    ('128x32_pioled_circuit_python', LCD_INFO['128x32_pioled_circuit_python']['name']),
    ('128x64_pioled_circuit_python', LCD_INFO['128x64_pioled_circuit_python']['name'])
]

# Math info
MATH_INFO = {
    'average': {
        'name': "{} ({}, {})".format(lazy_gettext('Average'), lazy_gettext('Last'), lazy_gettext('Multiple Channels')),
        'dependencies_module': [],
        'enable_measurements_select': True,
        'measure': {}
    },
    'average_single': {
        'name': "{} ({}, {})".format(lazy_gettext('Average'), lazy_gettext('Past'), lazy_gettext('Single Channel')),
        'dependencies_module': [],
        'enable_measurements_select': False,
        'enable_measurements_convert': True,
        'measure': {}
    },
    'sum': {
        'name': "{} ({}, {})".format(lazy_gettext('Sum'), lazy_gettext('Last'), lazy_gettext('Multiple Channels')),
        'dependencies_module': [],
        'enable_measurements_select': True,
        'measure': {}
    },
    'sum_single': {
        'name': "{} ({}, {})".format(lazy_gettext('Sum'), lazy_gettext('Past'), lazy_gettext('Single Channel')),
        'dependencies_module': [],
        'enable_measurements_select': False,
        'enable_measurements_convert': True,
        'measure': {}
    },
    'difference': {
        'name': lazy_gettext('Difference'),
        'dependencies_module': [],
        'enable_measurements_select': True,
        'measure': {}
    },
    'equation': {
        'name': lazy_gettext('Equation'),
        'dependencies_module': [],
        'enable_measurements_select': True,
        'measure': {}
    },
    'humidity': {
        'name': "{} ({})".format(lazy_gettext('Humidity'), lazy_gettext('Wet/Dry-Bulb')),
        'dependencies_module': [],
        'enable_measurements_convert': True,
        'measure': {
            0: {
                'measurement': 'humidity',
                'unit': 'percent'
            },
            1: {
                'measurement': 'humidity_ratio',
                'unit': 'kg_kg'
            },
            2: {
                'measurement': 'specific_enthalpy',
                'unit': 'kJ_kg'
            },
            3: {
                'measurement': 'specific_volume',
                'unit': 'm3_kg'
            }
        }
    },
    'redundancy': {
        'name': lazy_gettext('Redundancy'),
        'dependencies_module': [],
        'enable_measurements_select': True,
        'measure': {}
    },
    'statistics': {
        'name': lazy_gettext('Statistics'),
        'dependencies_module': [],
        'enable_single_measurement_select': True,
        'measure': {
            0: {
                'measurement': '',
                'unit': '',
                'name': 'Mean'
            },
            1: {
                'measurement': '',
                'unit': '',
                'name': 'Median'
            },
            2: {
                'measurement': '',
                'unit': '',
                'name': 'Minimum'
            },
            3: {
                'measurement': '',
                'unit': '',
                'name': 'Maximum'
            },
            4: {
                'measurement': '',
                'unit': '',
                'name': 'Standard Deviation'
            },
            5: {
                'measurement': '',
                'unit': '',
                'name': 'St. Dev. of Mean (upper)'
            },
            6: {
                'measurement': '',
                'unit': '',
                'name': 'St. Dev. of Mean (lower)'
            }
        }
    },
    'verification': {
        'name': lazy_gettext('Verification'),
        'dependencies_module': [],
        'enable_measurements_select': True,
        'measure': {}
    },
    'vapor_pressure_deficit': {
        'name': lazy_gettext('Vapor Pressure Deficit'),
        'dependencies_module': [],
        'enable_measurements_select': False,
        'measure': {
            0: {
                'measurement': 'vapor_pressure_deficit',
                'unit': 'Pa'
            }
        }
    }
}

METHOD_DEP_BASE = [
    ('apt', 'unzip', 'unzip'),
    ('bash-commands',
     [
         '/var/farm-root/farm/farm_flask/static/js/user_js/highcharts-9.1.2.js'
     ],
     [
        'wget --no-clobber https://code.highcharts.com/zips/Highcharts-9.1.2.zip',
        'unzip Highcharts-9.1.2.zip -d Highcharts-9.1.2',
        'cp -rf Highcharts-9.1.2/code/highcharts.js /var/farm-root/farm/farm_flask/static/js/user_js/highcharts-9.1.2.js',
        'cp -rf Highcharts-9.1.2/code/highcharts.js.map /var/farm-root/farm/farm_flask/static/js/user_js/highcharts.js.map',
        'rm -rf Highcharts-9.1.2'
     ])
]

# Method info
METHOD_INFO = {
    'Date': {
        'name': lazy_gettext('Time/Date'),
        'dependencies_module': METHOD_DEP_BASE
    },
    'Duration': {
        'name': lazy_gettext('Duration'),
        'dependencies_module': METHOD_DEP_BASE
    },
    'Daily': {
        'name': "{} ({})".format(lazy_gettext('Daily'), lazy_gettext('Time-Based')),
        'dependencies_module': METHOD_DEP_BASE
    },
    'DailySine': {
        'name': "{} ({})".format(lazy_gettext('Daily'), lazy_gettext('Sine Wave')),
        'dependencies_module': METHOD_DEP_BASE
    },
    'DailyBezier': {
        'name': "{} ({})".format(lazy_gettext('Daily'), lazy_gettext('Bezier Curve')),
        'dependencies_module': [
            ('apt', 'libatlas-base-dev', 'libatlas-base-dev'),
            ('apt', 'python3-numpy', 'python3-numpy')
        ] + METHOD_DEP_BASE
    },
    'Cascade': {
        'name': lazy_gettext('Method Cascade'),
        'dependencies_module': METHOD_DEP_BASE
    }
}

# Method form dropdown
METHODS = [
    ('Date', METHOD_INFO['Date']['name']),
    ('Duration', METHOD_INFO['Duration']['name']),
    ('Daily', METHOD_INFO['Daily']['name']),
    ('DailySine', METHOD_INFO['DailySine']['name']),
    ('DailyBezier', METHOD_INFO['DailyBezier']['name']),
    ('Cascade', METHOD_INFO['Cascade']['name'])
]

PID_INFO = {
    'measure': {
        0: {
            'measurement': '',
            'unit': '',
            'name': '{}'.format(TRANSLATIONS['setpoint']['title']),
            'measurement_type': 'setpoint'
        },
        1: {
            'measurement': '',
            'unit': '',
            'name': '{} ({})'.format(
                TRANSLATIONS['setpoint']['title'], lazy_gettext('Band Min')),
            'measurement_type': 'setpoint'
        },
        2: {
            'measurement': '',
            'unit': '',
            'name': '{} ({})'.format(
                TRANSLATIONS['setpoint']['title'], lazy_gettext('Band Max')),
            'measurement_type': 'setpoint'
        },
        3: {
            'measurement': 'pid_p_value',
            'unit': 'pid_value',
            'name': 'P-value'
        },
        4: {
            'measurement': 'pid_i_value',
            'unit': 'pid_value',
            'name': 'I-value'
        },
        5: {
            'measurement': 'pid_d_value',
            'unit': 'pid_value',
            'name': 'D-value'
        },
        6: {
            'measurement': 'duration_time',
            'unit': 's',
            'name': '{} ({})'.format(
                TRANSLATIONS['output']['title'], TRANSLATIONS['duration']['title'])
        },
        7: {
            'measurement': 'duty_cycle',
            'unit': 'percent',
            'name': '{} ({})'.format(
                TRANSLATIONS['output']['title'], TRANSLATIONS['duty_cycle']['title'])
        },
        8: {
            'measurement': 'volume',
            'unit': 'ml',
            'name': '{} ({})'.format(
                TRANSLATIONS['output']['title'], TRANSLATIONS['volume']['title'])
        },
        9: {
            'measurement': 'unitless',
            'unit': 'none',
            'name': '{} ({})'.format(
                TRANSLATIONS['output']['title'], TRANSLATIONS['value']['title'])
        }
    }
}

DEPENDENCIES_GENERAL = {
    'highstock': {
        'name': 'Highstock',
        'dependencies_module': [
            ('apt', 'unzip', 'unzip'),
            ('bash-commands',
             [
                 '/var/farm-root/farm/farm_flask/static/js/user_js/highstock-9.1.2.js',
                 '/var/farm-root/farm/farm_flask/static/js/user_js/highcharts-more-9.1.2.js',
                 '/var/farm-root/farm/farm_flask/static/js/user_js/data-9.1.2.js',
                 '/var/farm-root/farm/farm_flask/static/js/user_js/exporting-9.1.2.js',
                 '/var/farm-root/farm/farm_flask/static/js/user_js/export-data-9.1.2.js',
                 '/var/farm-root/farm/farm_flask/static/js/user_js/offline-exporting-9.1.2.js'
             ],
             [
                 'wget --no-clobber https://code.highcharts.com/zips/Highcharts-Stock-9.1.2.zip',
                 'unzip Highcharts-Stock-9.1.2.zip -d Highcharts-Stock-9.1.2',
                 'cp -rf Highcharts-Stock-9.1.2/code/highstock.js /var/farm-root/farm/farm_flask/static/js/user_js/highstock-9.1.2.js',
                 'cp -rf Highcharts-Stock-9.1.2/code/highstock.js.map /var/farm-root/farm/farm_flask/static/js/user_js/highstock.js.map',
                 'cp -rf Highcharts-Stock-9.1.2/code/highcharts-more.js /var/farm-root/farm/farm_flask/static/js/user_js/highcharts-more-9.1.2.js',
                 'cp -rf Highcharts-Stock-9.1.2/code/highcharts-more.js.map /var/farm-root/farm/farm_flask/static/js/user_js/highcharts-more.js.map',
                 'cp -rf Highcharts-Stock-9.1.2/code/modules/data.js /var/farm-root/farm/farm_flask/static/js/user_js/data-9.1.2.js',
                 'cp -rf Highcharts-Stock-9.1.2/code/modules/data.js.map /var/farm-root/farm/farm_flask/static/js/user_js/data.js.map',
                 'cp -rf Highcharts-Stock-9.1.2/code/modules/exporting.js /var/farm-root/farm/farm_flask/static/js/user_js/exporting-9.1.2.js',
                 'cp -rf Highcharts-Stock-9.1.2/code/modules/exporting.js.map /var/farm-root/farm/farm_flask/static/js/user_js/exporting.js.map',
                 'cp -rf Highcharts-Stock-9.1.2/code/modules/export-data.js /var/farm-root/farm/farm_flask/static/js/user_js/export-data-9.1.2.js',
                 'cp -rf Highcharts-Stock-9.1.2/code/modules/export-data.js.map /var/farm-root/farm/farm_flask/static/js/user_js/export-data.js.map',
                 'cp -rf Highcharts-Stock-9.1.2/code/modules/offline-exporting.js /var/farm-root/farm/farm_flask/static/js/user_js/offline-exporting-9.1.2.js',
                 'cp -rf Highcharts-Stock-9.1.2/code/modules/offline-exporting.js.map /var/farm-root/farm/farm_flask/static/js/user_js/offline-exporting.js.map',
                 'rm -rf Highcharts-Stock-9.1.2'
             ])
        ]
    }
}

# Conditional controllers
CONDITIONAL_CONDITIONS = [
    ('measurement', "{} ({}, {})".format(
        TRANSLATIONS['measurement']['title'],
        TRANSLATIONS['single']['title'],
        TRANSLATIONS['last']['title'])),
    ('measurement_past_average', "{} ({}, {}, {})".format(
        TRANSLATIONS['measurement']['title'],
        TRANSLATIONS['single']['title'],
        TRANSLATIONS['past']['title'],
        TRANSLATIONS['average']['title'])),
    ('measurement_past_sum', "{} ({}, {}, {})".format(
        TRANSLATIONS['measurement']['title'],
        TRANSLATIONS['single']['title'],
        TRANSLATIONS['past']['title'],
        TRANSLATIONS['sum']['title'])),
    ('measurement_dict', "{} ({}, {})".format(
        TRANSLATIONS['measurement']['title'],
        TRANSLATIONS['multiple']['title'],
        TRANSLATIONS['past']['title'])),
    ('gpio_state', lazy_gettext('GPIO State')),
    ('output_state', lazy_gettext('Output State')),
    ('output_duration_on', lazy_gettext('Output Duration On')),
    ('controller_status', lazy_gettext("Controller Running")),
]

FUNCTION_INFO = {
    'function_actions': {
        'name': lazy_gettext('Execute Actions'),
        'dependencies_module': []
    },
    'conditional_conditional': {
        'name': '{} {}'.format(
            TRANSLATIONS['conditional']['title'],
            TRANSLATIONS['controller']['title']),
        'dependencies_module': []
    },
    'pid_pid': {
        'name': '{} {}'.format(
            TRANSLATIONS['pid']['title'],
            TRANSLATIONS['controller']['title']),
        'dependencies_module': []
    },
    'trigger_edge': {
        'name': '{}: {}'.format(
            TRANSLATIONS['trigger']['title'],
            TRANSLATIONS['edge']['title']),
        'dependencies_module': []
    },
    'trigger_output': {
        'name': '{}: {} ({}/{})'.format(
            TRANSLATIONS['trigger']['title'],
            TRANSLATIONS['output']['title'],
            TRANSLATIONS['on']['title'],
            TRANSLATIONS['off']['title']),
        'dependencies_module': []
    },
    'trigger_output_pwm': {
        'name': '{}: {} ({})'.format(
            TRANSLATIONS['trigger']['title'],
            TRANSLATIONS['output']['title'],
            TRANSLATIONS['pwm']['title']),
        'dependencies_module': []
    },
    'trigger_timer_daily_time_point': {
        'name': lazy_gettext('Trigger: Timer (Daily Point)'),
        'dependencies_module': []
    },
    'trigger_timer_daily_time_span': {
        'name': '{}: {} ({})'.format(
            TRANSLATIONS['trigger']['title'],
            TRANSLATIONS['timer']['title'],
            lazy_gettext('Daily Span')),
        'dependencies_module': []
    },
    'trigger_timer_duration': {
        'name': '{}: {} ({})'.format(
            TRANSLATIONS['trigger']['title'],
            TRANSLATIONS['timer']['title'],
            TRANSLATIONS['duration']['title']),
        'dependencies_module': []
    },
    'trigger_run_pwm_method': {
        'name': '{}: {}'.format(
            TRANSLATIONS['trigger']['title'],
            lazy_gettext('Run PWM Method')),
        'dependencies_module': []
    },
    'trigger_sunrise_sunset': {
        'name': '{}: {}'.format(
            TRANSLATIONS['trigger']['title'],
            lazy_gettext('Sunrise/Sunset')),
        'dependencies_module': []
    }
}

FUNCTIONS = [
    ('function_actions', FUNCTION_INFO['function_actions']['name']),
    ('conditional_conditional', FUNCTION_INFO['conditional_conditional']['name']),
    ('pid_pid', FUNCTION_INFO['pid_pid']['name']),
    ('trigger_edge', FUNCTION_INFO['trigger_edge']['name']),
    ('trigger_output', FUNCTION_INFO['trigger_output']['name']),
    ('trigger_output_pwm', FUNCTION_INFO['trigger_output_pwm']['name']),
    ('trigger_timer_daily_time_point', FUNCTION_INFO['trigger_timer_daily_time_point']['name']),
    ('trigger_timer_daily_time_span', FUNCTION_INFO['trigger_timer_daily_time_span']['name']),
    ('trigger_timer_duration', FUNCTION_INFO['trigger_timer_duration']['name']),
    ('trigger_run_pwm_method', FUNCTION_INFO['trigger_run_pwm_method']['name']),
    ('trigger_sunrise_sunset', FUNCTION_INFO['trigger_sunrise_sunset']['name'])
]

# Function actions
FUNCTION_ACTION_INFO = {
    'activate_controller': {
        'name': '{}: {}'.format(
            TRANSLATIONS['controller']['title'], TRANSLATIONS['activate']['title']),
        'description': lazy_gettext('Activate a controller.'),
        'dependencies_module': []
    },
    'photo': {  # TODO: rename to camera_capture_photo
        'name': "{}: {}".format(TRANSLATIONS['camera']['title'], lazy_gettext('Capture Photo')),
        'description': lazy_gettext('Capture a photo with the selected Camera.'),
        'dependencies_module': []
    },
    'camera_timelapse_pause': {
        'name': '{}: {}: {}'.format(
            TRANSLATIONS['camera']['title'], TRANSLATIONS['timelapse']['title'], TRANSLATIONS['pause']['title']),
        'description': 'Pause a camera timelapse',
        'dependencies_module': []
    },
    'camera_timelapse_resume': {
        'name': '{}: {}: {}'.format(
            TRANSLATIONS['camera']['title'], TRANSLATIONS['timelapse']['title'], TRANSLATIONS['resume']['title']),
        'description': 'Resume a camera timelapse',
        'dependencies_module': []
    },
    'clear_total_volume': {
        'name': "{}: {}".format(
            lazy_gettext('Flow Meter'), lazy_gettext('Clear Total Volume')),
        'description': 'Clear the total volume saved for a flow meter input.',
        'dependencies_module': []
    },
    'command': {
        'name': "{}: {}".format(
            lazy_gettext('Execute Command'), lazy_gettext('Shell')),
        'description': lazy_gettext('Execute a Linux shell command.'),
        'dependencies_module': []
    },
    'create_note': {
        'name': TRANSLATIONS['note']['title'],
        'description': lazy_gettext('Create a note with the selected Tag.'),
        'dependencies_module': []
    },
    'deactivate_controller': {
        'name': '{}: {}'.format(
            TRANSLATIONS['controller']['title'], TRANSLATIONS['deactivate']['title']),
        'description': lazy_gettext('Deactivate a controller.'),
        'dependencies_module': []
    },
    'email': {
        'name': '{} ({})'.format(
            TRANSLATIONS['email']['title'], TRANSLATIONS['single']['title']),
        'description': 'Email a single recipient.',
        'dependencies_module': []
    },
    'email_multiple': {
        'name': '{} ({})'.format(
            TRANSLATIONS['email']['title'], TRANSLATIONS['multiple']['title']),
        'description': 'Email multiple recipients. Separate email addresses with commas (e.g. "email1@address.com,email2@address.com").',
        'dependencies_module': []
    },
    'flash_lcd_off': {
        'name': '{}: {}'.format(
            TRANSLATIONS['lcd']['title'], lazy_gettext('Flashing Off')),
        'description': 'Stop LCD flashing.',
        'dependencies_module': []
    },
    'flash_lcd_on': {
        'name': '{}: {}'.format(
            TRANSLATIONS['lcd']['title'], lazy_gettext('Flashing On')),
        'description': 'Start LCD flashing.',
        'dependencies_module': []
    },
    'input_force_measurements': {
        'name': "{}: {}".format(
            lazy_gettext('Input'), lazy_gettext('Force Measurements')),
        'description': lazy_gettext('Force measurements to be conducted for an input'),
        'dependencies_module': []
    },
    'lcd_backlight_color': {
        'name': '{}: {}: {}'.format(
            TRANSLATIONS['lcd']['title'],
            lazy_gettext('Backlight'),
            lazy_gettext('Color')),
        'description': 'Set LCD backlight color (if supported).',
        'dependencies_module': []
    },
    'lcd_backlight_off': {
        'name': '{}: {}: {}'.format(
            TRANSLATIONS['lcd']['title'],
            lazy_gettext('Backlight'),
            lazy_gettext('Off')),
        'description': 'Turn off LCD backlight (if supported).',
        'dependencies_module': []
    },
    'lcd_backlight_on': {
        'name': '{}: {}: {}'.format(
            TRANSLATIONS['lcd']['title'],
            lazy_gettext('Backlight'),
            lazy_gettext('On')),
        'description': 'Turn on LCD backlight (if supported).',
        'dependencies_module': []
    },
    'method_pid': {
        'name': '{}: {}'.format(
            TRANSLATIONS['pid']['title'], lazy_gettext('Set Method')),
        'description': lazy_gettext('Select a method to set the PID to use.'),
        'dependencies_module': []
    },
    'mqtt_publish': {
        'name': 'MQTT: {}'.format(lazy_gettext('Publish')),
        'description': 'Publish a value to an MQTT server.',
        'dependencies_module': [
            ('pip-pypi', 'paho', 'paho-mqtt==1.5.1')
        ]
    },
    'output': {
        'name': '{} ({}/{}/{})'.format(
            TRANSLATIONS['output']['title'],
            TRANSLATIONS['on']['title'],
            TRANSLATIONS['off']['title'],
            TRANSLATIONS['duration']['title']),
        'description': lazy_gettext('Turn an Output Off, On, or On for a duration.'),
        'dependencies_module': []
    },
    'output_pwm': {
        'name': '{} ({})'.format(
            TRANSLATIONS['output']['title'], TRANSLATIONS['duty_cycle']['title']),
        'description': lazy_gettext('Set an Output to a PWM duty cycle.'),
        'dependencies_module': []
    },
    'output_ramp_pwm': {
        'name': '{} ({} {})'.format(
            TRANSLATIONS['output']['title'],
            TRANSLATIONS['ramp']['title'],
            TRANSLATIONS['duty_cycle']['title']),
        'description': lazy_gettext('Ramp an Output from one duty cycle to another duty cycle over a period of time.'),
        'dependencies_module': []
    },
    'output_value': {
        'name': '{} ({})'.format(
            TRANSLATIONS['output']['title'], TRANSLATIONS['value']['title']),
        'description': lazy_gettext('Send a value to the Output.'),
        'dependencies_module': []
    },
    'output_volume': {
        'name': '{} ({})'.format(
            TRANSLATIONS['output']['title'], TRANSLATIONS['volume']['title']),
        'description': lazy_gettext('Instruct the Output to dispense a volume.'),
        'dependencies_module': []
    },
    'pause_actions': {
        'name': '{} {}'.format(
            TRANSLATIONS['pause']['title'], TRANSLATIONS['actions']['title']),
        'description': lazy_gettext('Set a delay between executing Actions when self.run_all_actions() is used.'),
        'dependencies_module': []
    },
    'pause_pid': {
        'name': '{}: {}'.format(
            TRANSLATIONS['pid']['title'], TRANSLATIONS['pause']['title']),
        'description': lazy_gettext('Pause a PID.'),
        'dependencies_module': []
    },
    'photo_email': {
        'name': lazy_gettext('Email with Photo Attachment'),
        'description': 'Capture a photo with the selected Camera and Email it as an attachment.',
        'dependencies_module': []
    },
    'resume_pid': {
        'name': '{}: {}'.format(
            TRANSLATIONS['pid']['title'], TRANSLATIONS['resume']['title']),
        'description': lazy_gettext('Resume a PID.'),
        'dependencies_module': []
    },
    'setpoint_pid': {
        'name': '{}: {}: {}'.format(
            TRANSLATIONS['pid']['title'],
            lazy_gettext('Set'),
            lazy_gettext('Setpoint')),
        'description': lazy_gettext('Set the Setpoint of a PID.'),
        'dependencies_module': []
    },
    'setpoint_pid_lower': {
        'name': '{}: {}: {}'.format(
            TRANSLATIONS['pid']['title'],
            lazy_gettext('Lower'),
            lazy_gettext('Setpoint')),
        'description': lazy_gettext('Lower the Setpoint of a PID by this value.'),
        'dependencies_module': []
    },
    'setpoint_pid_raise': {
        'name': '{}: {}: {}'.format(
            TRANSLATIONS['pid']['title'],
            lazy_gettext('Raise'),
            lazy_gettext('Setpoint')),
        'description': lazy_gettext('Raise the Setpoint of a PID by this value.'),
        'dependencies_module': []
    },
    'system_restart': {
        'name': '{}: {}'.format(
            TRANSLATIONS['system']['title'], lazy_gettext('Restart')),
        'description': 'Restart the System',
        'dependencies_module': []
    },
    'system_shutdown': {
        'name': '{}: {}'.format(
            TRANSLATIONS['system']['title'], lazy_gettext('Shutdown')),
        'description': 'Shutdown the System',
        'dependencies_module': []
    },
    'video_email': {
        'name': lazy_gettext('Email with Video Attachment'),
        'description': 'Capture a video with the selected Camera and Email it as an attachment',
        'dependencies_module': []
    },
    'webhook': {
        'name': lazy_gettext('Webhook'),
        'description': 'Emits a HTTP request when triggered. The first line contains a HTTP verb (GET, POST, PUT, ...) followed by a space and the URL to call. Subsequent lines are optional "name: value"-header parameters. After a blank line, the body payload to be sent follows. {{{message}}} is a placeholder that gets replaced by the message, {{{quoted_message}}} is the message in an URL safe encoding.',
        'dependencies_module': []
    },

    # TODO: These have been disabled until they can be properly tested
    # ('video', lazy_gettext('Video')),
}

FUNCTION_ACTIONS = [
    ('pause_actions', FUNCTION_ACTION_INFO['pause_actions']['name']),
    ('photo', FUNCTION_ACTION_INFO['photo']['name']),
    ('camera_timelapse_pause', FUNCTION_ACTION_INFO['camera_timelapse_pause']['name']),
    ('camera_timelapse_resume', FUNCTION_ACTION_INFO['camera_timelapse_resume']['name']),
    ('activate_controller', FUNCTION_ACTION_INFO['activate_controller']['name']),
    ('deactivate_controller', FUNCTION_ACTION_INFO['deactivate_controller']['name']),
    ('clear_total_volume', FUNCTION_ACTION_INFO['clear_total_volume']['name']),
    ('create_note', FUNCTION_ACTION_INFO['create_note']['name']),
    ('email', FUNCTION_ACTION_INFO['email']['name']),
    ('email_multiple', FUNCTION_ACTION_INFO['email_multiple']['name']),
    ('input_force_measurements', FUNCTION_ACTION_INFO['input_force_measurements']['name']),
    ('photo_email', FUNCTION_ACTION_INFO['photo_email']['name']),
    ('video_email', FUNCTION_ACTION_INFO['video_email']['name']),
    ('command', FUNCTION_ACTION_INFO['command']['name']),
    ('lcd_backlight_off', FUNCTION_ACTION_INFO['lcd_backlight_off']['name']),
    ('lcd_backlight_on', FUNCTION_ACTION_INFO['lcd_backlight_on']['name']),
    ('lcd_backlight_color', FUNCTION_ACTION_INFO['lcd_backlight_color']['name']),
    ('flash_lcd_off', FUNCTION_ACTION_INFO['flash_lcd_off']['name']),
    ('flash_lcd_on', FUNCTION_ACTION_INFO['flash_lcd_on']['name']),
    ('mqtt_publish', FUNCTION_ACTION_INFO['mqtt_publish']['name']),
    ('output', FUNCTION_ACTION_INFO['output']['name']),
    ('output_pwm', FUNCTION_ACTION_INFO['output_pwm']['name']),
    ('output_ramp_pwm', FUNCTION_ACTION_INFO['output_ramp_pwm']['name']),
    ('output_value', FUNCTION_ACTION_INFO['output_value']['name']),
    ('output_volume', FUNCTION_ACTION_INFO['output_volume']['name']),
    ('pause_pid', FUNCTION_ACTION_INFO['pause_pid']['name']),
    ('resume_pid', FUNCTION_ACTION_INFO['resume_pid']['name']),
    ('method_pid', FUNCTION_ACTION_INFO['method_pid']['name']),
    ('setpoint_pid', FUNCTION_ACTION_INFO['setpoint_pid']['name']),
    ('setpoint_pid_raise', FUNCTION_ACTION_INFO['setpoint_pid_raise']['name']),
    ('setpoint_pid_lower', FUNCTION_ACTION_INFO['setpoint_pid_lower']['name']),
    ('system_restart', FUNCTION_ACTION_INFO['system_restart']['name']),
    ('system_shutdown', FUNCTION_ACTION_INFO['system_shutdown']['name']),
    ('webhook', FUNCTION_ACTION_INFO['webhook']['name'])
]

# User Roles
USER_ROLES = [
    dict(id=1, name='Admin',
         edit_settings=True, edit_controllers=True, edit_users=True,
         view_settings=True, view_camera=True, view_stats=True, view_logs=True,
         reset_password=True),
    dict(id=2, name='Editor',
         edit_settings=True, edit_controllers=True, edit_users=False,
         view_settings=True, view_camera=True, view_stats=True, view_logs=True,
         reset_password=True),
    dict(id=3, name='Monitor',
         edit_settings=False, edit_controllers=False, edit_users=False,
         view_settings=True, view_camera=True, view_stats=True, view_logs=True,
         reset_password=True),
    dict(id=4, name='Guest',
         edit_settings=False, edit_controllers=False, edit_users=False,
         view_settings=False, view_camera=False, view_stats=False, view_logs=False,
         reset_password=False),
    dict(id=5, name='Kiosk',
         edit_settings=False, edit_controllers=False, edit_users=False,
         view_settings=False, view_camera=True, view_stats=True, view_logs=False,
         reset_password=False)
]

# Web UI themes
THEMES = [
    ('cerulean', 'Cerulean'),
    ('cosmo', 'Cosmo'),
    ('cyborg', 'Cyborg'),
    ('darkly', 'Darkly'),
    ('flatly', 'Flatly'),
    ('journal', 'Journal'),
    ('literia', 'Literia'),
    ('lumen', 'Lumen'),
    ('lux', 'Lux'),
    ('materia', 'Materia'),
    ('minty', 'Minty'),
    ('pulse', 'Pulse'),
    ('sandstone', 'Sandstone'),
    ('simplex', 'Simplex'),
    ('slate', 'Slate'),
    ('solar', 'Solar'),
    ('spacelab', 'Spacelab'),
    ('superhero', 'Superhero'),
    ('united', 'United'),
    ('yeti', 'Yeti')
]

THEMES_DARK = ['cyborg', 'darkly', 'slate', 'solar', 'superhero']

# Install path (the parent directory of this script)
INSTALL_DIRECTORY = os.path.abspath(os.path.dirname(os.path.realpath(__file__)) + '/..')

# Database
DATABASE_NAME = "farm.db"
DATABASE_PATH = os.path.join(INSTALL_DIRECTORY, 'databases')
ALEMBIC_UPGRADE_POST = os.path.join(DATABASE_PATH, 'alembic_post_upgrade_versions')
SQL_DATABASE_FARM = os.path.join(DATABASE_PATH, DATABASE_NAME)
FARM_DB_PATH = 'sqlite:///' + SQL_DATABASE_FARM

# Misc paths
PATH_1WIRE = '/sys/bus/w1/devices/'
PATH_CONTROLLERS = os.path.join(INSTALL_DIRECTORY, 'farm/controllers')
PATH_FUNCTIONS = os.path.join(INSTALL_DIRECTORY, 'farm/functions')
PATH_INPUTS = os.path.join(INSTALL_DIRECTORY, 'farm/inputs')
PATH_OUTPUTS = os.path.join(INSTALL_DIRECTORY, 'farm/outputs')
PATH_WIDGETS = os.path.join(INSTALL_DIRECTORY, 'farm/widgets')
PATH_FUNCTIONS_CUSTOM = os.path.join(PATH_FUNCTIONS, 'custom_functions')
PATH_INPUTS_CUSTOM = os.path.join(PATH_INPUTS, 'custom_inputs')
PATH_OUTPUTS_CUSTOM = os.path.join(PATH_OUTPUTS, 'custom_outputs')
PATH_WIDGETS_CUSTOM = os.path.join(PATH_WIDGETS, 'custom_widgets')
PATH_USER_SCRIPTS = os.path.join(INSTALL_DIRECTORY, 'farm/user_scripts')
PATH_HTML_USER = os.path.join(INSTALL_DIRECTORY, 'farm/farm_flask/templates/user_templates')
PATH_PYTHON_CODE_USER = os.path.join(INSTALL_DIRECTORY, 'farm/user_python_code')
PATH_MEASUREMENTS_BACKUP = os.path.join(INSTALL_DIRECTORY, 'farm/backup_measurements')
PATH_SETTINGS_BACKUP = os.path.join(INSTALL_DIRECTORY, 'farm/backup_settings')
USAGE_REPORTS_PATH = os.path.join(INSTALL_DIRECTORY, 'output_usage_reports')
DEPENDENCY_INIT_FILE = os.path.join(INSTALL_DIRECTORY, '.dependency')
UPGRADE_INIT_FILE = os.path.join(INSTALL_DIRECTORY, '.upgrade')
BACKUP_PATH = '/var/Farm-backups'  # Where Farm backups are stored

# Log files
LOG_PATH = '/var/log/farm'  # Where generated logs are stored
LOGIN_LOG_FILE = os.path.join(LOG_PATH, 'login.log')
DAEMON_LOG_FILE = os.path.join(LOG_PATH, 'farm.log')
KEEPUP_LOG_FILE = os.path.join(LOG_PATH, 'farmkeepup.log')
BACKUP_LOG_FILE = os.path.join(LOG_PATH, 'farmbackup.log')
DEPENDENCY_LOG_FILE = os.path.join(LOG_PATH, 'farmdependency.log')
UPGRADE_LOG_FILE = os.path.join(LOG_PATH, 'farmupgrade.log')
UPGRADE_TMP_LOG_FILE = '/tmp/farmupgrade.log'
RESTORE_LOG_FILE = os.path.join(LOG_PATH, 'farmrestore.log')
HTTP_ACCESS_LOG_FILE = '/var/log/nginx/access.log'
HTTP_ERROR_LOG_FILE = '/var/log/nginx/error.log'

# Lock files
LOCK_PATH = '/var/lock'
LOCK_FILE_STREAM = os.path.join(LOCK_PATH, 'farm-camera-stream.pid')

# Run files
RUN_PATH = '/var/run'
FRONTEND_PID_FILE = os.path.join(RUN_PATH, 'farmflask.pid')
DAEMON_PID_FILE = os.path.join(RUN_PATH, 'farm.pid')

# Remote admin
STORED_SSL_CERTIFICATE_PATH = os.path.join(
    INSTALL_DIRECTORY, 'farm/farm_flask/ssl_certs/remote_admin')

# Cameras
PATH_CAMERAS = os.path.join(INSTALL_DIRECTORY, 'cameras')

# Notes
PATH_NOTE_ATTACHMENTS = os.path.join(INSTALL_DIRECTORY, 'note_attachments')

# Determine if running in a Docker container
DOCKER_CONTAINER = os.environ.get('DOCKER_CONTAINER', False) == 'TRUE'

# Pyro5 URI/host, used by farm_client.py
if DOCKER_CONTAINER:
    PYRO_URI = 'PYRO:farm.pyro_server@farm_daemon:9090'
else:
    PYRO_URI = 'PYRO:farm.pyro_server@127.0.0.1:9090'

# Influx sensor/device measurement database
INFLUXDB_HOST = 'localhost' if not DOCKER_CONTAINER else 'influxdb'
INFLUXDB_PORT = 8086
INFLUXDB_USER = 'farm'
INFLUXDB_PASSWORD = 'mmdu77sj3nIoiajjs'
INFLUXDB_DATABASE = 'farm_db'

# Anonymous statistics
STATS_INTERVAL = 86400
STATS_HOST = 'fungi.mir.one'
STATS_PORT = 8086
STATS_USER = 'farm_stats'
STATS_PASSWORD = 'Io8Nasr5JJDdhPOj32222'
STATS_DATABASE = 'farm_stats'
STATS_CSV = os.path.join(DATABASE_PATH, 'statistics.csv')
ID_FILE = os.path.join(DATABASE_PATH, 'statistics.id')

# Login restrictions
LOGIN_ATTEMPTS = 5
LOGIN_BAN_SECONDS = 600  # 10 minutes

# Check for upgrade every 2 days (if enabled)
UPGRADE_CHECK_INTERVAL = 172800

RELEASE_URL = 'https://api.github.com/repos/mir-one/Farm/tags'


class ProdConfig(object):
    """ Production Configuration """
    SQL_DATABASE_FARM = os.path.join(DATABASE_PATH, DATABASE_NAME)
    FARM_DB_PATH = 'sqlite:///{}'.format(SQL_DATABASE_FARM)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///{}'.format(SQL_DATABASE_FARM)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    FLASK_PROFILER = {
        "enabled": True,
        "storage": {
            "engine": "sqlalchemy",
            "db_url": 'sqlite:///{}'.format(os.path.join(DATABASE_PATH, 'profile.db'))
        },
        "basicAuth": {
            "enabled": True,
            "username": "admin231",
            "password": "admin421378956"
        },
        "ignore": [
            "^/static/.*",
            "/login",
            "/settings/users"
        ],
        "endpointRoot": "farm-flask-profiler"
    }

    WTF_CSRF_TIME_LIMIT = 60 * 60 * 24 * 7  # 1 week expiration
    REMEMBER_COOKIE_DURATION = timedelta(days=90)
    SESSION_TYPE = "filesystem"

    # Ensure file containing the Flask secret_key exists
    FLASK_SECRET_KEY_PATH = os.path.join(DATABASE_PATH, 'flask_secret_key')
    if not os.path.isfile(FLASK_SECRET_KEY_PATH):
        secret_key = binascii.hexlify(os.urandom(32)).decode()
        with open(FLASK_SECRET_KEY_PATH, 'w') as file:
            file.write(secret_key)
    SECRET_KEY = open(FLASK_SECRET_KEY_PATH, 'rb').read()


class TestConfig(object):
    """ Testing Configuration """
    SQLALCHEMY_DATABASE_URI = 'sqlite://'  # in-memory db only. tests drop the tables after they run
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    RATELIMIT_ENABLED = False
    SECRET_KEY = '1234'
    SESSION_TYPE = "filesystem"
    TESTING = True
    DEBUG = True
