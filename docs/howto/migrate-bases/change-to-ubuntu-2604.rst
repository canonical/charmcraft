.. _howto-change-to-ubuntu-26-04:

.. meta::
    :description: How to migrate a charm to the Ubuntu 26.04 LTS base in Charmcraft, including using the new platform definitions.

Change to the Ubuntu 26.04 LTS base
===================================

This guide describes the process for migrating a charm from a lower base to Ubuntu 26.04 LTS.

.. _howto-change-to-ubuntu-26-04-12-factor:

Migrate a 12-factor charm
-------------------------

Ubuntu 26.04 LTS uses the experimental version of each 12-factor Charmcraft extension.
Changing only the ``base`` key, or running ``charmcraft pack``, applies parts of the new
extension but can't convert the complete project contract.

Generate a clean project from the Ubuntu 26.04 LTS profile in a temporary directory.
Replace ``<framework>`` with ``django``, ``expressjs``, ``fastapi``, ``flask``, ``go``,
or ``spring-boot``:

.. code-block:: bash

    mkdir /tmp/charmcraft-26-04-profile
    cd /tmp/charmcraft-26-04-profile
    CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=1 charmcraft init --profile <framework>-framework --base ubuntu@26.04

Don't run the command in the existing charm directory. The init command doesn't
overwrite existing files, so it can't safely update an existing project in place.

Merge the generated project files into the existing charm. Carry over the following
generated contract:

* The uv charm part and generated uv project files.
* The ``app`` workload container and ``app-image`` resource.
* The ``peers`` peer relation with the ``peers`` interface.
* One ``app-secret-key`` configuration option with the ``secret`` type.
* The ``paas-charm>=2.0.dev1,<3`` dependency and the generated charmlibs interface
  dependencies for OAuth, OpenFGA, and tracing. These PyPI packages replace the
  corresponding libraries fetched from Charmhub in the generated project.
* A Valkey relation instead of the obsolete Redis relation.
* The optional ``paas-config.yaml`` file when the app needs runtime customization.

Preserve the existing charm's app-specific metadata, configuration, actions, and
relations while merging. The :ref:`extension contract reference <extensions>` compares
the generated contracts for lower bases and Ubuntu 26.04 LTS.

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
We recommend replacing them with a dot (.), for example:

.. code-block:: diff
    :caption: charmcraft.yaml

     base: ubuntu@26.04

     # ...

     parts:
    -  my/part:
    +  my.part:
