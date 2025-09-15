.. _write-your-first-kubernetes-charm-for-a-flask-app:

Write your first Kubernetes charm for a Flask app
=================================================

Imagine you have a Flask app backed up by a database
such as PostgreSQL and need to deploy it. In a traditional setup,
this can be quite a challenge, but with Charmcraft you'll find
yourself packaging and deploying your Flask app in no time.

In this tutorial we will build a Kubernetes charm for a Flask
app using Charmcraft, so we can have a Flask app
up and running with Juju. Let's get started!

This tutorial should take 90 minutes for you to complete.

If you're new to the charming world, Flask apps are
specifically supported with a template to quickly generate a
**rock** and a matching template to generate a **charm**.
A rock is a special kind of OCI-compliant container image, while a
charm is a software operator for cloud operations that use the Juju
orchestration engine. The combined result is a Flask app that
can be deployed, configured, scaled, integrated, and so on,
on any Kubernetes cluster.


What you'll need
----------------

- A local system, e.g., a laptop, with AMD64 or ARM64 architecture which
  has sufficient resources to launch a virtual machine with 4 CPUs,
  4 GB RAM, and a 50 GB disk.
- Familiarity with Linux.

The RAM and disk space are necessary to set up all the required software and
to facilitate the creation of the rock and charm. If your local system has less
than the sufficient resources, the tutorial will take longer to complete.

What you'll do
--------------

#. Create a Flask app.
#. Use that to create a rock with Rockcraft.
#. Use that to create a charm with Charmcraft.
#. Use that to test, deploy, configure, etc., your Flask app on a local
   Kubernetes cloud with Juju.
#. Repeat the process, mimicking a real development process.

.. important::

    Should you get stuck or notice issues, please get in touch on
    `Matrix <https://matrix.to/#/#12-factor-charms:ubuntu.com>`_ or
    `Discourse <https://discourse.charmhub.io/>`_


Set things up
-------------

.. include:: /reuse/tutorial/setup_stable.rst
.. |12FactorApp| replace:: Flask

Let's create a new directory for this tutorial and enter into it:

.. code-block:: bash

    mkdir flask-hello-world
    cd flask-hello-world

Finally, install ``python3-venv`` and create a virtual environment:

.. literalinclude:: code/flask/task.yaml
    :language: bash
    :start-after: [docs:create-venv]
    :end-before: [docs:create-venv-end]
    :dedent: 2


Create the Flask app
--------------------

Let's start by creating the "Hello, world" Flask app that
will be used for this tutorial.

Create a new requirements file with ``nano requirements.txt``.
Then, copy the following text into it, and save:

.. literalinclude:: code/flask/requirements.txt
    :caption: ~/flask-hello-world/requirements.txt

.. note::

    The ``psycopg2-binary`` package is needed so the Flask app can
    connect to PostgreSQL, which we will do at the end of this tutorial.

Install the packages:

.. literalinclude:: code/flask/task.yaml
    :language: bash
    :start-after: [docs:install-requirements]
    :end-before: [docs:install-requirements-end]
    :dedent: 2

In the same directory, create a file called ``app.py``.
Then copy and save the following code into the file:

.. literalinclude:: code/flask/app.py
    :caption: ~/flask-hello-world/app.py
    :language: python


Run the Flask app locally
-------------------------

Now that we have a virtual environment with all the dependencies, let's
run the Flask app to verify that it works:

.. code-block:: bash

    flask run -p 8000

Verify the app
~~~~~~~~~~~~~~

Test the Flask app by using ``curl`` to send a request to the root
endpoint. You will need a new terminal for this; use
``multipass shell charm-dev`` to open a new terminal in Multipass:

.. literalinclude:: code/flask/task.yaml
    :language: bash
    :start-after: [docs:curl-flask]
    :end-before: [docs:curl-flask-end]
    :dedent: 2

The Flask app should respond with ``Hello, world!``.

Close the app
~~~~~~~~~~~~~

