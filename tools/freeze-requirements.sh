#!/bin/bash -eux

make_requirements() {
  uv pip compile --upgrade --output-file "$@" pyproject.toml
}

make_requirements requirements.txt
make_requirements requirements-dev.txt --extra dev
