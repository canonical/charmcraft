.. meta::
    :description: Reference for Charmcraft extensions, including how the Ubuntu base shapes the contract generated for 12-factor app frameworks.

.. _extensions:

Extensions
==========

Extensions initialize your project with YAML and Ops catered to supported web
frameworks. They each have a corresponding :ref:`profiles <profile>` that you use
when initializing your project.

- :ref:`django-framework-extension`
- :ref:`expressjs-framework-extension`
- :ref:`fastapi-framework-extension`
- :ref:`flask-framework-extension`
- :ref:`go-framework-extension`
- :ref:`spring-boot-framework-extension`

12-factor extension behavior by base
------------------------------------

The Ubuntu base selects the contract that a 12-factor framework extension generates.
There is no version key in ``charmcraft.yaml``.

* Ubuntu 22.04 LTS and Ubuntu 24.04 LTS generate the established contract, where the
  framework supports the base.
* Ubuntu 26.04 LTS generates an experimental contract. It requires
  ``CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=1`` when Charmcraft expands or packs the
  project. Charmcraft doesn't require the environment variable for lower bases.

Rockcraft has its own extension stability and environment variable. In particular, its
Spring Boot extension on Ubuntu 24.04 LTS remains experimental. The
:ref:`Spring Boot tutorial <write-your-first-kubernetes-charm-for-a-spring-boot-app>`
shows the required Rockcraft setting.

On Ubuntu 26.04 LTS, all six framework extensions generate the following contract:

.. list-table::
    :header-rows: 1

    * - Generated field
      - Ubuntu 22.04 LTS and 24.04 LTS
      - Ubuntu 26.04 LTS
    * - Charm part plugin
      - ``charm``
      - ``uv``
    * - Workload container
      - Framework-dependent
      - ``app``
    * - Workload resource
      - Framework-dependent
      - ``app-image``
    * - Peer relation
      - ``secret-storage`` with the ``secret-storage`` interface
      - ``peers`` with the ``peers`` interface
    * - Secret options
      - A string secret key and a separate secret-ID option
      - One ``app-secret-key`` option of type ``secret``
    * - Optional build input
      - None
      - :ref:`paas-config-yaml-file`
    * - OAuth, OpenFGA, and tracing libraries
      - Libraries fetched from Charmhub
      - Versioned ``charmlibs-interfaces-*`` dependencies from PyPI

Charmcraft stages ``paas-config.yaml`` only when the file exists in an Ubuntu 26.04 LTS
project. Changing the base or packing an existing project only partially migrates it to
the other contract. :ref:`Migrate a 12-factor charm to Ubuntu 26.04 LTS
<howto-change-to-ubuntu-26-04-12-factor>` describes how to generate and merge a complete
contract.


.. toctree::
    :hidden:

    django-framework-extension
    express-framework-extension
    fastapi-framework-extension
    flask-framework-extension
    go-framework-extension
    spring-boot-framework-extension
