.. _pyproject-toml-file:


``pyproject.toml`` file
=======================

The ``pyproject.toml`` file in your charm's root directory is a typical
Python ``pyproject.toml`` file.

    See more: `pip |
    pyproject.toml
    <https://pip.pypa.io/en/stable/reference/build-system/pyproject-toml/>`_

For the ``kubernetes`` and ``machine`` profiles, Charmcraft creates this file with the
following contents:

- Dependencies of the charm code, pre-populated with :external+ops:doc:`Ops <index>`
- Dependencies of static type checks, unit tests, and integration tests
- Configuration of testing and linting tools

If you manually modify the dependencies, you'll need to update the uv.lock file.

For the 12-factor profiles, ``django-framework`` and so on, ``pyproject.toml`` only
contains configuration of testing and linting tools. Dependencies are specified in
the :ref:`requirements-txt-file` and there's no ``uv.lock`` file.
