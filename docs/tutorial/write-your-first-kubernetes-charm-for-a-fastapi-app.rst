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

Install Multipass.

    See more: `Multipass | How to install Multipass
    <https://multipass.run/docs/install-multipass>`_

Use Multipass to launch an Ubuntu VM with the name charm-dev from the 24.04 blueprint:

.. code-block:: bash

    multipass launch --cpus 4 --disk 50G --memory 4G --name charm-dev 24.04

Once the VM is up, open a shell into it:

.. code-block:: bash

    multipass shell charm-dev

In order to create the rock, you'll need to install Rockcraft:

.. code-block:: bash

    sudo snap install rockcraft --channel latest/edge --classic

``LXD`` will be required for building the rock. Make sure it is installed
and initialised:

.. code-block:: bash

    sudo snap install lxd
    lxd init --auto

In order to create the charm, you'll need to install Charmcraft:

.. code-block:: bash

    sudo snap install charmcraft --channel latest/edge --classic

MicroK8s is required to deploy the FastAPI application on Kubernetes.
Install MicroK8s:

.. code-block:: bash

    sudo snap install microk8s --channel 1.31-strict/stable
    sudo adduser $USER snap_microk8s
    newgrp snap_microk8s

Wait for MicroK8s to be ready using ``sudo microk8s status --wait-ready``.
Several MicroK8s add-ons are required for deployment:

.. code-block:: bash

    sudo microk8s enable hostpath-storage
    # Required to host the OCI image of the FastAPI application
    sudo microk8s enable registry
    # Required to expose the FastAPI application
    sudo microk8s enable ingress

Juju is required to deploy the FastAPI application. Install Juju and bootstrap
a development controller:

.. code-block:: bash

    sudo snap install juju --channel 3.5/stable
    mkdir -p ~/.local/share
    juju bootstrap microk8s dev-controller

Finally, create a new directory for this tutorial and go inside it:

.. code-block:: bash

    mkdir fastapi-hello-world
    cd fastapi-hello-world

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


Create the FastAPI application
------------------------------

Start by creating the "Hello, world" FastAPI application that will be used for
this tutorial.

Create a ``requirements.txt`` file, copy the following text into it and then save it:

.. code-block:: bash

    fastapi[standard]

In the same directory, copy and save the following into a text file called ``app.py``:

.. code-block:: python

    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/")
    async def root():
        return {"message": "Hello World"}


Run the FastAPI application locally
-----------------------------------

Install ``python3-venv`` and create a virtual environment:

.. code-block:: bash

    sudo apt-get update && sudo apt-get install python3-venv -y
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

Now that we have a virtual environment with all the dependencies,
let's run the FastAPI application to verify that it works:

.. code-block:: bash

    fastapi dev app.py --port 8080

Test the FastAPI application by using ``curl`` to send a request to the root
endpoint. You may need a new terminal for this; if you are using Multipass, use
``multipass shell charm-dev`` to get another terminal:

.. code-block:: bash

    curl localhost:8080

The FastAPI application should respond with ``{"message":"Hello World"}``. The
FastAPI application looks good, so we can stop for now using :kbd:`Ctrl` +
:kbd:`C`.


Pack the FastAPI application into a rock
----------------------------------------

First, we'll need a ``rockcraft.yaml`` file. Rockcraft will automate its creation
and tailoring for a FastAPI application by using the ``fastapi-framework`` profile:

.. code-block:: bash

    rockcraft init --profile fastapi-framework

The ``rockcraft.yaml`` file will be automatically created, with its name being
set based on your working directory. Open the file in a text editor and ensure
that the ``name`` is ``fastapi-hello-world`` and that ``platforms`` includes
the architecture of your host. For example, if your host uses the ARM
architecture, include ``arm64`` in ``platforms``.

.. note::

    For this tutorial, we'll use the name ``fastapi-hello-world`` and assume that
    you are on the ``amd64`` platform. Check the architecture of your system using
    ``dpkg --print-architecture``. Choosing a different name or running on a
    different platform will influence the names of the files generated by Rockcraft.

Pack the rock:

.. code-block:: bash

    ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true rockcraft pack

.. note::

    Depending on your system and network, this step can take a couple of minutes
    to finish.

    ``ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS`` is required while the FastAPI
    extension is experimental.

Once Rockcraft has finished packing the FastAPI rock, you'll find a new file
in your working directory with the ``.rock`` extension. View its contents:

.. code-block:: bash

    ls *.rock -l

.. note::

    If you changed the ``name`` or ``version`` in ``rockcraft.yaml`` or are not
    on the ``amd64`` platform, the name of the ``.rock`` file will be different
    for you.

The rock needs to be copied to the MicroK8s registry so that it can be deployed
in the Kubernetes cluster:

