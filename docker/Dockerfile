FROM python:3.7-slim-buster

ENV DOCKER_CONTAINER TRUE

RUN useradd -ms /bin/bash pi
RUN useradd -ms /bin/bash farm

COPY . /home/farm

WORKDIR /home/farm/farm

RUN /home/farm/farm/scripts/upgrade_commands.sh create-files-directories
RUN /home/farm/farm/scripts/upgrade_commands.sh update-apt
RUN /home/farm/farm/scripts/upgrade_commands.sh update-packages
RUN /home/farm/farm/scripts/upgrade_commands.sh install-docker-ce-cli
RUN /home/farm/farm/scripts/upgrade_commands.sh docker-update-pip
RUN /home/farm/farm/scripts/upgrade_commands.sh docker-update-pip-packages
RUN /home/farm/farm/scripts/upgrade_commands.sh ssl-certs-generate
RUN /home/farm/farm/scripts/upgrade_commands.sh docker-compile-translations
RUN /home/farm/farm/scripts/upgrade_commands.sh compile-farm-wrapper
