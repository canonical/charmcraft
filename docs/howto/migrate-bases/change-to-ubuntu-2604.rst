.. _howto-change-to-ubuntu-26-04:

.. meta::
    :description: How to migrate a charm to the Ubuntu 26.04 LTS base in Charmcraft, including using the new platform definitions.

Change to the Ubuntu 26.04 LTS base
===================================

This guide describes the process for migrating a charm from a lower base to Ubuntu 26.04 LTS.

Migrate from the charm plugin
-----------------------------

The Charm plugin isn't available for the Ubuntu 26.04 LTS base. If your charm uses it,
switch to one of the replacement plugins:

- :ref:`howto-migrate-to-uv`
- :ref:`howto-migrate-to-python`
- :ref:`howto-migrate-to-poetry`

Update the base
---------------

Charms built with Ubuntu 22.04 LTS or lower might use the ``bases`` key in their project
file. This key is not supported by the Ubuntu 26.04 LTS base and must be replaced with
the ``base`` and ``platforms`` keys. The ``base`` key declares which Ubuntu release the
charm uses, while the ``platforms`` key declares the CPU architectures of the build and
production machines.

For a charm with a ``bases`` key as follows:

.. code-block:: yaml
    :caption: charmcraft.yaml

    bases:
      - build-on:
          - name: ubuntu
            channel: "22.04"
        run-on:
          - name: ubuntu
            channel: "22.04"

Replace the ``bases`` key with:

.. code-block:: yaml
    :caption: charmcraft.yaml

    base: ubuntu@26.04
    platforms:
      amd64:
      arm64:
      riscv64:
      s390x:

:ref:`reference-platforms` has all the details about the ``platforms`` key,
including the syntax for specifying multiple bases and architectures.

Update part names
-----------------

If you update a charm to use the Ubuntu 26.04 LTS base, then you must also verify its
part names. Part names on 26.04 and later bases can't contain any forward slashes (/).
We recommend replacing them with a hyphen (-):

.. code-block:: diff
    :caption: charmcraft.yaml

     base: ubuntu@26.04

     # ...

     parts:
    -  my/part:
    +  my-part:
