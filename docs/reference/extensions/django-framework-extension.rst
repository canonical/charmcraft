.. _django-framework-extension:


Django framework extension
==========================

The ``django-framework`` extension includes configuration options
customised for a Django application. This document describes all the
keys that a user may interact with.

.. tip::

    If you'd like to see the full contents contributed by this extension,
    see :ref:`How to manage extensions <manage-extensions>`.


Database requirement
--------------------

Django requires a database to function. When generating a new project,
the default is to make use of `SQLite <https://www.sqlite.org/>`_.
Using SQLite is not recommended for production, especially on Kubernetes
deployments, because the database is not shared across units and any
contents will be removed upon a new container being deployed. The
``django-framework`` extension therefore requires a database integration
for every application, such as
`PostgreSQL <https://www.postgresql.org/>`_ or
`MySQL <https://www.mysql.com/>`_. See the
:ref:`how-to guide <manage-12-factor-app-charms>` for how to deploy
a database and integrate the Django application with it.


``config.options`` key
----------------------

You can use the predefined options (run ``charmcraft expand-extensions``
for details) but also add your own, as needed.

In the latter case, any option you define will be used to generate
environment variables; a user-defined option ``config-option-name`` will
generate an environment variable named ``DJANGO_CONFIG_OPTION_NAME``
where the option name is converted to upper case, dashes will be
converted to underscores and the ``DJANGO_`` prefix will be added.

In either case, you will be able to set it in the usual way by running
``juju config <application> <option>=<value>``. For example, if you
define an option called ``token``, as below, this will generate a
``DJANGO_TOKEN`` environment variable, and a user of your charm can set
it by running ``juju config <application> token=<token>``.

.. code-block:: yaml

    config:
      options:
        token:
          description: The token for the service.
          type: string

For the predefined configuration option ``django-allowed-hosts``, that
will set the ``DJANGO_ALLOWED_HOSTS`` environment variable, the ingress
URL or the Kubernetes service URL if there is no ingress integration,
will be set automatically.

In addition to this, you can set the configuration options to be
mandatory by setting the ``optional`` key to ``false``. This will
block the charm and stop services until the configuration is supplied. For example,
if your application needs an ``api-token`` to function correctly you can set
``optional``, as shown below. This will block the charm and stop the
services until the ``api-token`` configuration is supplied.

.. code-block:: yaml

    config:
      options:
        api-token:
          description: The token necessary for the service to run.
          type: string
          optional: false

.. note::

    A configuration with the ``optional: false`` option cannot have a
     ``default`` value. If you set a ``default`` value to a configuration
     with ``optional: false`` ``charmcraft`` will fail when packing the charm.


``peers``, ``provides``, and ``requires`` keys
----------------------------------------------

Your charm already has some ``peers``, ``provides``, and ``requires``
integrations, for internal purposes.

.. dropdown:: Pre-populated integrations

.. code-block:: yaml

    peers:
      secret-storage:
        interface: secret-storage
    provides:
      metrics-endpoint:
        interface: prometheus_scrape
      grafana-dashboard:
        interface: grafana_dashboard
    requires:
      logging:
        interface: loki_push_api
      ingress:
        interface: ingress
        limit: 1

In addition to these integrations, in each ``provides`` and ``requires``
block you may specify further integration endpoints, to integrate with
the following charms and bundles:

- Ingress: `traefik <https://charmhub.io/traefik-k8s>`__ and `nginx
  ingress integrator <https://charmhub.io/nginx-ingress-integrator>`__
- MySQL: `machine <https://charmhub.io/mysql>`__ and
  `k8s <https://charmhub.io/mysql-k8s>`__ charm
- PostgreSQL: `machine <https://charmhub.io/postgresql>`__ and
  `k8s <https://charmhub.io/postgresql-k8s>`__ charm
- `MongoDB <https://charmhub.io/mongodb>`__
- `Canonical Observability Stack
  (COS) <https://charmhub.io/cos-lite>`__
- `Redis <https://charmhub.io/redis-k8s>`__
- `SAML <https://charmhub.io/saml-integrator>`__
- `S3 <https://charmhub.io/s3-integrator>`__
- RabbitMQ: `machine <https://charmhub.io/rabbitmq-server>`__ and
  `k8s <https://charmhub.io/rabbitmq-k8s>`__ charm
- `Tempo <https://charmhub.io/topics/charmed-tempo-ha>`__

These endpoint definitions are as below:

.. code-block:: yaml

    requires:
      mysql:
        interface: mysql_client
        optional: True
        limit: 1

.. code-block:: yaml

    requires:
      postgresql:
        interface: postgresql_client
        optional: True
        limit: 1

.. code-block:: yaml

    requires:
      mongodb:
        interface: mongodb_client
        optional: True
        limit: 1

.. code-block:: yaml

    requires:
      redis:
        interface: redis
        optional: True
        limit: 1

.. code-block:: yaml

    requires:
      saml:
        interface: saml
        optional: True
        limit: 1

.. code-block:: yaml

    requires:
      s3:
        interface: s3
        optional: True
        limit: 1

.. code-block:: yaml

   requires:
     rabbitmq:
       interface: rabbitmq
       optional: True
       limit: 1

.. code-block:: yaml

    requires:
      tracing:
        interface: tracing
        optional: True
        limit: 1

.. note::

    The key ``optional`` with value ``False`` means that the charm will
    get blocked and stop the services if the integration is not provided.

To add one of these integrations, e.g., PostgreSQL, in the
project file, include the appropriate requires block and
integrate with ``juju integrate <django charm> postgresql`` as usual.

