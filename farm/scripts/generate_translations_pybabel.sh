#!/bin/bash
#
# Generates the Farm translation .po files
#
# Requires: pybabel in virtualenv
#
# Note: The following tool is useful for rapid translation of po files
# https://github.com/naskio/po-auto-translation
#

INSTALL_DIRECTORY=$( cd "$( dirname "${BASH_SOURCE[0]}" )/../../" && pwd -P )
CURRENT_VERSION=$("${INSTALL_DIRECTORY}"/env/bin/python3 "${INSTALL_DIRECTORY}"/farm/utils/github_release_info.py -c 2>&1)

INFO_ARGS=(
  --project "Farm"
  --version "${CURRENT_VERSION}"
  --copyright "Roman Inozemtsev"
  --msgid-bugs-address "dao@mir.one"
)

cd "${INSTALL_DIRECTORY}"/farm || return

"${INSTALL_DIRECTORY}"/env/bin/pybabel extract "${INFO_ARGS[@]}" -s -F babel.cfg -k lazy_gettext -o farm_flask/translations/messages.pot .
"${INSTALL_DIRECTORY}"/env/bin/pybabel update --update-header-comment -i farm_flask/translations/messages.pot -d farm_flask/translations