.. code-block:: bash

    rockcraft.skopeo --insecure-policy copy --dest-tls-verify=false \
      oci-archive:fastapi-hello-world_0.1_amd64.rock \
      docker://localhost:32000/fastapi-hello-world:0.1


Create the charm
----------------

Create a new directory for the charm and go inside it:

.. code-block:: bash

    mkdir charm
    cd charm

We'll need a ``charmcraft.yaml``, ``requirements.txt`` and source code for the
charm. The source code contains the logic required to operate the FastAPI application.
Charmcraft will automate the creation of these files by using the
``fastapi-framework`` profile:

.. code-block:: bash

    charmcraft init --profile fastapi-framework --name fastapi-hello-world

The charm depends on several libraries. Download the libraries and pack the charm:

.. code-block:: bash

    CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true charmcraft fetch-libs
    CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true charmcraft pack

.. note::

    Depending on your system and network, this step may take a couple of minutes
    to finish.

    ``CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS`` is required while the FastAPI
    extension is experimental.

Once Charmcraft has finished packing the charm, you'll find a new file in your
working directory with the ``.charm`` extension. View its contents:

.. code-block:: bash

    ls *.charm -l

.. note::

    If you changed the name in ``charmcraft.yaml`` or are not on the ``amd64``
    platform, the name of the ``.charm`` file will be different for you.


Deploy the FastAPI application
------------------------------

A Juju model is needed to deploy the application. Let's create a new model:

.. code-block:: bash

    juju add-model fastapi-hello-world

.. note::

    If you are not on a host with the ``amd64`` architecture, you will
    need to include a constraint to the Juju model to specify your
    architecture. For example, using the ``arm64`` architecture, you
    would use ``juju set-model-constraints -m django-hello-world arch=arm64``.
    Check the architecture of your system using ``dpkg --print-architecture``.

Now the FastAPI application can be deployed using Juju:

.. code-block:: bash

    juju deploy ./fastapi-hello-world_amd64.charm fastapi-hello-world \
      --resource app-image=localhost:32000/fastapi-hello-world:0.1

.. note::

    It will take a few minutes to deploy the FastAPI application. You can monitor
    the progress using ``juju status --watch 5s``. Once the status of the app
    changes to ``active``, you can stop watching using :kbd:`Ctrl` + :kbd:`C`.

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

The deployment is finished when the status shows ``active``. Let's expose the
application using ingress. Deploy the ``nginx-ingress-integrator`` charm and
integrate it with the FastAPI app:

.. code-block:: bash

    juju deploy nginx-ingress-integrator
    juju integrate nginx-ingress-integrator fastapi-hello-world

The hostname of the app needs to be defined so that it is accessible via
the ingress. We will also set the default route to be the endpoint:

.. code-block:: bash

    juju config nginx-ingress-integrator \
      service-hostname=fastapi-hello-world path-routes=/

Monitor ``juju status`` until everything has a status of ``active``. Use
``curl http://fastapi-hello-world --resolve fast-api-hello-world:80:127.0.0.1``
to send a request via the ingress. It should return the ``{"message":"Hello World"}``
greeting.

.. note::

    The ``--resolve fastapi-hello-world:80:127.0.0.1`` option to the ``curl``
    command is a way of resolving the hostname of the request without
    setting a DNS record.


Configure the FastAPI application
---------------------------------

Let's customise the greeting using a configuration option. We will expect this
configuration option to be available in the environment variable ``APP_GREETING``.
Go back out to the root directory of the project using ``cd ..`` and copy the
following code into ``app.py``:

.. code-block:: python

    import os

    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/")
    async def root():
        return {"message": os.getenv("APP_GREETING", "Hello World")}

Open ``rockcraft.yaml`` and update the version to ``0.2``. Run
``ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true rockcraft pack`` again,
then upload the new OCI image to the MicroK8s registry:

.. code-block:: bash

    rockcraft.skopeo --insecure-policy copy --dest-tls-verify=false \
      oci-archive:fastapi-hello-world_0.2_amd64.rock \
      docker://localhost:32000/fastapi-hello-world:0.2

Change back into the charm directory using ``cd charm``. The ``fastapi-framework``
Charmcraft extension supports adding configurations to ``charmcraft.yaml`` which
will be passed as environment variables to the FastAPI application. Add the
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

    Configuration options are automatically capitalised and dashes are replaced by
    underscores. An ``APP_`` prefix will also be added to ensure that environment
    variables are namespaced.

Run ``CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true charmcraft pack`` again. The
deployment can now be refreshed to make use of the new code:

.. code-block:: bash

    juju refresh fastapi-hello-world \
      --path=./fastapi-hello-world_amd64.charm \
      --resource app-image=localhost:32000/fastapi-hello-world:0.2

