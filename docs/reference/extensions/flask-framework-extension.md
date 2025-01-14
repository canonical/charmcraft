(flask-framework-extension)=

# Flask framework extension

The `flask-framework` extension includes configuration options customised for a Flask application. This document describes all the keys that a user may interact with.

```{tip}
If you'd like to see the full contents contributed by this extension, see {ref}`How to manage extensions <manage-extensions>`.
```


## `charmcraft.yaml` > `config` > `options`

You can use the predefined options (run `charmcraft expand-extensions` for details) but also add your own, as needed. 

In the latter case, any option you define will be used to generate environment variables; a user-defined option `config-option-name` will generate an environment variable named `FLASK_CONFIG_OPTION_NAME` where the option name is converted to upper case and dashes are converted to underscores. 

In either case, you will be able to set it in the usual way by running `juju config <application> <option>=<value>`. For example, if you define an option called `token`, as below, this will generate a `FLASK_TOKEN` environment variable, and a user of your charm can set it by running `juju config <application> token=<token>`.


```yaml
config:
  options:
    token:
      description: The token for the service.
      type: string
```


## `charmcraft.yaml` > `peers`, `provides`, `requires`

Your charm already has some `peers`, `provides`, and `requires` integrations, for internal purposes. 

`````{dropdown} Expand to view pre-loaded integrations

```yaml
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
```

`````

In addition to these, in each `provides` and `requires` block you may specifying further integration endpoints, to integrate with the following charms and bundles:

