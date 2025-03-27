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

View application logs
~~~~~~~~~~~~~~~~~~~~~

Go to ``http://<IP_ADDRESS>/<JUJU_MODEL_NAME>-grafana/explore``, where
the URL is the one you fetched previously.

Filter for the label ``juju_application`` and then
select your Juju model name from the dropdown.
Then, click :guilabel:`Run query`.

The logs shown in the dashboard depend on the web framework, but they are
typically access logs, or the history of the requests sent to your web
app and their status codes.
