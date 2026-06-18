.. _manage-names:

Manage names
============

This guide shows how to register, view, and unregister names on Charmhub.

.. _register-a-name:

Register a name on Charmhub
---------------------------

To register a name for your charm on Charmhub, run
:ref:`charmcraft register <ref_commands_register>`:

.. code-block:: bash

   charmcraft register my-awesome-charm

This also automatically creates four channels, all with track ``latest`` but risk level
``edge``, ``beta``, ``candidate``, and ``stable``, respectively. To learn
how to manage channels, visit :ref:`manage-channels`.

View registered names
---------------------

To view the names you've registered on Charmhub, run
:ref:`charmcraft names <ref_commands_names>`.

Unregister a name
-----------------

To unregister a name, run :ref:`charmcraft unregister <ref_commands_unregister>`
followed by the name.

.. caution::

    A name can be unregistered only if you haven't yet uploaded anything to it.