The Flask app looks good, so we can stop it for now from the
original terminal using :kbd:`Ctrl` + :kbd:`C`.


Pack the Flask app into a rock
------------------------------

Now let's create a container image for our Flask app. We'll use a rock,
which is an OCI-compliant container image based on Ubuntu.

First, we'll need a ``rockcraft.yaml`` project file. We'll take advantage of a
pre-defined extension in Rockcraft with the ``--profile`` flag that caters
initial rock files for specific web app frameworks. Using the
``flask-framework`` profile, Rockcraft automates the creation of
``rockcraft.yaml`` and tailors the file for a Flask app.
From the ``~/flask-hello-world`` directory, initialize the rock:

.. literalinclude:: code/flask/task.yaml
    :language: bash
    :start-after: [docs:create-rockcraft-yaml]
    :end-before: [docs:create-rockcraft-yaml-end]
    :dedent: 2

The ``rockcraft.yaml`` file will automatically be created and set the name
based on your working directory.

Let's verify that the project file is compatible with your host machine.
Check the architecture of your system:

.. code-block:: bash

    dpkg --print-architecture

Check out the contents of ``rockcraft.yaml``:

.. code-block:: bash

    cat rockcraft.yaml

The top of the file should look similar to the following snippet:

.. code-block:: yaml
    :caption: ~/flask-hello-world/rockcraft.yaml

    name: flask-hello-world
    # see https://documentation.ubuntu.com/rockcraft/en/1.6.0/explanation/bases/
    # for more information about bases and using 'bare' bases for chiselled rocks
    base: ubuntu@22.04 # the base environment for this Flask app
    version: '0.1' # just for humans. Semantic versioning is recommended
    summary: A summary of your Flask app # 79 char long summary
    description: |
        This is flask-hello-world's description. You have a paragraph or two to tell the
        most important story about it. Keep it under 100 words though,
        we live in tweetspace and your description wants to look good in the
        container registries out there.
    # the platforms this rock should be built on and run on.
    # you can check your architecture with `dpkg --print-architecture`
    platforms:
        amd64:
        # arm64:
        # ppc64el:
        # s390x:

Verify that the ``name`` is ``flask-hello-world``.

The ``platforms`` key must match the architecture of your host.
Edit the ``platforms`` key in ``rockcraft.yaml`` if required.

Now let's pack the rock:

.. literalinclude:: code/flask/task.yaml
    :language: bash
    :start-after: [docs:pack]
    :end-before: [docs:pack-end]
    :dedent: 2

Depending on your system and network, this step can take several
minutes to finish.

.. admonition:: For more options when packing rocks

    See the :external+rockcraft:ref:`ref_commands_pack` command reference.

Once Rockcraft has finished packing the Flask rock,
the terminal will respond with something similar to
``Packed flask-hello-world_0.1_<architecture>.rock``. The file name
reflects your system's architecture. After the initial
pack, subsequent rock packings are faster.

The rock needs to be copied to the MicroK8s registry. This registry acts as a
temporary Dockerhub, storing OCI archives so they can be downloaded and
deployed in the Kubernetes cluster. Copy the rock:

.. literalinclude:: code/flask/task.yaml
    :language: bash
    :start-after: [docs:skopeo-copy]
    :end-before: [docs:skopeo-copy-end]
    :dedent: 2

This command contains the following pieces:

- ``--insecure-policy``: adopts a permissive policy that
  removes the need for a dedicated policy file.
- ``--dest-tls-verify=false``: disables the need for HTTPS
  and verify certificates while interacting with the MicroK8s registry.
- ``oci-archive``: specifies the rock we created for our Flask app.
- ``docker``: specifies the name of the image in the MicroK8s registry.

.. seealso::

    See more: `Ubuntu manpage | skopeo
    <https://manpages.ubuntu.com/manpages/jammy/man1/skopeo.1.html>`_


Create the charm
----------------

From the ``~/flask-hello-world`` directory, let's create a new directory
for the charm and change inside it:

.. literalinclude:: code/flask/task.yaml
    :language: bash
    :start-after: [docs:create-charm-dir]
    :end-before: [docs:create-charm-dir-end]
    :dedent: 2

Similar to the rock, we'll take advantage of a pre-defined extension in
Charmcraft with the ``--profile`` flag that caters initial charm files for
specific web app frameworks. Using the ``flask-framework`` profile,
Charmcraft automates the creation of the files needed for our charm,
including a ``charmcraft.yaml`` project file, ``requirements.txt`` and source
code for the charm. The source code contains the logic required to operate the
Flask app.

Initialize a charm named ``flask-hello-world``:

.. literalinclude:: code/flask/task.yaml
    :language: bash
    :start-after: [docs:charm-init]
    :end-before: [docs:charm-init-end]
    :dedent: 2

The files will automatically be created in your working directory.

.. tip::

    Want to learn more about all the configurations in the
    ``flask-framework`` profile? Run ``charmcraft expand-extensions``
    from the ``~/flask-hello-world/charm/`` directory.

Let's pack the charm:

.. literalinclude:: code/flask/task.yaml
    :language: bash
    :start-after: [docs:charm-pack]
    :end-before: [docs:charm-pack-end]
    :dedent: 2

Depending on your system and network, this step can take several
minutes to finish.

Once Charmcraft has finished packing the charm, the terminal will
respond with something similar to
``Packed flask-hello-world_ubuntu-24.04-<architecture>.charm``. The file name
reflects your system's architecture. After the initial
pack, subsequent charm packings are faster.

.. admonition:: For more options when packing charms

    See the :literalref:`pack<ref_commands_pack>` command reference.


Deploy the Flask app
--------------------

So far, we've packed our Flask app into a rock and used that rock to
create our corresponding charm. Now we have all the materials necessary
to deploy the Flask app with Juju.

A Juju model is needed to handle Kubernetes resources while deploying
the Flask app. The Juju model holds the app along with any supporting
components. In this tutorial, our model will hold the Flask app, ingress,
and a PostgreSQL database.

Let's create a new model:

.. literalinclude:: code/flask/task.yaml
    :language: bash
    :start-after: [docs:add-juju-model]
    :end-before: [docs:add-juju-model-end]
    :dedent: 2

Constrain the Juju model to your architecture:

.. literalinclude:: code/flask/task.yaml
    :language: bash
    :start-after: [docs:add-model-constraints]
    :end-before: [docs:add-model-constraints-end]
    :dedent: 2

Now let's use the OCI image we previously uploaded to deploy the Flask
app. Deploy using Juju by specifying the OCI image name with the
``--resource`` option:

.. literalinclude:: code/flask/task.yaml
    :language: bash
    :start-after: [docs:deploy-flask-app]
    :end-before: [docs:deploy-flask-app-end]
    :dedent: 2

It will take a few minutes to deploy the Flask app. You can monitor its
progress with:

.. code-block:: bash

    juju status --watch 2s

It can take a couple of minutes for the app to finish the deployment.
Once the status of the App has gone to ``active``, you can stop watching
using :kbd:`Ctrl` + :kbd:`C`.

.. tip::

    To monitor your deployment, keep a ``juju status`` session active in a
    second terminal.

    See more: :external+juju:ref:`Juju | juju status <command-juju-status>`

The Flask app should now be running. We can monitor the status of
the deployment using ``juju status`` which should be similar to the
following output:

.. terminal::
    :input: juju status

    Model              Controller      Cloud/Region        Version  SLA          Timestamp
    flask-hello-world  dev-controller  microk8s/localhost  3.6.2    unsupported  17:04:11+10:00

    App           Version  Status  Scale  Charm              Channel  Rev  Address         Exposed  Message
    flask-hello-world      active      1  flask-hello-world             0  10.152.183.166  no

    Unit                  Workload  Agent  Address      Ports  Message
    flask-hello-world/0*  active    idle   10.1.87.213

