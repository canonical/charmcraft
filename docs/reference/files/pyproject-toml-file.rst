.. _pyproject-toml-file:


``pyproject.toml`` file
=======================

The ``pyproject.toml`` file in your charm's root directory is a typical
Python ``pyproject.toml`` file.

    See more: `pip |
    pyproject.toml
    <https://pip.pypa.io/en/stable/reference/build-system/pyproject-toml/>`_

When a charm is initialized with the Kubernetes or machine profile, Charmcraft creates
this file with the following contents:

- Dependencies of the charm code, pre-populated with :external+ops:doc:`Ops <index>`
- Dependencies of tests and linters
- Configuration of tests and linters

If you manually modify the dependencies, you'll need to update the :ref:`uv-lock-file`.

When a charm is initialized with a 12-factor app profile, ``pyproject.toml`` contains
the configuration for tests and linters. Dependencies are specified in the
:ref:`requirements-txt-file`, and there's no ``uv.lock`` file.