After the integration has been established, the connection string will
be available as an environment variable. Integration with PostgreSQL,
MySQL, MongoDB or Redis provides the string as the
``POSTGRESQL_DB_CONNECT_STRING``, ``MYSQL_DB_CONNECT_STRING``,
``MONGODB_DB_CONNECT_STRING`` or ``REDIS_DB_CONNECT_STRING`` environment
variables respectively. Furthermore, the following environment variables
will be provided to your Django application for integrations with
PostgreSQL, MySQL, MongoDB or Redis:

- ``<integration>_DB_SCHEME``
- ``<integration>_DB_NETLOC``
- ``<integration>_DB_PATH``
- ``<integration>_DB_PARAMS``
- ``<integration>_DB_QUERY``
- ``<integration>_DB_FRAGMENT``
- ``<integration>_DB_USERNAME``
- ``<integration>_DB_PASSWORD``
- ``<integration>_DB_HOSTNAME``
- ``<integration>_DB_PORT``
- ``<integration>_DB_NAME``

Here, ``<integration>`` is replaced by ``POSTGRESQL``, ``MYSQL``
``MONGODB`` or ``REDIS`` for the relevant integration. The key
``optional`` with value ``False`` means that the charm will get blocked
and stop the services if the integration is not provided.

The provided SAML environment variables are as follows:

- ``SAML_ENTITY_ID`` (required)
- ``SAML_METADATA_URL`` (required)
- ``SAML_SINGLE_SIGN_ON_REDIRECT_URL`` (required)
- ``SAML_SIGNING_CERTIFICATE`` (required)

The S3 integration creates the following environment variables that you
may use to configure your Flask application:

- ``S3_ACCESS_KEY`` (required)
- ``S3_SECRET_KEY`` (required)
- ``S3_BUCKET`` (required)
- ``S3_REGION``
- ``S3_STORAGE_CLASS``
- ``S3_ENDPOINT``
- ``S3_PATH``
- ``S3_API_VERSION``
- ``S3_URI_STYLE``
- ``S3_ADDRESSING_STYLE``
- ``S3_ATTRIBUTES``
- ``S3_TLS_CA_CHAIN``

The RabbitMQ integration creates the connection string in the
environment variable ``RABBITMQ_CONNECT_STRING``. Furthermore, the
following environment variables may be provided, derived from the
connection string:

- ``RABBITMQ_SCHEME``
- ``RABBITMQ_NETLOC``
- ``RABBITMQ_PATH``
- ``RABBITMQ_PARAMS``
- ``RABBITMQ_QUERY``
- ``RABBITMQ_FRAGMENT``
- ``RABBITMQ_USERNAME``
- ``RABBITMQ_PASSWORD``
- ``RABBITMQ_HOSTNAME``
- ``RABBITMQ_PORT``
- ``RABBITMQ_VHOST``

The Tracing integration creates the following environment variables
that you can use to configure your application:

- ``OTEL_EXPORTER_OTLP_ENDPOINT``
- ``OTEL_SERVICE_NAME``

The environment variable ``DJANGO_BASE_URL`` provides the Ingress URL
for an Ingress integration or the Kubernetes service URL if there is no
Ingress integration.


HTTP Proxy
----------

Proxy settings should be set as model configurations. Charms generated
using the ``django-framework`` extension will make the Juju proxy
settings available as the ``HTTP_PROXY``, ``HTTPS_PROXY`` and
``NO_PROXY`` environment variables. For example, the ``juju-http-proxy``
environment variable will be exposed as ``HTTP_PROXY`` to the Django
service.

    See more: `Juju | List of model configuration
    keys <https://juju.is/docs/juju/list-of-model-configuration-keys>`_


Background Tasks
----------------

Extra services defined in the file
:external+rockcraft:ref:`rockcraft.yaml <rockcraft.yaml_reference>`
with names ending in ``-worker`` or ``-scheduler`` will be passed the
same environment variables as the main application. If there is more
than one unit in the application, the services with the name ending in
``-worker`` will run in all units. The services with name ending in
``-scheduler`` will only run in one of the units of the application.


Observability
-------------

12-factor app charms are designed to be easily observable using the
`Canonical Observability Stack
<https://charmhub.io/topics/canonical-observability-stack>`__.

You can easily integrate your charm with
`Loki <https://charmhub.io/loki-k8s>`__,
`Prometheus <https://charmhub.io/prometheus-k8s>`__ and
`Grafana <https://charmhub.io/grafana-k8s>`__ using Juju.

.. code-block:: bash

    juju integrate django-k8s grafana
    juju integrate django-k8s loki
    juju integrate django-k8s prometheus

After integration, you will be able to observe your workload
using Grafana dashboards.

In addition to that you can also trace your workload code
using `Tempo <https://charmhub.io/topics/charmed-tempo-ha>`__.

See `Charmed Tempo HA <https://charmhub.io/topics/charmed-tempo-ha>`_ on Discourse to
learn more about how to deploy Tempo.

OpenTelemetry will automatically read the environment variables
and configure the OpenTelemetry SDK to use them.
See the `OpenTelemetry documentation
<https://opentelemetry-python.readthedocs.io/en/latest/>`__
for further information about tracing.


Secrets
-------

Juju secrets can be passed as environment variables to your Django application. The
secret ID has to be passed to the application as a config option in the project file of
type ``secret``. This config option has to be populated with the secret ID, in the
format ``secret:<secret ID>``.

The environment variable name passed to the application will be:

.. code-block:: bash

    DJANGO_<config option name>_<key inside the secret>

The ``<config option name>`` and ``<key inside the secret>`` keywords in
the environment variable name will have the hyphens replaced by
underscores and all the letters capitalised.

   See more: :external+juju:ref:`Juju | Secret <secret>`