Wait for ``juju status`` to show that the App is ``active`` again. Verify that the
new configuration has been added using ``juju config fastapi-hello-world | grep
-A 6 greeting:`` which should show the configuration option.

.. note::

    The ``grep`` command extracts a portion of the configuration to make it easier to
    check whether the configuration option has been added.

Running ``http://fastapi-hello-world  --resolve fastapi-hello-world:80:127.0.0.1``
shows that the response is still ``{"message":"Hello, world!"}`` as expected. The
greeting can be changed using Juju:

.. code-block:: bash

    juju config fastapi-hello-world greeting='Hi!'

``curl http://fastapi-hello-world  --resolve fastapi-hello-world:80:127.0.0.1`` now
returns the updated ``{"message":"Hi!"}`` greeting.

.. note::

    It may take a short time for the configuration to take effect.


Integrate with a database
-------------------------

Now let's keep track of how many visitors your application has received. This will
require integration with a database to keep the visitor count. This will require
a few changes:

- We will need to create a database migration that creates the ``visitors`` table.
- We will need to keep track of how many times the root endpoint has been called
  in the database.
- We will need to add a new endpoint to retrieve the number of visitors from
  the database.

The charm created by the ``fastapi-framework`` extension will execute the
``migrate.py`` script if it exists. This script should ensure that the
database is initialised and ready to be used by the application. We will create
a ``migrate.py`` file containing this logic.

Go back out to the tutorial root directory using ``cd ..``. Create the
``migrate.py`` file using a text editor and paste the following code into it:

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

Open the ``rockcraft.yaml`` file in a text editor and update the version
to ``0.3``.

To be able to connect to postgresql from the FastAPI app, the ``psycopg2-binary``
dependency needs to be added in ``requirements.txt``. The app code also needs to
be updated to keep track of the number of visitors and to include a new endpoint
to retrieve the number of visitors. Open ``app.py`` in a text editor and replace
its contents with the following code:

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

Run ``ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true rockcraft pack`` and upload
the newly created rock to the MicroK8s registry:

.. code-block:: bash

    rockcraft.skopeo --insecure-policy copy --dest-tls-verify=false \
      oci-archive:fastapi-hello-world_0.3_amd64.rock \
      docker://localhost:32000/fastapi-hello-world:0.3

The FastAPI app now requires a database which needs to be declared in the
``charmcraft.yaml`` file. Go back into the charm directory using ``cd charm``.
Open ``charmcraft.yaml`` in a text editor and add the following section at the
end of the file:

.. code-block:: yaml

    requires:
      postgresql:
        interface: postgresql_client
        optional: false

Pack the charm using ``CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true charmcraft pack``
and refresh the deployment using Juju:

.. code-block:: bash

    juju refresh fastapi-hello-world \
      --path=./fastapi-hello-world_amd64.charm \
      --resource app-image=localhost:32000/fastapi-hello-world:0.3

Deploy ``postgresql-k8s`` using Juju and integrate it with ``fastapi-hello-world``:

.. code-block:: bash

    juju deploy postgresql-k8s --trust
    juju integrate fastapi-hello-world postgresql-k8s

Wait for ``juju status`` to show that the App is ``active`` again. Executing
``curl http://fastapi-hello-world  --resolve fastapi-hello-world:80:127.0.0.1`` should
still return the ``{"message":"Hi!"}`` greeting.

To check the local visitors, use ``curl http://fastapi-hello-world/visitors  --resolve
fastapi-hello-world:80:127.0.0.1``, which should return ``{"count":1}`` after the
previous request to the root endpoint. This should be incremented each time the root
endpoint is requested. If we repeat this process, the output should be as follows:

.. terminal::
    :input: curl http://fastapi-hello-world  --resolve fastapi-hello-world:80:127.0.0.1

    {"message":"Hi!"}
    :input: curl http://fastapi-hello-world/visitors  --resolve fastapi-hello-world:80:127.0.0.1
    {"count":2}


Tear things down
----------------

We've reached the end of this tutorial. We have created a FastAPI application,
deployed it locally, integrated it with a database and exposed it via ingress!

If you'd like to reset your working environment, you can run the following
in the root directory for the tutorial:

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

If you created an instance using Multipass, you can also clean it up.
Start by exiting it:

.. code-block:: bash

    exit

You can then proceed with its deletion:

.. code-block:: bash

    multipass delete charm-dev
    multipass purge


Next steps
----------

By the end of this tutorial, you will have built a charm and evolved it
in a number of practical ways, but there is a lot more to explore:

+-------------------------+----------------------+
| If you are wondering... | Visit...             |
+=========================+======================+
| "How do I...?"          | :ref:`how-to-guides` |
+-------------------------+----------------------+
| "What is...?"           | :ref:`reference`     |
+-------------------------+----------------------+
