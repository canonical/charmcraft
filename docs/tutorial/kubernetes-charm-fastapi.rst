.. _write-your-first-kubernetes-charm-for-a-fastapi-app:


Write your first Kubernetes charm for a FastAPI app
===================================================

Imagine you have a FastAPI app backed up by a database
such as PostgreSQL and need to deploy it. In a traditional setup,
this can be quite a challenge, but with Charmcraft you'll find
yourself packaging and deploying your FastAPI app in no time.

In this tutorial we will build a Kubernetes charm for a FastAPI
app using Charmcraft, so we can have a FastAPI app
up and running with Juju. Let's get started!

This tutorial should take 90 minutes for you to complete.

If you're new to the charming world, FastAPI apps are
specifically supported with a template to quickly generate a
**rock** and a matching template to generate a **charm**.
A rock is a special kind of OCI-compliant container image, while a
charm is a software operator for cloud operations that use the Juju
orchestration engine. The combined result is a FastAPI app that
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

#. Create a FastAPI app.
#. Use that to create a rock with Rockcraft.
#. Use that to create a charm with Charmcraft.
#. Use that to test, deploy, configure, etc., your FastAPI app on a local
   Kubernetes cloud with Juju.
#. Repeat the process, mimicking a real development process.

.. important::

    Should you get stuck or notice issues, please get in touch on
    `Matrix <https://matrix.to/#/#12-factor-charms:ubuntu.com>`_ or
    `Discourse <https://discourse.charmhub.io/>`_


Set things up
-------------

.. include:: /reuse/tutorial/setup_edge.rst
.. |12FactorApp| replace:: FastAPI

Let's create a directory for this tutorial and enter into it:

.. code-block:: bash

    mkdir fastapi-hello-world
    cd fastapi-hello-world

Finally, install ``python-venv`` and create a virtual environment:

.. literalinclude:: code/fastapi/task.yaml
    :language: bash
    :start-after: [docs:create-venv]
    :end-before: [docs:create-venv-end]
    :dedent: 2


Create the FastAPI app
----------------------

Start by creating the "Hello, world" FastAPI app that will be used for
this tutorial.

Create a new requirements file with ``nano requirements.txt``.
Then, copy the following text into it, and save:

.. literalinclude:: code/fastapi/requirements.txt
    :caption: ~/fastapi-hello-world/requirements.txt

.. note::

    The ``psycopg2-binary`` package is needed so the FastAPI app can
    connect to PostgreSQL.

Install the packages:

.. literalinclude:: code/fastapi/task.yaml
    :language: bash
    :start-after: [docs:install-requirements]
    :end-before: [docs:install-requirements-end]
    :dedent: 2

In the same directory, create a file called ``app.py``.
Then copy and save the following code into the file:

.. literalinclude:: code/fastapi/app.py
    :caption: ~/fastapi-hello-world/app.py
    :language: python


Run the FastAPI app locally
---------------------------

Now that we have a virtual environment with all the dependencies,
let's run the FastAPI app to verify that it works:

.. code-block:: bash

    fastapi dev app.py --port 8080

Test the FastAPI app by using ``curl`` to send a request to the root
endpoint. You will need a new terminal for this; use
``multipass shell charm-dev`` to open a new terminal in Multipass:

.. literalinclude:: code/fastapi/task.yaml
    :language: bash
    :start-after: [docs:curl-fastapi]
    :end-before: [docs:curl-fastapi-end]
    :dedent: 2

The FastAPI app should respond with ``{"message":"Hello World"}``.

The FastAPI app looks good, so we can stop for now from the
original terminal using :kbd:`Ctrl` + :kbd:`C`.


Pack the FastAPI app into a rock
--------------------------------

First, we'll need a ``rockcraft.yaml`` file. Using the
``fastapi-framework`` profile, Rockcraft will automate the creation of
``rockcraft.yaml`` and tailor the file for a FastAPI app.
From the ``~/fastapi-hello-world`` directory, initialize the rock:

