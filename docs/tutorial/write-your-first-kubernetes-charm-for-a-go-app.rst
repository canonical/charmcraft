.. _write-your-first-kubernetes-charm-for-a-go-app:

Write your first Kubernetes charm for a Go app
==============================================

Imagine you have a Go application backed up by a database
such as PostgreSQL and need to deploy it. In a traditional setup,
this can be quite a challenge, but with Charmcraft you'll find
yourself packaging and deploying your Go application in no time.
Let's get started!

In this tutorial we will build a Kubernetes charm for a Go
application using Charmcraft, so we can have a Go application
up and running with Juju.

This tutorial should take 90 minutes for you to complete.

.. note::
    If you're new to the charming world: Go applications are
    specifically supported with a coordinated pair of profiles
    for an OCI container image (**rock**) and corresponding
    packaged software (**charm**) that allow for the application
    to be deployed, integrated and operated on a Kubernetes
    cluster with the Juju orchestration engine.

What you'll need:
-----------------

- A workstation, e.g., a laptop, with amd64 or arm64 architecture which
  has sufficient resources to launch a virtual machine with 4 CPUs,
  4 GB RAM, and a 50 GB disk.
- Familiarity with Linux.

What you'll do:
---------------

Create a Go application. Use that to create a rock with
``rockcraft``. Use that to create a charm with ``charmcraft``. Use that
to test, deploy, configure, etc., your Go application on a local
Kubernetes cloud, ``microk8s``, with ``juju``. All of that multiple
times, mimicking a real development process.

.. important::

    Should you get stuck or notice issues, please get in touch on
    `Matrix <https://matrix.to/#/#12-factor-charms:ubuntu.com>`_ or
    `Discourse <https://discourse.charmhub.io/>`_


Set things up
-------------

.. include:: /reuse/tutorial/setup_edge.rst
.. |12FactorApp| replace: Go

Finally, let's create a new directory for this tutorial and
change into it:

.. code-block:: bash

    mkdir go-hello-world
    cd go-hello-world

Create the Go application
-------------------------

Start by creating the "Hello, world" Go application that will be
used for this tutorial.

Install ``go`` and initialize the Go module:

.. code-block:: bash

    sudo snap install go --classic go mod init go-hello-world

Create a ``main.go`` file, copy the following text into it and then
save it:

.. code-block:: python

    package main

    import (
      "fmt" "log" "net/http"
    )

    func helloWorldHandler(w http.ResponseWriter, req *http.Request) {
      log.Printf("new hello world request") fmt.Fprintln(w, "Hello, world!")
    }

    func main() {
      log.Printf("starting hello world application") http.HandleFunc("/",
      helloWorldHandler) http.ListenAndServe(":8080", nil)
    }


Run the Go application locally
------------------------------

First, we need to build the Go application so it can run:

.. code-block:: bash

    go build .

Now that we have a binary compiled, let's run the Go application to verify
that it works:

.. code-block:: bash

    ./go-hello-world

Test the Go application by using ``curl`` to send a request to the root
endpoint. You will need a new terminal for this; use
``multipass shell charm-dev`` to open a new terminal in Multipass:

.. code-block:: bash

    curl localhost:8080

The Go application should respond with ``Hello, world!``.

The Go application looks good, so we can stop it for now from the
original terminal using :kbd:`Ctrl` + :kbd:`C`.


Pack the Go application into a rock
-----------------------------------

First, we'll need a ``rockcraft.yaml`` file. Using the
``go-framework`` profile, Rockcraft will automate the creation of
``rockcraft.yaml`` and tailor the file for a Go application.
From the ``go-hello-world`` directory, initialize the rock:

.. code-block:: bash

    rockcraft init --profile go-framework

The ``rockcraft.yaml`` file will automatically be created and set the name
based on your working directory.

Check out the contents of ``rockcraft.yaml``:

.. code:: bash

    cat rockcraft.yaml

The top of the file should look similar to the following snippet:

.. code:: yaml

   name: go-hello-world
   # see https://documentation.ubuntu.com/rockcraft/en/latest/explanation/bases/
   # for more information about bases and using 'bare' bases for chiselled rocks
   base: bare # as an alternative, a ubuntu base can be used
   build-base: ubuntu@24.04 # build-base is required when the base is bare
   version: '0.1' # just for humans. Semantic versioning is recommended
   summary: A summary of your Go application # 79 char long summary
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

   ...

Verfiy that the ``name`` is ``go-hello-world``.

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

    ``ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS`` is required while the Go
    extension is experimental.

Depending on your system and network, this step can take several
minutes to finish.

Once Rockcraft has finished packing the Go rock,
the terminal will respond with something similar to
``Packed go-hello-world_0.1_amd64.rock``.

