.. _write-your-first-kubernetes-charm-for-a-spring-boot-app:

Write your first Kubernetes charm for a Spring Boot app
=======================================================

Imagine you have a Spring Boot app backed up by a database
such as PostgreSQL and need to deploy it. In a traditional setup,
this can be quite a challenge, but with Charmcraft you'll find
yourself packaging and deploying your Spring Boot app in no time.

In this tutorial we will build a Kubernetes charm for a Spring Boot
app using Charmcraft, so we can have a Spring Boot app
up and running with Juju. Let's get started!

This tutorial should take 90 minutes for you to complete.

If you're new to the charming world, Spring Boot apps are
specifically supported with a template to quickly generate a
**rock** and a matching template to generate a **charm**.
A rock is a special kind of OCI-compliant container image, while a
charm is a software operator for cloud operations that use the Juju
orchestration engine. The combined result is a Spring Boot app that
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

#. Create a Spring Boot app.
#. Use that to create a rock with Rockcraft.
#. Use that to create a charm with Charmcraft.
#. Use that to test, deploy, configure, etc., your Spring Boot app on a local
   Kubernetes cloud with Juju.
#. Repeat the process, mimicking a real development process.

.. important::

    Should you get stuck or notice issues, please get in touch on
    `Matrix <https://matrix.to/#/#12-factor-charms:ubuntu.com>`_ or
    `Discourse <https://discourse.charmhub.io/>`_


Set things up
-------------

.. include:: /reuse/tutorial/setup_edge.rst
.. |12FactorApp| replace:: Spring Boot

As the ``spring-boot-framework`` extensions for Rockcraft and Charmcraft are
still in development, we must enable experimental extensions for each:

.. literalinclude:: code/spring-boot/task.yaml
    :language: bash
    :start-after: [docs:export-experimental-env-vars]
    :end-before: [docs:export-experimental-env-vars-end]
    :dedent: 2

Create the Spring Boot app
--------------------------

Start by creating the "Hello, world" Spring Boot app that will be
used for this tutorial.

Install ``devpack-for-spring`` and Java.

.. literalinclude:: code/spring-boot/task.yaml
    :language: bash
    :start-after: [docs:install-devpack-for-spring]
    :end-before: [docs:install-devpack-for-spring-end]
    :dedent: 2

Create the demo Spring Boot app that will be used for
this tutorial.

.. seealso::

    For more information about the options: `Spring Boot CLI | Using the CLI
    <https://docs.spring.io/spring-boot/cli/using-the-cli.html>`_

.. literalinclude:: code/spring-boot/task.yaml
    :language: bash
    :start-after: [docs:init-spring-boot]
    :end-before: [docs:init-spring-boot-end]
    :dedent: 2

Create a new "Hello world" file with
``nano ~/spring-boot-hello-world/src/main/java/com/example/demo/HelloController.java``.
Then, copy the following text into it, and save:

.. literalinclude:: code/spring-boot/HelloController.java
    :caption: ~/spring-boot-hello-world/src/main/java/com/example/demo/\
              HelloController.java
    :language: java

Run the Spring Boot app locally
-------------------------------

First, we need to build the Spring Boot app so it can run:

.. literalinclude:: code/spring-boot/task.yaml
    :language: bash
    :start-after: [docs:spring-boot-build]
    :end-before: [docs:spring-boot-build-end]
    :dedent: 2

The app compiles to a JAR called ``demo-0.0.1.jar`` in
``~/spring-boot-hello-world/target/``. We'll only use this JAR for
local testing, as Rockcraft will package the Spring Boot app when
we pack the rock later.

Let's run the app to verify that it works:

.. code:: bash

  java -jar target/demo-0.0.1.jar

The app starts an HTTP server listening on port 8080
that we can test by using ``curl`` to send a request to the root
endpoint. You will need a new terminal for this -- use
``multipass shell charm-dev`` to open a new terminal
in Multipass:

.. literalinclude:: code/spring-boot/task.yaml
    :language: bash
    :start-after: [docs:curl-spring-boot]
    :end-before: [docs:curl-spring-boot-end]
    :dedent: 2

The Spring Boot app should respond with ``Hello, world!``

The Spring Boot app looks good, so let's stop it for now
with :kbd:`Ctrl` + :kbd:`C` and close the second terminal.


Pack the Spring Boot app into a rock
------------------------------------

Now let's create a container image for our Spring Boot app. We'll use a rock,
which is an OCI-compliant container image based on Ubuntu.

First, we'll need a ``rockcraft.yaml`` project file. We'll take advantage of a
pre-defined extension in Rockcraft with the ``--profile`` flag that caters
initial rock files for specific web app frameworks. Using the
``spring-boot-framework`` profile, Rockcraft automates the creation of
``rockcraft.yaml`` and tailors the file for a Spring Boot app.
From the ``~/spring-boot-hello-world`` directory, initialize the rock:

.. literalinclude:: code/spring-boot/task.yaml
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
    :caption: ~/spring-boot-hello-world/rockcraft.yaml

    name: spring-boot-hello-world
    # see https://documentation.ubuntu.com/rockcraft/en/latest/explanation/bases/
    # for more information about bases and using 'bare' bases for chiselled rocks
    base: bare # as an alternative, a ubuntu base can be used
    build-base: ubuntu@24.04 # build-base is required when the base is bare
    version: '0.1' # just for humans. Semantic versioning is recommended
    summary: A summary of your Spring Boot application # 79 char long summary
    description: |
        This is spring-boot-hello-world's description. You have a paragraph or two to tell the
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

Verfiy that the ``name`` is ``spring-boot-hello-world``.

The ``platforms`` key must match the architecture of your host.
Edit the ``platforms`` key in ``rockcraft.yaml`` if required.

Now let's pack the rock:

.. literalinclude:: code/spring-boot/task.yaml
    :language: bash
    :start-after: [docs:pack]
    :end-before: [docs:pack-end]
    :dedent: 2

Depending on your system and network, this step can take several
minutes to finish.

.. admonition:: For more options when packing rocks

    See the :external+rockcraft:ref:`ref_commands_pack` command reference.

Once Rockcraft has finished packing the Spring Boot rock,
the terminal will respond with something similar to
``Packed spring-boot-hello-world_0.1_<architecture>.rock``. The file name
reflects your system's architecture. After the initial
pack, subsequent rock packings are faster.

The rock needs to be copied to the MicroK8s registry. This registry acts as a
temporary Dockerhub, storing OCI archives so they can be downloaded and
deployed in the Kubernetes cluster. Copy the rock:

.. literalinclude:: code/spring-boot/task.yaml
    :language: bash
    :start-after: [docs:skopeo-copy]
    :end-before: [docs:skopeo-copy-end]
    :dedent: 2

This command contains the following pieces:

- ``--insecure-policy``: adopts a permissive policy that
  removes the need for a dedicated policy file.
- ``--dest-tls-verify=false``: disables the need for HTTPS
  and verify certificates while interacting with the MicroK8s registry.
- ``oci-archive``: specifies the rock we created for our Spring Boot app.
- ``docker``: specifies the name of the image in the MicroK8s registry.

.. seealso::

    See more: `Ubuntu manpage | skopeo
    <https://manpages.ubuntu.com/manpages/jammy/man1/skopeo.1.html>`_


Create the charm
----------------

From the ``~/spring-boot-hello-world`` directory, let's create a new directory
for the charm and change inside it:

.. literalinclude:: code/spring-boot/task.yaml
    :language: bash
    :start-after: [docs:create-charm-dir]
    :end-before: [docs:create-charm-dir-end]
    :dedent: 2

