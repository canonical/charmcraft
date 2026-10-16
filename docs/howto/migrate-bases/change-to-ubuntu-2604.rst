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
part names. Part names on the Ubuntu 26.04 LTS base can't contain any forward slashes (/).
We recommend replacing them with a dot (.), for example:

.. code-block:: diff
    :caption: charmcraft.yaml

     base: ubuntu@26.04

     # ...

     parts:
    -  my/part:
    +  my.part:

Migrate a 12-factor app charm
-----------------------------

For a charm that uses a 12-factor framework extension, such as ``flask-framework``,
changing to Ubuntu 26.04 LTS also changes the contract that the extension generates.
See :ref:`extensions` for the differences. In addition:

- The extension is experimental on Ubuntu 26.04 LTS. Set
  ``CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=1`` when you expand or pack the charm.
- The extension generates the charm part with the uv plugin and the
  ``charmlibs-pydeps`` dependency group. Define that group in the ``pyproject.toml``
  file.
- ``charmcraft pack`` fails without a ``uv.lock`` file. Generate it with ``uv lock``
  and commit it with the project.

For the full upgrade procedure, including the rock and the application secret key, see
the `12-factor upgrade guide
<https://canonical.com/juju/docs/12-factor/latest/how-to/upgrade/>`__.
