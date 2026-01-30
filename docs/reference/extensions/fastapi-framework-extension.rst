.. _fastapi-framework-extension:


FastAPI framework extension
===========================

The ``fastapi-framework`` extension includes configuration options
customised for a FastAPI application. This document describes all the
keys that a user may interact with.

.. tip::

    If you'd like to see the full contents contributed by this extension,
    see :ref:`How to manage extensions <manage-extensions>`.

.. _fastapi-framework-extension-config-options:

``charmcraft.yaml`` > ``config`` > ``options``
----------------------------------------------

You can use the predefined options (run ``charmcraft expand-extensions``
for details) but also add your own, as needed.

In the latter case, any option you define will be used to generate
environment variables; a user-defined option ``config-option-name`` will
generate an environment variable named ``APP_CONFIG_OPTION_NAME`` where
the option name is converted to upper case, dashes will be converted to
underscores and the ``APP_`` prefix will be added.

In either case, you will be able to set it in the usual way by running
``juju config <application> <option>=<value>``. For example, if you
define an option called ``token``, as below, this will generate a
``APP_TOKEN`` environment variable, and a user of your charm can set it
by running ``juju config <application> token=<token>``.

.. code-block:: yaml

    config:
      options:
        token:
          description: The token for the service.
          type: string

.. include:: /reuse/reference/extensions/non_optional_config.rst

.. |base_url| replace:: ``APP_BASE_URL``
.. |juju_integrate_postgresql| replace:: ``juju integrate <fastapi charm> postgresql``
.. |framework| replace:: FastAPI
.. |framework_prefix| replace:: APP

.. _fastapi-framework-extension-relations:

.. include:: /reuse/reference/extensions/integrations.rst

.. _fastapi-framework-extension-environment-variables:

.. include:: /reuse/reference/extensions/environment_variables.rst

.. _fastapi-framework-extension-http-proxy:

.. include:: /reuse/reference/extensions/http_proxy.rst

.. _fastapi-framework-extension-worker-scheduler-services:

Worker and Scheduler Services
-----------------------------

Extra services defined in the file
:external+rockcraft:ref:`rockcraft.yaml <reference-rockcraft-yaml>`
with names ending in ``-worker`` or ``-scheduler`` will be passed the
same environment variables as the main application. If there is more
than one unit in the application, the services with the name ending in
``-worker`` will run in all units. The services with name ending in
``-scheduler`` will only run in one of the units of the application.

.. _fastapi-framework-extension-observability:

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

    juju integrate fastapi-k8s grafana
    juju integrate fastapi-k8s loki
    juju integrate fastapi-k8s prometheus

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


.. _fastapi-migrate-sh:

Regarding the ``migrate.sh`` file
---------------------------------

If your app depends on a database it is common to run a database
migration script before app startup which, for example, creates or
modifies tables. This can be done by including the ``migrate.sh`` script
in the root of your project. It will be executed with the same
environment variables and context as the FastAPI application.

If the migration script fails, the app won't be started and the app
charm will go into blocked state. The migration script will be run on
every unit and it is assumed that it is idempotent (can be run multiple
times) and that it can be run on multiple units at the same time without
causing issues. This can be achieved by, for example, locking any tables
during the migration.

If you prefer you can also use different tooling for migration, for example `Alembic
<https://alembic.sqlalchemy.org/en/latest/>`__.

.. _fastapi-framework-extension-secrets:

Secrets
-------

Juju secrets can be passed as environment variables to your FastAPI application. The
secret ID has to be passed to the application as a config option in the project file of
type ``secret``. This config option has to be populated with the secret ID, in the
format ``secret:<secret ID>``.

The environment variable name passed to the application will be:

.. code-block:: bash

    APP_<config option name>_<key inside the secret>

The ``<config option name>`` and ``<key inside the secret>`` keywords in
the environment variable name will have the hyphens replaced by
underscores and all the letters capitalised.

   See more: :external+juju:ref:`Juju | Secret <secret>`

.. _fastapi-grafana-graphs:

Grafana dashboard graphs
------------------------

If the FastAPI app is connected to the `Canonical Observability Stack
(COS) <https://charmhub.io/topics/canonical-observability-stack>`_,
the Grafana dashboard **FastAPI Operator** displays the following
default graphs:

* Requests: Number of requests over time.
* Status code count: Number of requests broken by responses status code.
* Requests per second: Number of requests per second over time.
* 2XX Rate: Portion of responses that were successful (in the 200 range).
* 3XX Rate: Portion of responses that were redirects (in the 300 range).
* 4XX Rate: Portion of responses that were client errors (in the 400 range).
* 5XX Rate: Portion of responses that were server errors (in the 500 range).
* Request duration percentile: The 50th, 90th, and 99th percentile of all the
  request duration lengths after sorting them from slowest to fastest. For
  example, the 50th percentile represents the length of time (or less) that
  50\% of the requests lasted.

.. note::

  The default Grafana dashboard makes use of the ``prometheus_fastapi_instrumentator``
  package. To enable the metrics, you need to install the package and add the
  following lines to your FastAPI application code:

  .. code-block:: python
    :caption: app.py

    from prometheus_fastapi_instrumentator import Instrumentator

    app = FastAPI()

    Instrumentator().instrument(app).expose(app)