Similar to the rock, we'll take advantage of a pre-defined extension in
Charmcraft with the ``--profile`` flag that caters initial charm files for
specific web app frameworks. Using the ``spring-boot-framework`` profile,
Charmcraft automates the creation of the files needed for our charm,
including a ``charmcraft.yaml`` project file, ``requirements.txt`` and source
code for the charm. The source code contains the logic required to operate the
Spring Boot app.

Initialize a charm named ``spring-boot-hello-world``:

.. literalinclude:: code/spring-boot/task.yaml
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
    :caption: ~/spring-boot-hello-world/charm/charmcraft.yaml

    # This file configures Charmcraft.
    # See https://juju.is/docs/sdk/charmcraft-config for guidance.

    name: spring-boot-hello-world

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
    summary: A very short one-line summary of the Spring Boot app.

    ...

Verify that the ``name`` is ``spring-boot-hello-world``. Ensure that ``platforms``
includes the architecture of your host. Edit the ``platforms`` key in the
project file if required.

.. tip::

    Want to learn more about all the configurations in the
    ``spring-boot-framework`` profile? Run ``charmcraft expand-extensions``
    from the ``~/spring-boot-hello-world/charm/`` directory.

Let's pack the charm:

.. literalinclude:: code/spring-boot/task.yaml
    :language: bash
    :start-after: [docs:charm-pack]
    :end-before: [docs:charm-pack-end]
    :dedent: 2

Depending on your system and network, this step can take several
minutes to finish.

Once Charmcraft has finished packing the charm, the terminal will
respond with something similar to
``Packed spring-boot-hello-world_ubuntu-24.04-<architecture>.charm``. The file name
reflects your system's architecture. After the initial
pack, subsequent charm packings are faster.

.. admonition:: For more options when packing charms

    See the :literalref:`pack<ref_commands_pack>` command reference.


Deploy the Spring Boot app
--------------------------

A Juju model is needed to handle Kubernetes resources while deploying
the Spring Boot app. The Juju model holds the app along with any supporting
components. In this tutorial, our model will hold the Spring Boot app, ingress,
and a PostgreSQL database.

Let's create a new model:

.. literalinclude:: code/spring-boot/task.yaml
    :language: bash
    :start-after: [docs:add-juju-model]
    :end-before: [docs:add-juju-model-end]
    :dedent: 2

Constrain the Juju model to your architecture:

.. literalinclude:: code/spring-boot/task.yaml
    :language: bash
    :start-after: [docs:add-model-constraints]
    :end-before: [docs:add-model-constraints-end]
    :dedent: 2

Now let's use the OCI image we previously uploaded to deploy the Spring Boot
app. Deploy using Juju by specifying the OCI image name with the
``--resource`` option:

.. literalinclude:: code/spring-boot/task.yaml
    :language: bash
    :start-after: [docs:deploy-app]
    :end-before: [docs:deploy-app-end]
    :dedent: 2

It will take a few minutes to deploy the Spring Boot app. You can monitor its
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

The Spring Boot app should now be running. We can monitor the status of
the deployment using ``juju status``, which should be similar to the
following output:

.. terminal::
    :input: juju status

    Model                    Controller      Cloud/Region        Version  SLA          Timestamp
    spring-boot-hello-world  dev-controller  microk8s/localhost  3.6.6    unsupported  16:22:04+02:00

    App                      Version  Status  Scale  Charm                    Channel  Rev  Address         Exposed  Message
    spring-boot-hello-world           active      1  spring-boot-hello-world             0  10.152.183.157  no

    Unit                        Workload  Agent  Address       Ports  Message
    spring-boot-hello-world/0*  active    idle   10.1.223.117

Let's expose the app using ingress so that we can access it. Deploy the
``nginx-ingress-integrator`` charm and integrate it with the Spring Boot app:

.. literalinclude:: code/spring-boot/task.yaml
    :language: bash
    :start-after: [docs:deploy-nginx]
    :end-before: [docs:deploy-nginx-end]
    :dedent: 2

