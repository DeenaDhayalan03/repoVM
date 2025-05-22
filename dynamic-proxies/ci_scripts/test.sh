#!/usr/bin/env bash

cp dev-variables.env .env
coverage run -m pytest tests
coverage report --show-missing
