.. _uv-lock-file:


``uv.lock`` file
================

The ``uv.lock`` file in your charm's root directory specifies the exact versions of
your charm's dependencies and your development dependencies.

.. seealso::

    `uv | The lockfile
    <https://docs.astral.sh/uv/concepts/projects/layout/#the-lockfile>`_

Charmcraft doesn't create this file. This file is required by the tox-uv plugin and
charms with environments managed by the :ref:`craft_parts_uv_plugin`. For more
information, see :ref:`tox-ini-file`.

To create or update this file, run the ``uv lock`` command.
Alternatively, you can update this file by running ``uv add`` or ``uv remove``
to manage dependencies in the :ref:`pyproject-toml-file`.

You shouldn't manually edit this file.

For 12-factor app charms targeting Ubuntu 24.04 LTS or lower, this file isn't
necessary. Dependencies are specified in the :ref:`requirements-txt-file` instead of
``pyproject.toml``.