- Ingress: [traefik](https://charmhub.io/traefik-k8s) and
  [nginx ingress integrator](https://charmhub.io/nginx-ingress-integrator)
- MySQL: [machine](https://charmhub.io/mysql) and
  [k8s](https://charmhub.io/mysql-k8s) charm
- PostgreSQL: [machine](https://charmhub.io/postgresql) and
  [k8s](https://charmhub.io/postgresql-k8s) charm
- [MongoDB](https://charmhub.io/mongodb)
- [Canonical Observability Stack (COS)](https://charmhub.io/cos-lite)
- [Redis](https://charmhub.io/redis-k8s)
- [SAML](https://charmhub.io/saml-integrator)
- [S3](https://charmhub.io/s3-integrator)
- RabbitMQ: [machine](https://charmhub.io/rabbitmq-server) and
  [k8s](https://charmhub.io/rabbitmq-k8s) charm

These endpoint definitions are as below:

```yaml
requires:
  mysql:
    interface: mysql_client
    optional: True
    limit: 1
```

```yaml
requires:
  postgresql:
    interface: postgresql_client
    optional: True
    limit: 1
```

```yaml
requires:
  mongodb:
    interface: mongodb_client
    optional: True
    limit: 1
```

```yaml
requires:
  redis:
    interface: redis
    optional: True
    limit: 1
```

```yaml
requires:
  saml:
    interface: saml
    optional: True
    limit: 1
```

```yaml
requires:
  s3:
    interface: s3
    optional: True
    limit: 1
```

```yaml
requires:
  rabbitmq:
    interface: rabbitmq
    optional: True
    limit: 1
```

```{note}
The key `optional` with value `False` means that the charm will get blocked and stop the services if the integration is not provided.
```

To add one of these integrations, e.g. postgresql, in the `charmcraft.yaml` file include the appropriate requires block and integrate with `juju integrate <flask charm> postgresql` as usual. 

After the integration has been established, the connection string will be
available as an environment variable. Integration with PostgreSQL, MySQL, MongoDB or Redis provides the string as the `POSTGRESQL_DB_CONNECT_STRING`, `MYSQL_DB_CONNECT_STRING`,
`MONGODB_DB_CONNECT_STRING` or `REDIS_DB_CONNECT_STRING` environment variables respectively. Furthermore, the following environment variables will be provided to your Flask application for integrations with PostgreSQL, MySQL, MongoDB or Redis:

- `<integration>_DB_SCHEME`
- `<integration>_DB_NETLOC`
- `<integration>_DB_PATH`
- `<integration>_DB_PARAMS`
- `<integration>_DB_QUERY`
- `<integration>_DB_FRAGMENT`
- `<integration>_DB_USERNAME`
- `<integration>_DB_PASSWORD`
- `<integration>_DB_HOSTNAME`
- `<integration>_DB_PORT` 
- `<integration>_DB_NAME` 

Here, `<integration>` is replaced by `POSTGRESQL`, `MYSQL` `MONGODB` or `REDIS` for the relevant integration.

The provided SAML environment variables are as follows:

- `SAML_ENTITY_ID` (required)
- `SAML_METADATA_URL` (required)
- `SAML_SINGLE_SIGN_ON_REDIRECT_URL` (required)
- `SAML_SIGNING_CERTIFICATE` (required)

The S3 integration creates the following environment variables that you may use to configure your Flask application:

- `S3_ACCESS_KEY` (required)
- `S3_SECRET_KEY` (required)
- `S3_BUCKET` (required)
- `S3_REGION`
- `S3_STORAGE_CLASS`
- `S3_ENDPOINT`
- `S3_PATH`
- `S3_API_VERSION`
- `S3_URI_STYLE`
- `S3_ADDRESSING_STYLE`
- `S3_ATTRIBUTES`
- `S3_TLS_CA_CHAIN`

The RabbitMQ integration creates the connection string in the environment variable `RABBITMQ_CONNECT_STRING`. Furthermore, the following environment variables may be provided, derived from the connection string:

- `RABBITMQ_SCHEME`
- `RABBITMQ_NETLOC`
- `RABBITMQ_PATH`
- `RABBITMQ_PARAMS`
- `RABBITMQ_QUERY`
- `RABBITMQ_FRAGMENT`
- `RABBITMQ_USERNAME`
- `RABBITMQ_PASSWORD`
- `RABBITMQ_HOSTNAME`
- `RABBITMQ_PORT` 
- `RABBITMQ_VHOST` 

The environment variable `FLASK_BASE_URL` provides the Ingress URL for an Ingress integration or the Kubernetes service URL if there is no Ingress integration.


## HTTP Proxy

Proxy settings should be set as model configurations. Charms generated using the `flask-framework` extension will make the Juju proxy settings available as the `HTTP_PROXY`, `HTTPS_PROXY` and `NO_PROXY` environment variables. For example, the `juju-http-proxy` environment variable will be exposed as `HTTP_PROXY` to the Flask service.

> See more: [Juju | List of model configuration keys](https://juju.is/docs/juju/list-of-model-configuration-keys)


## Background Tasks

Extra services defined in the file [`rockcraft.yaml`](https://documentation.ubuntu.com/rockcraft/en/stable/reference/rockcraft.yaml/#services) with
names ending in `-worker` or `-scheduler` will be passed the same environment variables as the main application. If there is more than one unit
in the application, the services with the name ending in `-worker` will run in all units. The services with name ending in `-scheduler` will
only run in one of the units of the application.


## Regarding the `migrate.sh` file

If your app depends on a database it is common to run a database migration
script before app startup which, for example, creates or modifies tables.
This can be done by including the ``migrate.sh`` script in the root of your
project. It will be executed with the same environment variables and context
as the Flask application.

If the migration script fails, the app won't be started and the app charm
will go into blocked state. The migration script will be run on every unit
and it is assumed that it is idempotent (can be run multiple times) and that
it can be run on multiple units at the same time without causing issues.
This can be achieved by, for example, locking any tables during the migration.


## Secrets

Juju secrets can be passed as environment variables to your Flask application.
The secret ID has to be passed to the application as a config option in the
file `charmcraft.yaml` file of type `secret`. This config option has to be populated with the secret
ID, in the format `secret:<secret ID>`.

The environment variable name passed to the application will be:

```
FLASK_<config option name>_<key inside the secret>
```

The `<config option name>` and `<key inside the secret>` keywords in the environment variable name
will have the hyphens replaced by underscores and all the letters capitalised.

> See more: [Secret](https://juju.is/docs/juju/secret)
