
``peers``, ``provides``, and ``requires`` keys
----------------------------------------------

Your charm already has some ``peers``, ``provides``, and ``requires``
integrations, for internal purposes.

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
- `SMTP <https://charmhub.io/smtp-integrator>`__
- `OpenFGA <https://charmhub.io/openfga-k8s>`__

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

.. code-block:: yaml

    requires:
      smtp:
        interface: smtp
        optional: True
        limit: 1

.. code-block:: yaml

    requires:
      openfga:
        interface: openfga
        optional: True
        limit: 1

.. note::

    The key ``optional`` with value ``False`` means that the charm will
    get blocked and stop the services if the integration is not provided.

To add one of these integrations, e.g., PostgreSQL, in the
project file, include the appropriate requires block and
integrate with |juju_integrate_postgresql| as usual.

After the integration has been established, the connection string will
be available as an environment variable. Integration with PostgreSQL,
MySQL, MongoDB or Redis provides the string as the
``POSTGRESQL_DB_CONNECT_STRING``, ``MYSQL_DB_CONNECT_STRING``,
``MONGODB_DB_CONNECT_STRING`` or ``REDIS_DB_CONNECT_STRING`` environment
variables respectively. Furthermore, the following environment variables
will be provided to your |framework| application for integrations with
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
``MONGODB`` or ``REDIS`` for the relevant integration.

The provided SAML environment variables are as follows:

- ``SAML_ENTITY_ID`` (required)
- ``SAML_METADATA_URL`` (required)
- ``SAML_SINGLE_SIGN_ON_REDIRECT_URL`` (required)
- ``SAML_SIGNING_CERTIFICATE`` (required)

The S3 integration creates the following environment variables that you
may use to configure your |framework| application:

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

The provided SMTP environment variables are as follows:

- ``SMTP_HOST``
- ``SMTP_PORT``
- ``SMTP_USER``
- ``SMTP_PASSWORD_ID``
- ``SMTP_AUTH_TYPE``
- ``SMTP_TRANSPORT_SECURITY``
- ``SMTP_DOMAIN``

The provided OpenFGA environment variables are as follows:

- ``FGA_STORE_ID``
- ``FGA_TOKEN``
- ``FGA_GRPC_API_URL``
- ``FGA_HTTP_API_URL``

The environment variable |base_url| provides the Ingress URL
for an Ingress integration or the Kubernetes service URL if there is no
Ingress integration.
