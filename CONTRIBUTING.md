## Development environment

We recommend uv for setting up your local development environment:

- [uv snap](https://snapcraft.io/astral-uv)
- [Official uv binary](https://docs.astral.sh/uv/getting-started/installation/)

To set up an initial development environment:

    git clone https://github.com/canonical/charmcraft.git
    cd charmcraft
    uv sync --all-extras

If you need `python-apt`, add `https://people.canonical.com/~lengau/pypi/` as an
extra index URL.

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

    uv sync
    uv run pytest

Contributions welcome!
