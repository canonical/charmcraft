.. _plugins:

Plugins
=======

Plugins determine a part's build behavior. In Charmcraft, they are used to manage Python
environments and manipulate files.

.. admonition:: Unsupported plugins
    :class: important

    The additional plugins in :external+craft-parts:ref:`Craft Parts <plugins>` aren't
    supported in Charmcraft and should be used with caution.

    These plugins can significantly increase the size of a packed charm and may not work
    as intended. Please file a `feature request`_ in Charmcraft if you have a use case
    for another of the Craft Parts plugins.

- :ref:`craft_parts_python_plugin`
- :ref:`craft_parts_poetry_plugin`
- :ref:`craft_parts_uv_plugin`
- :ref:`craft_parts_dump_plugin`
- :ref:`craft_parts_nil_plugin`


.. toctree::
    :hidden:

    /common/craft-parts/reference/plugins/dump_plugin
    /common/craft-parts/reference/plugins/nil_plugin
    python_plugin
    poetry_plugin
    uv_plugin
