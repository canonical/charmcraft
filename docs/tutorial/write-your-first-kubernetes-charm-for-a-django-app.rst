.. _write-your-first-kubernetes-charm-for-a-django-app:

Write your first Kubernetes charm for a Django app
==================================================

Imagine you have a Django application backed up by a database such as
PostgreSQL and need to deploy it. In a traditional setup, this can be
quite a challenge, but with Charmcraft you’ll find yourself packaging
and deploying your Django application in no time. Let’s get started!

In this tutorial we will build a Kubernetes charm for a Django
application using Charmcraft, so we can have a Django application up and
running with Juju.

This tutorial should take 90 minutes for you to complete.

.. note::

   If you're new to the charming world: Django applications are
   specifically supported with a coordinated pair of profiles
   for an OCI container image (**rock**) and corresponding
   packaged software (**charm**) that allow for the application
   to be deployed, integrated and operated on a Kubernetes
   cluster with the Juju orchestration engine.

What you’ll need
----------------

-  A working station, e.g., a laptop, with amd64 or arm64 architecture
   which has sufficient resources to launch a virtual machine with 4
   CPUs, 4 GB RAM, and a 50 GB disk.
-  Familiarity with Linux.

What you’ll do
--------------

Create a Django application. Use that to create a rock with
``rockcraft``. Use that to create a charm with ``charmcraft``. Use that
to test, deploy, configure, etc., your Django application on a local
Kubernetes cloud, ``microk8s``, with ``juju``. All of that multiple
times, mimicking a real development process.

.. important::

    Should you get stuck or notice issues, please get in touch on
    `Matrix <https://matrix.to/#/#12-factor-charms:ubuntu.com>`_ or
    `Discourse <https://discourse.charmhub.io/>`_

Set things up
-------------

.. include:: /reuse/tutorial/setup_edge.rst
.. |12FactorApp| replace:: Django

Let’s create a new directory for this tutorial and change into it:

.. code:: bash

   mkdir django-hello-world
   cd django-hello-world

Finally, install ``python3-venv`` and create a virtual environment:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:create-venv]
    :end-before: [docs:create-venv-end]
    :dedent: 2

Create the Django application
-----------------------------

Let's start by creating the "Hello, world" Django application that
will be used for this tutorial.

Create a ``requirements.txt`` file, copy the following text into it and
then save it:

.. literalinclude:: code/django/requirements.txt

.. note::

   The ``psycopg2-binary`` package is needed so the Django application can
   connect to PostgreSQL.

Install the packages:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:install-requirements]
    :end-before: [docs:install-requirements-end]
    :dedent: 2

Create a new project using ``django-admin``:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:django-startproject]
    :end-before: [docs:django-startproject-end]
    :dedent: 2

Run the Django application locally
----------------------------------

We will test the Django application by visiting the app in a web
browser.

Change into the ``django_hello_world`` directory:

.. code:: bash

   cd django_hello_world

Open the settings file of the application located at
``django_hello_world/settings.py``. Update the ``ALLOWED_HOSTS`` setting
to allow all traffic:

.. code:: python

   ALLOWED_HOSTS = ['*']

Save and close the ``settings.py`` file.

Now, run the Django application to verify that it works:

.. code:: bash

   python3 manage.py runserver 0.0.0.0:8000

.. note::

   Specifying ``0.0.0.0:8000`` allows for traffic outside of the Multipass VM.

Now we need the private IP address of the Multipass VM. Outside of the
Multipass VM, run:

.. code-block::

   multipass info charm-dev | grep IP

.. note::

   The ``grep`` command extracts a portion of the output to highlight the
   IP address.

With the Multipass IP address, we can visit the Django app in a web
browser. Open a new tab and visit
``http://<MULTIPASS_PRIVATE_IP>:8000``, replacing
``<MULTIPASS_PRIVATE_IP>`` with your VM’s private IP address.

The Django application should respond in the browser with
``The install worked successfully! Congratulations!``.

The Django application looks good, so we can stop it for now from the
original terminal of the Multipass VM using :kbd:`Ctrl` + :kbd:`C`.

