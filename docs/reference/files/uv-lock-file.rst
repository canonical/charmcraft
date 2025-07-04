.. _uv-lock-file:


``uv.lock`` file
================

The ``uv.lock`` file in your charm's root directory specifies the exact versions of
your charm's dependencies and your development dependencies.

.. seealso::

    `uv | The lockfile
    <https://docs.astral.sh/uv/concepts/projects/layout/#the-lockfile>`_

This file is required if your charm uses the :ref:`craft_parts_uv_plugin`. It's also
required if you use tox with tox-uv. For more information, see :ref:`tox-ini-file`.

When a charm is initialized with the Kubernetes or machine profile, Charmcraft creates
this file.

If you change your charm's dependencies, use ``uv lock`` to update this file.
Alternatively, you can update this file by using ``uv add`` and ``uv remove`` to manage
dependencies in the :ref:`pyproject-toml-file`.

You shouldn't manually edit this file.

For the 12-factor app profiles, this file isn't necessary. Dependencies are specified
in the :ref:`requirements-txt-file` instead of ``pyproject.toml``.
