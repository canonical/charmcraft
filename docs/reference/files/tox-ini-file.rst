.. _tox-ini-file:


``tox.ini`` file
================

The ``tox.ini`` file in your charm's root directory is a typical tox
configuration file.

    See more: `tox |
    Configuration <https://tox.wiki/en/latest/user_guide.html#configuration>`_

Charmcraft creates this file and defines the following tox environments:

+-------------+-------------------------------------------------------------+
| Environment | Purpose                                                     |
+=============+=============================================================+
| format      | Apply coding style standards                                |
+-------------+-------------------------------------------------------------+
| lint        | Check code against coding style standards and static checks |
+-------------+-------------------------------------------------------------+
| unit        | Run the charm's unit tests                                  |
+-------------+-------------------------------------------------------------+
| integration | Run the charm's integration tests                           |
+-------------+-------------------------------------------------------------+

To run the commands in an environment, use ``tox -e <env-name>``.

For the Kubernetes and machine profiles, ``tox.ini`` requires the
`tox-uv <https://github.com/tox-dev/tox-uv>`_ plugin. First make sure that
`uv <https://docs.astral.sh/uv/>`_ is installed on the current host. Then use uv to
install tox and tox-uv:

.. code-block:: bash

    uv tool install tox --with tox-uv

Configuration of testing and linting tools is specified in the
:ref:`pyproject-toml-file`. Dependencies are also specified in ``pyproject.toml``. If
you manually modify the dependencies in ``pyproject.toml``, you'll need to update the
:ref:`uv-lock-file` before using tox.

For 12-factor app profiles, ``tox.ini`` doesn't require any plugins. Dependencies are
specified in the :ref:`requirements-txt-file` instead of ``pyproject.toml``.
