#!/usr/bin/env bash
export PIPENV_VENV_IN_PROJECT=1
/opt/homebrew/bin/pipenv sync
/opt/homebrew/bin/pipenv run python3 \
  /opt/aws-dynamic-dns/main.py \
  /opt/aws-dynamic-dns/config.toml