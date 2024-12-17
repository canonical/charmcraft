.. _craft_parts_uv_plugin:

uv plugin
=========

The uv plugin can be used for Python charms written using `uv`_ and the
`Operator framework`_.

.. include:: /common/craft-parts/reference/plugins/poetry_plugin.rst
    :start-after: .. _craft_parts_uv_plugin-keywords:
    :end-before: .. _craft_parts_uv_plugin-environment_variables:

python-keep-bins
~~~~~~~~~~~~~~~~
**Type**: boolean
**Default**: False

Whether to keep Python scripts in the virtual environment's :file:`bin`
directory.

.. include:: /common/craft-parts/reference/plugins/uv_plugin.rst
    :start-after: .. _craft_parts_poetry_plugin-environment_variables:
    :end-before: .. _uv-details-end:

How it works
------------

During the build step, the plugin performs the following actions:

#. It creates a virtual environment in the
   :ref:`${CRAFT_PART_INSTALL}/venv <craft_parts_step_execution_environment>`
   directory.
#. It uses :command:`uv sync` to install the packages referenced in the
   :file:`pyproject.toml` and :file:`uv.lock` files, along with any optional
   groups or extras specified.
#. It copies any existing :file:`src` and :file:`lib` directories from your
   charm project into the final charm.

Example
-------

The following :file:`charmcraft.yaml` file can be used with a uv project to
build the charm for Ubuntu 24.04:

.. literalinclude:: uv-charmcraft.yaml
    :language: yaml


.. _uv: https://docs.astral.sh/uv/
