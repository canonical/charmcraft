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

List the charm's dependencies
-----------------------------

If the project directory doesn't already contain a :ref:`pyproject-toml-file`, create
one. Next, list the charm's dependencies in the file's ``dependencies`` key.

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

You can also add dependencies to your project's ``pyproject.toml`` file by running:

.. code-block:: bash

    uv add <dependency>

List charm library dependencies
-------------------------------

Charm libraries are distributed either as regular Python packages under the
`charmlibs <https://documentation.ubuntu.com/charmlibs>`_ namespace, or hosted on
Charmhub. Python packages should be listed in the charm's dependencies.

Unlike the Charm plugin, the uv plugin does not install transitive dependencies for
Charmhub-hosted libraries. If any of these charm libraries have ``PYDEPS``, these need
to be added to the charm's dependencies.

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
`dependency group <dependency groups_>`_ called ``charmlibs-pydeps``.

.. code-block:: toml
    :caption: pyproject.toml

    [dependency-groups]
    # PYDEPS from libraries that the charm uses.
    charmlibs-pydeps = [
        "cosl",
        "pydantic",
        "cryptography",
    ]

To add a dependency to the ``charmlibs-pydeps`` dependency group using ``uv add``, run:

.. code-block:: bash

    uv add --group charmlibs-pydeps <dependency>

Library dependencies are runtime dependencies, and dependency groups are generally
intended for development dependencies. However, if the charm uses a lot of library
files, you might find a dependency group helpful for distinguishing the dependencies.

This advice doesn't apply to libraries that are distributed as Python packages. You
should list Python packages in ``dependencies``. You don't need to do anything further
for their transitive dependencies to be properly installed.

Lock the dependencies
---------------------

After defining the project's dependencies, make sure that the project directory has a
:ref:`uv-lock-file` by running:

.. code-block:: bash

    uv lock

Make sure you add this file to version control, so that your charm can be built after a
checkout by running ``charmcraft pack``.

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
          - charmlibs-pydeps

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
          - charmlibs-pydeps
      version-file:
        plugin: dump
        source: .
        stage:
          - charm_version


.. _dependency groups: https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-groups
.. _uv: https://docs.astral.sh/uv
