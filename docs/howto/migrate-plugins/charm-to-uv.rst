.. _howto-migrate-to-uv:

Migrate from the Charm plugin to the uv plugin
==============================================

For charms that use `uv`_, Charmcraft has a :ref:`craft_parts_uv_plugin`. Migrating
from the Charm plugin provides some benefits, such as using uv during the build
process not having to maintain a separate ``requirements.txt`` file. If the
charm to be migrated does not currently use uv, refer to the
`uv documentation <https://docs.astral.sh/uv/guides/projects/>`_ for instructions
on how to use uv for a Python project.

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

Add optional dependency groups
------------------------------

If the charm has `dependency groups`_ that should be included when creating the virtual
environment, the ``uv-groups`` key can be used to include those groups when creating
the virtual environment.

.. note::
    This is useful and encouraged, though not mandatory, for keeping track of
    library dependencies, as covered in the next section.

Include charm library dependencies
----------------------------------

Unlike the Charm plugin, the uv plugin does not install the dependencies for
included charmlibs. If any of the charm libraries used have ``PYDEPS``, these will
need to be added to the charm's dependencies, potentially as their own
`dependency group <dependency groups_>`_.

To find these dependencies, check each library file for its ``PYDEPS``. A command
that can find these is::

    find lib -name "*.py" -exec awk '/PYDEPS = \[/,/\]/' {} +

If run from the base directory of a charm, this will show all the PYDEPS declarations
from all loaded charm libs. These can then be included in ``pyproject.toml``.

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

Including this dependency group is as easy as adding it to ``charmcraft.yaml``:

.. code-block:: yaml
    :caption: charmcraft.yaml
    :emphasize-lines: 5-6

    parts:
      my-charm:
        plugin: uv
        source: .
        uv-groups:
          - charmlibs

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