Pack the Django application into a rock
---------------------------------------

First, we’ll need a ``rockcraft.yaml`` file. Using the
``django-framework`` profile, Rockcraft will automate the creation of
``rockcraft.yaml`` and tailor the file for a Django application. Change
back into the ``django-hello-world`` directory and initialize the rock:

.. code:: bash

   cd ..
   rockcraft init --profile django-framework

The ``rockcraft.yaml`` file will automatically be created and set the
name based on your working directory, ``django-hello-world``.

Check out the contents of ``rockcraft.yaml``:

.. code:: bash

   cat rockcraft.yaml

The top of the file should look similar to the following snippet:

.. code:: yaml

   name: django-hello-world
   # see https://documentation.ubuntu.com/rockcraft/en/1.6.0/explanation/bases/
   # for more information about bases and using 'bare' bases for chiselled rocks
   base: ubuntu@22.04 # the base environment for this Django application
   version: '0.1' # just for humans. Semantic versioning is recommended
   summary: A summary of your Django application # 79 char long summary
   description: |
       This is django-hello-world's description. You have a paragraph or two to tell the
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

Verify that the ``name`` is ``django-hello-world``.

Ensure that ``platforms`` includes the architecture of your host. Check
the architecture of your system:

.. code:: bash

   dpkg --print-architecture

If your host uses the ARM architecture, open ``rockcraft.yaml`` in a
text editor and include ``arm64`` under ``platforms``.

Django applications require a database. Django will use a sqlite
database by default. This won’t work on Kubernetes because the database
would disappear every time the pod is restarted (e.g., to perform an
upgrade) and this database would not be shared by all containers as the
application is scaled. We’ll use Juju later to easily deploy a database.

We’ll need to update the ``settings.py`` file to prepare for integrating
the app with a database. From the ``django-hello-world`` directory, open
``django_hello_world/django_hello_world/settings.py`` and update the
imports to include ``json``, ``os`` and ``secrets``. The top of the
``settings.py`` file should look similar to the following snippet:

.. code-block:: python
   :emphasize-lines: 15,16,17

   """
   Django settings for django_hello_world project.

   Generated by 'django-admin startproject' using Django 5.1.4.

   For more information on this file, see
   https://docs.djangoproject.com/en/5.1/topics/settings/

   For the full list of settings and their values, see
   https://docs.djangoproject.com/en/5.1/ref/settings/
   """

   from pathlib import Path

   import json
   import os
   import secrets

Near the top of the ``settings.py`` file change the following settings
to be production ready:

.. code-block:: python
   :emphasize-lines: 2,5,7

   # SECURITY WARNING: keep the secret key used in production secret!
   SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', secrets.token_hex(32))

   # SECURITY WARNING: don't run with debug turned on in production!
   DEBUG = os.environ.get('DJANGO_DEBUG', 'false') == 'true'

   ALLOWED_HOSTS = json.loads(os.environ.get('DJANGO_ALLOWED_HOSTS', '{ref}`]'))

We will also use PostgreSQL as the database for our Django app. In
``settings.py``, go further down to the Database section and change the
``DATABASES`` variable to:

.. code-block:: python
   :emphasize-lines: 3-8

   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': os.environ.get('POSTGRESQL_DB_NAME'),
           'USER': os.environ.get('POSTGRESQL_DB_USERNAME'),
           'PASSWORD': os.environ.get('POSTGRESQL_DB_PASSWORD'),
           'HOST': os.environ.get('POSTGRESQL_DB_HOSTNAME'),
           'PORT': os.environ.get('POSTGRESQL_DB_PORT'),
       }
   }

Save and close the ``settings.py`` file.

Now let’s pack the rock:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:pack]
    :end-before: [docs:pack-end]
    :dedent: 2

.. note::

   ``ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true`` may be required
   in the pack command for older versions of Rockcraft.

Depending on your system and network, this step can take several minutes to
finish.

Once Rockcraft has finished packing the Django rock, the
terminal will respond with something similar to
``Packed django-hello-world_0.1_amd64.rock``.

.. note::

   If you are not on an ``amd64`` platform, the name of the ``.rock`` file
   will be different for you.

