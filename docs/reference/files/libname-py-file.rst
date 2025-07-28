.. _libname-py-file:

``<libname>.py`` file
=====================

File ``<libname>.py`` is a Python file in your charm project that holds a charm
library -- that is, code that enables charm developers to easily share and reuse
auxiliary logic related to  charms -- for example, logic related to the relations
between charms.

Authors associate libraries with a specific charm and publish them to Charmhub with
a reference to the origin charm. This does not prevent reuse, modification or sharing.

The publishing tools around libraries are deliberately kept simple.
Libraries are however versioned and uniquely identified.


Location
--------

Charm libraries are located in a subdirectory inside the charm with the following
structure:

.. code-block::

    lib/charms/<charm-name>/v<API>/<libname>.py

where the ``<charm-name>`` placeholder represents the name of charm responsible for
the library (converted to a valid module name), ``<libname>`` represents this
particular library, and ``<API>`` represents the API version of the library.

For example, inside a charm ``mysql``, the library ``db`` with major version 3 will
be in a directory with the structure below:

.. code-block::

    lib/charms/mysql/v3/db.py

When you pack your charm, Charmcraft copies the top ``lib`` directory into the root
directory of the charm. Thus, to import this library in Python use the full path
minus the top ``lib`` directory, as below:

.. code-block:: python

    import charms.mysql.v3.db


Structure
---------

A charm library is a Python file with the following structure:


Docstring
~~~~~~~~~

Your charm file begins with a long docstring. This docstring describes your library.
Charmcraft publishes it as your library's documentation on Charmhub. This
documentation is updated whenever a new version of the library is published.

The docstring is expected to be in the `CommonMark <https://commonmark.org/>`_
dialect of Markdown.


Metadata
~~~~~~~~

After the docstring, there are a few metadata keys, as below.


``LIBID``
^^^^^^^^^

**Status:** Required

**Purpose:** Contains the unique identifier for a library across the entire
universe of charms. The value is assigned by Charmhub to this particular library
automatically at library creation time. This key enables Charmhub and ``charmcraft``
to track the library uniquely even if the charm or the library are renamed, which
allows updates to warn and guide users through the process.

**Type:** ``str``

**Value:** Assigned by :ref:`ref_commands_create-lib`


``LIBAPI``
^^^^^^^^^^

**Status:** Required

**Purpose:** Declares the API version of this charm library.

**Type:** ``int``

**Value:** ``LIBAPI``` is set to an initial state of ``0``. In general,
``LIBAPI`` must match the major version in the import path.


``LIBPATCH``
^^^^^^^^^^^^

**Status:** Required

**Purpose:** Declares the patch version of this charm library.

**Type:** ``int``

**Value:** ``LIBPATCH`` is set to an initial state of ``1``. In general, it must
match the current patch version (needs to be updated when changing).

.. note::

    While ``LIBPATCH`` can be set to ``0``, it is not allowed to set both ``LIBAPI``
    and ``LIBPATCH`` to ``0``. As such, a charm lib may have a version ``0.1`` and
    a version ``1.0``, but not a version ``0.0``.


``PYDEPS``
^^^^^^^^^^

**Status:** Optional

**Purpose:** Declares external Python dependencies for the library.

When using the ``charm`` plugin, Charmcraft will make sure to install them in the
virtual environment created in any charm that includes the library.

**Type:** ``list[str]``

Each string is a regular "pip installable" Python dependency that will be retrieved
from PyPI in the usual way (subject to the user's system configuration) and which
supports all dependency formats (just the package name, a link to a Github project,
etc.).

.. collapse:: Examples

    .. code-block:: python

        PYDEPS=["jinja2"]

    .. code-block:: python

        PYDEPS = ["pyyaml", "httpcore<0.15.0,>=0.14.5"]

    .. code-block:: python

        PYDEPS = [
            "git+https://github.com/canonical/operator/#egg=ops",
            "httpcore<0.15.0,>=0.14.5",
            "requests",
        ]

Note that when called to install all the dependencies from the charm and all the
used libraries, ``pip`` may detect conflicts between the requested packages and
their versions. This is a feature, because it's always better to detect
incompatibilities between dependencies at this moment than when the charm is being
deployed or run after deployment.


Code
^^^^

After the docstring and the metadata, there's the library code.
This is regular Python code.


Popular libraries
-----------------

This is a list of some popular charm libraries available from Charmhub.

.. note::

    This list does not and will not contain all charm libraries on Charmhub. However if
    you believe a library is missing from this list, please
    `open a pull request <https://github.com/canonical/charmcraft/pull/new/>`_ adding
    the library you believe to be missing.


Libraries that define relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following libraries provide programmatic instructions for relating to a specific
charm.

.. list-table::
    :header-rows: 1

    * - Library
      - Used in
      - Description
    * - `fluentbit <https://charmhub.io/fluentbit/libraries/fluentbit>`_
      - `fluentbit charm <https://charmhub.io/fluentbit>`_
      - Defines both sides of a relation interface to the
        fluentbit charm.
    * - `redis <https://charmhub.io/redis-k8s/libraries/redis>`_
      -
      - Import RedisRequires from this lib to relate your charm to the
        `redis charm <https://charmhub.io/redis-k8s>`_
    * - `grafana_dashboard
        <https://charmhub.io/grafana-k8s/libraries/grafana-dashboard>`_
      -
      - Defines a relation interface for charms that provide a dashboard to the
        `grafana-k8s charm <https://charmhub.io/grafana-k8s>`_
    * - `grafana_source <https://charmhub.io/grafana-k8s/libraries/grafana-source>`_
      -
      - Defines a relation interface for charms that serve as a data source for the
        `grafana-k8s charm <https://charmhub.io/grafana-k8s>`_
    * - `prometheus_scrape
        <https://charmhub.io/prometheus-k8s/libraries/prometheus_scrape>`_
      -
      - Defines a relation interface for charms that want to expose metrics endpoints
        to the `prometheus charm <https://charmhub.io/prometheus-k8s>`_.
    * - `alertmanager_dispatch
        <https://charmhub.io/alertmanager-k8s/libraries/alertmanager_dispatch>`_
      -
      - Defines a relation to the `alertmanager-dispatch charm
        <https://charmhub.io/alertmanager-k8s>`_.
    * - `karma_dashboard <https://charmhub.io/karma-k8s/libraries/karma_dashboard>`_
      - `karma-k8s <https://charmhub.io/karma-k8s>`_
      - Defines an interface for charms wishing to consume or provide a
        karma-dashboard relation.
    * - `loki_push_api
        <https://charmhub.io/loki-k8s/libraries/loki_push_api>`_
      - `loki-k8s <https://charmhub.io/loki-k8s>`_
      - Defines a relation interface for charms wishing to provide or consume the
        Loki Push API---e.g., a charm that wants to send logs to Loki.
    * - `log_proxy <https://charmhub.io/loki-k8s/libraries/log_proxy>`_
      - `loki-k8s <https://charmhub.io/loki-k8s>`_
      - Defines a relation interface that allows a charm to act as a Log Proxy for
        Loki (via the Loki Push API).
    * - `guacd <https://charmhub.io/apache-guacd/libraries/guacd>`_
      - `apache-guacd <https://charmhub.io/apache-guacd>`_
      - Defines a relation for charms wishing to set up a native server side proxy
        for Apache Guacamole.


Libraries that provide tools
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These libraries provide reusable tooling, typically to interact with cloud services,
or to perform operations common to several charms.

.. list-table::
    :header-rows: 1

    * - Library
      - Used in
      - Description
    * - `cert <https://charmhub.io/kubernetes-dashboard/libraries/cert>`_
      - `kubernetes-dashboard <https://charmhub.io/kubernetes-dashboard>`_
      - Generates a self signed certificate.
    * - `capture_events
        <https://discourse.charmhub.io/t/harness-recipe-capture-events/6581>`_
      - - `traefik-k8s <https://charmhub.io/traefik-k8s>`_,
        - `data-platform-libs <https://github.com/canonical/data-platform-libs/>`_
      - Helper for unit testing events.
    * - `networking <https://discourse.charmhub.io/t/harness-and-network-mocks/6633>`_
      -
      - Provides tools for mocking networks.
    * - `compound-status <https://charmhub.io/compound-status>`_
      -
      - Provides utilities to track multiple independent statuses in charms.
    * - `resurrect <https://github.com/PietroPasotti/resurrect>`_
      - `github-runner-image-builder
        <https://github.com/canonical/github-runner-image-builder-operator>`_
      - Provides utilities to periodically trigger charm hooks


