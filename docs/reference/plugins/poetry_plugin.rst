.. _craft_parts_poetry_plugin:

Poetry plugin
=============

The Poetry plugin can be used for Python charms written using `Poetry`_ and the
`Operator framework`_.

.. include:: /common/craft-parts/reference/plugins/poetry_plugin.rst
   :start-after: .. _craft_parts_poetry_plugin-keywords:
   :end-before: .. _craft_parts_poetry_plugin-environment_variables:

python-keep-bins
~~~~~~~~~~~~~~~~
**Type**: boolean
**Default**: False

Whether to keep python scripts in the virtual environment's ``bin`` directory.

.. include:: /common/craft-parts/reference/plugins/poetry_plugin.rst
   :start-after: .. _craft_parts_poetry_plugin-environment_variables:
   :end-before: .. _poetry-details-end:

How it works
------------

During the build step, the plugin performs the following actions:

1. It creates a virtual environment in the
   :ref:`${CRAFT_PART_INSTALL}/venv <craft_parts_step_execution_environment>` directory.
2. It uses :command:`poetry export` to create a ``requirements.txt`` in the project's
   build directory.
3. It uses :command:`pip` to install the packages referenced in ``requirements.txt``
   into the virtual environment. Undeclared dependencies are ignored.
4. It copies any existing ``src`` and ``lib`` directories from your charm project into
   the final charm.
5. It runs :command:`pip check` to ensure the virtual environment is consistent.

Example
-------

The following project file can be used with a poetry project to build
the charm for Ubuntu 24.04:

.. literalinclude:: poetry-charmcraft.yaml
   :language: yaml


.. _Poetry: https://python-poetry.org
.. _dependency groups: https://python-poetry.org/docs/managing-dependencies#dependency-groups
.. _environment variables to configure Poetry: https://python-poetry.org/docs/configuration/#using-environment-variables


.. include:: /common/craft-parts/reference/plugins/poetry_plugin.rst
    :start-after: .. _craft_parts_poetry_links:
