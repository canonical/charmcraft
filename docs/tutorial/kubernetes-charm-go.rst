.. _write-your-first-kubernetes-charm-for-a-go-app:

Write your first Kubernetes charm for a Go app
==============================================

Imagine you have a Go app backed up by a database
such as PostgreSQL and need to deploy it. In a traditional setup,
this can be quite a challenge, but with Charmcraft you'll find
yourself packaging and deploying your Go app in no time.

In this tutorial we will build a Kubernetes charm for a Go
app using Charmcraft, so we can have a Go app
up and running with Juju. Let's get started!

This tutorial should take 90 minutes for you to complete.

If you're new to the charming world, Go apps are
specifically supported with a template to quickly generate a
**rock** and a matching template to generate a **charm**.
A rock is a special kind of OCI-compliant container image, while a
charm is a software operator for cloud operations that use the Juju
orchestration engine. The combined result is a Go app that
can be deployed, configured, scaled, integrated, and so on,
on any Kubernetes cluster.


What you'll need
----------------

- A local system, e.g., a laptop, with AMD64 or ARM64 architecture which
  has sufficient resources to launch a virtual machine with 4 CPUs,
  4 GB RAM, and a 50 GB disk.
- Familiarity with Linux.


What you'll do
--------------

#. Create a Go app.
#. Use that to create a rock with Rockcraft.
#. Use that to create a charm with Charmcraft.
#. Use that to test, deploy, configure, etc., your Go app on a local
   Kubernetes cloud with Juju.
#. Repeat the process, mimicking a real development process.

.. important::

    Should you get stuck or notice issues, please get in touch on
    `Matrix <https://matrix.to/#/#12-factor-charms:ubuntu.com>`_ or
    `Discourse <https://discourse.charmhub.io/>`_


Set things up
-------------

.. include:: /reuse/tutorial/setup_edge.rst
.. |12FactorApp| replace:: Go

Finally, let's create a new directory for this tutorial and
enter into it:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:create-working-dir]
    :end-before: [docs:create-working-dir-end]
    :dedent: 2


Create the Go app
-----------------

Start by creating the "Hello, world" Go app that will be
used for this tutorial.

Install ``go`` and initialize the Go module:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:install-init-go]
    :end-before: [docs:install-init-go-end]
    :dedent: 2

Create a new Go program file with ``nano main.go``.
Then, copy the following text into it, and save:

.. literalinclude:: code/go/main.go
    :caption: ~/go-hello-world/main.go
    :language: go


Run the Go app locally
----------------------

First, we need to build the Go app so it can run:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:build-go]
    :end-before: [docs:build-go-end]
    :dedent: 2

Now that we have a binary compiled, let's run the Go app to verify
that it works:

.. code-block:: bash

    ./go-hello-world

Test the Go app by using ``curl`` to send a request to the root
endpoint. You will need a new terminal for this; use
``multipass shell charm-dev`` to open a new terminal in Multipass:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:curl-go]
    :end-before: [docs:curl-go-end]
    :dedent: 2

The Go app should respond with ``Hello, world!``.

The Go app looks good, so we can stop it for now from the
original terminal using :kbd:`Ctrl` + :kbd:`C`.


Pack the Go app into a rock
---------------------------

First, we'll need a ``rockcraft.yaml`` file. Using the
``go-framework`` profile, Rockcraft will automate the creation of
``rockcraft.yaml`` and tailor the file for a Go app.
From the ``~/go-hello-world`` directory, initialize the rock:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:create-rockcraft-yaml]
    :end-before: [docs:create-rockcraft-yaml-end]
    :dedent: 2

The ``rockcraft.yaml`` file will automatically be created and set the name
based on your working directory.

Check out the contents of ``rockcraft.yaml``:

.. code-block:: bash

    cat rockcraft.yaml

The top of the file should look similar to the following snippet:

.. code-block:: yaml
    :caption: ~/go-hello-world/rockcraft.yaml

    name: go-hello-world
    # see https://documentation.ubuntu.com/rockcraft/en/latest/explanation/bases/
    # for more information about bases and using 'bare' bases for chiselled rocks
    base: bare # as an alternative, a ubuntu base can be used
    build-base: ubuntu@24.04 # build-base is required when the base is bare
    version: '0.1' # just for humans. Semantic versioning is recommended
    summary: A summary of your Go app # 79 char long summary
    description: |
        This is go-hello-world's description. You have a paragraph or two to tell the
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

Verfiy that the ``name`` is ``go-hello-world``.

The ``platforms`` key must match the architecture of your host. Check
the architecture of your system:

.. code-block:: bash

    dpkg --print-architecture


Edit the ``platforms`` key in ``rockcraft.yaml`` if required.

Now let's pack the rock:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:pack]
    :end-before: [docs:pack-end]
    :dedent: 2

.. note::

    ``ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS`` is required while the Go
    extension is experimental.

Depending on your system and network, this step can take several
minutes to finish.

Once Rockcraft has finished packing the Go rock,
the terminal will respond with something similar to
``Packed go-hello-world_0.1_<architecture>.rock``. After the initial
pack, subsequent rock packings are faster.

.. note::

    If you aren't on AMD64 architecture, the name of the ``.rock`` file
    will be different for you.

The rock needs to be copied to the MicroK8s registry, which stores OCI
archives so they can be downloaded and deployed in the Kubernetes cluster.
Copy the rock:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:skopeo-copy]
    :end-before: [docs:skopeo-copy-end]
    :dedent: 2

.. seealso::

    `Ubuntu manpage | skopeo
    <https://manpages.ubuntu.com/manpages/noble/man1/skopeo.1.html>`_


Create the charm
----------------

From the ``~/go-hello-world`` directory, let's create a new directory
for the charm and change inside it:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:create-charm-dir]
    :end-before: [docs:create-charm-dir-end]
    :dedent: 2

Using the ``go-framework`` profile, Charmcraft will automate the
creation of the files needed for our charm, including a
``charmcraft.yaml``, ``requirements.txt`` and source code for the charm.
The source code contains the logic required to operate the Go
app.

Initialize a charm named ``go-hello-world``:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:charm-init]
    :end-before: [docs:charm-init-end]
    :dedent: 2

The files will automatically be created in your working directory.

Check out the contents of ``charmcraft.yaml``:

.. code-block:: bash

    cat charmcraft.yaml

The top of the file should look similar to the following snippet:

.. code-block:: yaml
    :caption: ~/go-hello-world/charm/charmcraft.yaml

    # This file configures Charmcraft.
    # See https://juju.is/docs/sdk/charmcraft-config for guidance.

    name: go-hello-world

    type: charm

    base: ubuntu@24.04

    # the platforms this charm should be built on and run on.
    # you can check your architecture with `dpkg --print-architecture`
    platforms:
      amd64:
      # arm64:
      # ppc64el:
      # s390x:

    # (Required)
    summary: A very short one-line summary of the Go app.

    ...

Verify that the ``name`` is ``go-hello-world``. Ensure that ``platforms``
includes the architecture of your host. If your host uses the ARM architecture,
open ``charmcraft.yaml`` in a text editor, comment out ``amd64``, and include
``arm64`` in ``platforms``.

.. tip::

    Want to learn more about all the configurations in the
    ``go-framework`` profile? Run ``charmcraft expand-extensions``
    from the ``~/go-hello-world/charm/`` directory.

Let's pack the charm:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:charm-pack]
    :end-before: [docs:charm-pack-end]
    :dedent: 2

.. note::

    ``CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS`` is required while the Go
    extension is experimental.

Depending on your system and network, this step can take several
minutes to finish.

Once Charmcraft has finished packing the charm, the terminal will
respond with something similar to
``Packed go-hello-world_ubuntu-24.04-amd64.charm``. After the initial
pack, subsequent charm packings are faster.

.. note::

    If you aren't on AMD64 architecture, the name of the ``.charm``
    file will be different for you.


Deploy the Go app
-----------------

A Juju model is needed to handle Kubernetes resources while deploying
the Go app. Let's create a new model:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:add-juju-model]
    :end-before: [docs:add-juju-model-end]
    :dedent: 2

Constrain the Juju model to your architecture:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:add-model-constraints]
    :end-before: [docs:add-model-constraints-end]
    :dedent: 2

Now let's use the OCI image we previously uploaded to deploy the Go
app. Deploy using Juju by specifying the OCI image name with the
``--resource`` option:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:deploy-go-app]
    :end-before: [docs:deploy-go-app-end]
    :dedent: 2

It will take a few minutes to deploy the Go app. You can monitor its
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

The Go app should now be running. We can monitor the status of
the deployment using ``juju status``, which should be similar to the
following output:

.. terminal::
    :input: juju status

    Model           Controller      Cloud/Region        Version  SLA          Timestamp
    go-hello-world  dev-controller  microk8s/localhost  3.6.2    unsupported  14:35:07+02:00

    App                 Version  Status  Scale  Charm               Channel    Rev  Address         Exposed  Message
    go-hello-world               active      1  go-hello-world                   0  10.152.183.229  no

    Unit               Workload  Agent  Address      Ports  Message
    go-hello-world/0*  active    idle   10.1.157.79

Let's expose the app using ingress. Deploy the
``nginx-ingress-integrator`` charm and integrate it with the Go app:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:deploy-nginx]
    :end-before: [docs:deploy-nginx-end]
    :dedent: 2

The hostname of the app needs to be defined so that it is accessible via
the ingress. We will also set the default route to be the root endpoint:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:config-nginx]
    :end-before: [docs:config-nginx-end]
    :dedent: 2

.. note::

    By default, the port for the Go app should be 8080. If you want to change
    the default port, it can be done with the configuration option ``app-port`` that
    will be exposed as the ``APP_PORT`` to the Go app.

Monitor ``juju status`` until everything has a status of ``active``.

Use ``curl http://go-hello-world  --resolve go-hello-world:80:127.0.0.1``
to send a request via the ingress. It should return the
``Hello, world!`` greeting.

.. note::

    The ``--resolve go-hello-world:80:127.0.0.1`` option to the ``curl``
    command is a way of resolving the hostname of the request without
    setting a DNS record.


Configure the Go app
--------------------

To demonstrate how to provide a configuration to the Go app,
we will make the greeting configurable. We will expect this
configuration option to be available in the Go app configuration under the
keyword ``GREETING``. Change back to the ``~/go-hello-world`` directory using
``cd ..`` and replace the code into ``main.go`` with the following:

.. literalinclude:: code/go/greeting_main.txt
    :caption: ~/go-hello-world/main.go
    :language: go

Increment the ``version`` in ``rockcraft.yaml`` to ``0.2`` such that the
top of the ``rockcraft.yaml`` file looks similar to the following:

.. code-block:: yaml
    :caption: ~/go-hello-world/rockcraft.yaml
    :emphasize-lines: 6

    name: go-hello-world
    # see https://documentation.ubuntu.com/rockcraft/en/latest/explanation/bases/
    # for more information about bases and using 'bare' bases for chiselled rocks
    base: bare # as an alternative, a ubuntu base can be used
    build-base: ubuntu@24.04 # build-base is required when the base is bare
    version: '0.2' # just for humans. Semantic versioning is recommended
    summary: A summary of your Go app # 79 char long summary
    description: |
        This is go-hello-world's description. You have a paragraph or two to tell the
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

Let's pack and upload the rock:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:docker-update]
    :end-before: [docs:docker-update-end]
    :dedent: 2

Change back into the charm directory using ``cd charm``.

