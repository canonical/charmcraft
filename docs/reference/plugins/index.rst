.. _plugins:

Plugins
=======

Most charms only need one, maybe two parts, typically consisting of one of Charmcraft's
application-specific plugins such as the `charm plugin`_ or the `reactive plugin`_ and
potentially the addition of further files using the :ref:`craft_parts_dump_plugin`.

.. warning::
   Other plugins are available from :external+craft-parts:ref:`craft-parts <plugins>`,
   but these are unsupported in Charmcraft and should be used with caution.

   These plugins may significantly increase the size of a packed charm, and they may
   not work as intended. Please file a `feature request`_ in Charmcraft if you have a
   use case for another craft-parts upstream plugin.

.. toctree::
    :maxdepth: 1

    /common/craft-parts/reference/plugins/dump_plugin
    /common/craft-parts/reference/plugins/nil_plugin
    python_plugin
    poetry_plugin
    uv_plugin

.. _charm plugin: https://juju.is/docs/sdk/charmcraft-yaml#heading--the-charm-plugin
.. _reactive plugin: https://juju.is/docs/sdk/charmcraft-yaml#heading--the-reactive-plugin
