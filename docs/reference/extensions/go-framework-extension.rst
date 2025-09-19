.. _go-framework-extension:


Go framework extension
======================

The ``go-framework`` extension includes configuration options customised for a Go
application. This document describes all the keys that a user may interact with.

.. tip::

    If you'd like to see the full contents contributed by this extension,
    see :ref:`How to manage extensions <manage-extensions>`.


``charmcraft.yaml`` > ``config`` > ``options``
----------------------------------------------

You can use the predefined options (run ``charmcraft expand-extensions`` for details)
but also add your own, as needed.

The predefined configuration options for the ``go-framework`` are:

* **app-port**: Port in which the application should listen. The ingress will be
  configured using this port. The environment variable passed to the app is
  ``APP_PORT``. Default value is 8080.

* **app-secret-key**: Long secret you can use for sessions, csrf or any other thing
  where you need a random secret shared by all units. The environment variable passed
  to the app is ``APP_METRICS_PORT``. The default value is random.

* **metrics-port**: Port where the prometheus metrics will be scraped. The environment
  variable passed to the app is ``APP_PORT``. Default value is 8080.

* **metrics-path**: Path where the prometheus metrics will be scraped. The environment
  variable passed to the app is ``APP_METRICS_PATH``. Default value is ``/metrics``.

In case you want to add extra configuration options, any option you define will be used
to generate environment variables; a user-defined option ``config-option-name`` will
generate an environment variable named ``APP_CONFIG_OPTION_NAME`` where the option name
is converted to upper case and dashes are converted to underscores.

In either case, you will be able to set it in the usual way by running ``juju config
<application> <option>=<value>``. For example, if you define an option called ``token``,
as below, this will generate a ``APP_TOKEN`` environment variable, and a user of your
charm can set it by running ``juju config <application> token=<token>``.

.. code-block:: yaml

    config:
      options:
        token:
          description: The token for the service.
          type: string

.. include:: /reuse/reference/extensions/non_optional_config.rst

.. |base_url| replace:: ``APP_BASE_URL``
.. |juju_integrate_postgresql| replace:: ``juju integrate <go charm> postgresql``
.. |framework| replace:: Go
.. |framework_prefix| replace:: APP

.. include:: /reuse/reference/extensions/integrations.rst
.. include:: /reuse/reference/extensions/environment_variables.rst


HTTP Proxy
----------

Proxy settings should be set as model configurations. Charms generated using the
``go-framework`` extension will make the Juju proxy settings available as the
``HTTP_PROXY``, ``HTTPS_PROXY`` and ``NO_PROXY`` environment variables. For example, the
``juju-http-proxy`` environment variable will be exposed as ``HTTP_PROXY`` to the Go
service.

    See more: `List of model configuration
    keys <https://juju.is/docs/juju/list-of-model-configuration-keys>`_


Worker and Scheduler Services
-----------------------------

Extra services defined in the file
:external+rockcraft:ref:`rockcraft.yaml <rockcraft.yaml_reference>`
with names ending in ``-worker`` or ``-scheduler`` will be passed the same environment
variables as the main application. If there is more than one unit in the application,
the services with the name ending in ``-worker`` will run in all units. The services
with name ending in ``-scheduler`` will only run in one of the units of the application.


Observability
-------------

12-Factor charms are designed to be easily observable using the
`Canonical Observability Stack
<https://charmhub.io/topics/canonical-observability-stack>`__.

You can easily integrate your charm with
`Loki <https://charmhub.io/loki-k8s>`__,
`Prometheus <https://charmhub.io/prometheus-k8s>`__ and
`Grafana <https://charmhub.io/grafana-k8s>`__ using Juju.

.. code-block:: bash

    juju integrate go-k8s grafana
    juju integrate go-k8s loki
    juju integrate go-k8s prometheus

After integration, you will be able to observe your workload
using Grafana dashboards.

In addition to that you can also trace your workload code
using `Tempo <https://charmhub.io/topics/charmed-tempo-ha>`__.

To learn about how to deploy Tempo you can read the
documentation `here <https://charmhub.io/topics/charmed-tempo-ha>`__.

OpenTelemetry will automatically read the environment variables
and configure the OpenTelemetry SDK to use them.
See the `OpenTelemetry documentation
<https://opentelemetry-python.readthedocs.io/en/latest/>`__
for further information about tracing.


.. _go-migrate-sh:

Regarding the ``migrate.sh`` file
---------------------------------

If your app depends on a database it is common to run a database migration script before
app startup which, for example, creates or modifies tables. This can be done by
including the ``migrate.sh`` script in the root of your project. It will be executed
with the same environment variables and context as the Go app.

If the migration script fails, the app won't be started and the app charm will go into
blocked state. The migration script will be run on every unit and it is assumed that it
is idempotent (can be run multiple times) and that it can be run on multiple units at
the same time without causing issues. This can be achieved by, for example, locking any
tables during the migration.

If you prefer you can also use different tooling for migration, for example
`golang-migrate <https://github.com/golang-migrate/migrate/>`__ or
`goose <https://github.com/pressly/goose/>`__ .


Secrets
-------

Juju secrets can be passed as environment variables to your Go application. The secret
ID has to be passed to the application as a config option in the project file of type
``secret``. This config option has to be populated with the secret ID, in the format
``secret:<secret ID>``.

The environment variable name passed to the application will be:

.. code-block:: bash

    APP_<config option name>_<key inside the secret>

The ``<config option name>`` and ``<key inside the secret>`` keywords in the environment
variable name will have the hyphens replaced by underscores and all the letters
capitalised.

   See more: :external+juju:ref:`Juju | Secret <secret>`
