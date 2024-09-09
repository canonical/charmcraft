## Development environment

To set up an initial development environment:

    git clone https://github.com/canonical/charmcraft.git
    cd charmcraft
    virtualenv venv
    . venv/bin/activate
    pip install -r requirements-dev.txt -e .

You will need a copy of `ruff` installed. On many Linux distributions, you
can install ruff with:

    sudo snap install ruff

Otherwise, you can install ruff in your virtual environment with:

    pip install ruff


## Developing against Charmcraft source

Make changes as appropriate. Some existing ideas are in the
[Github Issues](https://github.com/canonical/charmcraft/issues)

To test locally:

    CHARMCRAFT_DEVELOPER=1 python -m charmcraft

When you're done, make sure you run the tests.

You can do so with

    pip install -r requirements-dev.txt
    ./run_tests

Contributions welcome!
