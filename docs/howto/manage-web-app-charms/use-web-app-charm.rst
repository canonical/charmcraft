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

View Grafana dashboard
~~~~~~~~~~~~~~~~~~~~~~

To view the dashboard, get the endpoints:

.. code-block::

    juju show-unit catalogue/0 | grep url
    juju run grafana/leader get-admin-password

These commands output URLs and the default admin password. Look for the URL
with the Grafana postfix with the syntax
``http://<IP_ADDRESS>/<JUJU_MODEL_NAME>-grafana``. Here, ``JUJU_MODEL_NAME``
is the name of the Juju model on which you deployed your web app.

Append the ``/dashboards``
postfix to the URL and log in using the admin password to view the dashboards
overview page.

To view the specific dashboard for your web app, click :guilabel:`General` and
then on :guilabel:`WebApp Operator`, where "WebApp" is a stand-in for the
framework of your web app.

View application logs
~~~~~~~~~~~~~~~~~~~~~

Go to ``http://<IP_ADDRESS>/<JUJU_MODEL_NAME>-grafana/explore``.
At the top of the page, set the label filters to ``juju_application`` and then
pick ``JUJU_MODEL_NAME`` from the dropdown menu on the right.
To view the logs, click :guilabel:`Run query`.
