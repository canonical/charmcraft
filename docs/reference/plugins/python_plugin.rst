.. _craft_parts_python_plugin:

Python plugin
=============

The Python plugin can be used for charms written in Python, typically for charms
using the `Operator framework`_.

.. include:: /common/craft-parts/reference/plugins/python_plugin.rst
   :start-after: .. _craft_parts_python_plugin-keywords:
   :end-before: .. _craft_parts_python_plugin-environment_variables:

python-keep-bins
~~~~~~~~~~~~~~~~
**Type**: boolean
**Default**: False

Whether to keep python scripts in the virtual environment's ``bin`` directory.

.. include:: /common/craft-parts/reference/plugins/python_plugin.rst
   :start-after: .. _craft_parts_python_plugin-environment_variables:
   :end-before: .. _python-details-begin:

Dependencies
------------

This plugin creates a Python virtual environment in the ``venv`` directory of your
charm using the version of Python included with your base, using the requirements files
provided in the ``python-requirements`` keyword.

.. note::
   The python plugin prevents :command:`pip` from installing dependencies for the
   required packages. Therefore, requirements must include indirect dependencies as
   well as direct dependencies. It is recommended that you use a tool such as
   :command:`pip-compile` or :command:`uv` to manage the contents of your
   ``requirements.txt`` file.

How it works
------------

During the build step, the plugin performs the following actions:

1. It creates a virtual environment in the
   :ref:`${CRAFT_PART_INSTALL}/venv <craft_parts_step_execution_environment>`
   directory.
2. It uses :command:`pip` to install the required Python packages as configured
   in the ``python-requirements``, ``python-constraints`` and ``python-packages``
   keywords.
3. It copies the ``src`` and ``lib`` directories from your charm project into the
   final charm if they exist.


Example
-------

The following ``charmcraft.yaml`` file can be used with a standard charm structure
to build a charm for Ubuntu 24.04:

.. literalinclude:: python-charmcraft.yaml
   :language: yaml


