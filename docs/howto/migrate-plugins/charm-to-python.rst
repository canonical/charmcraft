.. _howto-migrate-to-python:

Migrate from the Charm plugin to the Python plugin
==================================================

The Python plugin in Charmcraft offers a faster, stricter means of packing an operator
charm with a virtual environment. This guide shows how to migrate from a charm using
the default Charm plugin to using the Python plugin.

Update the project file
-----------------------

The first step is to update the project file to include the correct parts definition.
Depending on the history of a specific charm, it may not have an explicitly-included
``parts`` section determining how to build the charm. In this case, a ``parts`` section
can be created as follows:

.. code-block:: yaml

    parts:
      my-charm:  # This can be named anything you want
        plugin: python
        source: .
        python-requirements:
          - requirements.txt  # Or whatever your requirements file is called.

Select a compatible version of ``pip``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Python plugin requires at least `pip 22.3`_, released in October 2022. If the
charm's base uses an older version of pip, a newer version can be installed in the
build environment using a dependency part. The following ``parts`` section can be
used in place of the section above to upgrade pip for charms that build on Ubuntu
22.04 or earlier:

.. code-block:: yaml
    :emphasize-lines: 2-5,7

    parts:
      python-deps:
        plugin: nil
        override-build: |
          /usr/bin/python3 -m pip install pip==24.2
      my-charm:  # This can be named anything you want
        after: [python-deps]
        plugin: python
        source: .
        python-requirements:
          - requirements.txt  # Or whatever your requirements file is called.

Flatten ``requirements.txt``
----------------------------

One difference between the Python plugin and the Charm plugin is that the Python
plugin does not install dependencies, so the ``requirements.txt`` file must be a
complete set of packages needed in the charm's virtual environment.

.. note::
    There are several tools for creating an exhaustive ``requirements.txt`` file.
    Charmcraft works with any as long as it generates a requirements file that ``pip``
    understands. Because different versions of packages may have different
    dependencies, it is recommended that the requirements file be generated using a
    tool that will lock the dependencies to specific versions.
    A few examples include:

    - `uv export <https://docs.astral.sh/uv/reference/cli/#uv-export>`_
    - `pip-compile <https://pip-tools.readthedocs.io/en/stable/cli/pip-compile/>`_
    - `pip freeze <https://pip.pypa.io/en/stable/cli/pip_freeze/>`_

A basic ``requirements.txt`` file for a charm with no dependencies other than the
Operator framework may look something like::

    ops==2.17.0
    pyyaml==6.0.2
    websocket-client==1.8.0

To check that the virtual environment for the charm would be valid, activate an
empty virtual environment and then run::

    pip install --no-deps -r requirements.txt
    pip check

Include charm library dependencies
----------------------------------

Unlike the Charm plugin, the Python plugin does not install the dependencies
for included charmlibs. If any of the charm libraries used have PYDEPS, these will
need to be added to a requirements file as well.

.. note::
    All requirements files are included in the same ``pip`` command to prevent
    conflicting requirements from overriding each other. However, this means
    that a charm will fail to build if it has conflicting requirements. A single
    ``requirements.txt`` file, while not mandatory, is recommended.

To find these dependencies, check each library file for its ``PYDEPS``. A command
that can find these is::

    find lib -name "*.py" -exec awk '/PYDEPS = \[/,/\]/' {} +

If run from the base directory of a charm, this will show all the PYDEPS declarations
from all loaded charm libs, which can be used to help generate the input for a tool
that generates ``requirements.txt``.

Include extra files
-------------------

The Python plugin only includes the contents of the ``src`` and ``lib`` directories
as well as the generated virtual environment. If other files were previously included
from the main directory, they can be included again using the
:ref:`craft_parts_dump_plugin`:

.. code-block:: yaml
    :emphasize-lines: 7-11

    parts:
      my-charm:  # This can be named anything you want
        plugin: python
        source: .
        python-requirements:
          - requirements.txt  # Or whatever your requirements file is called.
      version-file:
        plugin: dump
        source: .
        stage:
          - charm_version


.. _pip 22.3: https://pip.pypa.io/en/stable/news/#v22-3