The ``go-framework`` Charmcraft extension supports adding configurations
to ``charmcraft.yaml``, which will be passed as environment variables to
the Go app. Add the following to the end of the
``charmcraft.yaml`` file:

.. literalinclude:: code/go/greeting_charmcraft.yaml
    :language: yaml

.. note::

    Configuration options are automatically capitalized and ``-`` are replaced
    by ``_``. An ``APP_`` prefix will also be added as a namespace
    for app configurations.

We can now pack and deploy the new version of the Go app:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:refresh-deployment]
    :end-before: [docs:refresh-deployment-end]
    :dedent: 2

After we wait for a bit monitoring ``juju status`` the app
should go back to ``active`` again. Verify that the new configuration
has been added using
``juju config go-hello-world | grep -A 6 greeting:``,
which should show the configuration option.

Using ``curl http://go-hello-world  --resolve go-hello-world:80:127.0.0.1``
shows that the response is still ``Hello, world!`` as expected.

Now let's change the greeting:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:change-config]
    :end-before: [docs:change-config-end]
    :dedent: 2

After we wait for a moment for the app to be restarted, using
``curl http://go-hello-world  --resolve go-hello-world:80:127.0.0.1``
should now return the updated ``Hi!`` greeting.


Integrate with a database
-------------------------

Now let's keep track of how many visitors your app has received.
This will require integration with a database to keep the visitor count.
This will require a few changes:

- We will need to create a database migration that creates the ``visitors`` table.
- We will need to keep track how many times the root endpoint has been called
  in the database.
- We will need to add a new endpoint to retrieve the number of visitors from
  the database.

Let's start with the database migration to create the required tables.
The charm created by the ``go-framework`` extension will execute the
``migrate.sh`` script if it exists. This script should ensure that the
database is initialized and ready to be used by the app. We will
create a ``migrate.sh`` file containing this logic.

Go back out to the ``~/go-hello-world`` directory using ``cd ..``.
Create the ``migrate.sh`` file using a text editor and paste the
following code into it:

.. literalinclude:: code/go/visitors_migrate.sh
    :caption: ~/go-hello-world/migrate.sh
    :language: bash

.. note::

    The charm will pass the Database connection string in the
    ``POSTGRESQL_DB_CONNECT_STRING`` environment variable once
    PostgreSQL has been integrated with the charm.

Change the permissions of the file ``migrate.sh`` so that it is executable:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:change-migrate-permissions]
    :end-before: [docs:change-migrate-permissions-end]
    :dedent: 2

For the migrations to work, we need the ``postgresql-client`` package
installed in the rock. By default, the ``go-framework`` uses the ``base``
base, so we will also need to install a shell interpreter. Let's do it as a
slice, so that the rock doesn't include unnecessary files. Open the
``rockcraft.yaml`` file using a text editor and add the following to the
end of the file:

.. literalinclude:: code/go/visitors_rockcraft.yaml
    :language: yaml

Increment the ``version`` in ``rockcraft.yaml`` to ``0.3`` such that the
top of the ``rockcraft.yaml`` file looks similar to the following:

.. code-block:: yaml
    :caption: ~/go-hello-world/rockcraft.yaml
    :emphasize-lines: 6

    name: go-hello-world
    # see https://documentation.ubuntu.com/rockcraft/en/latest/explanation/bases/
    # for more information about bases and using 'bare' bases for chiselled rocks
    base: bare # as an alternative, a ubuntu base can be used
    build-base: ubuntu@24.04 # build-base is required when the base is bare
    version: '0.3' # just for humans. Semantic versioning is recommended
    summary: A summary of your Go app # 79 char long summary
    description: |
        This is go-hello-world's description. You have a paragraph or two to tell the
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

To be able to connect to PostgreSQL from the Go app, the library
``pgx`` will be used. The app code needs to be updated to keep track of
the number of visitors and to include a new endpoint to retrieve the
number of visitors. Open ``main.go`` in a text editor and
replace its content with the following code:

