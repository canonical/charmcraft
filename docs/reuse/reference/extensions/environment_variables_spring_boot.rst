
Environment variables
~~~~~~~~~~~~~~~~~~~~~

Each relation adds its own environment variables to your Spring Boot app. Some
are required, meaning they must be set for the relation to function.

The environment variable ``APP_BASE_URL`` provides the ingress URL
for an Ingress relation or the Kubernetes service URL if there is no
Ingress relation.

.. list-table::
  :widths: 20 40
  :header-rows: 1

  * - Relation
    - Environment variables
  * - PostgreSQL
    -
        - ``spring.datasource.url``
        - ``spring.jpa.hibernate.ddl-auto``
        - ``spring.datasource.username``
        - ``spring.datasource.password``
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
        - ``spring.datasource.url``
        - ``spring.jpa.hibernate.ddl-auto``
        - ``spring.datasource.username``
        - ``spring.datasource.password``
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
        - ``spring.data.mongodb.uri``
  * - Redis
    -
        - ``spring.data.redis.url``
        - ``spring.data.redis.host``
        - ``spring.data.redis.port``
        - ``spring.data.redis.username``
        - ``spring.data.redis.password``
  * - SAML
    -
        - ``spring.security.saml2.relyingparty.registration.``\
          ``testentity.assertingparty.metadata-uri``  (required)
        - ``spring.security.saml2.relyingparty.``\
          ``registration.testentity.entity-id`` (required)
        - ``spring.security.saml2.relyingparty.registration.``\
          ``testentity.assertingparty.singlesignin.url`` (required)
        - ``spring.security.saml2.relyingparty.registration.testentity.``\
          ``assertingparty.verification.credentials[0].certificate-location`` (required)
  * - S3
    -
        - ``spring.cloud.aws.credentials.accessKey`` (required)
        - ``spring.cloud.aws.credentials.secretKey`` (required)
        - ``spring.cloud.aws.s3.bucket`` (required)
        - ``spring.cloud.aws.region.static``
        - ``spring.cloud.aws.s3.endpoint``
  * - RabbitMQ
    -
        - ``spring.rabbitmq.host``
        - ``spring.rabbitmq.password``
        - ``spring.rabbitmq.port``
        - ``spring.rabbitmq.username``
        - ``spring.rabbitmq.virtual-host``
  * - Tracing
    -
        - ``OTEL_EXPORTER_OTLP_ENDPOINT``
        - ``OTEL_SERVICE_NAME``
  * - Prometheus
    -
        - ``management.endpoints.web.exposure.include``
        - ``management.endpoints.web.base-path``
        - ``management.endpoints.web.path-mapping.prometheus``
  * - SMTP
    -
        - ``spring.mail.host``
        - ``spring.mail.port``
        - ``spring.mail.username``
        - ``spring.mail.password``
        - ``spring.mail.properties.mail.smtp.auth``
        - ``spring.mail.properties.mail.smtp.starttls.enable``
  * - OpenFGA
    -
        - ``openfga.store-id``
        - ``openfga.credentials.method``
        - ``openfga.credentials.config.api-token``
        - ``openfga.api-url``
  * - OpenID Connect
    -
        - ``spring.security.oauth2.client.registration.{endpoint_name}.client-id``
        - ``spring.security.oauth2.client.registration.{endpoint_name}.client-secret``
        - ``spring.security.oauth2.client.registration.{endpoint_name}.redirect-uri``
        - ``spring.security.oauth2.client.registration.{endpoint_name}.scope``
        - ``spring.security.oauth2.client.registration.{endpoint_name}.user-name-attribute``
        - ``spring.security.oauth2.client.provider.{endpoint_name}.authorization-uri``
        - ``spring.security.oauth2.client.provider.{endpoint_name}.issuer-uri``
        - ``spring.security.oauth2.client.provider.{endpoint_name}.jwk-set-uri``
        - ``spring.security.oauth2.client.provider.{endpoint_name}.token-uri``
        - ``spring.security.oauth2.client.provider.{endpoint_name}.user-info-uri``
        - ``spring.security.oauth2.client.provider.{endpoint_name}.user-name-attribute``