The rock needs to be copied to the MicroK8s registry, which stores OCI
archives so they can be downloaded and deployed in a Kubernetes cluster.
Copy the rock:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:skopeo-copy]
    :end-before: [docs:skopeo-copy-end]
    :dedent: 2

.. seealso::

   See more: `Ubuntu manpage | skopeo
   <https://manpages.ubuntu.com/manpages/jammy/man1/skopeo.1.html>`_

Create the charm
----------------

From the ``django-hello-world`` directory, create a new directory for
the charm and change inside it:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:create-charm-dir]
    :end-before: [docs:create-charm-dir-end]
    :dedent: 2

Using the ``django-framework`` profile, Charmcraft will automate the
creation of the files needed for our charm, including a
``charmcraft.yaml``, ``requirements.txt`` and source code for the charm.
The source code contains the logic required to operate the Django
application.

Initialize a charm named ``django-hello-world``:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:charm-init]
    :end-before: [docs:charm-init-end]
    :dedent: 2

The files will automatically be created in your working directory.

We will need to connect the Django application to the PostgreSQL database.
Open the ``charmcraft.yaml`` file and add the following section to the end
of the file:

.. literalinclude:: code/django/postgres_requires_charmcraft.yaml
   :language: yaml

Now let’s pack the charm:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:charm-pack]
    :end-before: [docs:charm-pack-end]
    :dedent: 2

.. note::

   ``CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true`` may be required
   in the pack command for older versions of Charmcraft.

Depending on your system and network, this step can take several
minutes to finish.

Once Charmcraft has finished packing the charm, the terminal will
respond with something similar to
``Packed django-hello-world_ubuntu-22.04-amd64.charm``.

.. note::

   If you are not on the ``amd64`` platform, the name of the ``.charm``
   file will be different for you.

Deploy the Django application
-----------------------------

A Juju model is needed to handle Kubernetes resources while deploying
the Django application. Let’s create a new model:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:add-juju-model]
    :end-before: [docs:add-juju-model-end]
    :dedent: 2

If you are not on a host with the ``amd64`` architecture, you will need
to include a constraint to the Juju model to specify your architecture.
You can check the architecture of your system using
``dpkg --print-architecture``.

Set the Juju model constraints using

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:add-model-constraints]
    :end-before: [docs:add-model-constraints-end]
    :dedent: 2

Now let’s use the OCI image we previously uploaded to deploy the Django
application. Deploy using Juju by specifying the OCI image name with the
``--resource`` option:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:deploy-django-app]
    :end-before: [docs:deploy-django-app-end]
    :dedent: 2

Now let’s deploy PostgreSQL:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:deploy-postgres]
    :end-before: [docs:deploy-postgres-end]
    :dedent: 2

Integrate PostgreSQL with the Django application:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:integrate-postgres]
    :end-before: [docs:integrate-postgres-end]
    :dedent: 2

It will take a few minutes to deploy the Django application. You can
monitor the progress using

.. code:: bash

   juju status --relations --watch 2s

The ``--relations`` flag will list the currently enabled integrations.
It can take a couple of minutes for the apps to finish the deployment.
During this time, the Django app may enter a ``blocked`` state as it
waits to become integrated with the PostgreSQL database.

Once the status of the App has gone to ``active``, you can stop watching
using :kbd:`Ctrl` + :kbd:`C`.

.. seealso::

    See more: `Command 'juju status' <https://juju.is/docs/juju/juju-status>`_

The Django application should now be running. We can see the status of
the deployment using ``juju status`` which should be similar to the
following output:

.. terminal::
    :input: juju status

   Model               Controller      Cloud/Region        Version  SLA          Timestamp
   django-hello-world  dev-controller  microk8s/localhost  3.5.3    unsupported  16:47:01+10:00

   App                 Version  Status  Scale  Charm               Channel    Rev  Address         Exposed  Message
   django-hello-world           active      1  django-hello-world               3  10.152.183.126  no
   postgresql-k8s      14.11    active      1  postgresql-k8s      14/stable  281  10.152.183.197  no

   Unit                   Workload  Agent  Address      Ports  Message
   django-hello-world/0*  active    idle   10.1.157.80
   postgresql-k8s/0*      active    idle   10.1.157.78         Primary

