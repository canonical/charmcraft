.. _use-12-factor-charms:

Use a 12-factor app charm
=========================


Create an admin user for a Django app charm
-------------------------------------------

Use the ``create-superuser`` action to create a new Django admin account:

.. code-block:: bash

    juju run <app name> create-superuser username=<username> email=<email>


Migrate the workload database
-----------------------------

If your app depends on a database, it is common to run a database migration
script before app startup which, for example, creates or modifies tables. This
can be done by including the ``migrate.sh`` script in the root of your project.
It will be executed with the same environment variables and context as the
12-factor app.

If the migration script fails, it will retry upon ``update-status``. The migration
script will run on every unit. The script is assumed to be idempotent (in other words,
can be run multiple times) and that it can be run on multiple units simultaneously
without issue. Handling multiple migration scripts that run concurrently
can be achieved by, for example, locking any tables during the migration.

Using ``migrate.sh`` isn't mandatory. You can use programmatic approaches instead. Some
popular libraries for programmatic database migration are:

- `Alembic <https://alembic.sqlalchemy.org/en/latest/>`__ for Flask and FastAPI.
- `golang-migrate <https://github.com/golang-migrate/migrate/>`__ or `goose
  <https://github.com/pressly/goose/>`__ for Go.
- `prisma <https://www.npmjs.com/package/prisma/>`__ and `knex
  <https://www.npmjs.com/package/knex/>`__ for Express.

.. _use-12-factor-charms-troubleshoot:

Troubleshoot the charm
----------------------

This guide provides helpful commands to run in situations where your web app
deployment is not successful (for instance, if your app crashes).

Get the app logs
~~~~~~~~~~~~~~~~

One important step of troubleshooting is to review the app logs for errors.
They are a vital course of action because they flag any uncaught exceptions in
your code, but they are also a constant touchpoint when diagnosing and
debugging issues. You'll first need to obtain the logs for your particular
framework using Pebble.

To view the Pebble logs for a deployed web app, run:

.. tabs::

    .. group-tab:: Django

        .. code-block:: bash

            juju ssh --container django-app <django-app-name>/0 pebble logs

    .. group-tab:: Express

        .. code-block:: bash

            juju ssh --container app <express-app-name>/0 pebble logs

    .. group-tab:: FastAPI

        .. code-block:: bash

            juju ssh --container app <fastapi-app-name>/0 pebble logs

    .. group-tab:: Flask

        .. code-block:: bash

            juju ssh --container flask-app <flask-app-name>/0 pebble logs

    .. group-tab:: Go

        .. code-block:: bash

            juju ssh --container app <go-app-name>/0 pebble logs

    .. group-tab:: Spring Boot

        .. code-block:: bash

            juju ssh <spring-boot-app-name>/0 \
              PEBBLE_SOCKET=/charm/containers/app/pebble.socket /charm/bin/pebble logs

.. seealso::

   `Pebble CLI commands | logs
   <https://documentation.ubuntu.com/pebble/reference/cli-commands/#logs>`_

View app details
~~~~~~~~~~~~~~~~

To view more details about the web app itself, run:

.. tabs::

    .. group-tab:: Django

        .. code-block:: bash

            juju ssh --container django-app <django-app-name>/0 pebble plan

    .. group-tab:: Express

        .. code-block:: bash

            juju ssh --container app <express-app-name>/0 pebble plan

    .. group-tab:: FastAPI

        .. code-block:: bash

            juju ssh --container app <fastapi-app-name>/0 pebble plan

    .. group-tab:: Flask

        .. code-block:: bash

            juju ssh --container flask-app <flask-app-name>/0 pebble plan

    .. group-tab:: Go

        .. code-block:: bash

            juju ssh --container app <go-app-name>/0 pebble plan

    .. group-tab:: Spring Boot

        .. code-block:: bash

            juju ssh <spring-boot-app-name>/0 \
              PEBBLE_SOCKET=/charm/containers/app/pebble.socket /charm/bin/pebble plan

This command provides information on what services you may start in your app
and what environment variables exist (i.e., what is available for the app to
use).

.. seealso::

   `Pebble CLI commands | plan
   <https://documentation.ubuntu.com/pebble/reference/cli-commands/#plan>`_

SSH into the Juju container
~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can debug the app directly and monitor its status by SSHing into the
Juju container:

.. tabs::

    .. group-tab:: Django

        .. code-block:: bash

            juju ssh --container django-app <django-app-name>/0 \
              pebble exec --context=django -- bash

    .. group-tab:: Express

        .. code-block:: bash

            juju ssh --container app <express-app-name>/0 \
              pebble exec --context=expressjs -- bash

    .. group-tab:: FastAPI

        .. code-block:: bash

            juju ssh --container app <fastapi-app-name>/0 \
              pebble exec --context=fastapi -- bash

    .. group-tab:: Flask

        .. code-block:: bash

            juju ssh --container flask-app <flask-app-name>/0 \
              pebble exec --context=flask -- bash

    .. group-tab:: Go

        .. code-block:: bash

            juju ssh --container app <go-app-name>/0 \
              pebble exec --context=go -- bash

    .. group-tab:: Spring Boot

        .. code-block:: bash

            juju ssh <spring-boot-app-name>/0 \
              PEBBLE_SOCKET=/charm/containers/app/pebble.socket \
              /charm/bin/pebble  exec --context=spring-boot -- bash

.. important::

    This command is specific to the ``context`` of your web app and will run
    successfully only if the ``context`` already exists, in other words, if the
    app has been started. If the app has not been started (for instance, if the
    app has not been properly integrated to the PostgreSQL database), then this
    command will fail as the context does not exist.

If successful, the command opens a SSH shell into the web app. From there,
you can debug the app itself, manually run an action, or attempt to
manually start the web app. The web app can be found in the ``/`` directory
of the container, for instance, ``/django/app``.

.. seealso::

   `Juju documentation | ssh
   <https://documentation.ubuntu.com/juju/latest/user/reference/
   juju-cli/list-of-juju-cli-commands/ssh/>`_

Check MicroK8s pod services and logs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Check the currently deployed Kubernetes resources in the
``<model-namespace>``, which is the same as the Juju model name:

.. code::

   microk8s.kubectl get all -n <model-namespace>

This command outputs a list of all the MicroK8s resources in the web app's
Juju model.

Check the logs for a specific MicroK8s pod:

.. code::

   microk8s kubectl logs <pod-name> -n <model-namespace>

This command outputs the logs of the sidecar container pod. To fetch logs
specific to the workload of the web app, you need to specify the container
name of the web app with the ``-c`` option.

.. tabs::

    .. group-tab:: Django

        .. code-block:: bash

            microk8s kubectl logs <pod-name> -n <model-namespace> -c django-app

    .. group-tab:: Express

        .. code-block:: bash

            microk8s kubectl logs <pod-name> -n <model-namespace> -c app

    .. group-tab:: FastAPI

        .. code-block:: bash

            microk8s kubectl logs <pod-name> -n <model-namespace> -c app

    .. group-tab:: Flask

        .. code-block:: bash

            microk8s kubectl logs <pod-name> -n <model-namespace> -c flask-app

    .. group-tab:: Go

        .. code-block:: bash

            microk8s kubectl logs <pod-name> -n <model-namespace> -c app

    .. group-tab:: Spring Boot

        .. code-block:: bash

            microk8s kubectl logs <pod-name> -n <model-namespace> -c app

.. seealso::

   `MicroK8s | Troubleshooting <https://microk8s.io/docs/troubleshooting>`_

Check Juju logs
~~~~~~~~~~~~~~~

If you want to check the logs and status of your web app charm, Juju contains
debugging and logging information.

Use ``juju debug-log`` to view a running log for the model on which you
deployed your web app. The log outputs live messages and errors related to the
charm that you can follow (tail). To stop following the logs,
press :kbd:`Ctrl` + :kbd:`C`.

You can also update the model configuration to output more charm debugging
information using
``juju model-config "logging-config=<root>=INFO;unit=DEBUG"``.

.. seealso::

   `Juju documentation | How to manage logs
   <https://documentation.ubuntu.com/juju/latest/user/howto/manage-logs/>`_


Report an issue
~~~~~~~~~~~~~~~

If you cannot solve your issue, please reach out to us on
`Matrix <https://matrix.to/#/#12-factor-charms:ubuntu.com>`_ for hands-on
debugging. When describing your issue, please include the output of the
Juju and Pebble logs.

Use observability
-----------------

First, :ref:`integrate your web app with the Canonical Observability
Stack <integrate_web_app_cos>`.

Connect to the Grafana service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Retrieve the observability endpoints:

.. code-block:: bash

    juju show-unit catalogue/0 | grep url

Retrieve the password of the default Grafana admin account:

.. code-block:: bash

    juju run grafana/leader get-admin-password

From the list of URLs, look for the endpoint that contains a ``grafana``
suffix. This URL has the format:

.. terminal::

    http://<IP_ADDRESS>/<JUJU_MODEL_NAME>-grafana

