#!/usr/bin/env sh

coverage run -m pytest
coverage report cubetime/*py
coverage html cubetime/*py
xdg-open htmlcov/index.html &
