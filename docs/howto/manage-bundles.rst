.. _manage-charm-bundles:

Manage charm bundles
====================

    See first: :external+juju:ref:`Juju | Bundle <bundle>`

.. important::
    Bundles are being phased out. Starting on 1 Jan 2025, new bundles can no longer
    be registered on `Charmhub`_.


Create a bundle
---------------

To create a bundle, create a ``<bundle>.yaml`` file with your desired configuration.

    See more: :ref:`bundle-yaml-file`

.. tip::
    If you don't want to start from scratch, export the contents of your model to a
    ``<bundle>.yaml`` file via ``juju export-bundle --filename <bundle>.yaml`` or
    download the ``<bundle>.yaml`` of an existing bundle from Charmhub.
    See more: :external+juju:ref:`Juju | Compare and export the contents of a model to
    a bundle <export-model-to-bundle>`.

Pack a bundle
-------------

To pack a bundle, in the directory where you have your ``bundle.yaml`` file (and
possibly other files, e.g., a ``README.md`` file), create a ``charmcraft.yaml`` file
suitable for a bundle (at the minimum: ``type: bundle``), then run ``charmcraft pack``
to pack the bundle. The result is a ``.zip`` file.

    See more: :ref:`ref_commands_pack`


Publish a bundle on Charmhub
----------------------------

The process is identical to that for a simple charm except that, at the step where you
register the name, for bundles the command is ``register-bundle``.

    See more: :ref:`publish-a-charm`
