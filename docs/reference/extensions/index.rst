.. meta::
    :description: Reference for Charmcraft extensions, including the V1 and experimental V2 contracts for 12-factor app frameworks.

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

12-factor extension versions
----------------------------

The Ubuntu base selects the version of a 12-factor framework extension. There is no
version key in ``charmcraft.yaml``.

* Ubuntu 22.04 LTS and Ubuntu 24.04 LTS select V1 where the framework supports the base.
* Ubuntu 26.04 LTS selects experimental V2.

V2 requires ``CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=1`` when Charmcraft expands or
packs the project. V1 does not require the environment variable.

All six V2 framework extensions generate the following contract:

.. list-table::
    :header-rows: 1

    * - Generated field
      - V1
      - V2
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
    * - Flask and Django secret options
      - ``flask-secret-key`` or ``django-secret-key`` and their ``-id`` variants
      - ``app-secret-key`` and ``app-secret-key-id``
    * - Optional build input
      - None
      - :ref:`paas-config-yaml-file`

Charmcraft stages ``paas-config.yaml`` only when the file exists in a V2 project.
Migration between the extension versions is not automatic. Follow
:ref:`howto-change-to-ubuntu-26-04-12-factor` when changing an existing 12-factor
app charm to V2.


.. toctree::
    :hidden:

    django-framework-extension
    express-framework-extension
    fastapi-framework-extension
    flask-framework-extension
    go-framework-extension
    spring-boot-framework-extension
