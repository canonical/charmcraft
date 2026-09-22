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

.. _howto-change-to-ubuntu-26-04-12-factor:

Migrate a 12-factor app charm to V2
-----------------------------------

Changing the base of a 12-factor app charm from Ubuntu 22.04 LTS or Ubuntu 24.04 LTS
to Ubuntu 26.04 LTS selects the experimental V2 framework extension. The migration
is not automatic.

#. Replace the ``bases`` key with ``base: ubuntu@26.04`` and a ``platforms`` mapping.
#. Replace the Charm plugin and ``requirements.txt`` dependency workflow with the uv
   plugin, ``pyproject.toml``, and a committed ``uv.lock`` file.
#. Require ``paas-charm>=2.0.dev0,<3``. Stable paas-charm 1.x implements the V1
   metadata and workload contract and is not compatible with V2.
#. Update generated metadata to use the ``app`` container, ``app-image`` resource,
   and a ``peers`` relation with the ``peers`` interface.
#. Replace the V1 string and secret-ID options with one ``app-secret-key`` option of
   type ``secret``. For Flask and Django, this also removes the framework prefix.
#. If the charm uses :ref:`paas-config-yaml-file`, verify its top-level V2 keys and
   values before packing.
#. Build the workload with the matching experimental Ubuntu 26.04 LTS Rockcraft
   framework extension. In particular, the Flask and Django V2 images place the
   workload under ``/app``.
#. Set ``CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=1`` when expanding or packing
   the charm.

Run ``uv lock`` after updating ``pyproject.toml``:

.. code-block:: bash

    uv lock

Then inspect the expanded metadata before packing:

.. code-block:: bash

    CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=1 charmcraft expand-extensions

The `12-factor app support documentation
<https://canonical.com/juju/docs/12-factor/>`__ describes paas-charm runtime
semantics. The `Rockcraft extension reference
<https://documentation.ubuntu.com/rockcraft/latest/reference/extensions/>`__
describes the matching workload-image extensions.

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
