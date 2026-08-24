.. meta::
    :description: How to pack a charm located in a monorepo structure with shared dependencies.

.. _how-to-pack-a-charm-in-a-monorepo:
.. _pack-a-charm-in-a-monorepo:

How to pack a charm in a monorepo
=================================

By default, Charmcraft isolates the build environment to the directory containing
``charmcraft.yaml``. When building in managed environments (such as LXD containers or
virtual machines), files outside the charm's directory are not copied into the build
instance.

With experimental monorepo support enabled, Charmcraft detects the root of the enclosing
Git repository and mounts the entire repository into the build environment, allowing parts
to access parent and sibling directories.


Prerequisites
-------------

- A Git repository containing your charm and shared assets.
- Charmcraft 4.5 or higher.


Example repository layout
-------------------------

Consider a monorepo structured as follows:

.. code-block:: text

    my-monorepo/
    ├── .git/
    ├── shared/
    │   ├── pyproject.toml
    │   └── common/
    │       └── utils.py
    └── charms/
        └── my-charm/
            ├── charmcraft.yaml
            ├── pyproject.toml
            └── src/
                └── charm.py


Configure charmcraft.yaml
-------------------------

When a charm is located in a subdirectory of a repository, configure the charm part in
``charmcraft.yaml`` to set the ``source`` key to the repository root (or parent directory)
and use the ``source-subdir`` key to point to the charm directory:

.. code-block:: yaml
    :caption: charms/my-charm/charmcraft.yaml

    name: my-charm
    type: charm
    base: ubuntu@24.04
    build-base: ubuntu@24.04
    platforms:
      amd64:

    parts:
      my-charm:
        plugin: uv
        source: ../..
        source-subdir: charms/my-charm


.. note::

    If you want a top-level ``charmcraft.yaml`` file at the repository root with the charm source located in a subdirectory, you can use ``source-subdir`` on the charm part directly without enabling experimental monorepo mode.


In your charm's ``pyproject.toml``, you can then reference shared local dependencies using
relative paths:

.. code-block:: toml
    :caption: charms/my-charm/pyproject.toml

    [project]
    name = "my-charm"
    version = "0.1.0"
    dependencies = [
        "ops",
        "common",
    ]

    [tool.uv.sources]
    common = { path = "../../shared" }


Pack the charm
--------------

To pack the charm using the monorepo root as the build root, set the
``CHARMCRAFT_EXPERIMENTAL_MONOREPO`` environment variable when invoking
``charmcraft pack``:

.. code-block:: bash

    cd charms/my-charm/
    CHARMCRAFT_EXPERIMENTAL_MONOREPO=1 charmcraft pack

Charmcraft will mount the root of the Git repository into the build instance and build the
charm with access to the shared files.
