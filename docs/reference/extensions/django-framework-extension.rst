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

.. include:: /reuse/reference/extensions/non_optional_config.rst

.. |base_url| replace:: ``DJANGO_BASE_URL``
.. |juju_integrate_postgresql| replace:: ``juju integrate <django charm> postgresql``
.. |framework| replace:: Django
.. |framework_prefix| replace:: DJANGO

.. include:: /reuse/reference/extensions/integrations.rst
.. include:: /reuse/reference/extensions/environment_variables.rst


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


Worker and Scheduler Services
-----------------------------

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


.. _django-migrate-sh:

About the ``migrate.sh`` file
---------------------------------

If your app depends on a database it is common to run a database migration script before
app startup which, for example, creates or modifies tables. This can be done by
including the ``migrate.sh`` script in the root of your project. It will be executed
with the same environment variables and context as the Django app.

Charmcraft runs the migration script on every unit. In doing so, it assumes the script
is idempotent, meaning it doesn't mutate when rerun with the same input, and can be run
on multiple units at the same time. You can make your script idempotent by, for example,
locking any tables for the duration of the migration.

If the migration script fails, the app won't start, and the app charm becomes blocked.


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

.. _django-grafana-graphs:

Grafana dashboard graphs
------------------------

If the Django app is connected to the `Canonical Observability Stack
(COS) <https://charmhub.io/topics/canonical-observability-stack>`_,
the Grafana dashboard **Django Operator** displays the following
default graphs:

* Requests: Number of requests over time.
* Status code count: Number of requests broken by responses status code.
* Requests per second: Number of requests per second over time.
* 2XX Rate: Portion of responses that were successful (in the 200 range).
* 3XX Rate: Portion of responses that were redirects (in the 300 range).
* 4XX Rate: Portion of responses that were client errors (in the 400 range).
* 5XX Rate: Portion of responses that were server errors (in the 500 range).
* Request average duration: Average duration of the requests over time.
* Request duration percentile: The 50th, 90th, and 99th percentile of all the
  request duration lengths after sorting them from slowest to fastest. For
  example, the 50th percentile represents the length of time (or less) that
  50\% of the requests lasted.