.. dropdown:: main.go

    .. literalinclude:: code/go/visitors_main.txt
        :language: go

Check all the packages and their dependencies in the Go project with the
following command:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:check-go-app]
    :end-before: [docs:check-go-app-end]
    :dedent: 2

Let's pack and upload the rock:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:docker-2nd-update]
    :end-before: [docs:docker-2nd-update-end]
    :dedent: 2

Change back into the charm directory using ``cd charm``.

The Go app now requires a database which needs to be declared in the
``charmcraft.yaml`` file. Open ``charmcraft.yaml`` in a text editor and
add the following section to the end of the file:

.. literalinclude:: code/go/visitors_charmcraft.yaml
    :language: yaml

We can now pack and deploy the new version of the Go app:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:refresh-2nd-deployment]
    :end-before: [docs:refresh-2nd-deployment-end]
    :dedent: 2

Now let's deploy PostgreSQL and integrate it with the Go app:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:deploy-postgres]
    :end-before: [docs:deploy-postgres-end]
    :dedent: 2

Wait for ``juju status`` to show that the App is ``active`` again.
During this time, the Go app may enter a ``blocked`` state as it
waits to become integrated with the PostgreSQL database. Due to the
``optional: false`` key in the endpoint definition, the Go app will not
start until the database is ready.

Running ``curl http://go-hello-world  --resolve go-hello-world:80:127.0.0.1``
should still return the ``Hi!`` greeting.

To check the local visitors, use
``curl http://go-hello-world/visitors  --resolve go-hello-world:80:127.0.0.1``,
which should return ``Number of visitors 1`` after the
previous request to the root endpoint.
This should be incremented each time the root endpoint is requested. If we
repeat this process, the output should be as follows:

.. terminal::
    :input: curl http://go-hello-world  --resolve go-hello-world:80:127.0.0.1

    Hi!
    :input: curl http://go-hello-world/visitors  --resolve go-hello-world:80:127.0.0.1
    Number of visitors 2


Tear things down
----------------

We've reached the end of this tutorial. We went through the entire
development process, including:

- Creating a Go app
- Deploying the app locally
- Packaging the app using Rockcraft
- Building the app with Ops code using Charmcraft
- Deplyoing the app using Juju
- Exposing the app using an ingress
- Configuring the app
- Integrating the app with a database

If you'd like to quickly tear things down, start by exiting the Multipass VM:

.. code-block:: bash

    exit

And then you can proceed with its deletion:

.. code-block:: bash

    multipass delete charm-dev
    multipass purge

If you'd like to manually reset your working environment, you can run the
following in the rock directory ``~/go-hello-world`` for the tutorial:

.. literalinclude:: code/go/task.yaml
    :language: bash
    :start-after: [docs:clean-environment]
    :end-before: [docs:clean-environment-end]
    :dedent: 2

You can also clean up your Multipass instance by exiting and deleting it
using the same commands as above.

Next steps
----------

By the end of this tutorial you will have built a charm and evolved it
in a number of typical ways. But there is a lot more to explore:

.. list-table::
    :widths: 30 30
    :header-rows: 1

    * - If you are wondering...
      - Visit...
    * - "How do I...?"
      - :ref:`How-to guides <how-to-guides>`,
        :external+ops:ref:`Ops | How-to guides <how-to-guides>`
    * - "How do I debug?"
      - `Charm debugging tools <https://juju.is/docs/sdk/debug-a-charm>`_
    * - "How do I get in touch?"
      - `Matrix channel <https://matrix.to/#/#12-factor-charms:ubuntu.com>`_
    * - "What is...?"
      - :ref:`reference`,
        :external+ops:ref:`Ops | Reference <reference>`,
        :external+juju:ref:`Juju | Reference <reference>`
    * - "Why...?", "So what?"
      - :external+ops:ref:`Ops | Explanation <explanation>`,
        :external+juju:ref:`Juju | Explanation <explanation>`
