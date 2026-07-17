.. _uv-lock-file:


``uv.lock`` file
================

The ``uv.lock`` file in your charm's root directory specifies the exact versions of
your charm's dependencies and your development dependencies.

.. seealso::

    `uv | The lockfile
    <https://docs.astral.sh/uv/concepts/projects/layout/#the-lockfile>`_

This file is required if your charm uses the :ref:`craft_parts_uv_plugin`. It's also
required by the tox-uv plugin. For more information, see :ref:`tox-ini-file`.

Charmcraft doesn't create this file.

Use ``uv lock`` to create this file and update it if you change your charm's
dependencies. Alternatively, you can update this file by using ``uv add`` and
``uv remove`` to manage dependencies in the :ref:`pyproject-toml-file`.

You shouldn't manually edit this file.

For 12-factor app profiles targeting Ubuntu 24.04 LTS or lower: This file isn't
necessary. Dependencies are specified in the :ref:`requirements-txt-file` instead of
``pyproject.toml``.