.. note::

   If you are not on an ``amd64`` platform, the name of the ``.rock`` file
   will be different for you.

The rock needs to be copied to the MicroK8s registry, which stores OCI
archives so they can be downloaded and deployed in the Kubernetes cluster.
Copy the rock:

.. code-block:: bash

    rockcraft.skopeo --insecure-policy copy --dest-tls-verify=false \
      oci-archive:go-hello-world_0.1_amd64.rock \
      docker://localhost:32000/go-hello-world:0.1

.. seealso::

    See more: `Ubuntu manpage | skopeo
    <https://manpages.ubuntu.com/manpages/noble/man1/skopeo.1.html>`_

Create the charm
----------------

From the ``go-hello-world`` directory, let's create a new directory
for the charm and change inside it:

.. code-block:: bash

    mkdir charm
    cd charm

Using the ``go-framework`` profile, Charmcraft will automate the
creation of the files needed for our charm, including a
``charmcraft.yaml``, ``requirements.txt`` and source code for the charm.
The source code contains the logic required to operate the Go
application.

Initialize a charm named ``go-hello-world``:

.. code-block:: bash

    charmcraft init --profile go-framework --name go-hello-world

The files will automatically be created in your working directory.

The charm depends on several libraries. Download the libraries and pack the charm:

.. code-block:: bash

    CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true charmcraft fetch-libs
    CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true charmcraft pack

.. note::

    ``CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS`` is required while the FastAPI
    extension is experimental.

Depending on your system and network, this step can take several
minutes to finish.

Once Charmcraft has finished packing the charm, the terminal will
respond with something similar to
``Packed go-hello-world_ubuntu-24.04-amd64.charm``.

.. note::

    If you are not on the ``amd64`` platform, the name of the ``.charm``
    file will be different for you.


Deploy the Go application
-------------------------

A Juju model is needed to deploy the application. Let's create a enw model:

.. code-block:: bash

    juju add-model go-hello-world

.. note::

    If you are not on a host with the ``amd64`` architecture, you will need to include a
    constraint to the Juju model to specify your architecture. For example, using the
    ``arm64`` architecture, you would use ``juju set-model-constraints -m
    django-hello-world arch=arm64``. Check the architecture of your system using ``dpkg
    --print-architecture``.

Now the Go application can be deployed using Juju:

.. code-block:: bash

    juju deploy ./go-hello-world_amd64.charm \
      go-hello-world \ --resource app-image=localhost:32000/go-hello-world:0.1

.. note::

    It will take a few minutes to deploy the FastAPI application. You can monitor the
    progress using ``juju status --watch 5s``. Once the status of the app changes to
    ``active``, you can stop watching using :kbd:`Ctrl` + :kbd:`C`.

The Go application should now be running. We can monitor the status of the deployment
using ``juju status``, which should be similar to the following output:

.. terminal::
    :input: juju status

    go-hello-world  microk8s    microk8s/localhost  3.5.4    unsupported  14:35:07+02:00

    App             Version  Status  Scale  Charm           Channel  Rev  Address
    Exposed  Message go-hello-world           active      1  go-hello-world
    0  10.152.183.229  no

    Unit               Workload  Agent  Address      Ports  Message go-hello-world/0*
    active    idle   10.1.157.79

The deployment is finished when the status shows ``active``. Let's expose the
application using ingress. Deploy the ``nginx-ingress-integrator`` charm and integrate
it with the Go app:

.. code-block:: bash

    juju deploy nginx-ingress-integrator --trust juju integrate nginx-ingress-integrator
    go-hello-world

The hostname of the app needs to be defined so that it is accessible via the ingress. We
will also set the default route to be the root endpoint:

.. code-block:: bash

    juju config nginx-ingress-integrator \
      service-hostname=go-hello-world path-routes=/

.. note::

    By default, the port for the Go application should be 8080. If you want to change
    the default port, it can be done with the configuration option ``app-port`` that
    will be exposed as the ``APP_PORT`` to the Go application.

Monitor ``juju status`` until everything has a status of ``active``. Use ``curl
http://go-hello-world  --resolve go-hello-world:80:127.0.0.1`` to send a request via the
ingress. The Go application should respond with ``Hello, world~``.


Configure the Go application
----------------------------

Now let's customise the greeting using a configuration option. We will expect this
configuration option to be available in the Go app configuration under the keyword
``GREETING``. Go back out to the root directory of the project using ``cd ..`` and copy
the following code into ``main.go``:

.. code-block:: c

    package main

    import (
      "fmt" "log" "os" "net/http"
    )

    func helloWorldHandler(w http.ResponseWriter, req *http.Request) {
      log.Printf("new hello world request") greeting, found :=
      os.LookupEnv("APP_GREETING") if !found {
        greeting = "Hello, world!"
      } fmt.Fprintln(w, greeting)
    }

    func main() {
      log.Printf("starting hello world application") http.HandleFunc("/",
      helloWorldHandler) http.ListenAndServe(":8080", nil)
    }

