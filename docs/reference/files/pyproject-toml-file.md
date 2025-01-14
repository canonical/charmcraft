(pyproject-toml-file)=

# `pyproject.toml` file

The `pyproject.toml` file in your charm's root directory is a typical Python
`pyproject.toml` file.

> See more: [`pip` |
> `pyproject.toml`](https://pip.pypa.io/en/stable/reference/build-system/pyproject-toml/)

This file is generated automatically by `charmcraft init` with the contents below:

```toml
# Testing tools configuration
[tool.coverage.run]
branch = true

[tool.coverage.report]
show_missing = true

[tool.pytest.ini_options]
minversion = "6.0"
log_cli_level = "INFO"

# Formatting tools configuration
[tool.black]
line-length = 99
target-version = ["py38"]

# Linting tools configuration
[tool.ruff]
line-length = 99
select = ["E", "W", "F", "C", "N", "D", "I001"]
extend-ignore = [
    "D203",
    "D204",
    "D213",
    "D215",
    "D400",
    "D404",
    "D406",
    "D407",
    "D408",
    "D409",
    "D413",
]
ignore = ["E501", "D107"]
extend-exclude = ["__pycache__", "*.egg_info"]
per-file-ignores = {"tests/*" = ["D100","D101","D102","D103","D104"]}

[tool.ruff.mccabe]
max-complexity = 10

[tool.codespell]
skip = "build,lib,venv,icon.svg,.tox,.git,.mypy_cache,.ruff_cache,.coverage"

[tool.pyright]
include = ["src/**.py"]
```
