#!/bin/bash
#
#  upgrade_commands.sh - Farm commands
#

exec 2>&1

if [[ "$EUID" -ne 0 ]]; then
    printf "Must be run as root.\n"
    exit 1
fi

# Current Farm major version number
FARM_MAJOR_VERSION="8"

# Dependency versions/URLs
PIGPIO_URL="https://github.com/joan2937/pigpio/archive/v79.tar.gz"
MCB2835_URL="http://www.airspayce.com/mikem/bcm2835/bcm2835-1.50.tar.gz"
WIRINGPI_URL="https://project-downloads.drogon.net/wiringpi-latest.deb"
INFLUXDB_VERSION="1.8.0"
VIRTUALENV_VERSION="20.7.0"

# Required apt packages. This has been tested with Raspbian for the
# Raspberry Pi and Ubuntu, it should work with most Debian-based systems.
APT_PKGS="gawk gcc g++ git libffi-dev libi2c-dev logrotate moreutils nginx sqlite3 wget python3 python3-dev python3-setuptools python3-smbus python3-pylint-common rng-tools"

PYTHON_BINARY_SYS_LOC="$(python3 -c "import os; print(os.environ['_'])")"

UNAME_TYPE=$(uname -m)
MACHINE_TYPE=$(dpkg --print-architecture)

# Get the Farm root directory
SOURCE="${BASH_SOURCE[0]}"

while [[ -h "$SOURCE" ]]; do # resolve $SOURCE until the file is no longer a symlink
    DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done

FARM_PATH="$( cd -P "$( dirname "${SOURCE}" )/../.." && pwd )"

cd "${FARM_PATH}" || return

HELP_OPTIONS="upgrade_commands.sh [option] - Program to execute various farm commands

Options:
  backup-create                 Create a backup of the ~/Farm directory
  backup-restore [backup]       Restore [backup] location, which must be the full path to the backup.
                                Ex.: '/var/Farm-backups/Farm-backup-2018-03-11_21-19-15-5.6.4/'
  compile-farm-wrapper        Compile farm_wrapper.c
  compile-translations          Compile language translations for web interface
  create-files-directories      Create required directories
  create-symlinks               Create required symlinks
  create-user                   Create 'farm' user and add to appropriate groups
  initialize                    Issues several commands to set up directories/files/permissions
  generate-widget-html          Generate HTML templates for all widgets
  restart-daemon                Restart the Farm daemon
  setup-virtualenv              Create a Python virtual environment
  setup-virtualenv-full         Create a Python virtual environment and install dependencies
  ssl-certs-generate            Generate SSL certificates for the web user interface
  ssl-certs-regenerate          Regenerate SSL certificates
  uninstall-apt-pip             Uninstall the apt version of pip
  update-alembic                Use alembic to upgrade the farm.db settings database
  update-alembic-post           Execute script following all alembic upgrades
  update-apt                    Update apt sources
  update-cron                   Update cron entries
  update-dependencies           Check for updates to dependencies and update
  install-bcm2835               Install bcm2835
  install-wiringpi              Install wiringpi
  install-pigpiod               Install pigpiod
  uninstall-pigpiod             Uninstall pigpiod
  disable-pigpiod               Disable pigpiod
  enable-pigpiod-low            Enable pigpiod with 1 ms sample rate
  enable-pigpiod-high           Enable pigpiod with 5 ms sample rate
  enable-pigpiod-disabled       Create empty service to indicate pigpiod is disabled
  update-pigpiod                Update to latest version of pigpiod service file
  update-influxdb               Update influxdb to the latest version
  update-influxdb-db-user       Create the influxdb database and user
  update-logrotate              Install logrotate script
  update-farm-startup-script  Install the Farm daemon startup script
  update-packages               Ensure required apt packages are installed/up-to-date
  update-permissions            Set permissions for Farm directories/files
  update-pip3                   Update pip
  update-pip3-packages          Update required pip packages
  update-swap-size              Ensure swap size is sufficiently large (512 MB)
  upgrade-farm                Upgrade Farm to latest compatible release and preserve database and virtualenv
  upgrade-release-major {ver}   Upgrade Farm to a major version release {ver} and preserve database and virtualenv
  upgrade-release-wipe {ver}    Upgrade Farm to a major version release {ver} and wipe database and virtualenv
  upgrade-master                Upgrade Farm to the master branch at https://github.com/mir-one/Farm
  upgrade-post                  Execute post-upgrade script
  web-server-connect            Attempt to connect to the web server
  web-server-reload             Reload the web server
  web-server-restart            Restart the web server
  web-server-update             Update the web server configuration files

