#!/usr/bin bash

pip install ruff black --upgrade
ruff scripts
black scripts --check
