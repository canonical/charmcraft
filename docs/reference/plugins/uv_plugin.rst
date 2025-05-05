.. _craft_parts_uv_plugin:

uv plugin
=========

    See also: :ref:`howto-migrate-to-uv`

The uv plugin is designed for Python charms that use `uv`_ as the build system
and are written with the `Operator framework`_.

.. include:: /common/craft-parts/reference/plugins/uv_plugin.rst
    :start-after: .. _craft_parts_uv_plugin-keywords:
    :end-before: .. _craft_parts_uv_plugin-environment_variables:

python-keep-bins
~~~~~~~~~~~~~~~~
**Type**: boolean
**Default**: False

Whether to keep Python scripts in the virtual environment's :file:`bin`
directory.

.. include:: /common/craft-parts/reference/plugins/uv_plugin.rst
    :start-after: .. _craft_parts_uv_plugin-environment_variables:
    :end-before: .. _uv-details-end:

How it works
------------

During the build step, the plugin performs the following actions:

#. It creates a virtual environment in the
   :ref:`${CRAFT_PART_INSTALL}/venv <craft_parts_step_execution_environment>`
   directory.
#. It runs :command:`uv sync` to install the packages referenced in the
   :file:`pyproject.toml` and :file:`uv.lock` files, along with any optional
   groups or extras specified.
#. It copies any existing :file:`src` and :file:`lib` directories from your
   charm project into the final charm.

Example
-------

The following project file can be used with a uv project to
craft a charm with Ubuntu 24.04 as its base:

.. literalinclude:: uv-charmcraft.yaml
    :language: yaml


.. _uv: https://docs.astral.sh/uv/
