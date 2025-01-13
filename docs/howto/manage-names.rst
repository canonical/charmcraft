.. _manage-names:

Manage names
============


.. _register-a-name:

Register a name on Charmhub
---------------------------

To register a name for your charm on Charmhub, use the ``charmcraft register`` command
followed by your desired name. E.g.,

.. code-block:: bash

   charmcraft register my-awesome-charm

..

   See more: :ref:`ref_commands_register`

This also automatically creates four channels, all with track ``latest`` but risk level
``edge``, ``beta``, ``candidate``, and ``stable``, respectively.

   See more: :ref:`manage-channels`


View registered names
---------------------

To view the names you've registered on Charmhub, run ``charmcraft names``.

   See more: :ref:`ref_commands_names`


Unregister a name
-----------------

.. caution::

    A name can be unregistered only if you haven't yet uploaded anything to it.

To unregister a name, run ``charmcraft unregister`` followed by the name.

    See more: :ref:`ref_commands_unregister`
