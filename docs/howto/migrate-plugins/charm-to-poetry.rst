.. _howto-migrate-to-poetry:

Migrate from the Charm plugin to the Poetry plugin
==================================================

Many charms use `Poetry`_ to manage their Python projects. For these charms, Charmcraft
has a :ref:`craft_parts_poetry_plugin`. Migrating from the Charm plugin provides some
benefits, such as no longer having to maintain a ``requirements.txt`` file. If the
charm to be migrated does not currently use poetry, refer to the
`Poetry documentation <https://python-poetry.org/docs/basic-usage/>`_ for instructions
on how to use poetry for a Python project.

Update the project file
-----------------------

The first step is to update the project file to include the correct parts definition.
Depending on the history of a specific charm, it may not have an explicitly-included
``parts`` section determining how to build the charm. In this case, a ``parts`` section
can be created as follows:

.. code-block:: yaml

    parts:
      my-charm:  # This can be named anything you want
        plugin: poetry
        source: .

Select compatible versions of ``pip`` and ``poetry``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Poetry plugin requires at least `pip 22.3
<https://pypi.org/project/pip/22.3>`_, released in October 2022. If the
charm's base uses an older version of pip, a newer version can be installed in the
build environment using a dependency part. Likewise, a charm may require a newer
version of Poetry than is available in the distribution's repositories. The following
``parts`` section can be used in place of the section above to upgrade pip and Poetry
for charms that build on Ubuntu 22.04 or earlier:

.. code-block:: yaml
    :emphasize-lines: 2-9,11

    parts:
      poetry-deps:
        plugin: nil
        build-packages:
          - curl
        override-build: |
          /usr/bin/python3 -m pip install pip==24.2
          curl -sSL https://install.python-poetry.org | python3 -
          ln -sf $HOME/.local/bin/poetry /usr/local/bin/poetry
      my-charm:  # This can be named anything you want
        after: [poetry-deps]
        plugin: poetry
        source: .

Add optional dependency groups
------------------------------

If the charm has `dependency groups`_ that should be included when creating the virtual
environment, the ``poetry-with`` key can be used to include those groups when creating
the virtual environment.

.. note::
    This is useful and encouraged, though not mandatory, for keeping track of
    library dependencies, as covered in the next section. For an example, see
    `postgresql-operator`_.

Include charm library dependencies
----------------------------------

Unlike the Charm plugin, the Poetry plugin does not install the dependencies for
included charmlibs. If any of the charm libraries used have PYDEPS, these will
need to be added to the charm's dependencies, potentially as their own
`dependency group <dependency groups_>`_.

To find these dependencies, check each library file for its ``PYDEPS``. A command
that can find these is::

    find lib -name "*.py" -exec awk '/PYDEPS = \[/,/\]/' {} +

If run from the base directory of a charm, this will show all the PYDEPS declarations
from all loaded charm libs.

Include extra files
-------------------

A Poetry plugin only includes the contents of the ``src`` and ``lib`` directories
as well as the generated virtual environment. If other files were previously included
from the main directory, they can be included again using the
:ref:`craft_parts_dump_plugin`:

.. code-block:: yaml
    :emphasize-lines: 5-9

    parts:
      my-charm:  # This can be named anything you want
        plugin: poetry
        source: .
      version-file:
        plugin: dump
        source: .
        stage:
          - charm_version


.. _dependency groups: https://python-poetry.org/docs/managing-dependencies/#dependency-groups
.. _Poetry: https://python-poetry.org
.. _postgresql-operator: https://github.com/canonical/postgresql-operator/blob/3c7c783d61d4bee4ce64c190a9f7d4a78048e4e7/pyproject.toml#L22-L35
