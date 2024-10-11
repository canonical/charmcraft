## Development environment

To set up an initial development environment:

    git clone https://github.com/canonical/charmcraft.git
    cd charmcraft
    uv sync --frozen --all-extras

You will need a copy of `ruff` installed. On many Linux distributions, you
can install ruff with:

    sudo snap install ruff

Otherwise, you can install ruff with:

    uv tool install ruff


## Developing against Charmcraft source

Make changes as appropriate. Some existing ideas are in the
[Github Issues](https://github.com/canonical/charmcraft/issues)

To test locally:

    CHARMCRAFT_DEVELOPER=1 CRAFT_DEBUG=1 python -m charmcraft

When you're done, make sure you run the tests.

You can do so with

    uv sync --frozen --all-extras
    uv run pytest

Contributions welcome!
