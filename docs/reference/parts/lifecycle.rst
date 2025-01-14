.. _lifecycle:

Lifecycle details
=================

Each part is built in :ref:`four separate steps <craft_parts_steps>`, each with
its own input and output locations:

#. ``PULL`` — The source and external dependencies (such as package
   dependencies) for the part are retrieved from their stated location and
   placed into a package cache area.
#. ``BUILD`` — The part is built according to the particular part plugin and
   build override.
#. ``STAGE`` — The specified outputs from the ``BUILD`` step are copied into
   a unified staging area for all parts.
#. ``PRIME`` — The specified files are copied from the staging area to the
   priming area for use in the final payload. This is distinct from ``STAGE``
   in that the ``STAGE`` step allows files that are used in the ``BUILD`` steps
   of dependent parts to be accessed, while the ``PRIME`` step occurs after all
   parts have been staged.

.. note::
   While craft-parts offers an ``OVERLAY`` step as well, charmcraft does not use it.
   This is a distinction between how Charmcraft and `Rockcraft`_ work.


Step order
----------

While each part's steps are guaranteed to run in the order above, they are
not necessarily run immediately following each other, especially if multiple
parts are included in a project. While specifics are implementation-dependent,
the general rules for combining parts are:

#. ``PULL`` all parts before running further steps.
#. ``BUILD`` any unbuilt parts whose dependencies have been staged. If a part
   has no dependencies, this part is built in the first iteration.
#. ``STAGE`` any newly-built parts.
#. Repeat the ``BUILD`` and ``STAGE`` steps until all parts have been staged.
#. ``PRIME`` all parts.


Further Information
-------------------

Further information can be found in the `Craft-parts`_ documentation.