Open ``rockcraft.yaml`` and update the version to ``0.2``. Run
``ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true rockcraft pack`` again, then upload the
new OCI image to the MicroK8s registry.

.. code-block:: bash

    rockcraft.skopeo --insecure-policy copy --dest-tls-verify=false \
      oci-archive:go-hello-world_0.2_amd64.rock \
      docker://localhost:32000/go-hello-world:0.2

Change back into the charm directory using ``cd charm``. The ``go-framework`` Charmcraft
extension supports adding configurations to ``charmcraft.yaml``, which will be passed as
environment variables to the Go application. Add the following to the end of the
``charmcraft.yaml`` file:

.. code-block:: yaml

    config:
      options:
        greeting:
          description: |
            The greeting to be returned by the Go application.
          default: "Hello, world!" type: string

.. note::

    Configuration options are automatically capitalised and dashes are replaced by
    underscores. An ``APP_`` prefix will also be added to ensure that environment
    variables are namespaced.

Run ``CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true charmcraft pack`` again. The
deployment can now be refreshed to make use of the new code:

.. code-block:: bash

    juju refresh go-hello-world \
      --path=./go-hello-world_amd64.charm \ --resource
      app-image=localhost:32000/go-hello-world:0.2

Wait for ``juju status`` to show that the App is ``active`` again. Verify that the new
configuration has been added using ``juju config go-hello-world | grep -A 6 greeting:``,
which should show the configuration option.

.. note::

    The ``grep`` command extracts a portion of the configuration to make it easier to
    check whether the configuration option has been added.

Using ``curl http://go-hello-world  --resolve go-hello-world:80:127.0.0.1`` shows that
the response is still ``Hello, world!`` as expected. The greeting can be changed using
Juju:

.. code-block:: bash

    juju config go-hello-world greeting='Hi!'

``curl http://go-hello-world  --resolve go-hello-world:80:127.0.0.1`` now returns the
updated ``Hi!`` greeting.

.. note::

    It might take a short time for the configuration to take effect.


Integrate with a database
-------------------------

Now let's keep track of how many visitors your application has received. This will
require integration with a database to keep the visitor count. This will require a few
changes:

- We will need to create a database migration that creates the ``visitors`` table.
- We will need to keep track how many times the root endpoint has been called in the
  database.
- We will need to add a new endpoint to retrieve the number of visitors from the
- database.

The charm created by the ``go-framework`` extension will execute the ``migrate.sh``
script if it exists. This script should ensure that the database is initialised and
ready to be used by the application. We will create a ``migrate.sh`` file containing the
logic.

Go back out to the tutorial root directory using ``cd ..``. Create the ``migrate.sh``
file using a text editor and paste the following code into it:

.. code-block:: bash

    #!/bin/bash

    PGPASSWORD="${POSTGRESQL_DB_PASSWORD}" psql -h "${POSTGRESQL_DB_HOSTNAME}" -U
    "${POSTGRESQL_DB_USERNAME}" "${POSTGRESQL_DB_NAME}" -c "CREATE TABLE IF NOT EXISTS
    visitors (timestamp TIMESTAMP NOT NULL, user_agent TEXT NOT NULL);"

.. note::

    The charm will pass the Database connection string in the
    ``POSTGRESQL_DB_CONNECT_STRING`` environment variable once PostgreSQL has been
    integrated with the charm.

Change the permissions of the file ``migrate.sh`` so that it is executable:

.. code-block:: bash

    chmod u+x migrate.sh

For the migrations to work, we need the ``postgresql-client`` package installed in the
rock. By default, the ``go-framework`` uses the ``base`` base, so we will also need to
install a shell interpreter. Let's do it as a slice, so that the rock does not include
unnecessary files. Open the ``rockcraft.yaml`` file using a text editor, update the
version to ``0.3`` and add the following to the end of the file:

.. code-block:: yaml

    parts:
      runtime-debs:
        plugin: nil stage-packages:
          - postgresql-client
      runtime-slices:
        plugin: nil stage-packages:
          - bash_bins

To be able to connect to PostgreSQL from the Go app, the library ``pgx`` will be used.
The app code needs to be updated to keep track of the number of visitors and to include
a new endpoint to retrieve the number of visitors. Open ``main.go`` in a text editor and
replace its content with the following code:

.. dropdown:: main.go

    .. code-block:: c

        package main

        import (
                "database/sql" "fmt" "log" "net/http" "os" "time"

                _ "github.com/jackc/pgx/v5/stdlib"
        )

        func helloWorldHandler(w http.ResponseWriter, req *http.Request) {
                log.Printf("new hello world request") postgresqlURL :=
                os.Getenv("POSTGRESQL_DB_CONNECT_STRING") db, err := sql.Open("pgx",
                postgresqlURL) if err != nil {
                        log.Printf("An error occurred while connecting to postgresql:
                        %v", err) return
                } defer db.Close()

                ua := req.Header.Get("User-Agent") timestamp := time.Now() _, err =
                db.Exec("INSERT into visitors (timestamp, user_agent) VALUES ($1, $2)",
                timestamp, ua) if err != nil {
                        log.Printf("An error occurred while executing query: %v", err)
                        return
                }

                greeting, found := os.LookupEnv("APP_GREETING") if !found {
                        greeting = "Hello, world!"
                }

                fmt.Fprintln(w, greeting)
        }

        func visitorsHandler(w http.ResponseWriter, req *http.Request) {
                log.Printf("visitors request") postgresqlURL :=
                os.Getenv("POSTGRESQL_DB_CONNECT_STRING") db, err := sql.Open("pgx",
                postgresqlURL) if err != nil {
                        return
                } defer db.Close()

                var numVisitors int err = db.QueryRow("SELECT count(*) from
                visitors").Scan(&numVisitors) if err != nil {
                        log.Printf("An error occurred while executing query: %v", err)
                        return
                } fmt.Fprintf(w, "Number of visitors %d\n", numVisitors)
        }

        func main() {
                log.Printf("starting hello world application") http.HandleFunc("/",
                helloWorldHandler) http.HandleFunc("/visitors", visitorsHandler)
                http.ListenAndServe(":8080", nil)
        }

Check all the packages and their dependencies in the Go project with the following
command:

.. code-block:: bash

    go mod tidy

Run ``ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true rockcraft pack`` and upload the
newly created rock to the MicroK8s registry:

.. code-block:: bash

    rockcraft.skopeo --insecure-policy copy --dest-tls-verify=false \
      oci-archive:go-hello-world_0.3_amd64.rock \
      docker://localhost:32000/go-hello-world:0.3

Go back into the charm directory using ``cd charm``. The Go app now requires a database
which needs to be declared in the ``charmcraft.yaml`` file. Open ``charmcraft.yaml`` in
a text editor and add the following section to the end of the file:

.. code-block:: yaml

    requires:
      postgresql:
        interface: postgresql_client optional: false

Pack the charm using ``CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true charmcraft pack``
and refresh the deployment using Juju:

.. code-block:: bash

    juju refresh go-hello-world \
      --path=./go-hello-world_amd64.charm \ --resource
      app-image=localhost:32000/go-hello-world:0.3

Deploy ``postgresql-k8s`` using Juju and integrate it with ``go-hello-world``:

.. code-block:: bash

    juju deploy postgresql-k8s --trust juju integrate go-hello-world postgresql-k8s

Wait for ``juju status`` to show that the App is ``active`` again. Executing ``curl
http://go-hello-world  --resolve go-hello-world:80:127.0.0.1`` should still return the
``Hi!`` greeting.

To check the local visitors, use ``curl http://go-hello-world/visitors  --resolve
go-hello-world:80:127.0.0.1``, which should return ``Number of visitors 1`` after the
previous request to the root endpoint. This should be incremented each time the root
endpoint is requested. If we repeat this process, the output should be as follows:

.. terminal::
    :input: curl http://go-hello-world  --resolve go-hello-world:80:127.0.0.1

    Hi! :input: curl http://go-hello-world/visitors  --resolve
    go-hello-world:80:127.0.0.1 Number of visitors 2


Tear things down
----------------

We've reached the end of this tutorial. We have created a Go application, deployed it
locally, integrated it with a database and exposed it via ingress!

If you'd like to reset your working environment, you can run the following in the root
directory for the tutorial:

.. code-block:: bash

    cd .. rm -rf charm # delete all the files created during the tutorial rm
    go-hello-world_0.1_amd64.rock go-hello-world_0.2_amd64.rock \
      go-hello-world_0.3_amd64.rock rockcraft.yaml main.go \ migrate.sh go-hello-world
      go.mod go.sum
    # Remove the juju model juju destroy-model go-hello-world --destroy-storage

If you created an instance using Multipass, you can also clean it up. Start by exiting
it:

.. code-block:: bash

    exit

You can then proceed with its deletion:

.. code-block:: bash

    multipass delete charm-dev multipass purge


Next steps
----------

By the end of this tutorial, you will have built a charm and evolved it in a number of
practical ways, but there is a lot more to explore:

+-------------------------+----------------------+
| If you are wondering... | Visit...             |
+=========================+======================+
| "How do I...?"          | :ref:`how-to-guides` |
+-------------------------+----------------------+
| "What is...?"           | :ref:`reference`     |
+-------------------------+----------------------+
