#!/usr/bin/env bash

cp variables.yml .env
coverage run -m pytest tests
coverage report --show-missing
