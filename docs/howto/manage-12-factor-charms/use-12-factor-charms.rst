.. _use-12-factor-charms:

Use 12-factor app charms
========================


(If your charm is a Django charm) Create an admin user
------------------------------------------------------

Use the ``create-superuser`` action to create a new Django admin account:

.. code-block:: bash

    juju run <app name> create-superuser username=<username> email=<email>


(If your workload depends on a database) Migrate the database
-------------------------------------------------------------

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
