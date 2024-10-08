## Development environment

It's recommended to use `uv` for setting up your development environment, but
this is not required. `uv` is available [as a snap](https://snapcraft.io/astral-uv)
and from [official sources](https://docs.astral.sh/uv/getting-started/installation/).

To set up an initial development environment:

    git clone https://github.com/canonical/charmcraft.git
    cd charmcraft
    uv venv
    . .venv/bin/activate
    uv pip install -r requirements-dev.txt -e .

You will need a copy of `ruff` installed. On many Linux distributions, you
can install ruff with:

    sudo snap install ruff

Otherwise, you can install ruff in your virtual environment with:

    uv tool install ruff


## Developing against Charmcraft source

Make changes as appropriate. Some existing ideas are in the
[Github Issues](https://github.com/canonical/charmcraft/issues)

To test locally:

    CHARMCRAFT_DEVELOPER=1 python -m charmcraft

When you're done, make sure you run the tests.

You can do so with

    uv pip install -r requirements-dev.txt
    ./run_tests

Contributions welcome!
