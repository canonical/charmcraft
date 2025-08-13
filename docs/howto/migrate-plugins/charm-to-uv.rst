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
        build-snaps:
          - astral-uv

Include charm dependencies
--------------------------

Make sure that the project directory has a :ref:`pyproject-toml-file`. Use the
``dependencies`` key to list the dependencies of the charm code.

.. code-block:: toml
    :caption: pyproject.toml
    :emphasize-lines: 6-9

    [project]
    name = "my-charm"
    version = "0.0.1"
    requires-python = ">=3.10"

    # Dependencies of the charm code.
    dependencies = [
        "ops>=3,<4",
    ]

If you use ``uv add`` to include dependencies, uv updates the ``dependencies`` key in
``pyproject.toml``.

Include charm library dependencies
----------------------------------

Unlike the Charm plugin, the uv plugin does not install the dependencies for
included charmlibs. If any of the charm libraries used have ``PYDEPS``, these will
need to be added to the charm's dependencies.

To find library dependencies, check each loaded library file for its ``PYDEPS`` by
running the following command at the root of the charm project:

.. code-block:: bash

    find lib -name "*.py" -exec awk '/PYDEPS = \[/,/\]/' {} +

Next, in ``pyproject.toml``, list them in the ``dependencies`` key.

.. code-block:: toml
    :caption: pyproject.toml
    :emphasize-lines: 4-6

    # Dependencies of the charm code and PYDEPS from libraries.
    dependencies = [
        "ops>=3,<4",
        "cosl",
        "pydantic",
        "cryptography",
    ]

Alternatively, you could list the library dependencies in a
`dependency group <dependency groups_>`_ called ``charmlibs``.

.. code-block:: toml
    :caption: pyproject.toml

    [dependency-groups]
    # PYDEPS from libraries that the charm uses.
    charmlibs = [
        "cosl",
        "pydantic",
        "cryptography",
        "ops>=2.0.0",
    ]

Library dependencies are runtime dependencies, and dependency groups are generally
intended for development dependencies. However, if the charm uses a lot of library
files, you might find a dependency group helpful for distinguishing the dependencies.

If the charm uses libraries that are distributed as Python packages, list the libraries
in ``dependencies``, along with other dependencies of the charm code. You don't need to
inspect Python packages to find their dependencies.

Lock the dependencies
---------------------

After including dependencies, make sure that the project directory has a
:ref:`uv-lock-file`.

If you used ``uv add`` to include dependencies, uv created ``uv.lock``. Otherwise, run
``uv lock``.

Add dependency groups
---------------------

If the charm has dependency groups that should be included when creating the virtual
environment, such as one for charm libraries, the
:ref:`uv plugin's <craft_parts_uv_plugin>` ``uv-groups`` key can be set to include them:

.. code-block:: yaml
    :caption: charmcraft.yaml
    :emphasize-lines: 7-8

    parts:
      my-charm:
        plugin: uv
        source: .
        build-snaps:
          - astral-uv
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
    :emphasize-lines: 9-13

    parts:
      my-charm:
        plugin: uv
        source: .
        build-snaps:
          - astral-uv
        uv-groups:
          - charmlibs
      version-file:
        plugin: dump
        source: .
        stage:
          - charm_version


.. _dependency groups: https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-groups
.. _uv: https://docs.astral.sh/uv
