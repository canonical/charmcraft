Rotating the generated secret key
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The extension adds the ``rotate-secret-key`` action to the charm. When the secret key
option isn't set, run the action on the leader unit to generate a new random key:

.. code-block:: bash

    juju run <LEADER_UNIT> rotate-secret-key

The action fails on units that aren't the leader. Rotating the key invalidates any
sessions signed with the previous key. The action doesn't change a key that you set
through the secret key option. To rotate that key, update its value instead.