Let's expose the app using ingress so that we can access it. Deploy the
``nginx-ingress-integrator`` charm and integrate it with the Flask app:

.. literalinclude:: code/flask/task.yaml
    :language: bash
    :start-after: [docs:deploy-nginx]
    :end-before: [docs:deploy-nginx-end]
    :dedent: 2

The hostname of the app needs to be defined so that it is accessible via
the ingress. We will also set the default route to be the root endpoint:

.. literalinclude:: code/flask/task.yaml
    :language: bash
    :start-after: [docs:config-nginx]
    :end-before: [docs:config-nginx-end]
    :dedent: 2

Monitor ``juju status`` until everything has a status of ``active``.

Test the deployment by sending a request via the ingress:

.. code-block:: bash

    curl http://flask-hello-world --resolve flask-hello-world:80:127.0.0.1

The request should return the ``Hello, world!`` greeting.

.. note::

    The ``--resolve flask-hello-world:80:127.0.0.1`` option to the ``curl``
    command is a way of resolving the hostname of the request without
    setting a DNS record.


The development cycle
---------------------

So far, we have worked through the entire cycle, from creating an app to deploying it.
But now – as in every real-world case -- we will go through the experience of
iterating to develop the app, and deploy each iteration.

Provide a configuration
~~~~~~~~~~~~~~~~~~~~~~~

To demonstrate how to provide a configuration to the Flask app,
we will make the greeting configurable. We will expect this
configuration option to be available in the Flask app configuration under the
keyword ``GREETING``. Change back to the ``~/flask-hello-world`` directory using
``cd ..`` and copy the following code into ``app.py``:

.. literalinclude:: code/flask/greeting_app.py
    :caption: ~/flask-hello-world/app.py
    :language: python

Update the rock
~~~~~~~~~~~~~~~

Increment the ``version`` in ``rockcraft.yaml`` to ``0.2`` such that the
top of the ``rockcraft.yaml`` file looks similar to the following:

.. code-block:: yaml
    :caption: ~/flask-hello-world/rockcraft.yaml
    :emphasize-lines: 5

    name: flask-hello-world
    # see https://documentation.ubuntu.com/rockcraft/en/1.6.0/explanation/bases/
    # for more information about bases and using 'bare' bases for chiselled rocks
    base: ubuntu@22.04 # the base environment for this Flask app
    version: '0.2' # just for humans. Semantic versioning is recommended
    summary: A summary of your Flask app # 79 char long summary
    description: |
        This is flask-hello-world's description. You have a paragraph or two to tell the
        most important story about it. Keep it under 100 words though,
        we live in tweetspace and your description wants to look good in the
        container registries out there.
    # the platforms this rock should be built on and run on.
    # you can check your architecture with `dpkg --print-architecture`
    platforms:
        amd64:
        # arm64:
        # ppc64el:
        # s390x:

Let's pack and upload the new version of the rock:

.. literalinclude:: code/flask/task.yaml
    :language: bash
    :start-after: [docs:docker-update]
    :end-before: [docs:docker-update-end]
    :dedent: 2

Update the charm
~~~~~~~~~~~~~~~~

Change back into the charm directory using ``cd charm``.

The ``flask-framework`` Charmcraft extension supports adding
configurations to ``charmcraft.yaml`` which will be passed as
environment variables to the Flask app. Add the following to
the end of the ``charmcraft.yaml`` file:

.. literalinclude:: code/flask/greeting_charmcraft.yaml
    :caption: ~/flask-hello-world/charm/charmcraft.yaml
    :language: yaml

.. note::

    When configuration options are converted to environment variables,
    their names are automatically capitalized and ``-`` are replaced
    by ``_``. A ``FLASK_`` prefix will also be added as a namespace
    for app configurations.

    In this tutorial, the new ``greeting`` configuration results in an
    environment variable named ``FLASK_GREETING``.

We can now pack and deploy the new version of the Flask app:

.. literalinclude:: code/flask/task.yaml
    :language: bash
    :start-after: [docs:refresh-deployment]
    :end-before: [docs:refresh-deployment-end]
    :dedent: 2