.. literalinclude:: code/fastapi/task.yaml
    :language: bash
    :start-after: [docs:create-rockcraft-yaml]
    :end-before: [docs:create-rockcraft-yaml-end]
    :dedent: 2

The ``rockcraft.yaml`` file will be automatically created, with the name being
set based on your working directory.

Check out the contents of ``rockcraft.yaml``:

.. code-block:: bash

    cat rockcraft.yaml

The top of the file should look similar to the following snippet:

.. code-block:: yaml
    :caption: ~/fastapi-hello-world/rockcraft.yaml

    name: fastapi-hello-world
    # see https://documentation.ubuntu.com/rockcraft/en/latest/explanation/bases/
    # for more information about bases and using 'bare' bases for chiselled rocks
    base: ubuntu@24.04 # the base environment for this FastAPI app
    version: '0.1' # just for humans. Semantic versioning is recommended
    summary: A summary of your FastAPI app # 79 char long summary
    description: |
        This is fastapi project's description. You have a paragraph or two to tell the
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

Verify that the ``name`` is ``fastapi-hello-world``.

The ``platforms`` key must match the architecture of your host. Check
the architecture of your system:

.. code-block:: bash

    dpkg --print-architecture

Edit the ``platforms`` key in ``rockcraft.yaml`` if required.

Now let's pack the rock:

.. literalinclude:: code/fastapi/task.yaml
    :language: bash
    :start-after: [docs:pack]
    :end-before: [docs:pack-end]
    :dedent: 2

.. note::

    ``ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS`` is required while the FastAPI
    extension is experimental.

Depending on your system and network, this step can take several
minutes to finish.

Once Rockcraft has finished packing the FastAPI rock,
the terminal will respond with something similar to
``Packed fastapi-hello-world_0.1_<architecture>.rock``. After the initial
pack, subsequent rock packings are faster.

.. note::

    If you aren't on AMD64 architecture, the name of the ``.rock`` file
    will be different for you.

The rock needs to be copied to the MicroK8s registry, which stores OCI
archives so they can be downloaded and deployed in the Kubernetes cluster.
Copy the rock:

.. literalinclude:: code/fastapi/task.yaml
    :language: bash
    :start-after: [docs:skopeo-copy]
    :end-before: [docs:skopeo-copy-end]
    :dedent: 2

.. seealso::

    `Ubuntu manpage | skopeo
    <https://manpages.ubuntu.com/manpages/noble/man1/skopeo.1.html>`_


Create the charm
----------------

From the ``~/fastapi-hello-world`` directory, let's create a new directory
for the charm and change inside it:

.. literalinclude:: code/fastapi/task.yaml
    :language: bash
    :start-after: [docs:create-charm-dir]
    :end-before: [docs:create-charm-dir-end]
    :dedent: 2

Using the ``fastapi-framework`` profile, Charmcraft will automate the
creation of the files needed for our charm, including a
``charmcraft.yaml``, ``requirements.txt`` and source code for the charm.
The source code contains the logic required to operate the FastAPI
app.

Initialize a charm named ``fastapi-hello-world``:

.. literalinclude:: code/fastapi/task.yaml
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
    :caption: ~/fastapi-hello-world/charm/charmcraft.yaml

    # This file configures Charmcraft.
    # See https://juju.is/docs/sdk/charmcraft-config for guidance.

    name: fastapi-hello-world

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
    summary: A very short one-line summary of the FastAPI app.

    ...

Verify that the ``name`` is ``fastapi-hello-world``. Ensure that ``platforms``
includes the architecture of your host. If your host uses the ARM architecture,
open ``charmcraft.yaml`` in a text editor, comment out ``amd64``, and include
``arm64`` in ``platforms``.