Docker-specific Commands:
  docker-update-pip             Update pip
  docker-update-pip-packages    Update required pip packages
  install-docker-ce-cli         Install Docker Client
"

case "${1:-''}" in
    'backup-create')
        /bin/bash "${FARM_PATH}"/farm/scripts/farm_backup_create.sh
    ;;
    'backup-restore')
        /bin/bash "${FARM_PATH}"/farm/scripts/farm_backup_restore.sh "${2}"
    ;;
    'compile-farm-wrapper')
        printf "\n#### Compiling farm_wrapper\n"
        gcc "${FARM_PATH}"/farm/scripts/farm_wrapper.c -o "${FARM_PATH}"/farm/scripts/farm_wrapper
        chown root:farm "${FARM_PATH}"/farm/scripts/farm_wrapper
        chmod 4770 "${FARM_PATH}"/farm/scripts/farm_wrapper
    ;;
    'compile-translations')
        printf "\n#### Compiling Translations\n"
        cd "${FARM_PATH}"/farm || return
        "${FARM_PATH}"/env/bin/pybabel compile -d farm_flask/translations
    ;;
    'create-files-directories')
        printf "\n#### Creating files and directories\n"
        mkdir -p /var/log/farm
        mkdir -p /var/Farm-backups
        mkdir -p "${FARM_PATH}"/note_attachments
        mkdir -p "${FARM_PATH}"/farm/farm_flask/static/js/user_js
        mkdir -p "${FARM_PATH}"/farm/farm_flask/static/css/user_css

        if [[ ! -e /var/log/farm/farm.log ]]; then
            touch /var/log/farm/farm.log
        fi
        if [[ ! -e /var/log/farm/farmbackup.log ]]; then
            touch /var/log/farm/farmbackup.log
        fi
        if [[ ! -e /var/log/farm/farmkeepup.log ]]; then
            touch /var/log/farm/farmkeepup.log
        fi
        if [[ ! -e /var/log/farm/farmdependency.log ]]; then
            touch /var/log/farm/farmdependency.log
        fi
        if [[ ! -e /var/log/farm/farmupgrade.log ]]; then
            touch /var/log/farm/farmupgrade.log
        fi
        if [[ ! -e /var/log/farm/farmrestore.log ]]; then
            touch /var/log/farm/farmrestore.log
        fi
        if [[ ! -e /var/log/farm/login.log ]]; then
            touch /var/log/farm/login.log
        fi

        # Create empty farm database file if it doesn't exist
        if [[ ! -e ${FARM_PATH}/databases/farm.db ]]; then
            touch "${FARM_PATH}"/databases/farm.db
        fi
    ;;
    'create-symlinks')
        printf "\n#### Creating symlinks to Farm executables\n"
        ln -sfn "${FARM_PATH}" /var/farm-root
        ln -sfn "${FARM_PATH}"/farm/farm_daemon.py /usr/bin/farm-daemon
        ln -sfn "${FARM_PATH}"/farm/farm_client.py /usr/bin/farm-client
        ln -sfn "${FARM_PATH}"/farm/scripts/upgrade_commands.sh /usr/bin/farm-commands
        ln -sfn "${FARM_PATH}"/farm/scripts/farm_backup_create.sh /usr/bin/farm-backup
        ln -sfn "${FARM_PATH}"/farm/scripts/farm_backup_restore.sh /usr/bin/farm-restore
        ln -sfn "${FARM_PATH}"/farm/scripts/farm_wrapper /usr/bin/farm-wrapper
        ln -sfn "${FARM_PATH}"/env/bin/pip3 /usr/bin/farm-pip
        ln -sfn "${FARM_PATH}"/env/bin/python3 /usr/bin/farm-python
    ;;
    'create-user')
        printf "\n#### Creating farm user\n"
        useradd -M farm
        adduser farm adm
        adduser farm dialout
        adduser farm i2c
        adduser farm kmem
        adduser farm video
        if getent group gpio; then
            adduser farm gpio
        fi
        if id pi &>/dev/null; then
            adduser pi farm
            adduser farm pi
        fi
    ;;
    'generate-widget-html')
        printf "\n#### Generating widget HTML files\n"
        "${FARM_PATH}"/env/bin/python "${FARM_PATH}"/farm/utils/widget_generate_html.py
    ;;
    'initialize')
        printf "\n#### Running initialization\n"
        /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_commands.sh create-user
        /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_commands.sh compile-farm-wrapper
        /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_commands.sh create-symlinks
        /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_commands.sh create-files-directories
        /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_commands.sh update-permissions
        systemctl daemon-reload
    ;;
    'restart-daemon')
        printf "\n#### Restarting the Farm daemon\n"
        service farm restart
    ;;
    'setup-virtualenv')
        printf "\n#### Checking python 3 virtualenv\n"
        if [[ ! -e ${FARM_PATH}/env/bin/python3 ]]; then
            printf "#### Virtualenv doesn't exist. Creating...\n"
            python3 -m pip install virtualenv==${VIRTUALENV_VERSION}
            rm -rf "${FARM_PATH}"/env
            python3 -m virtualenv --system-site-packages -p "${PYTHON_BINARY_SYS_LOC}" "${FARM_PATH}"/env
        else
            printf "#### Virtualenv already exists, skipping creation\n"
        fi
    ;;
    'setup-virtualenv-full')
        /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_commands.sh setup-virtualenv
        /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_commands.sh update-pip3-packages
        /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_commands.sh update-dependencies
        /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_commands.sh update-permissions
    ;;
    'ssl-certs-generate')
        printf "\n#### Generating SSL certificates at %s/farm/farm_flask/ssl_certs (replace with your own if desired)\n" "${FARM_PATH}"
        mkdir -p "${FARM_PATH}"/farm/farm_flask/ssl_certs
        cd "${FARM_PATH}"/farm/farm_flask/ssl_certs/ || return
        rm -f ./*.pem ./*.csr ./*.crt ./*.key

        openssl genrsa -out server.pass.key 4096
        openssl rsa -in server.pass.key -out server.key
        rm -f server.pass.key
        openssl req -new -key server.key -out server.csr \
            -subj "/O=farm/OU=farm/CN=farm"
        openssl x509 -req \
            -days 3653 \
            -in server.csr \
            -signkey server.key \
            -out server.crt
    ;;
    'ssl-certs-regenerate')
        printf "\n#### Regenerating SSL certificates at %s/farm/farm_flask/ssl_certs\n" "${FARM_PATH}"
        rm -rf "${FARM_PATH}"/farm/farm_flask/ssl_certs/*.pem
        /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_commands.sh ssl-certs-generate
        /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_commands.sh initialize
        sudo service nginx restart
        sudo service farmflask restart
    ;;
    'uninstall-apt-pip')
        printf "\n#### Uninstalling apt version of pip (if installed)\n"
        apt-get purge -y python-pip
    ;;
    'update-alembic')
        printf "\n#### Upgrading Farm database with alembic (if needed)\n"
        cd "${FARM_PATH}"/databases || return
        "${FARM_PATH}"/env/bin/alembic upgrade head
    ;;
    'update-alembic-post')
        printf "\n#### Executing post-alembic script\n"
        "${FARM_PATH}"/env/bin/python "${FARM_PATH}"/databases/alembic_post.py
    ;;
    'update-apt')
        printf "\n#### Updating apt repositories\n"
        apt-get update -y
    ;;
    'update-cron')  # TODO: Remove at next major revision
        printf "\n#### Remove Farm restart monitor crontab entry (if it exists)\n"
        /bin/bash "${FARM_PATH}"/install/crontab.sh restart_daemon --remove
    ;;
    'update-dependencies')
        printf "\n#### Checking for updates to dependencies\n"
        "${FARM_PATH}"/env/bin/python "${FARM_PATH}"/farm/utils/update_dependencies.py
    ;;
    'install-bcm2835')
        printf "\n#### Installing bcm2835\n"
        cd "${FARM_PATH}"/install || return
        apt-get install -y automake libtool
        wget ${MCB2835_URL} -O bcm2835.tar.gz
        mkdir bcm2835
        tar xzf bcm2835.tar.gz -C bcm2835 --strip-components=1
        cd bcm2835 || return
        autoreconf -vfi
        ./configure
        make
        sudo make check
        sudo make install
        cd "${FARM_PATH}"/install || return
        rm -rf ./bcm2835
    ;;
    'install-wiringpi')
        if [[ ${MACHINE_TYPE} == 'armhf' ]]; then
            cd "${FARM_PATH}"/install || return
            wget ${WIRINGPI_URL} -O wiringpi-latest.deb
            dpkg -i wiringpi-latest.deb
        else
            printf "\n#### WiringPi not supported on this architecture, skipping.\n"
        fi
    ;;
    'build-pigpiod')
        apt-get install -y python3-pigpio
        cd "${FARM_PATH}"/install || return
        # wget --quiet -P "${FARM_PATH}"/install abyz.co.uk/rpi/pigpio/pigpio.zip
        wget ${PIGPIO_URL} -O pigpio.tar.gz
        mkdir PIGPIO
        tar xzf pigpio.tar.gz -C PIGPIO --strip-components=1
        cd "${FARM_PATH}"/install/PIGPIO || return
        make -j4
        make install
        cd "${FARM_PATH}"/install || return
        rm -rf ./PIGPIO
        rm -rf pigpio.tar.gz
    ;;
    'install-pigpiod')
        printf "\n#### Installing pigpiod\n"
        /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_commands.sh build-pigpiod
        /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_commands.sh disable-pigpiod
        /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_commands.sh enable-pigpiod-high
        mkdir -p /opt/farm
        touch /opt/farm/pigpio_installed
    ;;
    'uninstall-pigpiod')
        printf "\n#### Uninstalling pigpiod\n"
        apt-get remove -y python3-pigpio
        apt-get install -y jq
        cd "${FARM_PATH}"/install || return
        # wget --quiet -P "${FARM_PATH}"/install abyz.co.uk/rpi/pigpio/pigpio.zip
        wget ${PIGPIO_URL} -O pigpio.tar.gz
        mkdir PIGPIO
        tar xzf pigpio.tar.gz -C PIGPIO --strip-components=1
        cd "${FARM_PATH}"/install/PIGPIO || return
        make uninstall
        cd "${FARM_PATH}"/install || return
        rm -rf ./PIGPIO
        rm -rf pigpio.tar.gz
        touch /etc/systemd/system/pigpiod_uninstalled.service
        rm -f /opt/farm/pigpio_installed
    ;;
    'disable-pigpiod')
        printf "\n#### Disabling installed pigpiod startup script\n"
        service pigpiod stop
        systemctl disable pigpiod.service
        rm -rf /etc/systemd/system/pigpiod.service
        systemctl disable pigpiod_low.service
        rm -rf /etc/systemd/system/pigpiod_low.service
        systemctl disable pigpiod_high.service
        rm -rf /etc/systemd/system/pigpiod_high.service
        rm -rf /etc/systemd/system/pigpiod_disabled.service
        rm -rf /etc/systemd/system/pigpiod_uninstalled.service
    ;;
    'enable-pigpiod-low')
        printf "\n#### Enabling pigpiod startup script (1 ms sample rate)\n"
        systemctl enable "${FARM_PATH}"/install/pigpiod_low.service
        service pigpiod restart
    ;;
    'enable-pigpiod-high')
        printf "\n#### Enabling pigpiod startup script (5 ms sample rate)\n"
        systemctl enable "${FARM_PATH}"/install/pigpiod_high.service
        service pigpiod restart
    ;;
    'enable-pigpiod-disabled')
        printf "\n#### pigpiod has been disabled. It can be enabled in the web UI configuration\n"
        touch /etc/systemd/system/pigpiod_disabled.service
    ;;
    'update-pigpiod')
        printf "\n#### Checking which pigpiod startup script is being used\n"
        GPIOD_SAMPLE_RATE=99
        if [[ -e /etc/systemd/system/pigpiod_low.service ]]; then
            GPIOD_SAMPLE_RATE=1
        elif [[ -e /etc/systemd/system/pigpiod_high.service ]]; then
            GPIOD_SAMPLE_RATE=5
        elif [[ -e /etc/systemd/system/pigpiod_disabled.service ]]; then
            GPIOD_SAMPLE_RATE=100
        fi

        /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_commands.sh disable-pigpiod

        if [[ "$GPIOD_SAMPLE_RATE" -eq "1" ]]; then
            /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_commands.sh enable-pigpiod-low
        elif [[ "$GPIOD_SAMPLE_RATE" -eq "5" ]]; then
            /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_commands.sh enable-pigpiod-high
        elif [[ "$GPIOD_SAMPLE_RATE" -eq "100" ]]; then
            /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_commands.sh enable-pigpiod-disabled
        else
            printf "#### Could not determine pgiod sample rate. Setting up pigpiod with 1 ms sample rate\n"
            /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_commands.sh enable-pigpiod-low
        fi
    ;;
    'update-influxdb')
        printf "\n#### Ensuring compatible version of influxdb is installed ####\n"
        INSTALL_ADDRESS="https://dl.influxdata.com/influxdb/releases/"
        INSTALL_FILE="influxdb_${INFLUXDB_VERSION}_${MACHINE_TYPE}.deb"
        CORRECT_VERSION="${INFLUXDB_VERSION}-1"
        CURRENT_VERSION=$(apt-cache policy influxdb | grep 'Installed' | gawk '{print $2}')
        if [[ "${CURRENT_VERSION}" != "${CORRECT_VERSION}" ]]; then
            echo "#### Incorrect InfluxDB version (v${CURRENT_VERSION}) installed. Installing v${CORRECT_VERSION}..."
            wget --quiet ${INSTALL_ADDRESS}${INSTALL_FILE}
            dpkg -i ${INSTALL_FILE}
            rm -rf ${INSTALL_FILE}
            service influxdb restart
        else
            printf "Correct version of InfluxDB currently installed\n"
        fi
    ;;
    'update-influxdb-db-user')
        printf "\n#### Creating InfluxDB database and user\n"
        # Attempt to connect to influxdb 10 times, sleeping 60 seconds every fail
        for _ in {1..10}; do
            # Check if influxdb has successfully started and be connected to
            printf "#### Attempting to connect...\n" &&
            curl -sL -I localhost:8086/ping > /dev/null &&
            influx -execute "CREATE DATABASE farm_db" &&
            influx -database farm_db -execute "CREATE USER farm WITH PASSWORD 'mmdu77sj3nIoiajjs'" &&
            printf "#### Influxdb database and user successfully created\n" &&
            break ||
            # Else wait 60 seconds if the influxd port is not accepting connections
            # Everything below will begin executing if an error occurs before the break
            printf "#### Could not connect to Influxdb. Waiting 60 seconds then trying again...\n" &&
            sleep 60
        done
    ;;
    'update-logrotate')
        printf "\n#### Installing logrotate scripts\n"
        if [[ -e /etc/cron.daily/logrotate ]]; then
            printf "logrotate execution moved from cron.daily to cron.hourly\n"
            mv -f /etc/cron.daily/logrotate /etc/cron.hourly/
        fi
        cp -f "${FARM_PATH}"/install/logrotate_farm /etc/logrotate.d/farm
        printf "Farm logrotate script installed\n"
    ;;
    'update-farm-startup-script')
        printf "\n#### Disabling installed farm startup script\n"
        systemctl disable farm.service
        rm -rf /etc/systemd/system/farm.service
        printf "#### Enabling current farm startup script\n"
        systemctl enable "${FARM_PATH}"/install/farm.service
    ;;
    'update-packages')
        printf "\n#### Installing prerequisite apt packages and update pip\n"
        apt-get remove -y apache2 python-cffi-backend python3-cffi-backend
        apt-get install -y ${APT_PKGS}
        python3 /usr/lib/python3/dist-packages/easy_install.py pip
        python3 -m pip install --upgrade pip
    ;;
    'update-permissions')
        printf "\n#### Setting permissions\n"
        chown -LR farm.farm "${FARM_PATH}"
        chown -R farm.farm /var/log/farm
        chown -R farm.farm /var/Farm-backups
        chown -R influxdb.influxdb /var/lib/influxdb/data/

        find "${FARM_PATH}" -type d -exec chmod u+wx,g+wx {} +
        find "${FARM_PATH}" -type f -exec chmod u+w,g+w,o+r {} +

        chown root:farm "${FARM_PATH}"/farm/scripts/farm_wrapper
        chmod 4770 "${FARM_PATH}"/farm/scripts/farm_wrapper
    ;;
    'update-pip3')
        printf "\n#### Updating pip\n"
        "${FARM_PATH}"/env/bin/python -m pip install --upgrade pip
    ;;
    'update-pip3-packages')
        printf "\n#### Installing pip requirements\n"
        if [[ ! -d ${FARM_PATH}/env ]]; then
            printf "\n## Error: Virtualenv doesn't exist. Create with %s setup-virtualenv\n" "${0}"
        else
            "${FARM_PATH}"/env/bin/python -m pip install --upgrade pip setuptools
            "${FARM_PATH}"/env/bin/python -m pip install --upgrade -r "${FARM_PATH}"/install/requirements.txt
            "${FARM_PATH}"/env/bin/python -m pip install --upgrade -r "${FARM_PATH}"/install/requirements-rpi.txt
            "${FARM_PATH}"/env/bin/python -m pip install --upgrade -r "${FARM_PATH}"/install/requirements-testing.txt
        fi
    ;;
    'update-swap-size')
        printf "\n#### Checking if swap size is 100 MB and needs to be changed to 512 MB\n"
        if grep -q -s "CONF_SWAPSIZE=100" "/etc/dphys-swapfile"; then
            printf "#### Swap currently set to 100 MB. Changing to 512 MB and restarting\n"
            sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=512/g' /etc/dphys-swapfile
            /etc/init.d/dphys-swapfile stop
            /etc/init.d/dphys-swapfile start
        else
            printf "#### Swap not currently set to 100 MB. Not changing.\n"
        fi
    ;;
    'upgrade-farm')
        /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_download.sh upgrade-release-major "${FARM_MAJOR_VERSION}"
    ;;
    'upgrade-release-major')
        /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_download.sh upgrade-release-major "${2}"
    ;;
    'upgrade-release-wipe')
        /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_download.sh upgrade-release-wipe "${2}"
    ;;
    'upgrade-master')
        /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_download.sh force-upgrade-master
    ;;
    'upgrade-post')
        /bin/bash "${FARM_PATH}"/farm/scripts/upgrade_post.sh
    ;;
    'web-server-connect')
        printf "\n#### Connecting to http://localhost (creates Farm database if it doesn't exist)\n"
        # Attempt to connect to localhost 10 times, sleeping 60 seconds every fail
        for _ in {1..10}; do
            wget --quiet --no-check-certificate -p http://localhost/ -O /dev/null &&
            printf "#### Successfully connected to http://localhost\n" &&
            break ||
            # Else wait 60 seconds if localhost is not accepting connections
            # Everything below will begin executing if an error occurs before the break
            printf "#### Could not connect to http://localhost. Waiting 60 seconds then trying again (up to 10 times)...\n" &&
            sleep 60 &&
            printf "#### Trying again...\n"
        done
    ;;
    'web-server-reload')
        printf "\n#### Restarting nginx\n"
        service nginx restart
        sleep 5
        printf "#### Reloading farmflask\n"
        service farmflask reload
    ;;
    'web-server-restart')
        printf "\n#### Restarting nginx\n"
        service nginx restart
        sleep 5
        printf "#### Restarting farmflask\n"
        service farmflask restart
    ;;
    'web-server-update')
        printf "\n#### Installing and configuring nginx web server\n"
        systemctl disable farmflask.service
        rm -rf /etc/systemd/system/farmflask.service
        ln -sf "${FARM_PATH}"/install/farmflask_nginx.conf /etc/nginx/sites-enabled/default
        systemctl enable nginx
        systemctl enable "${FARM_PATH}"/install/farmflask.service
    ;;


    #
    # Docker-specific commands
    #

    'docker-compile-translations')
        printf "\n#### Compiling Translations\n"
        cd "${FARM_PATH}"/farm || exit
        "${FARM_PATH}"/env/bin/pybabel compile -d farm_flask/translations
    ;;
    'docker-update-pip')
        printf "\n#### Updating pip\n"
        "${FARM_PATH}"/env/bin/python -m pip install --upgrade pip
    ;;
    'docker-update-pip-packages')
        printf "\n#### Installing pip requirements\n"
        "${FARM_PATH}"/env/bin/python -m pip install --upgrade pip setuptools
        "${FARM_PATH}"/env/bin/python -m pip install --no-cache-dir -r /home/farm/install/requirements.txt
        "${FARM_PATH}"/env/bin/python -m pip install --no-cache-dir -r /home/farm/install/requirements-rpi.txt
    ;;
    'install-docker-ce-cli')
        printf "\n#### Installing Docker Client\n"
        apt-get -y install \
            apt-transport-https \
            ca-certificates \
            curl \
            gnupg2 \
            software-properties-common
        curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add -

        if [[ ${UNAME_TYPE} == 'x86_64' ]]; then
            add-apt-repository -y \
               "deb [arch=amd64] https://download.docker.com/linux/debian \
               $(lsb_release -cs) \
               stable"
        elif [[ ${MACHINE_TYPE} == 'armhf' ]]; then
            add-apt-repository -y \
               "deb [arch=armhf] https://download.docker.com/linux/debian \
               $(lsb_release -cs) \
               stable"
        elif [[ ${MACHINE_TYPE} == 'arm64' ]]; then
            add-apt-repository -y \
               "deb [arch=arm64] https://download.docker.com/linux/debian \
               $(lsb_release -cs) \
               stable"
        else
            printf "\nCould not detect architecture\n"
            exit 1
        fi
        apt-get update
        apt-get -y install docker-ce-cli
    ;;
    *)
        printf "Error: Unrecognized command: %s\n%s" "${1}" "${HELP_OPTIONS}"
    ;;
esac
