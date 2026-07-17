.. _pyproject-toml-file:


``pyproject.toml`` file
=======================

The ``pyproject.toml`` file in your charm's root directory is a typical
Python ``pyproject.toml`` file.

.. seealso::

    `pyproject.toml <https://pip.pypa.io/en/stable/reference/build-system>`__ in the pip
    documentation.

Charmcraft creates this file with the following contents:

- Dependencies of the charm code, pre-populated with :external+ops:doc:`Ops <index>`
- Dependencies of tests and linters
- Configuration of tests and linters

You'll need to create :ref:`uv-lock-file` and update it if you change your charm's
dependencies.

For 12-factor app profiles targeting Ubuntu 24.04 LTS or lower: ``pyproject.toml``
only contains the configuration for tests and linters. Dependencies are specified in the
:ref:`requirements-txt-file`, and there's no ``uv.lock`` file.
