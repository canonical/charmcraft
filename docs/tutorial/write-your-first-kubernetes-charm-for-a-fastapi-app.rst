.. _write-your-first-kubernetes-charm-for-a-fastapi-app:


Write your first Kubernetes charm for a FastAPI app
===================================================

Imagine you have a FastAPI application backed up by a database
such as PostgreSQL and need to deploy it. In a traditional setup,
this can be quite a challenge, but with Charmcraft you'll find
yourself packaging and deploying your FastAPI application in no time.
Let's get started!

In this tutorial we will build a Kubernetes charm for a FastAPI
application using Charmcraft, so we can have a FastAPI application
up and running with Juju.

This tutorial should take 90 minutes for you to complete.

.. note::
    If you're new to the charming world: Flask applications are
    specifically supported with a coordinated pair of profiles
    for an OCI container image (**rock**) and corresponding
    packaged software (**charm**) that allow for the application
    to be deployed, integrated and operated on a Kubernetes
    cluster with the Juju orchestration engine.

What you'll need
----------------

- A workstation, e.g., a laptop, with amd64 or arm64 architecture which
  has sufficient resources to launch a virtual machine with 4 CPUs,
  4 GB RAM, and a 50 GB disk.
- Familiarity with Linux.


What you'll do
--------------

Create a FastAPI application. Use that to create a rock with
``rockcraft``. Use that to create a charm with ``charmcraft``. Use that
to test, deploy, configure, etc., your FastAPI application on a local
Kubernetes cloud, ``microk8s``, with ``juju``. All of that multiple
times, mimicking a real development process.

.. important::

    Should you get stuck or notice issues, please get in touch on
    `Matrix <https://matrix.to/#/#12-factor-charms:ubuntu.com>`_ or
    `Discourse <https://discourse.charmhub.io/>`_


Set things up
-------------

.. include:: /reuse/tutorial/setup_edge.rst
.. |12FactorApp| replace:: FastAPI

.. note::

    This tutorial requires version ``3.0.0`` or later of Charmcraft. Check which
    version of Charmcraft you have installed using ``charmcraft --version``. If
    you have an older version of Charmcraft installed, use
    ``sudo snap refresh charmcraft --channel latest/edge`` to get the latest edge
    version of Charmcraft.

    This tutorial requires version ``1.5.4`` or later of Rockcraft. Check which
    version of Rockcraft you have installed using ``rockcraft --version``. If you
    have an older version of Rockcraft installed, use
    ``sudo snap refresh rockcraft --channel latest/edge`` to get the latest edge
    version of Rockcraft.

Let's create a directory for this tutorial and change into it:

.. code-block:: bash

    mkdir fastapi-hello-world
    cd fastapi-hello-world

Finally, install ``python-venv`` and create a virtual environment:

.. code-block:: bash

    sudo apt-get update && sudo apt-get install python3-venv -y
    python3 -m venv .venv
    source .venv/bin/activate

Create the FastAPI application
------------------------------

Start by creating the "Hello, world" FastAPI application that will be used for
this tutorial.

Create a ``requirements.txt`` file, copy the following text into it
and then save it:

.. code-block:: bash

    fastapi[standard]
    psycopg2-binary

.. note::

   The ``psycopg2-binary`` package is needed so the Flask application can
   connect to PostgreSQL.

Install the packages:

.. code-block:: bash

    pip install -r requirements.txt

In the same directory, copy and save the following into a text file
called ``app.py``:

.. code-block:: python

    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/")
    async def root():
        return {"message": "Hello World"}


Run the FastAPI application locally
-----------------------------------

Now that we have a virtual environment with all the dependencies,
let's run the FastAPI application to verify that it works:

.. code-block:: bash

    fastapi dev app.py --port 8080

Test the FastAPI application by using ``curl`` to send a request to the root
endpoint. You will need a new terminal for this; use
``multipass shell charm-dev`` to open a new terminal in Multipass:

.. code-block:: bash

    curl localhost:8080

The FastAPI application should respond with ``{"message":"Hello World"}``.

The FastAPI application looks good, so we can stop for now from the
original terminal using :kbd:`Ctrl` + :kbd:`C`.


Pack the FastAPI application into a rock
----------------------------------------

First, we'll need a ``rockcraft.yaml`` file. Using the
``fastapi-framework`` profile, Rockcraft will automate the creation of
``rockcraft.yaml`` and tailor the file for a FastAPI application.
From the ``fastapi-hello-world`` directory, initialize the rock:

.. code-block:: bash

    rockcraft init --profile fastapi-framework

The ``rockcraft.yaml`` file will be automatically created, with the name being
set based on your working directory.

Check out the contents of ``rockcraft.yaml``:

