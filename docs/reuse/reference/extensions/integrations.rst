
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

  * - `Hydra <https://charmhub.io/hydra>`__ charm
    - The ``oauth`` interface is a conduit for the OpenID Connect authentication
      protocol. Each configuration option for this endpoint is prefixed with the
      endpoint name.

      .. code-block:: yaml

          requires:
            oauth-endpoint-name:
              interface: oauth
              optional: True
              limit: 1

      The relation will create two configuration options,
      ``{endpoint_name}-redirect-path`` and ``{endoint_name}-scopes``.
      ``{endpoint_name}-scopes`` is a space separated list of scopes, and the scope
      ``openid`` is manadatory.



.. note::

    The key ``optional`` with value ``False`` means that the charm will
    get blocked and stop the services if the integration is not provided.

To add one of these relations, e.g., PostgreSQL, in the
project file, include the appropriate ``requires`` block and
integrate with |juju_integrate_postgresql| as usual.
