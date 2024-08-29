#!/bin/bash -eux

requirements_fixups() {
  req_file="$1"

  # Python apt library pinned to source.
  sed -i '/^python-apt==/d' "$req_file"
}

uv sync --no-dev --locked --reinstall
uv pip freeze --strict --exclude-editable > requirements.txt
requirements_fixups "requirements.txt"
