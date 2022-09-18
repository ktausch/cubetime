#!/usr/bin/env sh

PYTHON_EXEC=$1
if [ -z "$PYTHON_EXEC" ]
then
    PYTHON_EXEC="$(which python)"
else
    shift
fi
echo "Trying to use python interpreter at $PYTHON_EXEC"
$PYTHON_EXEC -m coverage run -m pytest $@
$PYTHON_EXEC -m coverage report cubetime/core/*py
$PYTHON_EXEC -m coverage html cubetime/core/*py
xdg-open htmlcov/index.html &
