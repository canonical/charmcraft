
Environment variables
~~~~~~~~~~~~~~~~~~~~~

Each relation adds its own environment variables to your |framework| app. Some
are required, meaning they must be set for the relation to function.

The environment variable |base_url| provides the ingress URL
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
  * - OpenID Connect
    -
        - :substitution-code:`|framework_prefix|_{endpoint_name}_CLIENT_ID`
        - :substitution-code:`|framework_prefix|_{endpoint_name}_CLIENT_ID`
        - :substitution-code:`|framework_prefix|_{endpoint_name}_CLIENT_SECRET`
        - :substitution-code:`|framework_prefix|_{endpoint_name}_ACCESS_TOKEN_URL`
        - :substitution-code:`|framework_prefix|_{endpoint_name}_AUTHORIZE_URL`
        - :substitution-code:`|framework_prefix|_{endpoint_name}_USERINFO_URL`
        - :substitution-code:`|framework_prefix|_{endpoint_name}_JWKS_URL`
        - :substitution-code:`|framework_prefix|_{endpoint_name}_API_BASE_URL`
        - :substitution-code:`|framework_prefix|_{endpoint_name}_CLIENT_KWARGS`