Monitor ``juju status`` until the app goes
back to ``active`` again. Verify that
the new configuration has been added:

.. code-block:: bash

    juju config flask-hello-world | grep -A 6 greeting:

Check that the response is still ``Hello, world!`` using:

.. code-block:: bash

    curl http://flask-hello-world --resolve flask-hello-world:80:127.0.0.1

Now let's change the greeting:

.. literalinclude:: code/flask/task.yaml
    :language: bash
    :start-after: [docs:change-config]
    :end-before: [docs:change-config-end]
    :dedent: 2

Wait for the app to restart, then check the response:

.. code-block:: bash

    curl http://flask-hello-world --resolve flask-hello-world:80:127.0.0.1

The response should now return the updated ``Hi!`` greeting.

Integrate with a database
-------------------------

Now let's keep track of how many visitors your app has received.
This will require integration with a database to keep the visitor count.
This will require a few changes:

* We will need to create a database migration that creates the ``visitors`` table.
* We will need to keep track of how many times the root endpoint has been called
  in the database.
* We will need to add a new endpoint to retrieve the number of visitors from the
  database.

Let's start with the database migration to create the required tables.
The charm created by the ``flask-framework`` extension will execute the
``migrate.py`` script if it exists. This script should ensure that the
database is initialized and ready to be used by the app. We will
create a ``migrate.py`` file containing this logic.

Return to the ``~/flask-hello-world`` directory,
create the ``migrate.py`` file, open the file using a text editor
and paste the following code into it:

.. literalinclude:: code/flask/visitors_migrate.py
    :caption: ~/flask-hello-world/migrate.py
    :language: python

.. note::

    The charm will pass the database connection string in the
    ``POSTGRESQL_DB_CONNECT_STRING`` environment variable once
    PostgreSQL has been integrated with the charm.

.. tip::

    In production you can also use the ``migrate.sh`` file
    and run CLI tools for database migration.

    See more:
    :ref:`Flask framework extension | Regarding the migrate.sh file <flask-migrate-sh>`.

    You could also use different tooling for migration, for example
    `Alembic <https://alembic.sqlalchemy.org/en/latest/>`__.

Update the rock again
~~~~~~~~~~~~~~~~~~~~~

Increment the ``version`` in ``rockcraft.yaml`` to ``0.3`` such that the
top of the ``rockcraft.yaml`` file looks similar to the following:

.. code-block:: yaml
    :caption: ~/flask-hello-world/rockcraft.yaml
    :emphasize-lines: 5

    name: flask-hello-world
    # see https://documentation.ubuntu.com/rockcraft/en/1.6.0/explanation/bases/
    # for more information about bases and using 'bare' bases for chiselled rocks
    base: ubuntu@22.04 # the base environment for this Flask app
    version: '0.3' # just for humans. Semantic versioning is recommended
    summary: A summary of your Flask app # 79 char long summary
    description: |
        This is flask-hello-world's description. You have a paragraph or two to tell the
        most important story about it. Keep it under 100 words though,
        we live in tweetspace and your description wants to look good in the
        container registries out there.
    # the platforms this rock should be built on and run on.
    # you can check your architecture with `dpkg --print-architecture`
    platforms:
        amd64:
        # arm64:
        # ppc64el:
        # s390x:

The app code also needs to be updated to keep track of the number of visitors
and to include a new endpoint to retrieve the number of visitors to the
app. Open ``app.py`` in a text editor and replace its contents with the
following code:

.. dropdown:: ~/flask-hello-world/app.py

  .. literalinclude:: code/flask/visitors_app.py
      :language: python

Let's pack and upload the new version of the rock:

.. literalinclude:: code/flask/task.yaml
    :language: bash
    :start-after: [docs:docker-2nd-update]
    :end-before: [docs:docker-2nd-update-end]
    :dedent: 2

Update the charm again
~~~~~~~~~~~~~~~~~~~~~~