The hostname of the app needs to be defined so that it is accessible via
the ingress. We will also set the default route to be the root endpoint:

.. literalinclude:: code/spring-boot/task.yaml
    :language: bash
    :start-after: [docs:config-nginx]
    :end-before: [docs:config-nginx-end]
    :dedent: 2

.. note::

    By default, the port for the Spring Boot app should be 8080. If you want to change
    the default port, it can be done with the configuration option ``app-port`` that
    will be exposed as the environment variable ``SERVER_PORT`` to the Spring Boot app.

Monitor ``juju status`` until everything has a status of ``active``.

Send a request via the ingress:

.. code-block:: bash

    curl http://spring-boot-hello-world --resolve spring-boot-hello-world:80:127.0.0.1

The request should return the ``Hello, world!`` greeting.

.. note::

    The ``--resolve spring-boot-hello-world:80:127.0.0.1`` option to the ``curl``
    command is a way of resolving the hostname of the request without
    setting a DNS record.


The development cycle
---------------------

So far, we have worked though the entire cycle, from creating an app to deploying it.
But now – as in every real-world case – we will go through the experience of
iterating to develop the app, and deploy each iteration.

Configure the Spring Boot app
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To demonstrate how to provide a configuration to the Spring Boot app,
we will make the greeting configurable. We will expect this
configuration option to be available in the Spring Boot app configuration under the
keyword ``GREETING``. Change back to the ``~/spring-boot-hello-world`` directory using
``cd ..`` and replace the code into
``src/main/java/com/example/demo/HelloController.java`` with the following:

.. literalinclude:: code/spring-boot/HelloController.java.greeting.txt
    :caption: ~/spring-boot-hello-world/src/main/java/com/example/demo/\
              HelloController.java
    :language: java

Update the rock
~~~~~~~~~~~~~~~

Increment the ``version`` in ``rockcraft.yaml`` to ``0.2`` such that the
top of the ``rockcraft.yaml`` file looks similar to the following:

.. code-block:: yaml
    :caption: ~/spring-boot-hello-world/rockcraft.yaml
    :emphasize-lines: 6

    name: spring-boot-hello-world
    # see https://documentation.ubuntu.com/rockcraft/en/latest/explanation/bases/
    # for more information about bases and using 'bare' bases for chiselled rocks
    base: bare # as an alternative, a ubuntu base can be used
    build-base: ubuntu@24.04 # build-base is required when the base is bare
    version: '0.2' # just for humans. Semantic versioning is recommended
    summary: A summary of your Spring Boot app # 79 char long summary
    description: |
        This is spring-boot-hello-world's description. You have a paragraph or two to tell the
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

.. literalinclude:: code/spring-boot/task.yaml
    :language: bash
    :start-after: [docs:skopeo-update]
    :end-before: [docs:skopeo-update-end]
    :dedent: 2

Update the charm
~~~~~~~~~~~~~~~~

Change back into the charm directory using ``cd charm``.

The ``spring-boot-framework`` Charmcraft extension supports adding configurations
to ``charmcraft.yaml``, which will be passed as environment variables to
the Spring Boot app. Add the following to the end of the
``charmcraft.yaml`` file:

.. literalinclude:: code/spring-boot/greeting_charmcraft.yaml
    :caption: ~/spring-boot-hello-world/charm/charmcraft.yaml
    :language: yaml

.. note::

    When configuration options are converted to environment variables,
    their names are automatically capitalized and ``-`` are replaced
    by ``_``. An ``APP_`` prefix will also be added as a namespace
    for app configurations.

    In this tutorial, the new ``greeting`` configuration results in an
    environment variable named ``APP_GREETING``.

We can now pack and deploy the new version of the Spring Boot app:

.. literalinclude:: code/spring-boot/task.yaml
    :language: bash
    :start-after: [docs:refresh-deployment]
    :end-before: [docs:refresh-deployment-end]
    :dedent: 2