Here, ``JUJU_MODEL_NAME`` is the name of the Juju model on which you deployed
your web app.


Access the Grafana web app
~~~~~~~~~~~~~~~~~~~~~~~~~~

To view the dashboards overview page, append the ``/dashboards``
suffix to the URL and log in using the admin password.

To view the specific dashboard for your web app, click **General** and
then on **WebApp Operator**, where "WebApp" is a stand-in for the
framework of your web app.

.. seealso::

  :ref:`Flask framework extension | Grafana dashboard graphs <flask-grafana-graphs>`

  :ref:`Django framework extension | Grafana dashboard graphs <django-grafana-graphs>`

View app logs
~~~~~~~~~~~~~

Go to ``http://<IP_ADDRESS>/<JUJU_MODEL_NAME>-grafana/explore``, where
the URL is the one you fetched previously.

Filter for the label ``juju_application`` and then
select your Juju model name from the dropdown.
Then, click **Run query**.

The logs shown in the dashboard depend on the web framework, but they are
typically access logs, or the history of the requests sent to your web
app and their status codes.

The Pebble logs are available via Grafana or Loki and can be viewed in
the **WebApp Operator** dashboard for Flask and Django.
For other frameworks, you may access the logs by picking ``loki`` in the
``http://<IP_ADDRESS>/<JUJU_MODEL_NAME>-grafana/explore`` page.


Configure TLS for a web app charm
---------------------------------

You can configure TLS if your ingress provider charm supports integration with
a certificate provider charm. To configure TLS locally, you can use the
`Self Signed Certificates <https://charmhub.io/self-signed-certificates>`_
charm as a certificate provider.

First, :ref:`integrate your web app with ingress
<integrate-web-app-charm-integrate-ingress>`.

Using the `Nginx Ingress Integrator <https://charmhub.io/nginx-ingress-integrator>`_
charm as an ingress provider, set the hostname with:

.. code-block:: bash

    juju config nginx-ingress-integrator service-hostname=<yourdomain.example.com>

Deploy the `Self Signed X.509 Certificates
<https://charmhub.io/self-signed-certificates>`_ charm and integrate the two charms:

.. code-block:: bash

    juju deploy self-signed-certificates
    juju integrate self-signed-certificates nginx-ingress-integrator

Your 12-factor app is now accessible over HTTPS. If you access the external URL of your
app using HTTP, it returns an HTTP ``308 Permanent Redirect`` status and a redirect to
the HTTPS URL. You can access the HTTPS URL of your app with a command like:

.. code-block:: bash

   curl -v --insecure https://<yourdomain.example.com> \
     --resolve <yourdomain.example.com>:443:<ingress-ip>

.. note::

    The ``--insecure`` option is needed because the certificate authority in the
    ``self-signed-certificate`` charm is not trusted.
    The ``--resolve <yourdomain.example.com>:443:<ingress-ip>`` option is a way of
    resolving the hostname of the request without
    setting a DNS record.

To obtain a TLS certificate signed by a trusted certificate authority (CA)
using the ACME protocol, use the `LEGO <https://charmhub.io/lego>`_
charm instead.


Run a worker or scheduler process in your workloads
---------------------------------------------------

You can run extra processes in the workload charm that receive the same environment
variables as the main app. These services must be added to the
project file as entries of the ``services`` key. If the service name
ends with ``-worker`` it will run in all units of the app,
while if the name ends with ``-scheduler`` it will run in only one unit.

A common use case is running `Celery beat`_
as a scheduler to kick off tasks at regular intervals, together with
`Celery worker servers`_ to execute those tasks.
Celery beat should run in only one unit, while Celery worker servers
will run in all units.

For a Flask app that has the Celery app in the module
``webapp.app.celery_app``, you can declare them as services like this:

.. code-block:: yaml
    :caption: rockcraft.yaml

    services:
      celery-worker:
        override: replace
        command: celery -A webapp.app.celery_app worker --loglevel=INFO
        startup: enabled
        user: _daemon_
        working-dir: /flask/app
      celery-beat-scheduler:
        override: replace
        command: celery -A webapp.app.celery_app beat -s /tmp/celerybeat-schedule
        startup: enabled
        user: _daemon_
        working-dir: /flask/app


The service named ``celery-worker`` will run in all units of the app,
while the service named ``celery-beat-scheduler`` will run in only one unit.

.. _`Celery beat`: https://docs.celeryq.dev/en/latest/userguide/periodic-tasks.html
.. _`Celery worker servers`: https://docs.celeryq.dev/en/latest/getting-started/first-steps-with-celery.html