Libraries that provide tools for Kubernetes charms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These libraries provide tooling for charms that run on top of Kubernetes clouds.

.. list-table::
    :header-rows: 1

    * - Library
      - Used in
      - Description
    * - `kubernetes_service_patch
        <https://charmhub.io/observability-libs/libraries/kubernetes_service_patch>`_
      - - `cos-configuration-k8s <https://charmhub.io/cos-configuration-k8s>`_
        - `alertmanager-k8s <https://charmhub.io/alertmanager-k8s>`_
        - `grafana-agent-k8s <https://charmhub.io/grafana-agent-k8s>`_
        - `prometheus-k8s <https://charmhub.io/prometheus-k8s>`_
        - `loki-k8s <https://charmhub.io/loki-k8s>`_
        - `traefik-k8s <https://charmhub.io/traefik-k8s>`_
      - Allows charm authors to simply and elegantly define service overrides that
        persist through a charm upgrade.
    * - `ingress <https://charmhub.io/nginx-ingress-integrator/libraries/ingress>`_
      - `nginx-ingress-integrator <https://charmhub.io/nginx-ingress-integrator>`_
      - Configures nginx to use an existing Kubernetes Ingress.
    * - `ingress-per-unit <https://charmhub.io/traefik-k8s/libraries/ingress_per_unit>`_
      - `traefik-k8s <https://charmhub.io/traefik-k8s>`_
      - Configures traefik to provide per-unit routing.


Libraries that provide tools for machine charms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These libraries contain tools meant for use in machine charms, e.g., libraries that
interact with package managers or other CLI tools that are often not present in
containers.

.. list-table::
    :header-rows: 1

    * - Library
      - Used in
      - Description
    * - `apt <https://charmhub.io/operator-libs-linux/libraries/apt>`_
      - - `mysql <https://charmhub.io/mysql>`_
        - `zookeeper <https://charmhub.io/zookeeper>`_
        - `cos-proxy <https://charmhub.io/cos-proxy>`_
        - `kafka <https://charmhub.io/kafka>`_
        - `ceph-mon <https://charmhub.io/ceph-mon>`_
      - Install and manage packages via ``apt``.
    * - `dnf <https://charmhub.io/operator-libs-linux/libraries/dnf>`_
      -
      - Install and manage packages via ``dnf``.
    * - `grub <https://charmhub.io/operator-libs-linux/libraries/grub>`_
      -
      - Manage kernel configuration via ``grub``.
    * - `passwd <https://charmhub.io/operator-libs-linux/libraries/passwd>`_
      -
      - Manage users and groups on a Linux system.
    * - `snap <https://charmhub.io/operator-libs-linux/libraries/snap>`_
      - - `mongodb <https://charmhub.io/mongodb>`_
        - `mongodb-k8s <https://charmhub.io/mongodb-k8s>`_
        - `postgresql <https://charmhub.io/postgresql>`_
        - `grafana-agent <https://charmhub.io/grafana-agent>`_
        - `kafka <https://charmhub.io/kafka>`_
      - Install and manage packages via ``snapd``.
    * - `sysctl <https://charmhub.io/operator-libs-linux/libraries/sysctl>`_
      - `kafka <https://charmhub.io/kafka>`_
      - Manage sysctl configuration.
    * - `systemd <https://charmhub.io/operator-libs-linux/libraries/systemd>`_
      - - `mongodb <https://charmhub.io/mongodb>`_
        - `pgbouncer <https://charmhub.io/pgbouncer>`_
        - `cos-proxy <https://charmhub.io/cos-proxy>`_
        - `ceph-mon <https://charmhub.io/ceph-mon>`_
        - `calico <https://charmhub.io/calico>`_
      - Interact with services via ``systemd``.
