(manage-a-12-factor-app-charm)=

# Manage a 12-factor app charm

<!--TODO: There are a few more low-hanging fruit topics that we can and should cover:

When we create such sections we should include thinks at both the rock and the charm level (because the 12-Factor app app charm wants you to think about them in this coupled fashion). However, for the Rockcraft things, we should have those sections point to Rockcraft docs. For example:

## Update the OCI image for a 12-Factor app charm

See {ref}`Rockcraft Documentation > How to update the OCI image... <15018md>`

-->

> See also: [`juju` | 12-factor-app charms](https://juju.is/docs/juju/charmed-operator)


## Prepare an OCI image for a 12-factor app charm

> See more: [`rockcraft` | Build a 12-factor app rock](https://documentation.ubuntu.com/rockcraft/en/latest/how-to/build-a-12-factor-app-rock/#include-extra-files-in-the-oci-image)


## Initialise a 12-factor app charm 

Use `charmcraft init` and specify the relevant profile:

```bash
charmcraft init --profile <profile>
```

Charmcraft automatically creates `charmcraft.yaml`, `requirements.txt` and source code
for the charm in your current directory. You will need to check `charmcraft.yaml` and
`README.md` and verify that the charm's name and description are correct.

> See also: {ref}`ref_commands_init`

````{dropdown} Example: Flask application

Specify the `flask-framework` profile:

```bash
charmcraft init --profile flask-framework
```

````


````{dropdown} Example: Django application

Specify the `django-framework` profile:

```bash
charmcraft init --profile django-framework
```

````


````{dropdown} Example: FastAPI application


Specify the `fastapi-framework` profile:

```bash
charmcraft init --profile fastapi-framework
```

````


````{dropdown} Example: Go application

Specify the `go-framework` profile:

```bash
charmcraft init --profile go-framework
```

````


## Manage configurations for a 12-factor app charm

A charm configuration can be added if your 12-factor app requires environment variables,
for example, to pass a token for a service. Add the configuration in `charmcraft.yaml`:

```yaml
config:
  options:
    token:
      description: The token for the service.
      type: string
```

```{dropdown} Flask application

A user-defined configuration option will correspond to an environment variable generated
by the `paas-charm` project to expose the configuration to the Flask workload. In
general, a configuration option `config-option-name` will be mapped as
`FLASK_CONFIG_OPTION_NAME` where the option name will be converted to upper case, dashes
will be converted to underscores and the `FLASK_` prefix will be added. In the example
above, the `token` configuration will be mapped as the `FLASK_TOKEN` environment
variable. In addition to the environment variable, the configuration is also available
in the Flask variable `app.config` without the `FLASK_` prefix.

The configuration can be set on the deployed charm using `juju config <app name>
token=<token>`.

> See also: [How to add a configuration to a charm](https://juju.is/docs/sdk/config),
> [Configuration Handling -- Flask
> Documentation](https://flask.palletsprojects.com/en/3.0.x/config/)
```

```{dropdown} Django application

A user-defined configuration option will correspond to an environment variable generated
by the `paas-charm` project to expose the configuration to the Django workload. In
general, a configuration option `config-option-name` will be mapped as
`DJANGO_CONFIG_OPTION_NAME` where the option name will be converted to upper case,
dashes will be converted to underscores and the `DJANGO_` prefix will be added. In the
example above, the `token` configuration will be mapped as the `DJANGO_TOKEN`
environment variable. 

The configuration can be set on the deployed charm using `juju config <app name>
token=<token>`.

> See also: [How to add a configuration to a charm](https://juju.is/docs/sdk/config)
```

```{dropdown} FastAPI application

A user-defined configuration option will correspond to an environment variable generated
by the `paas-charm` project to expose the configuration to the FastAPI workload. In
general, a configuration option `config-option-name` will be mapped as
`APP_CONFIG_OPTION_NAME` where the option name will be converted to upper case, dashes
will be converted to underscores and the `APP_` prefix will be added. In the example
above, the `token` configuration will be mapped as the `APP_TOKEN` environment variable. 

The configuration can be set on the deployed charm using `juju config <app name>
token=<token>`.

> See also: [How to add a configuration to a charm](https://juju.is/docs/sdk/config),
```

<!--In addition to the environment variable, the configuration is also available in the FastAPI variable `app.config` without the `APP_` prefix.-->

```{dropdown} Go application

A user-defined configuration option will correspond to an environment variable generated
by the `paas-charm` project to expose the configuration to the Go workload. In general,
a configuration option `config-option-name` will be mapped as `APP_CONFIG_OPTION_NAME`
where the option name will be converted to upper case, dashes will be converted to
underscores and the `APP_` prefix will be added. In the example above, the `token`
configuration will be mapped as the `APP_TOKEN` environment variable. 

The configuration can be set on the deployed charm using `juju config <app name>
token=<token>`.

> See also: [How to add a configuration to a charm](https://juju.is/docs/sdk/config),
```


## Manage relations for a 12-factor app charm

A charm integration can be added to your charmed 12-factor app by providing the
integration and endpoint definition in `charmcraft.yaml`:

```yaml
requires:
  <endpoint name>:
    interface: <endpoint interface name>
    optional: false
```

Here, `<endpoint name>` corresponds to the endpoint of the application with which you
want the integration, and `<endpoint interface name>` is the endpoint schema to which
this relation conforms. Both the `<endpoint name>` and `<endpoint interface name>` must
coincide with the structs defined in that particular application's charm's
`charmcraft.yaml` file. The key `optional` with value `False` means that the charm will
get blocked and stop the services if the integration is not provided.

You can provide the integration to your deployed 12-factor app using `juju integrate
<12-factor app charm> <endpoint name>`. After the integration has been established, the
connection string and other configuration options will be available as environment
variables that you may use to configure your 12-factor application.

For example, if you wish to integrate your 12-factor application with PostgreSQL
([machine](https://charmhub.io/postgresql) or [k8s](https://charmhub.io/postgresql-k8s)
charm), add the following endpoint definition to `charmcraft.yaml`:

```yaml
requires:
  postgresql:
    interface: postgresql_client
    optional: True
```

Provide the integration to your deployed 12-factor app with `juju integrate <12-factor
app charm> postgresql`. This integration creates the following environment variables you
may use to configure your 12-factor application:

- `POSTGRESQL_DB_CONNECT_STRING`
- `POSTGRESQL_DB_SCHEME`
- `POSTGRESQL_DB_NETLOC`
- `POSTGRESQL_DB_PATH`
- `POSTGRESQL_DB_PARAMS`
- `POSTGRESQL_DB_QUERY`
- `POSTGRESQL_DB_FRAGMENT`
- `POSTGRESQL_DB_USERNAME`
- `POSTGRESQL_DB_PASSWORD`
- `POSTGRESQL_DB_HOSTNAME`
- `POSTGRESQL_DB_PORT`

> See also: [How to add an integration to a
> charm](https://juju.is/docs/sdk/implement-integrations-in-a-charm)


## Manage secrets for a 12-factor app charm

A user secret can be added to a charm and all the keys and values in the secret will be
exposed as environment variables. Add the secret configuration option in
`charmcraft.yaml`:

```yaml
config:
  options:
    api-token:
      type: secret
      description: Secret needed to access some API secret information
```

Once the charm is deployed, you can add a Juju secret to the model:

```bash
juju add-secret my-api-token value=1234 othervalue=5678
```

The output from the previous command will look something like:

```console
secret:cru00lvmp25c77qa0qrg
```

From the output of the previous command, you can get the Juju secret ID. 
Grant the application access to view the value of the secret:

```bash
juju grant-secret my-api-token <app name>
```

Add the Juju secret ID to the application:

```bash
juju config <app name> api-token=secret:cru00lvmp25c77qa0qrg
```

```{dropdown} Flask application

The following environment variables are available for the application:

- `FLASK_API_TOKEN_VALUE: "1234"`
- `FLASK_API_TOKEN_OTHERVALUE: "5678"`

> See also: [How to manage secrets](https://juju.is/docs/juju/manage-secrets)
```

```{dropdown} Django application

The following environment variables are available for the application:

- `DJANGO_API_TOKEN_VALUE: "1234"`
- `DJANGO_API_TOKEN_OTHERVALUE: "5678"`

> See also: [How to manage secrets](https://juju.is/docs/juju/manage-secrets)
```

```{dropdown} FastAPI application

The following environment variables are available for the application:

- `APP_API_TOKEN_VALUE: "1234"`
- `APP_API_TOKEN_OTHERVALUE: "5678"`

> See also: [How to manage secrets](https://juju.is/docs/juju/manage-secrets)
```

```{dropdown} Go application

The following environment variables are available for the application:

- `APP_API_TOKEN_VALUE: "1234"`
- `APP_API_TOKEN_OTHERVALUE: "5678"`

> See also: [How to manage secrets](https://juju.is/docs/juju/manage-secrets)
```


## Use 12-factor app charms


### (If your charm is a Django charm) Create an admin user

Use the `create-superuser` action to create a new Django admin account:

```bash
juju run <app name> create-superuser username=<username> email=<email>
```

You must provide the username and email address. 


### (If your workload depends on a database) Migrate the database

If your app depends on a database, it is common to run a database migration
script before app startup which, for example, creates or modifies tables. This
can be done by including the `migrate.sh` script in the root of your project. It
will be executed with the same environment variables and context as the 12-factor
app.

If the migration script fails, it will retry upon `update-status`. The migration script
will run on every unit. The script is assumed to be idempotent (in other words, can be
run multiple times) and that it can be run on multiple units simultaneously without
issue. Handling multiple migration scripts that run concurrently can be achieved by, for
example, locking any tables during the migration.
