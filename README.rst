Farm
======

Система автоматизации и мониторинга экологических проектов

Актуальная версия: 1.0.0

Farm - это автоматизированная система с открытым кодом ждя мониторинга и регулирования, созданная для работы на Raspberry Pi (версии Zero, 1, 2, 3 и 4).

Farm презназначен для автоматизации сиситем, включая выращивание растений, выращивание микроорганизмов, поддержание гомеостаза пасеки медоносных пчел, инкубацию животных или яиц, поддержание водных систем, выдержка сыров, ферментацию продуктов, приготовление пищи методом (sous-vide) и многое другое.

Система включает в себя бэкэнд (демон) и интерфейс (пользовательский интерфейс). Бэкэнд проводит измерения от датчиков и устройств, затем координирует разнообразный набор ответов на эти измерения, включая возможность модулировать выходы (реле, ШИМ, беспроводные выходы), регулировать условия окружающей среды с помощью электрических устройств под управлением ПИД (постоянное регулирование или переключение). время), планировать таймеры, захватывать фотографии и потоковое видео, запускать действия, когда измерения соответствуют определенным условиям (модулировать реле, выполнять команды, отправлять уведомления по электронной почте и т. д.) и многое другое. Интерфейс представляет собой веб-интерфейс, который обеспечивает простую навигацию и настройку с любого устройства с поддержкой браузера.

Поддержка
-------

Документация
~~~~~~~~~~~~~

`Farm API <https://mir-one.github.io/Farm/farm-api.html>`__ (Version: v1)

`Репозиторий Farm Custom Module <https://github.com/mir-one/Farm-custom>`__

Discussion
~~~~~~~~~~

`Farm Issues (Bug Reports/Feature Requests) <https://github.com/mir-one/Farm/issues>`__

Bug in the Farm Software
~~~~~~~~~~~~~~~~~~~~~~~~~~

If you believe there is a bug in the Farm software, first search through the guthub `Issues <https://github.com/mir-one/Farm/issues>`__ and see if your issue has already recently been discussed or resolved. If your issue is novel or significantly mre recent than a similar one, you should create a `New Issue <https://github.com/mir-one/Farm/issues/new>`__. When creating a new issue, make sure to read all information in the issue template and follow the instructions. Replace the template text with the information being requested (e.g. "step 1" under "Steps to Reproduce the issue" should be replaced with the actual steps to reproduce the issue). The more information you provide, the easier it is to reproduce and diagnose the issue. If the issue is not able to reproduced because not enough information is provided, it may delay or prevent solving the issue.

--------------

.. contents:: Table of Contents
   :depth: 1

Features
--------

-  `Inputs <https://mir-one.github.io/Farm/Inputs/>`__ that record measurements from sensors, GPIO pin states, analog-to-digital converters, and more (or create your own `Custom Inputs <#custom-inputs>`__). See all `Supported Inputs <https://mir-one.github.io/Farm/Supported-Inputs-By-Measurement/>`__.
-  `Outputs <https://mir-one.github.io/Farm/Outputs/>`__ that perform actions such as switching GPIO pins high/low, generating PWM signals, executing shell scripts and Python code, and more (or create your own `Custom Outputs <#custom-outputs>`__). See all `Supported Outputs <https://mir-one.github.io/Farm/Supported-Outputs/>`__.
-  `Functions <https://mir-one.github.io/Farm/Functions/>`__ that perform tasks, such as coupling Inputs and Outputs in interesting ways, such as `PID controllers <https://mir-one.github.io/Farm/Functions/#pid-controller>`__, `Conditional Controllers <https://mir-one.github.io/Farm/Functions/#conditional>`__, `Trigger Controllers <https://mir-one.github.io/Farm/Functions/#trigger>`__, to name a few (or create your own `Custom Functions <https://mir-one.github.io/Farm/Functions/#custom-functions>`__). See all `Supported Functions <https://mir-one.github.io/Farm/Supported-Functions/>`__.
-  `Web Interface <https://mir-one.github.io/Farm/About/#web-interface>`__ for securely accessing Farm using a web browser on your local network or anywhere in the world with an internet connection, to view and configure the system, which includes several light and dark themes.
-  `Dashboards <https://mir-one.github.io/Farm/Data-Viewing/#dashboard>`__ that display configurable widgets, including interactive live and historical graphs, gauges, output state indicators, measurements, and more (or create your own `Custom Widgets <https://mir-one.github.io/Farm/Widgets/#custom-widgets>`__). See all `Supported Widgets <https://mir-one.github.io/Farm/Supported-Widgets/>`__.
-  `Alert Notifications <https://mir-one.github.io/Farm/Alerts/>`__ to send emails when measurements reach or exceed user-specified thresholds, important for knowing immediately when issues arise.
-  `Setpoint Tracking <https://mir-one.github.io/Farm/Methods/>`__ for changing a PID controller setpoint over time, for use with things like terrariums, reflow ovens, thermal cyclers, sous-vide cooking, and more.
-  `Notes <https://mir-one.github.io/Farm/Notes/>`__ to record events, alerts, and other important points in time, which can be overlaid on graphs to visualize events with your measurement data.
-  `Cameras <https://mir-one.github.io/Farm/Camera/>`__ for remote live streaming, image capture, and time-lapse photography.
-  `Energy Usage Measurement <https://mir-one.github.io/Farm/Energy-Usage/>`__ for calculating and tracking power consumption and cost over time.
-  `Upgrade System <https://mir-one.github.io/Farm/Upgrade-Backup-Restore/>`__ to easily upgrade the Farm system to the latest release to get the newest features or restore to a previously-backed up version.
-  `Translations <https://mir-one.github.io/Farm/Translations/>`__ that enable the web interface to be presented in different `Languages <https://github.com/mir-one/Farm#features>`__.

