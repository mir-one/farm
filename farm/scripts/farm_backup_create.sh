#!/bin/bash

exec 2>&1

if [ "$EUID" -ne 0 ] ; then
    printf "Must be run as root.\n"
    exit 1
fi

INSTALL_DIRECTORY=$( cd -P /var/farm-root/.. && pwd -P )

function error_found {
    date
    printf "\n#### ERROR ####"
    printf "\nThere was an error detected while creating the backup. Please review the log at /var/log/farm/farmbackup.log"
    exit 1
}

CURRENT_VERSION=$("${INSTALL_DIRECTORY}"/Farm/env/bin/python "${INSTALL_DIRECTORY}"/Farm/farm/utils/github_release_info.py -c 2>&1)
NOW=$(date +"%Y-%m-%d_%H-%M-%S")
TMP_DIR="/var/tmp/Farm-backup-${NOW}-${CURRENT_VERSION}"
BACKUP_DIR="/var/Farm-backups/Farm-backup-${NOW}-${CURRENT_VERSION}"

printf "\n#### Create backup initiated %s ####\n" "${NOW}"

mkdir -p /var/Farm-backups

printf "Backing up current Farm from %s/Farm to %s..." "${INSTALL_DIRECTORY}" "${TMP_DIR}"
if ! rsync -avq --exclude=cameras --exclude=env --exclude=.upgrade "${INSTALL_DIRECTORY}"/Farm "${TMP_DIR}" ; then
    printf "Failed: Error while trying to back up current Farm install from %s/Farm to %s.\n" "${INSTALL_DIRECTORY}" "${BACKUP_DIR}"
    error_found
fi
printf "Done.\n"

printf "Moving %s/Farm to %s..." "${TMP_DIR}" "${BACKUP_DIR}"
if ! mv "${TMP_DIR}"/Farm "${BACKUP_DIR}" ; then
    printf "Failed: Error while trying to move %s/Farm to %s.\n" "${TMP_DIR}" "${BACKUP_DIR}"
    error_found
fi
printf "Done.\n"

date
printf "Backup completed successfully without errors.\n"