To be able to test the deployment, we need to include the IP address in
the allowed hosts configuration. We’ll also enable debug mode for now
whilst we are testing. Set both configurations:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:config-allowed-hosts-debug]
    :end-before: [docs:config-allowed-hosts-debug-end]
    :dedent: 2

.. note::

   Setting the Django allowed hosts to ``*`` and turning on debug mode should not
   be done in production where you should set the actual hostname of the
   application and disable debug mode. We will do this in the tutorial for now and
   later demonstrate how we can set these to production ready values.

Let’s expose the application using ingress. Deploy the
``nginx-ingress-integrator`` charm and integrate it with the Django app:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:deploy-nginx]
    :end-before: [docs:deploy-nginx-end]
    :dedent: 2

The hostname of the app needs to be defined so that it is accessible via
the ingress. We will also set the default route to be the root endpoint:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:config-nginx]
    :end-before: [docs:config-nginx-end]
    :dedent: 2

Monitor ``juju status`` until everything has a status of ``active``.

Now we will visit the Django app in a web browser. Outside of the
Multipass VM, open your machine’s ``/etc/hosts`` file in a text editor
and add a line like the following:

.. code:: bash

   <MULTIPASS_PRIVATE_IP> django-hello-world

Here, replace ``<MULTIPASS_PRIVATE_IP>`` with the same Multipass VM
private IP address you previously used.

Now you can open a new tab and visit http://django-hello-world. The
Django app should respond in the browser with
``The install worked successfully! Congratulations!``.

We can now also change the Django allowed hosts to
``django-hello-world`` which is a production ready value (for
production, you will need to set up a DNS record). Inside the Multipass
VM, set the configuration:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:config-allowed-hosts]
    :end-before: [docs:config-allowed-hosts-end]
    :dedent: 2

Visiting http://django-hello-world should still respond with
``The install worked successfully! Congratulations!``.

Add an initial app
------------------

The generated Django application does not come with an app, which is why
we had to initially enable debug mode for testing. Let’s add a greeting
app that returns a ``Hello, world!`` greeting. We will need to go back
out to the ``django-hello-world`` directory where the rock is and enter
into the ``django_hello_world`` directory where the Django application
is. Let’s add a new Django app:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:startapp-greeting]
    :end-before: [docs:startapp-greeting-end]
    :dedent: 2

Open the ``greeting/views.py`` file and replace the content with:

.. literalinclude:: code/django/views_greeting.py
   :language: python

Create the ``greeting/urls.py`` file with the following contents:

.. literalinclude:: code/django/urls_greeting.py
   :language: python

Open the ``django_hello_world/urls.py`` file and edit the imports to
contain ``include`` and the value of ``urlpatterns`` to include
``path('', include("greeting.urls")`` like in the following example:

.. code-block:: python
   :emphasize-lines: 2,5

   from django.contrib import admin
   from django.urls import include, path

   urlpatterns = [
       path("", include("greeting.urls")),
       path("admin/", admin.site.urls),
   ]

Since we’re changing the application we should update the version of the
rock. Go back to the ``django-hello-world`` directory where the rock is
and change the ``version`` in ``rockcraft.yaml`` to ``0.2``. The top of
the ``rockcraft.yaml`` file should look similar to the following:

.. code-block:: yaml
   :emphasize-lines: 5

   name: django-hello-world
   # see https://documentation.ubuntu.com/rockcraft/en/1.6.0/explanation/bases/
   # for more information about bases and using 'bare' bases for chiselled rocks
   base: ubuntu@22.04 # the base environment for this Django application
   version: '0.2' # just for humans. Semantic versioning is recommended
   summary: A summary of your Django application # 79 char long summary
   description: |
       This is django-hello-world's description. You have a paragraph or two to tell the
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

Now let’s pack and upload the rock using similar commands as before:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:repack-update]
    :end-before: [docs:repack-update-end]
    :dedent: 2

