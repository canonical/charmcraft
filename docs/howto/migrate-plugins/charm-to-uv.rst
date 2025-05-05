.. _howto-migrate-to-uv:

Migrate from the Charm plugin to the uv plugin
==============================================

For charms that use `uv`_, Charmcraft has a :ref:`craft_parts_uv_plugin`. This guide
shows how to migrate from the default Charm plugin to the uv plugin.

Migrating from the Charm plugin provides some benefits, notably not having to maintain a
separate ``requirements.txt`` file. For package management, uv is much faster than pip.

If the charm to be migrated does not currently use uv, refer to the
`uv documentation <https://docs.astral.sh/uv/guides/projects/>`_ for instructions on
how to use uv for a Python project.

Update the project file
-----------------------

The first step is to update the project file to include the correct parts definition.
Depending on the history of a specific charm, it may not have an explicitly-included
``parts`` section determining how to build the charm. In this case, a ``parts`` section
can be created as follows:

.. code-block:: yaml
    :caption: charmcraft.yaml

    parts:
      my-charm:  # This can be named anything you want
        plugin: uv
        source: .

Include charm library dependencies
----------------------------------

Unlike the Charm plugin, the uv plugin does not install the dependencies for
included charmlibs. If any of the charm libraries used have ``PYDEPS``, these will
need to be added to the charm's dependencies, potentially as their own
`dependency group <dependency groups_>`_.

To find these dependencies, check each loaded library file for its ``PYDEPS`` by running
the following command at the root of the charm project:

.. code-block:: bash

    find lib -name "*.py" -exec awk '/PYDEPS = \[/,/\]/' {} +

Next, in ``pyproject.toml``, list them in a ``charmlibs`` dependency group.

.. code-block:: toml
    :caption: pyproject.toml

    [dependency-groups]
    # Dependencies brought from libraries the charm uses.
    charmlibs = [
        "cosl",
        "pydantic",
        "cryptography",
        "ops>=2.0.0",
    ]

Add dependency groups
---------------------

If the charm has dependency groups that should be included when creating the virtual
environment, such as one for charm libraries, the
:ref:`uv plugin's <craft_parts_uv_plugin>` ``uv-groups`` key can be set to include them:

.. code-block:: yaml
    :caption: charmcraft.yaml
    :emphasize-lines: 5-6

    parts:
      my-charm:
        plugin: uv
        source: .
        uv-groups:
          - charmlibs

Likewise, optional dependencies under the ``pyproject.toml`` key
``project.optional-dependencies`` can be added with the ``uv-extras`` key.

Include extra files
-------------------

The uv plugin only includes the contents of the ``src`` and ``lib`` directories
as well as the generated virtual environment. If other files were previously included
from the main directory, they can be included again using the
:ref:`craft_parts_dump_plugin`:

.. code-block:: yaml
    :caption: charmcraft.yaml
    :emphasize-lines: 7-11

    parts:
      my-charm:
        plugin: uv
        source: .
        uv-groups:
          - charmlibs
      version-file:
        plugin: dump
        source: .
        stage:
          - charm_version


.. _dependency groups: https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-groups
.. _uv: https://docs.astral.sh/uv