.. image:: https://mir.one/projects/wp-content/uploads/sites/3/2020/06/Screenshot_2020-04-25-hydra-Default-Dashboard-Farm-8-4-0-dashboard_2.png
   :target: https://mir.one/projects/wp-content/uploads/sites/3/2020/06/Screenshot_2020-04-25-hydra-Default-Dashboard-Farm-8-4-0-dashboard_2.png

Uses
----

Originally developed to cultivate edible mushrooms, Farm has evolved to do much more. Here are a few things that have been done with Farm:


Screenshots
-----------

Visit the `Screenshots <https://github.com/mir-one/Farm/wiki/Screenshots>`__ page of the Wiki.

Install Farm
--------------

Prerequisites
~~~~~~~~~~~~~

-  `Raspberry Pi <https://www.raspberrypi.org>`__ single-board computer (any version: Zero, 1, 2, 3, or 4)
-  `Raspberry Pi Operating System <https://www.raspberrypi.org/downloads/raspberry-pi-os/>`__ flashed to a micro SD card
-  An active internet connection

Farm has been tested to work with Raspberry Pi OS Lite (2020-05-27), and also the Desktop version if using Farm version => 8.6.0.

Install
~~~~~~~

Once you have the Raspberry Pi booted into the Raspberry Pi OS with an internet connection, run the following command in a terminal to initiate the Farm install:

.. code:: bash

    curl -L https://mir-one.github.io/Farm/install | bash


Install Notes
~~~~~~~~~~~~~

Make sure the install script finishes without errors. A log of the output will be created at ``~/Farm/install/setup.log``.

If the install is successful, the web user interface should be accessible by navigating a web browser to ``https://127.0.0.1/``, replacing ``127.0.0.1`` with your Raspberry Pi's IP address. Upon your first visit, you will be prompted to create an admin user before being redirected to the login page. Once logged in, check that the time is correct at the top left of the page. Incorrect time can cause a number of issues with measurement storage and retrieval, among others. Also ensure the host name and version number at the top left of the page is green, indicating the daemon is running. Red indicates the daemon is inactive or unresponsive. Last, ensure any java-blocking plugins of your browser are disabled for all parts of the web interface to function properly.

If you receive an error during the install that you believe is preventing your system from operating, please `create an issue <https://github.com/mir-one/Farm/issues>`__ with the install log attached. If you would first like to attempt to diagnose the issue yourself, see `Diagnosing Issues <#diagnosing-issues>`__.

A minimal set of anonymous usage statistics are collected to help improve development. No identifying information is saved from the information that is collected and it is only used to improve Farm. No other sources will have access to this information. The data collected is mainly what and how many features are used, and other similar information. The data that's collected can be viewed from the 'View collected statistics' link in the ``Settings -> General`` page. There is an opt out option on the General Settings page.

REST API
--------

The latest API documentation can be found here: `API Information <https://mir-one.github.io/Farm/API/>`__ and `API Endpoint Documentation <https://mir-one.github.io/Farm/farm-api.html>`__.

About PID Control
-----------------

A `proportional–integral–derivative (PID) controller <https://en.wikipedia.org/wiki/PID_controller>`__ is a control loop feedback mechanism used throughout industry for controlling systems. It efficiently brings a measurable condition, such as temperature, to a desired state (setpoint). A well-tuned PID controller can raise to a setpoint quickly, have minimal overshoot, and maintain the setpoint with little oscillation.

.. figure:: docs/images/PID-Animation.gif
   :alt: PID Animation


|Farm|

The top graph visualizes the regulation of temperature. The red line is the desired temperature (setpoint) that has been configured to change over the course of each day. The blue line is the actual recorded temperature. The green vertical bars represent how long a heater has been activated for every 20-second period. This regulation was achieved with minimal tuning, and already displays a very minimal deviation from the setpoint (±0.5° Celsius). Further tuning would reduce this variability further.

See the `PID Controller <https://mir-one.github.io/Farm/Functions/#pid-controller>`__ and `PID Tuning <https://mir-one.github.io/Farm/Functions/#pid-tuning>`__ sections of the manual for more information.