Now we can deploy the new version of the Django application from the
``charm`` directory using:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:refresh-deployment]
    :end-before: [docs:refresh-deployment-end]
    :dedent: 2

Now that we have the greeting app, we can disable debug mode:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:disable-debug-mode]
    :end-before: [docs:disable-debug-mode-end]
    :dedent: 2

Use ``juju status --watch 2s`` again to wait until the App is active
again. You may visit http://django-hello-world from a web browser, or
you can use ``curl 127.0.0.1 -H "Host: django-hello-world"`` inside the
Multipass VM. Either way, the Django application should respond with
``Hello, world!``.

.. note::

   The ``-H "Host: django-hello-world"`` option to the ``curl`` command
   is a way of setting the hostname of the request without setting a
   DNS record.

Enable a configuration
----------------------

To demonstrate how to provide a configuration to the Django application,
we will make the greeting configurable. We will expect this
configuration option to be available in the Django app configuration under the
keyword ``GREETING``. Go back out to the rock
directory ``django-hello-world`` using ``cd ..``. From there, open the
``django_hello_world/greeting/views.py`` file and replace the content
with:

.. literalinclude:: code/django/views_greeting_configuration.py
   :language: python

Increment the ``version`` in ``rockcraft.yaml`` to ``0.3`` such that the
top of the ``rockcraft.yaml`` file looks similar to the following:

.. code-block:: yaml
   :emphasize-lines: 5

   name: django-hello-world
   # see https://documentation.ubuntu.com/rockcraft/en/1.6.0/explanation/bases/
   # for more information about bases and using 'bare' bases for chiselled rocks
   base: ubuntu@22.04 # the base environment for this Django application
   version: '0.3' # just for humans. Semantic versioning is recommended
   summary: A summary of your Django application # 79 char long summary
   description: |
       This is django-hello-world's description. You have a paragraph or two to tell the
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

Let’s run the pack and upload commands for the rock:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:repack-2nd-update]
    :end-before: [docs:repack-2nd-update-end]
    :dedent: 2

Change back into the charm directory using ``cd charm``.

The ``django-framework`` Charmcraft extension supports adding
configurations in ``charmcraft.yaml`` which will be passed as
environment variables to the Django application. Add the following to
the end of the ``charmcraft.yaml`` file:

.. literalinclude:: code/django/greeting_charmcraft.yaml
   :language: yaml

.. note::

   Configuration options are automatically capitalized and ``-`` are
   replaced by ``_``. A ``DJANGO_`` prefix will also be added as a
   namespace for app configurations.

We can now pack and deploy the new version of the Django app:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:repack-refresh-2nd-deployment]
    :end-before: [docs:repack-refresh-2nd-deployment-end]
    :dedent: 2

After we wait for a bit monitoring ``juju status`` the application
should go back to ``active`` again. Sending a request to the root
endpoint using ``curl 127.0.0.1 -H "Host: django-hello-world"`` or
visiting http://django-hello-world in a web browser should result in the
Django application responding with ``Hello, world!`` again.

Now let’s change the greeting:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:change-config]
    :end-before: [docs:change-config-end]
    :dedent: 2

After we wait for a moment for the app to be restarted, using
``curl 127.0.0.1 -H "Host: django-hello-world"`` or visiting
http://django-hello-world should now respond with ``Hi!``.

Tear things down
----------------

We’ve reached the end of this tutorial. We went through the entire
development process, including:

- Creating a Django application
- Deploying the application locally
- Building an OCI image using Rockcraft
- Packaging the application using Charmcraft
- Deplyoing the application using Juju
- Integrating the application with PostgreSQL to be production ready
- Exposing the application using an ingress
- Adding an initial app and configuring the application

If you’d like to reset your working environment, you can run the
following in the rock directory ``django-hello-world`` for the tutorial:

.. literalinclude:: code/django/task.yaml
    :language: bash
    :start-after: [docs:clean-environment]
    :end-before: [docs:clean-environment-end]
    :dedent: 2

You can also clean up your Multipass instance. Start by exiting it:

.. code:: bash

   exit

And then you can proceed with its deletion:

.. code:: bash

   multipass delete charm-dev
   multipass purge

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
