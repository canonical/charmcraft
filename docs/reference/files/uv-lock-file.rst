.. _uv-lock-file:


``uv.lock`` file
================

The ``uv.lock`` file in your charm's root directory is a lockfile that specifies the
exact versions of your charm's dependencies and your development dependencies.

    See more: `uv |
    The lockfile
    <https://docs.astral.sh/uv/concepts/projects/layout/#the-lockfile>`_

This file is required if your charm uses the :ref:`craft_parts_uv_plugin`. It's also
required if you use tox with tox-uv. For more information, see :ref:`tox-ini-file`.

Charmcraft doesn't create this file when you run the :ref:`ref_commands_init` command.

For ``init`` with the ``kubernetes`` or ``machine`` profile, you should create this
file by running ``uv lock``. Alternatively, you can create/update this file by using
``uv add`` and ``uv remove`` to manage dependencies in the :ref:`pyproject-toml-file`.

You shouldn't manually edit this file.

For ``init`` with a 12-factor profile (``django-framework`` and so on), this file isn't
necessary. Dependencies are specified in the :ref:`requirements-txt-file` instead of
``pyproject.toml``.