.. tip::

    Want to learn more about all the configurations in the
    ``fastapi-framework`` profile? Run ``charmcraft expand-extensions``
    from the ``~/fastapi-hello-world/charm/`` directory.

Let's pack the charm:

.. literalinclude:: code/fastapi/task.yaml
    :language: bash
    :start-after: [docs:charm-pack]
    :end-before: [docs:charm-pack-end]
    :dedent: 2

.. note::

    ``CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS`` is required while the FastAPI
    extension is experimental.

Depending on your system and network, this step may take several
minutes to finish.

Once Charmcraft has finished packing the charm, the terminal will
respond with something similar to
``Packed fastapi-hello-world_ubuntu-24.04-amd64.charm``. After the initial
pack, subsequent charm packings are faster.

.. note::

    If you aren't on AMD64 architecture, the name of the ``.charm``
    file will be different for you.


Deploy the FastAPI app
----------------------

A Juju model is needed to handle Kubernetes resources while deploying
the FastAPI app. Let's create a new model:

.. literalinclude:: code/fastapi/task.yaml
    :language: bash
    :start-after: [docs:add-juju-model]
    :end-before: [docs:add-juju-model-end]
    :dedent: 2

Constrain the Juju model to your architecture:

.. literalinclude:: code/fastapi/task.yaml
    :language: bash
    :start-after: [docs:add-model-constraints]
    :end-before: [docs:add-model-constraints-end]
    :dedent: 2


Now let's use the OCI image we previously uploaded to deploy the FastAPI
app. Deploy using Juju by specifying the OCI image name with the
``--resource`` option:

.. literalinclude:: code/fastapi/task.yaml
    :language: bash
    :start-after: [docs:deploy-fastapi-app]
    :end-before: [docs:deploy-fastapi-app-end]
    :dedent: 2

It will take a few minutes to deploy the FastAPI app. You can monitor
its progress with:

.. code-block:: bash

    juju status --watch 2s


It can take a couple of minutes for the app to finish the deployment.
Once the status of the App has gone to ``active``, you can stop watching
using :kbd:`Ctrl` + :kbd:`C`.

.. tip::

    To monitor your deployment, keep a ``juju status`` session active in a
    second terminal.

    See more: :external+juju:ref:`Juju | juju status <command-juju-status>`

The FastAPI app should now be running. We can monitor the status of
the deployment using ``juju status``, which should be similar to the following
output:

.. terminal::
    :input: juju status

    Model                Controller      Cloud/Region        Version  SLA          Timestamp
    fastapi-hello-world  dev-controller  microk8s/localhost  3.6.2    unsupported  13:45:18+10:00

    App                  Version  Status  Scale  Charm                Channel  Rev  Address        Exposed  Message
    fastapi-hello-world           active      1  fastapi-hello-world             0  10.152.183.53  no

    Unit                    Workload  Agent  Address      Ports  Message
    fastapi-hello-world/0*  active    idle   10.1.157.75

Let's expose the app using ingress. Deploy the
``nginx-ingress-integrator`` charm and integrate it with the FastAPI app:

.. literalinclude:: code/fastapi/task.yaml
    :language: bash
    :start-after: [docs:deploy-nginx]
    :end-before: [docs:deploy-nginx-end]
    :dedent: 2

The hostname of the app needs to be defined so that it is accessible via
the ingress. We will also set the default route to be the root endpoint:

.. literalinclude:: code/fastapi/task.yaml
    :language: bash
    :start-after: [docs:config-nginx]
    :end-before: [docs:config-nginx-end]
    :dedent: 2

Monitor ``juju status`` until everything has a status of ``active``.

Test the deployment using
``curl http://fastapi-hello-world --resolve fastapi-hello-world:80:127.0.0.1``
to send a request via the ingress. It should return the
``{"message":"Hello World"}`` greeting.

.. note::

    The ``--resolve fastapi-hello-world:80:127.0.0.1`` option to the ``curl``
    command is a way of resolving the hostname of the request without
    setting a DNS record.


