.. _part:
.. _parts:

Parts
=====

Parts are most commonly used with the :ref:`Python <craft_parts_python_plugin>`,
:ref:`Poetry <craft_parts_poetry_plugin>`, and :ref:`uv <craft_parts_uv_plugin>` plugins
to manage a charm's Python environment, but they can also add additional files with
parts using the :ref:`craft_parts_dump_plugin`.

- :ref:`reference-part-properties`
- :ref:`craft_parts_step_execution_environment`
- :ref:`lifecycle`
- :ref:`filesets_explanation`


Plugins
-------

Plugins determine a part's build behavior. In Charmcraft, they are used to manage Python
environments and manipulate files.

- :ref:`craft_parts_python_plugin`
- :ref:`craft_parts_poetry_plugin`
- :ref:`craft_parts_uv_plugin`
- :ref:`craft_parts_dump_plugin`
- :ref:`craft_parts_nil_plugin`

.. toctree::
   :hidden:

   /common/craft-parts/reference/part_properties
   /common/craft-parts/reference/parts_steps
   /common/craft-parts/reference/step_execution_environment
   /common/craft-parts/explanation/filesets
   lifecycle
   ../plugins/index
