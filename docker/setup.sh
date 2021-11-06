#!/bin/bash

if [ "$EUID" -ne 0 ] ; then
  printf "Please run as root.\n"
  exit 1
fi

INSTALL_PATH="$( cd -P "$( dirname "${SOURCE}" )/.." && pwd )"
LOG_LOCATION="${INSTALL_PATH}"/docker/docker.log
touch "${LOG_LOCATION}"

cd "${INSTALL_PATH}" || exit

case "${1:-''}" in
    "dependencies")
        apt-get update -y
        apt-get install -y python3 python3-dev python3-setuptools libffi-dev libssl-dev build-essential
        apt remove -y python3-cffi-backend

        python3 /usr/lib/python3/dist-packages/easy_install.py pip
        python3 -m pip install --upgrade pip

        "${INSTALL_PATH}"/farm/scripts/upgrade_commands.sh setup-virtualenv
        "${INSTALL_PATH}"/farm/scripts/upgrade_commands.sh install-docker-ce-cli
        apt install -y docker-ce containerd.io

        usermod -aG docker pi

        if ! [ -x "$(command -v "${INSTALL_PATH}"/env/bin/docker-compose)" ]; then
            printf "#### Installing docker-compose\n" 2>&1 | tee -a "${LOG_LOCATION}"
            "${INSTALL_PATH}"/env/bin/python -m pip install docker-compose
        else
            printf "#### docker-compose already installed. Skipping install.\n" 2>&1 | tee -a "${LOG_LOCATION}"
        fi

        if ! [ -x "$(command -v logrotate)" ]; then
            printf "#### Installing logrotate\n" 2>&1 | tee -a "${LOG_LOCATION}"
            apt install logrotate
            cp "${INSTALL_PATH}"/docker/logrotate_docker /etc/logrotate.d/
        else
            printf "#### logrotate already installed. Skipping install.\n" 2>&1 | tee -a "${LOG_LOCATION}"
        fi

        printf "\n#### All dependencies installed\n\n" 2>&1 | tee -a "${LOG_LOCATION}"

        printf "#### You must log out then back in before running 'make build'. If you are not running Raspbian under the user 'pi', then you need to add your user to the 'docker group with the command 'usermod -aG docker pi', substituting 'pi' with your user, then log out for the changes to take effect.\n" 2>&1 | tee -a "${LOG_LOCATION}"
        printf 'For example, to add you current user: `sudo usermod -aG docker $USER`\n' 2>&1 | tee -a "${LOG_LOCATION}"
    ;;
    "test")
        docker exec -ti farm_flask "${INSTALL_PATH}"/env/bin/python -m pip install --upgrade -r /home/farm/farm/install/requirements-testing.txt
        docker exec -ti farm_flask "${INSTALL_PATH}"/env/bin/python -m pytest /home/farm/farm/tests/software_tests
    ;;
    "clean-all")
        docker container stop "$(docker container ls -a -q)" && docker system prune -a -f --volumes
    ;;
    *)
        printf "\nError: Unrecognized command: %s\n%s" "${1}" "${HELP_OPTIONS}"
        exit 1
    ;;
esac
