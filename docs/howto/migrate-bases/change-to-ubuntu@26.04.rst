.. _howto-change-to-ubuntu-26-04:

.. meta::
    :description: Learn how to migrate a charm to the Ubuntu 26.04 base in Charmcraft, including updating from the bases key to base and platforms keys.

Change to Ubuntu 26.04
======================

This guide describes the process for migrating a charm from an older base to Ubuntu 26.04.

Removed features
----------------

The charm plugin isn't available for the ``ubuntu@26.04`` base. Before changing the
base, follow one of the plugin migration guides:

- :ref:`howto-migrate-to-uv`
- :ref:`howto-migrate-to-python`
- :ref:`howto-migrate-to-poetry`

``bases`` key
-------------

Charms currently using Ubuntu 22.04 or older might use the ``bases`` key in
``charmcraft.yaml``. Charmcraft doesn't support this with Ubuntu 26.04, instead relying
on the ``base`` and ``platforms`` keys. The ``base`` key controls which Ubuntu release
the charm uses, while the ``platforms`` key decides the CPU architectures of both the
build machine and the production machine.

For a charm with a ``bases`` key as follows:

.. code-block:: yaml

    bases:
      - build-on:
          - name: ubuntu
            channel: "22.04"
        run-on:
          - name: ubuntu
            channel: "22.04"

Replace the ``bases`` key with:

.. code-block:: yaml

    base: ubuntu@26.04
    platforms:
      amd64:
      arm64:
      riscv64:
      s390x:

The :ref:`reference-platforms` has all the details about the ``platforms`` syntax,
including the grammar for specifying multiple bases and architectures.
