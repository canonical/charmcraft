.. _pack-a-reactive-charm-with-charmcraft:

How to pack a reactive charm with Charmcraft
==================================================

  Introduced in Charmcraft 1.4.


..  See also: -
..   {ref}\ ``How to set up a charm project <how-to-set-up-a-charm-project>``
..   -
..   {ref}\ ``How to pack your charm using Charmcraft <how-to-pack-a-charm>``
..   - {ref}\ ``About charm types, by creation type <charm-taxonomy>``

To pack a legacy reactive charm with Charmcraft, in the charm directory create a
``charmcraft.yaml`` file with the part definition for a reactive-based charm:

.. code-block:: yaml

   type: "charm"
   bases:
     - build-on:
         - name: "ubuntu"
           channel: "20.04"
       run-on:
         - name: "ubuntu"
           channel: "20.04"
   parts:
     charm:
       source: .
       plugin: reactive
       build-snaps: [charm]

Done. Now you can go ahead and pack your reactive-based charm with Charmcraft
in the usual way using ``charmcraft pack``.