Monitor ``juju status`` until the app goes
back to ``active`` again. Verify that the new configuration
has been added:

.. code-block:: bash

    juju config spring-boot-hello-world | grep -A 6 greeting:

Check that the response is still ``Hello, world!`` using:

.. code-block:: bash

    curl http://spring-boot-hello-world --resolve spring-boot-hello-world:80:127.0.0.1``

Now let's change the greeting:

.. literalinclude:: code/spring-boot/task.yaml
    :language: bash
    :start-after: [docs:change-config]
    :end-before: [docs:change-config-end]
    :dedent: 2

Wait for the app to restart, then check the response:

.. code-block:: bash

    curl http://spring-boot-hello-world  --resolve spring-boot-hello-world:80:127.0.0.1

The response should now return the updated ``Hi!`` greeting.

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
We will use the auto DDL generation from JPA using the
property ``spring.jpa.generate-ddl``.

Return to the ``~/spring-boot-hello-world`` directory.
Add the following line to the ``src/main/resources/application.properties``
file:


.. code-block:: Properties
    :caption: ~/spring-boot-hello-world/src/main/resources/application.properties

    spring.jpa.generate-ddl=true

To connect the Spring Boot app to PostgreSQL, we need
Spring Data JPA and the ``postgresl`` driver. We also need the ``h2`` driver
for the tests to pass. Add the following snippet to the app's ``pom.xml``,
under the ``dependencies`` tag:

.. literalinclude:: code/spring-boot/pom.xml.visitors.dependencies.txt
    :caption: ~/spring-boot-hello-world/pom.xml
    :language: xml

Replace the contents of ``src/main/java/com/example/demo/HelloController.java``
with the following:

.. dropdown:: ~/spring-boot-hello-world/src/main/java/com/example/demo/\
              HelloController.java

    .. literalinclude:: code/spring-boot/HelloController.java.visitors.txt
        :language: java


Now we'll create some new classes in the ``src/main/java/com/example/demo/`` directory.
Create the class ``ApplicationConfig`` in a new
``ApplicationConfig.java`` file with the following content:

.. dropdown:: ~/spring-boot-hello-world/src/main/java/com/example/demo/\
              ApplicationConfig.java

    .. literalinclude:: code/spring-boot/ApplicationConfig.java.visitors.txt
        :language: java

Create the class ``Visitor`` in a new
``Visitor.java`` file with the following content:

.. dropdown:: ~/spring-boot-hello-world/src/main/java/com/example/demo/\
              Visitor.java

    .. literalinclude:: code/spring-boot/Visitor.java.visitors.txt
        :language: java

Create the class ``VisitorRepository`` in a new
``VisitorRepository.java`` file with the following content:

.. dropdown:: ~/spring-boot-hello-world/src/main/java/com/example/demo/\
              VisitorRepository.java

    .. literalinclude:: code/spring-boot/VisitorRepository.java.visitors.txt
        :language: java

Finally, create the class ``VisitorService`` in a new
``VisitorService.java`` file with the following content:

.. dropdown:: ~/spring-boot-hello-world/src/main/java/com/example/demo/\
              VisitorService.java

    .. literalinclude:: code/spring-boot/VisitorService.java.visitors.txt
        :language: java


Update the rock again
~~~~~~~~~~~~~~~~~~~~~

Increment the ``version`` in ``rockcraft.yaml`` to ``0.3`` such that the
top of the ``rockcraft.yaml`` file looks similar to the following:

.. code-block:: yaml
    :caption: ~/spring-boot-hello-world/rockcraft.yaml
    :emphasize-lines: 6

    name: spring-boot-hello-world
    # see https://documentation.ubuntu.com/rockcraft/en/latest/explanation/bases/
    # for more information about bases and using 'bare' bases for chiselled rocks
    base: bare # as an alternative, a ubuntu base can be used
    build-base: ubuntu@24.04 # build-base is required when the base is bare
    version: '0.3' # just for humans. Semantic versioning is recommended
    summary: A summary of your Spring Boot app # 79 char long summary
    description: |
        This is spring-boot-hello-world's description. You have a paragraph or two to tell the
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

