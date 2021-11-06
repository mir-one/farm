#!/bin/bash
# Upgrade from a previous release to this current release.
# Check currently-installed version for the ability to upgrade to this release version.

exec 2>&1

RELEASE_WIPE=$1

if [ "$EUID" -ne 0 ] ; then
  printf "Must be run as root.\n"
  exit 1
fi

runSelfUpgrade() {
  function error_found {
    echo '2' > "${INSTALL_DIRECTORY}"/Farm/.upgrade
    printf "\n\n"
    printf "#### ERROR ####\n"
    printf "There was an error detected during the upgrade. Please review the log at /var/log/farm/farmupgrade.log"
    exit 1
  }

  printf "\n#### Beginning Upgrade Stage 2 of 3 ####\n\n"
  TIMER_START_stage_two=$SECONDS

  printf "RELEASE_WIPE = %s\n" "$RELEASE_WIPE"

  CURRENT_FARM_DIRECTORY=$( cd -P /var/farm-root && pwd -P )
  CURRENT_FARM_INSTALL_DIRECTORY=$( cd -P /var/farm-root/.. && pwd -P )
  THIS_FARM_DIRECTORY=$( cd "$( dirname "${BASH_SOURCE[0]}" )/../.." && pwd -P )
  NOW=$(date +"%Y-%m-%d_%H-%M-%S")

  if [ "$CURRENT_FARM_DIRECTORY" == "$THIS_FARM_DIRECTORY" ] ; then
    printf "Cannot perform upgrade to the Farm instance already intalled. Halting upgrade.\n"
    exit 1
  fi

  if [ -d "${CURRENT_FARM_DIRECTORY}" ] ; then
    printf "Found currently-installed version of Farm. Checking version...\n"
    CURRENT_VERSION=$("${CURRENT_FARM_INSTALL_DIRECTORY}"/Farm/env/bin/python3 "${CURRENT_FARM_INSTALL_DIRECTORY}"/Farm/farm/utils/github_release_info.py -c 2>&1)
    MAJOR=$(echo "$CURRENT_VERSION" | cut -d. -f1)
    MINOR=$(echo "$CURRENT_VERSION" | cut -d. -f2)
    REVISION=$(echo "$CURRENT_VERSION" | cut -d. -f3)
    if [ -z "$MAJOR" ] || [ -z "$MINOR" ] || [ -z "$REVISION" ] ; then
      printf "Could not determine Farm version\n"
      exit 1
    else
      printf "Farm version found installed: %s.%s.%s\n" "${MAJOR}" "${MINOR}" "${REVISION}"
    fi
  else
    printf "Could not find a current version of Farm installed. Check the symlink /var/mycdo-root that is supposed to point to the install directory"
    exit 1
  fi

  ################################
  # Begin tests prior to upgrade #
  ################################

  printf "\n#### Beginning pre-upgrade checks ####\n\n"

  # Maintenance mode
  # This is a temporary state so the developer can test a version release before users can upgrade.
  # Creating the file ~/Farm/.maintenance will override maintenece mode.
  if python "${CURRENT_FARM_DIRECTORY}"/farm/scripts/upgrade_check.py --maintenance_mode; then
    if [[ ! -e $CURRENT_FARM_DIRECTORY/.maintenance ]]; then
      printf "The Farm upgrade system is currently in maintenance mode so the developer can test the latest upgrade.\n"
      printf "Please wait and attempt the upgrade later.\n"
      echo '0' > "${CURRENT_FARM_DIRECTORY}"/.upgrade
      exit 1
    fi
  fi

  # Upgrade requires Python >= 3.6
  printf "Checking Python version...\n"
  if hash python3 2>/dev/null; then
    if ! python3 "${CURRENT_FARM_DIRECTORY}"/farm/scripts/upgrade_check.py --min_python_version "3.6"; then
      printf "\nIncorrect Python version found. Farm requires Python >= 3.6.\n"
      printf "If you're running Raspbian 9 (Stretch) with Python 3.5, you will need to install at least Raspbian 10 (Buster) with Python 3.7 to upgrade to the latest version of Farm.\n"
      echo '0' > "${CURRENT_FARM_DIRECTORY}"/.upgrade
      exit 1
    else
      printf "Python >= 3.6 found. Continuing with the upgrade.\n"
    fi
  else
    printf "\npython3 was not found. Cannot proceed with the upgrade without python3 (Python >= 3.6).\n"
    echo '0' > "${CURRENT_FARM_DIRECTORY}"/.upgrade
    exit 1
  fi

  # If upgrading from version 7 and Python >= 3.6 found (from previous check), upgrade without wiping database
  if [[ "$MAJOR" == 7 ]] && [[ "$RELEASE_WIPE" = true ]]; then
    printf "Your system was found to have Python >= 3.6 installed. Proceeding with upgrade without wiping database.\n"
    RELEASE_WIPE=false
  fi

  printf "All pre-upgrade checks passed. Proceeding with upgrade.\n\n"

  ##############################
  # End tests prior to upgrade #
  ##############################

  THIS_VERSION=$("${CURRENT_FARM_DIRECTORY}"/env/bin/python3 "${THIS_FARM_DIRECTORY}"/farm/utils/github_release_info.py -c 2>&1)
  printf "Upgrading Farm to version %s\n\n" "$THIS_VERSION"

  printf "Stopping the Farm daemon..."
  if ! service farm stop ; then
    printf "Error: Unable to stop the daemon. Continuing anyway...\n"
  fi
  printf "Done.\n"

  if [ -d "${CURRENT_FARM_DIRECTORY}"/env ] ; then
    printf "Moving env directory..."
    if ! mv "${CURRENT_FARM_DIRECTORY}"/env "${THIS_FARM_DIRECTORY}" ; then
      printf "Failed: Error while trying to move env directory.\n"
      error_found
    fi
    printf "Done.\n"
  fi

  printf "Copying databases..."
  if ! cp "${CURRENT_FARM_DIRECTORY}"/databases/*.db "${THIS_FARM_DIRECTORY}"/databases ; then
    printf "Failed: Error while trying to copy databases."
    error_found
  fi
  printf "Done.\n"

  printf "Copying flask_secret_key..."
  if ! cp "${CURRENT_FARM_DIRECTORY}"/databases/flask_secret_key "${THIS_FARM_DIRECTORY}"/databases ; then
    printf "Failed: Error while trying to copy flask_secret_key."
  fi
  printf "Done.\n"

  if [ -d "${CURRENT_FARM_DIRECTORY}"/farm/farm_flask/ssl_certs ] ; then
    printf "Copying SSL certificates..."
    if ! cp -R "${CURRENT_FARM_DIRECTORY}"/farm/farm_flask/ssl_certs "${THIS_FARM_DIRECTORY}"/farm/farm_flask/ssl_certs ; then
      printf "Failed: Error while trying to copy SSL certificates."
      error_found
    fi
    printf "Done.\n"
  fi

  # TODO: Remove in next major release
  if [ -d "${CURRENT_FARM_DIRECTORY}"/farm/controllers/custom_controllers ] ; then
    printf "Copying farm/controllers/custom_controllers..."
    if ! cp "${CURRENT_FARM_DIRECTORY}"/farm/controllers/custom_controllers/*.py "${THIS_FARM_DIRECTORY}"/farm/functions/custom_functions/ ; then
      printf "Failed: Error while trying to copy farm/controllers/custom_controllers"
      error_found
    fi
    printf "Done.\n"
  fi

  if [ -d "${CURRENT_FARM_DIRECTORY}"/farm/functions/custom_functions ] ; then
    printf "Copying farm/functions/custom_functions..."
    if ! cp "${CURRENT_FARM_DIRECTORY}"/farm/functions/custom_functions/*.py "${THIS_FARM_DIRECTORY}"/farm/functions/custom_functions/ ; then
      printf "Failed: Error while trying to copy farm/functions/custom_functions"
      error_found
    fi
    printf "Done.\n"
  fi

  if [ -d "${CURRENT_FARM_DIRECTORY}"/farm/inputs/custom_inputs ] ; then
    printf "Copying farm/inputs/custom_inputs..."
    if ! cp "${CURRENT_FARM_DIRECTORY}"/farm/inputs/custom_inputs/*.py "${THIS_FARM_DIRECTORY}"/farm/inputs/custom_inputs/ ; then
      printf "Failed: Error while trying to copy farm/inputs/custom_inputs"
      error_found
    fi
    printf "Done.\n"
  fi

  if [ -d "${CURRENT_FARM_DIRECTORY}"/farm/outputs/custom_outputs ] ; then
    printf "Copying farm/outputs/custom_outputs..."
    if ! cp "${CURRENT_FARM_DIRECTORY}"/farm/outputs/custom_outputs/*.py "${THIS_FARM_DIRECTORY}"/farm/outputs/custom_outputs/ ; then
      printf "Failed: Error while trying to copy farm/outputs/custom_outputs"
      error_found
    fi
    printf "Done.\n"
  fi

  if [ -d "${CURRENT_FARM_DIRECTORY}"/farm/widgets/custom_widgets ] ; then
    printf "Copying farm/widgets/custom_widgets..."
    if ! cp "${CURRENT_FARM_DIRECTORY}"/farm/widgets/custom_widgets/*.py "${THIS_FARM_DIRECTORY}"/farm/widgets/custom_widgets/ ; then
      printf "Failed: Error while trying to copy farm/widgets/custom_widgets"
      error_found
    fi
    printf "Done.\n"
  fi

  if [ -d "${CURRENT_FARM_DIRECTORY}"/farm/user_python_code ] ; then
    printf "Copying farm/user_python_code..."
    if ! cp "${CURRENT_FARM_DIRECTORY}"/farm/user_python_code/*.py "${THIS_FARM_DIRECTORY}"/farm/user_python_code/ ; then
      printf "Failed: Error while trying to copy farm/user_python_code"
      error_found
    fi
    printf "Done.\n"
  fi

  if [ -d "${CURRENT_FARM_DIRECTORY}"/farm/farm_flask/static/js/user_js ] ; then
    printf "Copying farm/farm_flask/static/js/user_js..."
    if ! cp -r "${CURRENT_FARM_DIRECTORY}"/farm/farm_flask/static/js/user_js "${THIS_FARM_DIRECTORY}"/farm/farm_flask/static/js/ ; then
      printf "Failed: Error while trying to copy farm/farm_flask/static/js/user_js"
      error_found
    fi
    printf "Done.\n"
  fi

  if [ -d "${CURRENT_FARM_DIRECTORY}"/farm/farm_flask/static/css/user_css ] ; then
    printf "Copying farm/farm_flask/static/css/user_css..."
    if ! cp -r "${CURRENT_FARM_DIRECTORY}"/farm/farm_flask/static/css/user_css "${THIS_FARM_DIRECTORY}"/farm/farm_flask/static/css/ ; then
      printf "Failed: Error while trying to copy farm/farm_flask/static/css/user_css"
      error_found
    fi
    printf "Done.\n"
  fi

  if [ -d "${CURRENT_FARM_DIRECTORY}"/output_usage_reports ] ; then
    printf "Moving output_usage_reports directory..."
    if ! mv "${CURRENT_FARM_DIRECTORY}"/output_usage_reports "${THIS_FARM_DIRECTORY}" ; then
      printf "Failed: Error while trying to move output_usage_reports directory.\n"
    fi
    printf "Done.\n"
  fi

  if [ -d "${CURRENT_FARM_DIRECTORY}"/cameras ] ; then
    printf "Moving cameras directory..."
    if ! mv "${CURRENT_FARM_DIRECTORY}"/cameras "${THIS_FARM_DIRECTORY}" ; then
      printf "Failed: Error while trying to move cameras directory.\n"
    fi
    printf "Done.\n"
  fi

  if [ -d "${CURRENT_FARM_DIRECTORY}"/.upgrade ] ; then
    printf "Moving .upgrade file..."
    if ! mv "${CURRENT_FARM_DIRECTORY}"/.upgrade "${THIS_FARM_DIRECTORY}" ; then
      printf "Failed: Error while trying to move .upgrade file.\n"
    fi
    printf "Done.\n"
  fi

  if [ ! -d "/var/Farm-backups" ] ; then
    mkdir /var/Farm-backups
  fi

  BACKUP_DIR="/var/Farm-backups/Farm-backup-${NOW}-${CURRENT_VERSION}"

  printf "Moving current Farm intstall from %s to %s..." "${CURRENT_FARM_DIRECTORY}" "${BACKUP_DIR}"
  if ! mv "${CURRENT_FARM_DIRECTORY}" "${BACKUP_DIR}" ; then
    printf "Failed: Error while trying to move old Farm install from %s to %s.\n" "${CURRENT_FARM_DIRECTORY}" "${BACKUP_DIR}"
    error_found
  fi
  printf "Done.\n"

  printf "Moving downloaded Farm version from %s to %s/Farm..." "${THIS_FARM_DIRECTORY}" "${CURRENT_FARM_INSTALL_DIRECTORY}"
  if ! mv "${THIS_FARM_DIRECTORY}" "${CURRENT_FARM_INSTALL_DIRECTORY}"/Farm ; then
    printf "Failed: Error while trying to move new Farm install from %s to %s/Farm.\n" "${THIS_FARM_DIRECTORY}" "${CURRENT_FARM_INSTALL_DIRECTORY}"
    error_found
  fi
  printf "Done.\n"

  sleep 30

  CURRENT_FARM_DIRECTORY=$( cd -P /var/farm-root && pwd -P )
  cd "${CURRENT_FARM_DIRECTORY}" || return

  ############################################
  # Begin tests prior to post-upgrade script #
  ############################################

  if [ "$RELEASE_WIPE" = true ] ; then
    # Instructed to wipe configuration files (database, virtualenv)

    if [ -d "${CURRENT_FARM_DIRECTORY}"/env ] ; then
      printf "Removing virtualenv at %s/env..." "${CURRENT_FARM_DIRECTORY}"
      if ! rm -rf "${CURRENT_FARM_DIRECTORY}"/env ; then
        printf "Failed: Error while trying to delete virtaulenv.\n"
      fi
      printf "Done.\n"
    fi

    if [ -d "${CURRENT_FARM_DIRECTORY}"/databases/farm.db ] ; then
      printf "Removing database at %s/databases/farm.db..." "${CURRENT_FARM_DIRECTORY}"
      if ! rm -f "${CURRENT_FARM_DIRECTORY}"/databases/farm.db ; then
        printf "Failed: Error while trying to delete database.\n"
      fi
      printf "Done.\n"
    fi

  fi

  printf "\n#### Completed Upgrade Stage 2 of 3 in %s seconds ####\n" "$((SECONDS - TIMER_START_stage_two))"

  ##########################################
  # End tests prior to post-upgrade script #
  ##########################################

  printf "\n#### Beginning Upgrade Stage 3 of 3 ####\n\n"
  TIMER_START_stage_three=$SECONDS

  printf "Running post-upgrade script...\n"
  if ! "${CURRENT_FARM_DIRECTORY}"/farm/scripts/upgrade_post.sh ; then
    printf "Failed: Error while running post-upgrade script.\n"
    error_found
  fi

  printf "\n#### Completed Upgrade Stage 3 of 3 in %s seconds ####\n\n" "$((SECONDS - TIMER_START_stage_three))"

  printf "Upgrade completed. Review the log to ensure no critical errors were encountered\n"

  #############################
  # Begin tests after upgrade #
  #############################



  ###########################
  # End tests after upgrade #
  ###########################

  echo '0' > "${CURRENT_FARM_DIRECTORY}"/.upgrade

  exit 0
}

runSelfUpgrade
