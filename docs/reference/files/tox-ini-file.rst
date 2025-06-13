.. _tox-ini-file:


``tox.ini`` file
================

The ``tox.ini`` file in your charm's root directory is a typical tox
configuration file.

    See more: `Tox |
    Configuration <https://tox.wiki/en/latest/user_guide.html#configuration>`_

Charmcraft creates this file with the following environments:

- ``format`` - Apply coding style standards
- ``lint`` - Check code against coding style standards
- ``static`` - Run static type checks
- ``unit`` - Run the charm's unit tests
- ``integration`` - Run the charm's integration tests

To run an environment, use ``tox -e <env-name>``.

For the ``kubernetes`` and ``machine`` profiles, ``tox.ini`` requires the
`tox-uv <https://github.com/tox-dev/tox-uv>`_ plugin, so you should use
`uv <https://docs.astral.sh/uv/>`_ to install tox:

.. code-block:: bash

    uv tool install tox --with tox-uv

Configuration of testing and linting tools is specified in :ref:`pyproject-toml-file`.
Dependencies are also specified in ``pyproject.toml``. If you manually modify the
dependencies in ``pyproject.toml``, you'll need to update the uv.lock file before using
tox.

For the 12-factor profiles, ``django-framework`` and so on, ``tox.ini`` doesn't require
any plugins. Dependencies are specified in the :ref:`requirements-txt-file` instead of
``pyproject.toml``.
