
Relations
---------

Your charm already has the following ``peers``, ``provides``, and ``requires``
relations, as they were automatically supplied by the |framework| extension:

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

In addition to these relations, in each ``provides`` and ``requires``
block you may specify further relations, to integrate with
the following charms:

.. list-table::
  :header-rows: 1

  * - Relation
    - Endpoint definition
  * - Ingress `traefik <https://charmhub.io/traefik-k8s>`__ and `nginx
      ingress integrator <https://charmhub.io/nginx-ingress-integrator>`__
    - Already available in the charm
  * - MySQL `machine <https://charmhub.io/mysql>`__ and
      `Kubernetes <https://charmhub.io/mysql-k8s>`__ charm
    - .. code-block:: yaml

          requires:
            mysql:
              interface: mysql_client
              optional: True
              limit: 1

  * - PostgreSQL `machine <https://charmhub.io/postgresql>`__ and
      `Kubernetes <https://charmhub.io/postgresql-k8s>`__ charm
    - .. code-block:: yaml

          requires:
            postgresql:
              interface: postgresql_client
              optional: True
              limit: 1

  * - `MongoDB <https://charmhub.io/mongodb>`__ charm
    - .. code-block:: yaml

          requires:
            mongodb:
              interface: mongodb_client
              optional: True
              limit: 1

  * - `Canonical Observability Stack
      (COS) <https://charmhub.io/cos-lite>`__
    - Already available in the charm
  * - `Redis <https://charmhub.io/redis-k8s>`__ charm
    - .. code-block:: yaml

          requires:
            redis:
              interface: redis
              optional: True
              limit: 1

  * - `SAML <https://charmhub.io/saml-integrator>`__ charm
    - .. code-block:: yaml

          requires:
            saml:
              interface: saml
              optional: True
              limit: 1

  * - `S3 <https://charmhub.io/s3-integrator>`__ charm
    - .. code-block:: yaml

          requires:
            s3:
              interface: s3
              optional: True
              limit: 1

  * - RabbitMQ `machine <https://charmhub.io/rabbitmq-server>`__ and
      `Kubernetes <https://charmhub.io/rabbitmq-k8s>`__ charm
    - .. code-block:: yaml

         requires:
           rabbitmq:
             interface: rabbitmq
             optional: True
             limit: 1

  * - `Tempo <https://charmhub.io/topics/charmed-tempo-ha>`__ charm
    - .. code-block:: yaml

          requires:
            tracing:
              interface: tracing
              optional: True
              limit: 1

  * - `SMTP <https://charmhub.io/smtp-integrator>`__ charm
    - .. code-block:: yaml

          requires:
            smtp:
              interface: smtp
              optional: True
              limit: 1

  * - `OpenFGA <https://charmhub.io/openfga-k8s>`__ charm
    - .. code-block:: yaml

          requires:
            openfga:
              interface: openfga
              optional: True
              limit: 1


.. note::

    The key ``optional`` with value ``False`` means that the charm will
    get blocked and stop the services if the integration is not provided.

To add one of these relations, e.g., PostgreSQL, in the
project file, include the appropriate ``requires`` block and
integrate with |juju_integrate_postgresql| as usual.

Environment variables
~~~~~~~~~~~~~~~~~~~~~

Each relation adds its own environment variables to your |framework| app. Some
are required, meaning they must be set for the relation to function.

The environment variable |base_url| provides the Ingress URL
for an Ingress relation or the Kubernetes service URL if there is no
Ingress relation.

.. list-table::
  :widths: 20 40
  :header-rows: 1

  * - Relation
    - Environment variables
  * - PostgreSQL
    -
        - ``POSTGRESQL_DB_CONNECT_STRING``
        - ``POSTGRESQL_DB_SCHEME``
        - ``POSTGRESQL_DB_NETLOC``
        - ``POSTGRESQL_DB_PATH``
        - ``POSTGRESQL_DB_PARAMS``
        - ``POSTGRESQL_DB_QUERY``
        - ``POSTGRESQL_DB_FRAGMENT``
        - ``POSTGRESQL_DB_USERNAME``
        - ``POSTGRESQL_DB_PASSWORD``
        - ``POSTGRESQL_DB_HOSTNAME``
        - ``POSTGRESQL_DB_PORT``
        - ``POSTGRESQL_DB_NAME``
  * - MySQL
    -
        - ``MYSQL_DB_CONNECT_STRING``
        - ``MYSQL_DB_SCHEME``
        - ``MYSQL_DB_NETLOC``
        - ``MYSQL_DB_PATH``
        - ``MYSQL_DB_PARAMS``
        - ``MYSQL_DB_QUERY``
        - ``MYSQL_DB_FRAGMENT``
        - ``MYSQL_DB_USERNAME``
        - ``MYSQL_DB_PASSWORD``
        - ``MYSQL_DB_HOSTNAME``
        - ``MYSQL_DB_PORT``
        - ``MYSQL_DB_NAME``
  * - MongoDB
    -
        - ``MONGODB_DB_CONNECT_STRING``
        - ``MONGODB_DB_SCHEME``
        - ``MONGODB_DB_NETLOC``
        - ``MONGODB_DB_PATH``
        - ``MONGODB_DB_PARAMS``
        - ``MONGODB_DB_QUERY``
        - ``MONGODB_DB_FRAGMENT``
        - ``MONGODB_DB_USERNAME``
        - ``MONGODB_DB_PASSWORD``
        - ``MONGODB_DB_HOSTNAME``
        - ``MONGODB_DB_PORT``
        - ``MONGODB_DB_NAME``
  * - Redis
    -
        - ``REDIS_DB_CONNECT_STRING``
        - ``REDIS_DB_SCHEME``
        - ``REDIS_DB_NETLOC``
        - ``REDIS_DB_PATH``
        - ``REDIS_DB_PARAMS``
        - ``REDIS_DB_QUERY``
        - ``REDIS_DB_FRAGMENT``
        - ``REDIS_DB_USERNAME``
        - ``REDIS_DB_PASSWORD``
        - ``REDIS_DB_HOSTNAME``
        - ``REDIS_DB_PORT``
        - ``REDIS_DB_NAME``
  * - SAML
    -
        - ``SAML_ENTITY_ID`` (required)
        - ``SAML_METADATA_URL`` (required)
        - ``SAML_SINGLE_SIGN_ON_REDIRECT_URL`` (required)
        - ``SAML_SIGNING_CERTIFICATE`` (required)
  * - S3
    -
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
  * - RabbitMQ
    -
        - ``RABBITMQ_CONNECT_STRING``
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
  * - Tracing
    -
        - ``OTEL_EXPORTER_OTLP_ENDPOINT``
        - ``OTEL_SERVICE_NAME``
  * - SMTP
    -
        - ``SMTP_HOST``
        - ``SMTP_PORT``
        - ``SMTP_USER``
        - ``SMTP_PASSWORD_ID``
        - ``SMTP_AUTH_TYPE``
        - ``SMTP_TRANSPORT_SECURITY``
        - ``SMTP_DOMAIN``
  * - OpenFGA
    -
        - ``FGA_STORE_ID``
        - ``FGA_TOKEN``
        - ``FGA_GRPC_API_URL``
        - ``FGA_HTTP_API_URL``