.. code:: bash

    cat rockcraft.yaml

The top of the file should look similar to the following snippet:

.. code:: yaml

    name: fastapi-hello-world
    # see https://documentation.ubuntu.com/rockcraft/en/latest/explanation/bases/
    # for more information about bases and using 'bare' bases for chiselled rocks
    base: ubuntu@24.04 # the base environment for this FastAPI application
    version: '0.1' # just for humans. Semantic versioning is recommended
    summary: A summary of your FastAPI application # 79 char long summary
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

   ...

Verify that the ``name`` is ``fastapi-hello-world``. 

Ensure that ``platforms`` includes the architecture of your host. Check
the architecture of your system:

.. code-block:: bash

    dpkg --print-architecture

If your host uses the ARM architecture, open ``rockcraft.yaml`` in a
text editor and include ``arm64`` in ``platforms``.

Now let's pack the rock:

.. code-block:: bash

    ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true rockcraft pack

.. note::

    ``ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS`` is required while the FastAPI
    extension is experimental.

Depending on your system and network, this step can take several
minutes to finish.

Once Rockcraft has finished packing the FastAPI rock,
the terminal will respond with something similar to
``Packed fastapi-hello-world_0.1_amd64.rock``.

.. note::

    If you are not on the ``amd64`` platform, the name of the ``.rock`` file
    will be different for you.

The rock needs to be copied to the MicroK8s registry, which stores OCI
archives so they can be downloaded and deployed in the Kubernetes cluster.
Copy the rock:

.. code-block:: bash

    rockcraft.skopeo --insecure-policy copy --dest-tls-verify=false \
      oci-archive:fastapi-hello-world_0.1_amd64.rock \
      docker://localhost:32000/fastapi-hello-world:0.1

.. seealso::

    See more: `Ubuntu manpage | skopeo
    <https://manpages.ubuntu.com/manpages/noble/man1/skopeo.1.html>`_


Create the charm
----------------

From the ``fastapi-hello-world`` direcotyr, let's create a new directory
for the charm and change inside it:

.. code-block:: bash

    mkdir charm
    cd charm

Using the ``fastapi-framework`` profile, Charmcraft will automate the
creation of the files needed for our charm, including a
``charmcraft.yaml``, ``requirements.txt`` and source code for the charm.
The source code contains the logic required to operate the FastAPI
application.

Initialize a charm named ``fastapi-hello-world``:

.. code-block:: bash

    charmcraft init --profile fastapi-framework --name fastapi-hello-world

The files will automatically be created in your working directory.

The charm depends on several libraries. Download the libraries and pack the charm:

.. code-block:: bash

    CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true charmcraft fetch-libs
    CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true charmcraft pack

.. note::

    ``CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS`` is required while the FastAPI
    extension is experimental.

Depending on your system and network, this step may take several
minutes to finish.

Once Charmcraft has finished packing the charm, the terminal will
respond with something similar to
``Packed fastapi-hello-world_ubuntu-24.04-amd64.charm``.

.. note::

    If you are not on the ``amd64`` platform, the name of the ``.charm``
    file will be different for you.


Deploy the FastAPI application
------------------------------

A Juju model is needed to handle Kubernetes resources while deploying
the FastAPI application. Let's create a new model:

.. code-block:: bash

    juju add-model fastapi-hello-world

If you are not on a host with the ``amd64`` architecture, you will
need to include a constraint to the Juju model to specify your
architecture. You can check the architecture of your system using
``dpkg --print-architecture``.

Set the Juju model constraints using

.. code-block:: bash

      juju set-model-constraints -m fastapi-hello-world \
         arch=$(dpkg --print-architecture)


Now let’s use the OCI image we previously uploaded to deploy the FastAPI
application. Deploy using Juju by specifying the OCI image name with the
``--resource`` option:

.. code-block:: bash

    juju deploy ./fastapi-hello-world_amd64.charm fastapi-hello-world \
      --resource app-image=localhost:32000/fastapi-hello-world:0.1

It will take a few minutes to deploy the FastAPI application. You can monitor
the progress using

.. code:: bash

    juju status --watch 2s


It can take a couple of minutes for the app to finish the deployment.
Once the status of the App has gone to ``active``, you can stop watching
using :kbd:`Ctrl` + :kbd:`C`.

.. seealso::

    See more: :external+juju:ref:`Juju | juju status <command-juju-status>`

The FastAPI application should now be running. We can monitor the status of
the deployment using ``juju status``, which should be similar to the following
output:

.. terminal::
    :input: juju status

    Model                Controller      Cloud/Region        Version  SLA          Timestamp
    fastapi-hello-world  dev-controller  microk8s/localhost  3.5.4    unsupported  13:45:18+10:00

    App                  Version  Status  Scale  Charm                Channel  Rev  Address        Exposed  Message
    fastapi-hello-world           active      1  fastapi-hello-world             0  10.152.183.53  no

    Unit                    Workload  Agent  Address      Ports  Message
    fastapi-hello-world/0*  active    idle   10.1.157.75

Let's expose the application using ingress. Deploy the
``nginx-ingress-integrator`` charm and integrate it with the FastAPI app:

.. code-block:: bash

    juju deploy nginx-ingress-integrator
    juju integrate nginx-ingress-integrator fastapi-hello-world

The hostname of the app needs to be defined so that it is accessible via
the ingress. We will also set the default route to be the root endpoint:

.. code-block:: bash

    juju config nginx-ingress-integrator \
      service-hostname=fastapi-hello-world path-routes=/

Monitor ``juju status`` until everything has a status of ``active``.

Test the deployment using
``curl http://fastapi-hello-world --resolve fast-api-hello-world:80:127.0.0.1``
to send a request via the ingress. It should return the
``{"message":"Hello World"}`` greeting.

.. note::

    The ``--resolve fastapi-hello-world:80:127.0.0.1`` option to the ``curl``
    command is a way of resolving the hostname of the request without
    setting a DNS record.


Configure the FastAPI application
---------------------------------

To demonstrate how to provide a configuration to the Flask application,
we will make the greeting configurable. We will expect this
configuration option to be available in the FastAPI app configuration under the
keyword ``APP_GREETING``. Change back to the ``fastapi-hello-world`` directory
using ``cd ..`` and copy the following code into ``app.py``:

.. code-block:: python

    import os

    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/")
    async def root():
        return {"message": os.getenv("APP_GREETING", "Hello World")}

Increment the ``version`` in ``rockcraft.yaml`` to ``0.2`` such that the
top of the ``rockcraft.yaml`` file looks similar to the following:

.. code-block:: yaml
    :emphasize-lines: 5

    name: fastapi-hello-world
    # see https://documentation.ubuntu.com/rockcraft/en/latest/explanation/bases/
    # for more information about bases and using 'bare' bases for chiselled rocks
    base: ubuntu@24.04 # the base environment for this FastAPI application
    version: '0.2' # just for humans. Semantic versioning is recommended
    summary: A summary of your FastAPI application # 79 char long summary
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

   ...

Let's run the pack and upload commands for the rock:

.. code-block:: bash

    ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true rockcraft pack
    rockcraft.skopeo --insecure-policy copy --dest-tls-verify=false \
      oci-archive:fastapi-hello-world_0.2_amd64.rock \
      docker://localhost:32000/fastapi-hello-world:0.2

Change back into the charm directory using ``cd charm``.

The ``fastapi-framework`` Charmcraft extension supports adding
configurations to ``charmcraft.yaml`` which will be passed as
environment variables to the FastAPI application. Add the
following to the end of the ``charmcraft.yaml`` file:

.. code-block:: yaml

    config:
      options:
        greeting:
          description: |
            The greeting to be returned by the FastAPI application.
          default: "Hello, world!"
          type: string

.. note::

    Configuration options are automatically capitalized and ``-`` are replaced
    by ``_``. An ``APP_`` prefix will also be added as a namespace
    for app configurations.

We can now pack and deploy the new version of the FastAPI app:

.. code-block:: bash

    CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true charmcraft pack
    juju refresh fastapi-hello-world \
      --path=./fastapi-hello-world_amd64.charm \
      --resource app-image=localhost:32000/fastapi-hello-world:0.2

After we wait for a bit monitoring ``juju status`` the application
should go back to ``active`` again. Verify that the
new configuration has been added using
``juju config fastapi-hello-world | grep -A 6 greeting:`` which should show
the configuration option.

.. note::

    The ``grep`` command extracts a portion of the configuration to make it easier to
    check whether the configuration option has been added.

Using ``http://fastapi-hello-world  --resolve fastapi-hello-world:80:127.0.0.1``
shows that the response is still ``{"message":"Hello, world!"}`` as expected.

Now let's change the greeting:

.. code-block:: bash

    juju config fastapi-hello-world greeting='Hi!'

After we wait for a moment for the app to be restarted, using
``curl http://fastapi-hello-world  --resolve fastapi-hello-world:80:127.0.0.1``
should now return the updated ``{"message":"Hi!"}`` greeting.

Integrate with a database
-------------------------

Now let's keep track of how many visitors your application has received.
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
database is initialized and ready to be used by the application. We will
create a ``migrate.py`` file containing this logic.

Go back out to the ``fastapi-hello-world`` directory using ``cd ..``,
open the ``migrate.py`` file using a text editor and paste the
following code into it:

.. code-block:: python

    import os

    import psycopg2

    DATABASE_URI = os.environ["POSTGRESQL_DB_CONNECT_STRING"]

    def migrate():
        with psycopg2.connect(DATABASE_URI) as conn, conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS visitors (
                    timestamp TIMESTAMP NOT NULL,
                    user_agent TEXT NOT NULL
                );
            """)
            conn.commit()


    if __name__ == "__main__":
        migrate()

.. note::

    The charm will pass the Database connection string in the
    ``POSTGRESQL_DB_CONNECT_STRING`` environment variable once postgres has
    been integrated with the charm.

Increment the ``version`` in ``rockcraft.yaml`` to ``0.3`` such that the
top of the ``rockcraft.yaml`` file looks similar to the following:

.. code-block:: yaml
    :emphasize-lines: 5

    name: fastapi-hello-world
    # see https://documentation.ubuntu.com/rockcraft/en/latest/explanation/bases/
    # for more information about bases and using 'bare' bases for chiselled rocks
    base: ubuntu@24.04 # the base environment for this FastAPI application
    version: '0.3' # just for humans. Semantic versioning is recommended
    summary: A summary of your FastAPI application # 79 char long summary
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

   ...

The app code also needs to be updated to keep track of the number of visitors
and to include a new endpoint to retrieve the number of visitors to the
app. Open ``app.py`` in a text editor and replace its contents with the
following code:

.. code-block:: python

    import datetime
    import os
    from typing import Annotated

    from fastapi import FastAPI, Header
    import psycopg2

    app = FastAPI()
    DATABASE_URI = os.environ["POSTGRESQL_DB_CONNECT_STRING"]


    @app.get("/")
    async def root(user_agent: Annotated[str | None, Header()] = None):
        with psycopg2.connect(DATABASE_URI) as conn, conn.cursor() as cur:
            timestamp = datetime.datetime.now()

            cur.execute(
                "INSERT INTO visitors (timestamp, user_agent) VALUES (%s, %s)",
                (timestamp, user_agent)
            )
            conn.commit()

        return {"message": os.getenv("APP_GREETING", "Hello World")}


    @app.get("/visitors")
    async def visitors():
        with psycopg2.connect(DATABASE_URI) as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM visitors")
            total_visitors = cur.fetchone()[0]

        return {"count": total_visitors}

Let's run the pack and upload commands for the rock:

.. code-block:: bash

    ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true rockcraft pack
    rockcraft.skopeo --insecure-policy copy --dest-tls-verify=false \
      oci-archive:fastapi-hello-world_0.3_amd64.rock \
      docker://localhost:32000/fastapi-hello-world:0.3

Change back into the charm directory using ``cd charm``.

The FastAPI app now requires a database which needs to be declared in the
``charmcraft.yaml`` file. Open ``charmcraft.yaml`` in a text editor and
add the following section to the end:

.. code-block:: yaml

    requires:
      postgresql:
        interface: postgresql_client
        optional: false

We can now pack and deploy the new version of the FastAPI app:

.. code-block:: bash

    CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true charmcraft pack
    juju refresh fastapi-hello-world \
      --path=./fastapi-hello-world_amd64.charm \
      --resource app-image=localhost:32000/fastapi-hello-world:0.3

Now let’s deploy PostgreSQL and integrate it with the FastAPI application:

.. code-block:: bash

    juju deploy postgresql-k8s --trust
    juju integrate fastapi-hello-world postgresql-k8s

Wait for ``juju status`` to show that the App is ``active`` again. Running
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

We’ve reached the end of this tutorial. We went through the entire
development process, including:

- Creating a FastAPI application
- Deploying the application locally
- Building an OCI image using Rockcraft
- Packaging the application using Charmcraft
- Deplyoing the application using Juju
- Exposing the application using an ingress
- Configuring the application
- Integrating the application with a database

If you'd like to reset your working environment, you can run the following
in the rock directory ``fastapi-hello-world`` for the tutorial:

.. code-block:: bash

    # exit and delete the virtual environment
    deactivate
    rm -rf charm .venv __pycache__
    # delete all the files created during the tutorial
    rm fastapi-hello-world_0.1_amd64.rock fastapi-hello-world_0.2_amd64.rock \
      fastapi-hello-world_0.3_amd64.rock rockcraft.yaml app.py \
      requirements.txt migrate.py
    # Remove the juju model
    juju destroy-model fastapi-hello-world --destroy-storage

You can also clean up your Multipass instance. Start by exiting it:

.. code-block:: bash

    exit

You can then proceed with its deletion:

.. code-block:: bash

    multipass delete charm-dev
    multipass purge


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

