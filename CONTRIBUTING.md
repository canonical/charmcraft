## Set up the development environment

We recommend uv for setting up your local development environment:

- [uv snap](https://snapcraft.io/astral-uv)
- [Official uv binary](https://docs.astral.sh/uv/getting-started/installation/)

To set up a local copy of the repository for development:

```bash
git clone https://github.com/canonical/charmcraft.git
cd charmcraft
make setup
```

If you need `python-apt`, add `https://people.canonical.com/~lengau/pypi/` as an
extra index URL.

You will need a copy of `ruff` installed. On many Linux distributions, you
can install ruff with:

```bash
sudo snap install ruff
```

Otherwise, you can install ruff in your virtual environment with:

```bash
uv tool install ruff
```

## Develop for the Charmcraft source

Make changes as appropriate. Some existing ideas are in the
[Github Issues](https://github.com/canonical/charmcraft/issues)

To test locally:

```bash
source .venv/bin/activate
CHARMCRAFT_DEVELOPER=1 python -m charmcraft
```

When you're done, make sure you run the tests.

You can do so with:

```bash
uv sync
uv run pytest
```

Contributions welcome!

## Contribute to the documentation

Charmcraft stores its documentation source in the repository and tests it for errors.
Contributing to the documentation is similar to contributing to the code.

Before you begin, [set up the development
environment](#set-up-the-development-environment).

### Write the docs

The Charmcraft documentation follows [Diátaxis](https://diataxis.fr), and adheres to the
conventions of the [Canonical Documentation Style
Guide](https://docs.ubuntu.com/styleguide/en).

The documentation source is written in reStructuredText, and is formatted according to
[Canonical's reStructuredText
style](https://canonical-documentation-with-sphinx-and-readthedocscom.readthedocs-hosted.com/style-guide).
It uses Sphinx for linting and building, and employs the
[Intersphinx](https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html)
extension to link to the related Juju and ops library documentation.

### Build the docs

After you've made changes to the documentation, it's a good practice to generate it
locally so you can verify that the results look and feel correct.

You can preview the entire documentation set with your changes by building it as a
website:

```bash
make docs
```

To view the rendered website, open `docs/_build/index.html` in a web browser. More
changes to the files require you to rebuild.

You can also host the docs on an interactive server on your local system:

```bash
make docs-auto
```

The server can be reached at [`127.0.0.1:8080`](http://127.0.0.1:8080) in a web browser.
The server dynamically loads any changes you save to the documentation files, so you
don't have to manually re-build every time you make a change.

### Test your work

Once you've completed your draft, run a local test to make sure your changes follow the
coding and documentation conventions:

```bash
make lint-docs
```

Please fix any errors the linter detects before submitting your changes for review.
