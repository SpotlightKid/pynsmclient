#!/bin/bash

VENV=pynsm
VENV_DIR="$WORKON_HOME/$VENV"
PYNSM_HOME="$(cat $VENV_DIR/.project 2>/dev/null)"

if [ -d "$VENV_DIR" ]; then
    PYTHON="$VENV_DIR/bin/python"
else
    PYTHON=python
fi

exec "$PYTHON" "$PYNSM_HOME/example.py" testpynsm "$@"