Supported Inputs and Outputs
----------------------------

All supported Inputs, Outputs, and other devices can be found under the `Supported Devices <https://mir-one.github.io/Farm/Input-Devices/>`__ section of the manual.

Custom Inputs, Outputs, and Controllers
---------------------------------------

Farm supports importing custom Input, Output, and Controller modules. you can find more information about each in the manual under `Custom Inputs <https://mir-one.github.io/Farm/Inputs/#custom-inputs>`__, `Custom Outputs <https://mir-one.github.io/Farm/Outputs/#custom-outputs>`__, and `Custom Functions <https://mir-one.github.io/Farm/Functions/#custom-functions>`__.

If you would like to add to the list of supported Inputs, Outputs, and Controllers, submit a pull request with the module you created or start a `New Issue <https://github.com/mir-one/Farm/issues/new?assignees=&labels=&template=feature-request.md&title=>`__.

Additionally, I have another github repository devoted to custom Inputs, Outputs, and Controllers that do not necessarily fit with the built-in set and are not included by default with Farm, but can be imported. These can be found at `mir-one/Farm-custom <https://github.com/mir-one/Farm-custom>`__.

Links
-----

Thanks for using and supporting Farm, however depending where you found this documentation, you may not have the latest version or it may have been altered, if not obtained through an official distribution site. You should be able to find the latest version on github or my web site at the following links.

https://github.com/mir-one/Farm

https://mir.one

License
-------

See `License.txt <https://github.com/mir-one/Farm/blob/master/LICENSE.txt>`__

Farm is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

Farm is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the `GNU General Public License <http://www.gnu.org/licenses/gpl-3.0.en.html>`__ for more details.

A full copy of the GNU General Public License can be found at http://www.gnu.org/licenses/gpl-3.0.en.html

This software includes third party open source software components. Please see individual files for license information, if applicable.

Languages
---------

|Translation Table|

-  Native: English
-  `Dutch <#dutch>`__,
   `German <#german>`__,
   `French <#french>`__,
   `Italian <#italian>`__,
   `Norwegian <#norwegian>`__,
   `Polish <#polish>`__,
   `Portuguese <#portuguese>`__,
   `Russian <#russian>`__,
   `Serbian <#serbian>`__,
   `Spanish <#spanish>`__,
   `Swedish <#swedish>`__,
   `Chinese <#chinese>`__.

By default, farm will display the default language set by your browser. You may also force a language in the settings at ``[Gear Icon] -> Configure -> General -> Language``

------

-  `Alembic <https://alembic.sqlalchemy.org>`__
-  `Argparse <https://pypi.org/project/argparse>`__
-  `Bcrypt <https://pypi.org/project/bcrypt>`__
-  `Bootstrap <https://getbootstrap.com>`__
-  `Daemonize <https://pypi.org/project/daemonize>`__
-  `Date Range Picker <https://github.com/dangrossman/daterangepicker>`__
-  `Distro <https://pypi.org/project/distro>`__
-  `Email_Validator <https://pypi.org/project/email_validator>`__
-  `Filelock <https://pypi.org/project/filelock>`__
-  `Flask <https://pypi.org/project/flask>`__
-  `Flask_Accept <https://pypi.org/project/flask_accept>`__
-  `Flask_Babel <https://pypi.org/project/flask_babel>`__
-  `Flask_Compress <https://pypi.org/project/flask_compress>`__
-  `Flask_Limiter <https://pypi.org/project/flask_limiter>`__
-  `Flask_Login <https://pypi.org/project/flask_login>`__
-  `Flask_Marshmallow <https://pypi.org/project/flask_marshmallow>`__
-  `Flask_RESTX <https://pypi.org/project/flask_restx>`__
-  `Flask_Session <https://pypi.org/project/flask_session>`__
-  `Flask_SQLAlchemy <https://pypi.org/project/flask_sqlalchemy>`__
-  `Flask_Talisman <https://pypi.org/project/flask_talisman>`__
-  `Flask_WTF <https://pypi.org/project/flask_wtf>`__
-  `FontAwesome <https://fontawesome.com>`__
-  `Geocoder <https://pypi.org/project/geocoder>`__
-  `gridstack.js <https://github.com/gridstack/gridstack.js>`__
-  `Gunicorn <https://gunicorn.org>`__
-  `Highcharts <https://www.highcharts.com>`__
-  `InfluxDB <https://github.com/influxdata/influxdb>`__
-  `jQuery <https://jquery.com>`__
-  `Marshmallow_SQLAlchemy <https://pypi.org/project/marshmallow_sqlalchemy>`__
-  `Pyro5 <https://github.com/irmen/Pyro5>`__
-  `SQLAlchemy <https://www.sqlalchemy.org>`__
-  `SQLite <https://www.sqlite.org>`__
-  `toastr <https://github.com/CodeSeven/toastr>`__
-  `WTForms <https://pypi.org/project/wtforms>`__