Configure the FastAPI app
-------------------------

To demonstrate how to provide a configuration to the FastAPI app,
we will make the greeting configurable. We will expect this
configuration option to be available in the FastAPI app configuration under the
keyword ``APP_GREETING``. Change back to the ``~/fastapi-hello-world`` directory
using ``cd ..`` and copy the following code into ``app.py``:

.. literalinclude:: code/fastapi/greeting_app.py
    :caption: ~/fastapi-hello-world/app.py
    :language: python

Increment the ``version`` in ``rockcraft.yaml`` to ``0.2`` such that the
top of the ``rockcraft.yaml`` file looks similar to the following:

.. code-block:: yaml
    :caption: ~/fastapi-hello-world/rockcraft.yaml
    :emphasize-lines: 5

    name: fastapi-hello-world
    # see https://documentation.ubuntu.com/rockcraft/en/latest/explanation/bases/
    # for more information about bases and using 'bare' bases for chiselled rocks
    base: ubuntu@24.04 # the base environment for this FastAPI app
    version: '0.2' # just for humans. Semantic versioning is recommended
    summary: A summary of your FastAPI app # 79 char long summary
    description: |
        This is fastapi project's description. You have a paragraph or two to tell the
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

.. literalinclude:: code/fastapi/task.yaml
    :language: bash
    :start-after: [docs:docker-update]
    :end-before: [docs:docker-update-end]
    :dedent: 2

Change back into the charm directory using ``cd charm``.

The ``fastapi-framework`` Charmcraft extension supports adding
configurations to ``charmcraft.yaml`` which will be passed as
environment variables to the FastAPI app. Add the
following to the end of the ``charmcraft.yaml`` file:

.. literalinclude:: code/fastapi/greeting_charmcraft.yaml
    :language: yaml

.. note::

    Configuration options are automatically capitalized and ``-`` are replaced
    by ``_``. An ``APP_`` prefix will also be added as a namespace
    for app configurations.

We can now pack and deploy the new version of the FastAPI app:

.. literalinclude:: code/fastapi/task.yaml
    :language: bash
    :start-after: [docs:refresh-deployment]
    :end-before: [docs:refresh-deployment-end]
    :dedent: 2

After we wait for a bit monitoring ``juju status`` the app
should go back to ``active`` again. Verify that the
new configuration has been added using
``juju config fastapi-hello-world | grep -A 6 greeting:`` which should show
the configuration option.

Using ``curl http://fastapi-hello-world  --resolve fastapi-hello-world:80:127.0.0.1``
shows that the response is still ``{"message":"Hello, world!"}`` as expected.

Now let's change the greeting:

.. literalinclude:: code/fastapi/task.yaml
    :language: bash
    :start-after: [docs:change-config]
    :end-before: [docs:change-config-end]
    :dedent: 2

After we wait for a moment for the app to be restarted, using
``curl http://fastapi-hello-world  --resolve fastapi-hello-world:80:127.0.0.1``
should now return the updated ``{"message":"Hi!"}`` greeting.


Integrate with a database
-------------------------

Now let's keep track of how many visitors your app has received.
This will require integration with a database to keep the visitor count.
This will require a few changes:

- We will need to create a database migration that creates the ``visitors`` table.
- We will need to keep track of how many times the root endpoint has been called
  in the database.
- We will need to add a new endpoint to retrieve the number of visitors from
  the database.

Let's start with the database migration to create the required tables.
The charm created by the ``fastapi-framework`` extension will execute the
``migrate.py`` script if it exists. This script should ensure that the
database is initialized and ready to be used by the app. We will
create a ``migrate.py`` file containing this logic.

Go back out to the ``~/fastapi-hello-world`` directory using ``cd ..``,
create the ``migrate.py`` file, open the file using a text editor
and paste the following code into it:

.. literalinclude:: code/fastapi/visitors_migrate.py
    :caption: ~/fastapi-hello-world/migrate.py
    :language: python

.. note::

    The charm will pass the Database connection string in the
    ``POSTGRESQL_DB_CONNECT_STRING`` environment variable once postgres has
    been integrated with the charm.

Increment the ``version`` in ``rockcraft.yaml`` to ``0.3`` such that the
top of the ``rockcraft.yaml`` file looks similar to the following:

.. code-block:: yaml
    :caption: ~/fastapi-hello-world/rockcraft.yaml
    :emphasize-lines: 5

    name: fastapi-hello-world
    # see https://documentation.ubuntu.com/rockcraft/en/latest/explanation/bases/
    # for more information about bases and using 'bare' bases for chiselled rocks
    base: ubuntu@24.04 # the base environment for this FastAPI app
    version: '0.3' # just for humans. Semantic versioning is recommended
    summary: A summary of your FastAPI app # 79 char long summary
    description: |
        This is fastapi project's description. You have a paragraph or two to tell the
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

.. collapse:: app.py

  .. literalinclude:: code/fastapi/visitors_app.py
      :language: python

Let's pack and upload the rock:

.. literalinclude:: code/fastapi/task.yaml
    :language: bash
    :start-after: [docs:docker-2nd-update]
    :end-before: [docs:docker-2nd-update-end]
    :dedent: 2

Change back into the charm directory using ``cd charm``.

The FastAPI app now requires a database which needs to be declared in the
``charmcraft.yaml`` file. Open ``charmcraft.yaml`` in a text editor and
add the following section to the end:

.. literalinclude:: code/fastapi/visitors_charmcraft.yaml
    :language: yaml

We can now pack and deploy the new version of the FastAPI app:

.. literalinclude:: code/fastapi/task.yaml
    :language: bash
    :start-after: [docs:refresh-2nd-deployment]
    :end-before: [docs:refresh-2nd-deployment-end]
    :dedent: 2

Now let's deploy PostgreSQL and integrate it with the FastAPI app:

.. literalinclude:: code/fastapi/task.yaml
    :language: bash
    :start-after: [docs:deploy-postgres]
    :end-before: [docs:deploy-postgres-end]
    :dedent: 2

Wait for ``juju status`` to show that the App is ``active`` again.
During this time, the FastAPI app may enter a ``blocked`` state as it
waits to become integrated with the PostgreSQL database. Due to the
``optional: false`` key in the endpoint definition, the FastAPI app will not
start until the database is ready.

Running
``curl http://fastapi-hello-world  --resolve fastapi-hello-world:80:127.0.0.1``
should still return the ``{"message":"Hi!"}`` greeting.

To check the local visitors, use
``curl http://fastapi-hello-world/visitors
--resolve fastapi-hello-world:80:127.0.0.1``, which should return
``{"count":1}`` after the previous request to the root endpoint. This should
be incremented each time the root endpoint is requested. If we repeat
this process, the output should be as follows:

.. terminal::
    :input: curl http://fastapi-hello-world  --resolve fastapi-hello-world:80:127.0.0.1

    {"message":"Hi!"}
    :input: curl http://fastapi-hello-world/visitors  --resolve fastapi-hello-world:80:127.0.0.1
    {"count":2}


Tear things down
----------------

We've reached the end of this tutorial. We went through the entire
development process, including:

- Creating a FastAPI app
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
following in the rock directory ``~/fastapi-hello-world`` for the tutorial:

.. literalinclude:: code/fastapi/task.yaml
    :language: bash
    :start-after: [docs:clean-environment]
    :end-before: [docs:clean-environment-end]
    :dedent: 2

You can also clean up your Multipass instance by exiting and deleting it
using the same commands as above.

Next steps
----------

By the end of this tutorial, you will have built a charm and evolved it
in a number of typical ways, but there is a lot more to explore:

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