Change back into the charm directory using ``cd charm``.

The Flask app now requires a database which needs to be declared in the
``charmcraft.yaml`` file. Open ``charmcraft.yaml`` in a text editor and
add the following section to the end of the file:

.. literalinclude:: code/flask/visitors_charmcraft.yaml
    :caption: ~/flask-hello-world/charm/charmcraft.yaml
    :language: yaml

We can now pack and deploy the new version of the Flask app:

.. literalinclude:: code/flask/task.yaml
    :language: bash
    :start-after: [docs:refresh-2nd-deployment]
    :end-before: [docs:refresh-2nd-deployment-end]
    :dedent: 2

Now let's deploy PostgreSQL and integrate it with the Flask app:

.. literalinclude:: code/flask/task.yaml
    :language: bash
    :start-after: [docs:deploy-postgres]
    :end-before: [docs:deploy-postgres-end]
    :dedent: 2

Wait for ``juju status`` to show that the App is ``active`` again.
During this time, the Flask app may enter a ``blocked`` state as it
waits to become integrated with the PostgreSQL database. Due to the
``optional: false`` key in the endpoint definition, the Flask app will not
start until the database is ready.

Send a request to the endpoint:

.. code-block:: bash

    curl http://flask-hello-world --resolve flask-hello-world:80:127.0.0.1

It should still return the ``Hi!`` greeting.

Check the total number of visitors:

.. code-block:: bash

    curl http://flask-hello-world/visitors --resolve flask-hello-world:80:127.0.0.1

This request should return ``1`` after the previous request to the root endpoint.
This should be incremented each time the root endpoint is requested. If we
repeat this process, the output should be as follows:

.. terminal::
    :input: curl http://flask-hello-world --resolve flask-hello-world:80:127.0.0.1

    Hi!
    :input: curl http://flask-hello-world/visitors --resolve flask-hello-world:80:127.0.0.1
    2

Tear things down
----------------

If you'd like to quickly tear things down, start by exiting the Multipass VM:

.. code-block:: bash

    exit

And then you can proceed with its deletion:

.. code-block:: bash

    multipass delete charm-dev
    multipass purge

If you'd like to manually reset your working environment, you can run the
following in the rock directory ``~/flask-hello-world`` for the tutorial:

.. literalinclude:: code/flask/task.yaml
    :language: bash
    :start-after: [docs:clean-environment]
    :end-before: [docs:clean-environment-end]
    :dedent: 2

You can also clean up your Multipass instance by exiting and deleting it
using the same commands as above.

Conclusion and next steps
-------------------------

You've reached the end of this tutorial. You made it through the entire
development process, including:

- Creating a Flask app
- Deploying the app locally
- Packaging the app using Rockcraft
- Building the app with Ops code using Charmcraft
- Deploying the app using Juju
- Exposing the app using an ingress
- Configuring the app
- Integrating the app with a database

By the end of this tutorial you built a charm and evolved it
in a number of typical ways. But there is a lot more to explore:

.. list-table::
    :widths: 30 30
    :header-rows: 1

    * - If you are wondering...
      - Visit...
    * - "How do I...?"
      - :ref:`How to manage a 12-factor app charm <manage-12-factor-app-charms>`
    * - "How do I debug?"
      - :ref:`Troubleshoot a 12-factor app charm <use-12-factor-charms-troubleshoot>`

        :external+juju:ref:`Juju | Debug a charm <debug-a-charm>`
    * - "How do I get in touch?"
      - `Matrix channel <https://matrix.to/#/#12-factor-charms:ubuntu.com>`_
    * - "What is...?"
      - :external+rockcraft:ref:`flask-framework extension in Rockcraft
        <flask-framework-reference>`

        :ref:`flask-framework extension in Charmcraft
        <flask-framework-extension>`

        :external+juju:ref:`Juju | Reference <reference>`
    * - "Why...?", "So what?"
      - :external+12-factor:ref:`12-Factor app principles and support in Charmcraft
        and Rockcraft <explanation>`