.. literalinclude:: code/spring-boot/task.yaml
    :language: bash
    :start-after: [docs:skopeo-2nd-update]
    :end-before: [docs:skopeo-2nd-update-end]
    :dedent: 2

Update the charm again
~~~~~~~~~~~~~~~~~~~~~~

Change back into the charm directory using ``cd charm``.

The Spring Boot app now requires a database which needs to be declared in the
``charmcraft.yaml`` file. Open ``charmcraft.yaml`` in a text editor and
add the following section to the end of the file:

.. literalinclude:: code/spring-boot/visitors_charmcraft.yaml
    :caption: ~/spring-boot-hello-world/charm/charmcraft.yaml
    :language: yaml

We can now pack and deploy the new version of the Spring Boot app:

.. literalinclude:: code/spring-boot/task.yaml
    :language: bash
    :start-after: [docs:refresh-2nd-deployment]
    :end-before: [docs:refresh-2nd-deployment-end]
    :dedent: 2

Now let's deploy PostgreSQL and integrate it with the Spring Boot app:

.. literalinclude:: code/spring-boot/task.yaml
    :language: bash
    :start-after: [docs:deploy-postgres]
    :end-before: [docs:deploy-postgres-end]
    :dedent: 2

Wait for ``juju status`` to show that the App is ``active`` again.
During this time, the Spring Boot app may enter a ``blocked`` state as it
waits to become integrated with the PostgreSQL database. Due to the
``optional: false`` key in the endpoint definition, the Spring Boot app will not
start until the database is ready.

Send a request to the endpoint:

.. code-block:: bash

    curl http://spring-boot-hello-world --resolve spring-boot-hello-world:80:127.0.0.1

It should still return the ``Hi!`` greeting.

Check the local visitors:

.. code-block:: bash

    curl http://spring-boot-hello-world/visitors --resolve spring-boot-hello-world:80:127.0.0.1

This request should return ``Number of visitors 1`` after the
previous request to the root endpoint.
This should be incremented each time the root endpoint is requested. If we
repeat this process, the output should be as follows:

.. terminal::
    :input: curl http://spring-boot-hello-world --resolve spring-boot-hello-world:80:127.0.0.1

    Hi!
    :input: curl http://spring-boot-hello-world/visitors --resolve spring-boot-hello-world:80:127.0.0.1
    Number of visitors 2


Tear things down
----------------

We've reached the end of this tutorial. We went through the entire
development process, including:

- Creating a Spring Boot app
- Deploying the app locally
- Packaging the app using Rockcraft
- Building the app with Ops code using Charmcraft
- Deploying the app using Juju
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
following in the directory ``~/spring-boot-hello-world/charm`` for the tutorial:

.. literalinclude:: code/spring-boot/task.yaml
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
      - :ref:`How to manage a 12-factor app charm <manage-12-factor-app-charms>`
    * - "How do I debug?"
      - :ref:`Troubleshoot a 12-factor app charm <use-12-factor-charms-troubleshoot>`

        :external+juju:ref:`Juju | Debug a charm <debug-a-charm>`
    * - "How do I get in touch?"
      - `Matrix channel <https://matrix.to/#/#12-factor-charms:ubuntu.com>`_
    * - "What is...?"
      - :external+rockcraft:ref:`spring-boot-framework extension in Rockcraft
        <spring-boot-framework-reference>`

        :ref:`spring-boot-framework extension in Charmcraft
        <spring-boot-framework-extension>`

        :external+juju:ref:`Juju | Reference <reference>`
    * - "Why...?", "So what?"
      - :external+12-factor:ref:`12-Factor app principles and support in Charmcraft
        and Rockcraft <explanation>`
