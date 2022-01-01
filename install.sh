#!/bin/bash

if [[ ! $(command -v python3) ]]
then
  echo "python3 not found"
  exit 1
fi

VERSION="$(python3 --version | sed -E 's/Python 3\.([0-9]+)\.[0-9]+/\1/')"
if [[ ${VERSION} -lt 7 ]]
then
  echo "Python version less than 3.7"
  exit 1
fi

VENV="$(pip3 list | grep -c "virtualenv")"
if [[ ${VENV} -eq 0 ]]
then
  echo "virtualenv not found"
  exit 1
fi

DERMY="${HOME}/.dermy"
if [[ -d ${DERMY} ]]
then
  rm -rf "${DERMY}"
fi

mkdir -p "${DERMY}"

python3 -m venv "${DERMY}/venv"
PYPATH="${DERMY}/venv/bin"

"${PYPATH}/pip" install "${PWD}"

WRAPPER="#!/bin/bash

PYPATH=${PYPATH}
\${PYPATH}/python3 -m dermy \"\$@\"
"

SCRIPT="${DERMY}/wrapper.sh"
echo "${WRAPPER}" > "${SCRIPT}"

chmod +x "${SCRIPT}"

ALIAS="alias dermy=~/.dermy/wrapper.sh"
IS_PRESENT=$(grep "${ALIAS}" "${HOME}/.zshrc")
if [[ ! ${IS_PRESENT} ]]
then
  echo "${ALIAS}" >> "${HOME}/.zshrc"
fi
