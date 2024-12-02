====================================================
Write your a Kubernetes charm for an Async Flask app
====================================================

Imagine you have a Flask application that has endpoints
run for quite some time and need to deploy it. In a traditional setup,
this can be quite a challenge, but with Juju you’ll find yourself
deploying, configuring, scaling, integrating, monitoring, etc.,
your Flask application in no time. Let’s get started!

In this tutorial we will build a rock and Kubernetes charm for a
Flask application using the charm SDK, so we can have a Flask
application up and running with Juju in about 90 minutes. We will
also configure this application to use asynchronous Gunicorn workers
to be able to serve to multiple users easily.

.. note::

    **rock**: An Ubuntu LTS-based OCI compatible
    container image designed to meet security, stability, and
    reliability requirements for cloud-native software.

    **charm**: A package consisting of YAML files + Python code that will
    automate every aspect of an application's lifecycle so it can
    be easily orchestrated with Juju.

    **Juju**: An orchestration engine for software
    operators that enables the deployment, integration and lifecycle
    management of applications using charms.

**What you’ll need:**

- A workstation, e.g., a laptop, with amd64 or arm64 architecture which
  has sufficient resources to launch a virtual machine with 4 CPUs,
  4 GB RAM, and a 50 GB disk
- Familiarity with Linux

**What you’ll do:**

- Set things up
- Create the Flask application
- Run the Flask application locally
- Pack the Flask application into a rock
- Create the charm
- Deploy the Flask application and expose via ingress
- Enable ``juju config flask-async-app webserver-worker-class=gevent``
- Clean up environment

.. hint::

    Don't hesitate to get in touch on
    `Matrix <https://matrix.to/#/#12-factor-charms:ubuntu.com>`_ or
    `Discourse <https://discourse.charmhub.io/>`_ (or follow the
    "Edit this page on GitHub" on the bottom of
    this document to comment directly on the document).


Set things up
=============

.. include:: /reuse/tutorial/setup.rst

Finally, create a new directory for this tutorial and go inside it:

.. code-block:: bash

    mkdir flask-async-app
    cd flask-async-app

Create the Flask application
============================

Start by creating the "Hello, world" Flask application that will be
used for this tutorial.

Create a ``requirements.txt`` file, copy the following text into it
and then save it:

.. literalinclude:: code/flask-async/requirements.txt

In the same directory, copy and save the following into a text file
called ``app.py``:

.. literalinclude:: code/flask-async/app.py
    :language: python

Run the Flask application locally
=================================

Install ``python3-venv`` and create a virtual environment:

.. literalinclude:: code/flask-async/task.yaml
    :language: bash
    :start-after: [docs:create-venv]
    :end-before: [docs:create-venv-end]
    :dedent: 2

Now that we have a virtual environment with all the dependencies, let's
run the Flask application to verify that it works:

.. code-block:: bash

    flask run -p 8000

Test the Flask application by using ``curl`` to send a request to the root
endpoint. You may need a new terminal for this; if you are using Multipass
use ``multipass shell charm-dev`` to get another terminal:

.. literalinclude:: code/flask-async/task.yaml
    :language: bash
    :start-after: [docs:curl-flask]
    :end-before: [docs:curl-flask-end]
    :dedent: 2

The Flask application should respond with ``Hello, world!``.

Test the long running endpoint by sending a request to ``/io``:

.. literalinclude:: code/flask-async/task.yaml
    :language: bash
    :start-after: [docs:curl-flask-async]
    :end-before: [docs:curl-flask-async-end]
    :dedent: 2

The Flask application looks good, so we can stop for now using
:kbd:`Ctrl` + :kbd:`C`.

Pack the Flask application into a rock
======================================

First, we'll need a ``rockcraft.yaml`` file. Rockcraft will automate its
creation and tailoring for a Flask application by using the
``flask-framework`` profile:

.. literalinclude:: code/flask-async/task.yaml
    :language: bash
    :start-after: [docs:create-rockcraft-yaml]
    :end-before: [docs:create-rockcraft-yaml-end]
    :dedent: 2

The ``rockcraft.yaml`` file will automatically be created and set the name
based on your working directory. Open the file in a text editor and check
that the ``name`` is ``flask-async-app``. Ensure that ``platforms``
includes the architecture of your host. For example, if your host uses the
ARM architecture, include ``arm64`` in ``platforms``. Make sure to uncomment
the ``parts:`` line and the following lines to enable async workers:

.. code-block::
    flask-framework/async-dependencies:
      python-packages:
      - gunicorn[gevent]

.. note::

    For this tutorial, we'll use the ``name`` "flask-async-app" and assume
    you are on the ``amd64`` platform. Check the architecture of your system
    using ``dpkg --print-architecture``. Choosing a different name or
    running on a different platform will influence the names of the files
    generated by Rockcraft.

Pack the rock:

.. literalinclude:: code/flask-async/task.yaml
    :language: bash
    :start-after: [docs:pack]
    :end-before: [docs:pack-end]
    :dedent: 2

.. note::

    Depending on your system and network, this step can take a couple of
    minutes to finish.

Once Rockcraft has finished packing the Flask rock, you'll find a new file
in your working directory with the ``.rock`` extension:

.. literalinclude:: code/flask-async/task.yaml
    :language: bash
    :start-after: [docs:ls-rock]
    :end-before: [docs:ls-rock-end]
    :dedent: 2

.. note::

    If you changed the ``name`` or ``version`` in ``rockcraft.yaml`` or are
    not on an ``amd64`` platform, the name of the ``.rock`` file will be
    different for you.

The rock needs to be copied to the MicroK8s registry so that it can be
deployed in the Kubernetes cluster:

.. literalinclude:: code/flask-async/task.yaml
    :language: bash
    :start-after: [docs:skopeo-copy]
    :end-before: [docs:skopeo-copy-end]
    :dedent: 2

.. seealso::

    See more: `skopeo <https://manpages.ubuntu.com/manpages/jammy/man1/skopeo.1.html>`_

Create the charm
================

Create a new directory for the charm and go inside it:

.. literalinclude:: code/flask-async/task.yaml
    :language: bash
    :start-after: [docs:create-charm-dir]
    :end-before: [docs:create-charm-dir-end]
    :dedent: 2

We'll need a ``charmcraft.yaml``, ``requirements.txt`` and source code for
the charm. The source code contains the logic required to operate the Flask
application. Charmcraft will automate the creation of these files by using
the ``flask-framework`` profile:

.. literalinclude:: code/flask-async/task.yaml
    :language: bash
    :start-after: [docs:charm-init]
    :end-before: [docs:charm-init-end]
    :dedent: 2

The files will automatically be created in your working directory.
Pack the charm:

.. literalinclude:: code/flask-async/task.yaml
    :language: bash
    :start-after: [docs:charm-pack]
    :end-before: [docs:charm-pack-end]
    :dedent: 2

.. note::

    Depending on your system and network, this step can take a couple
    of minutes to finish.

Once Charmcraft has finished packing the charm, you'll find a new file in your
working directory with the ``.charm`` extension:

.. literalinclude:: code/flask-async/task.yaml
    :language: bash
    :start-after: [docs:ls-charm]
    :end-before: [docs:ls-charm-end]
    :dedent: 2

.. note::

    If you changed the name in charmcraft.yaml or are not on the amd64 platform,
    the name of the ``.charm`` file will be different for you.

Deploy the Flask application
============================

A Juju model is needed to deploy the application. Let's create a new model:

.. literalinclude:: code/flask-async/task.yaml
    :language: bash
    :start-after: [docs:add-juju-model]
    :end-before: [docs:add-juju-model-end]
    :dedent: 2

.. warning::

    If you are not on a host with the amd64 architecture, you will need to include
    a constraint to the Juju model to specify your architecture. For example, for
    the arm64 architecture, use
    ``juju set-model-constraints -m flask-async-app arch=arm64``.
    Check the architecture of your system using ``dpkg --print-architecture``.

Now the Flask application can be deployed using `Juju <https://juju.is/docs/juju>`_:

.. literalinclude:: code/flask-async/task.yaml
    :language: bash
    :start-after: [docs:deploy-juju-model]
    :end-before: [docs:deploy-juju-model-end]
    :dedent: 2

.. note::

    It will take a few minutes to deploy the Flask application. You can monitor the
    progress using ``juju status --watch 5s``. Once the status of the App has gone
    to ``active``, you can stop watching using :kbd:`Ctrl` + :kbd:`C`.

    See more: `Command 'juju status' <https://juju.is/docs/juju/juju-status>`_

The Flask application should now be running. We can monitor the status of the deployment
using ``juju status`` which should be similar to the following output:

.. code-block::

    Model              Controller      Cloud/Region        Version  SLA          Timestamp
    flask-async-app  dev-controller  microk8s/localhost  3.1.8    unsupported  17:04:11+10:00

    App           Version  Status  Scale  Charm              Channel  Rev  Address         Exposed  Message
    flask-async-app      active      1  flask-async-app             0  10.152.183.166  no

    Unit             Workload  Agent  Address      Ports  Message
    flask-async-app/0*  active    idle   10.1.87.213

The deployment is finished when the status shows ``active``. Let's expose the
application using ingress. Deploy the ``nginx-ingress-integrator`` charm and integrate
it with the Flask app:

.. literalinclude:: code/flask-async/task.yaml
    :language: bash
    :start-after: [docs:deploy-nginx]
    :end-before: [docs:deploy-nginx-end]
    :dedent: 2

The hostname of the app needs to be defined so that it is accessible via the ingress.
We will also set the default route to be the root endpoint:

.. literalinclude:: code/flask-async/task.yaml
    :language: bash
    :start-after: [docs:config-nginx]
    :end-before: [docs:config-nginx-end]
    :dedent: 2

Monitor ``juju status`` until everything has a status of ``active``. Test the
deployment using
``curl http://flask-async-app --resolve flask-async-app:80:127.0.0.1`` to send
a request via the ingress to the root endpoint. It should still be returning
the ``Hello, world!`` greeting.

.. note::

    The ``--resolve flask-async-app:80:127.0.0.1`` option to the ``curl``
    command is a way of resolving the hostname of the request without
    setting a DNS record.

Configure the Flask application
===============================

Now let's enable async Gunicorn workers using a configuration option. We will
expect this configuration option to be available in the Flask app configuration under the
keyword ``webserver-worker-class``. Verify that
the new configuration has been added using
``juju config flask-async-app | grep -A 6 webserver-worker-class:`` which should show
the configuration option.

.. note::

    The ``grep`` command extracts a portion of the configuration to make
    it easier to check whether the configuration option has been added.

The worker class can be changed using Juju:

.. literalinclude:: code/flask-async/task.yaml
    :language: bash
    :start-after: [docs:config-async]
    :end-before: [docs:config-async-end]
    :dedent: 2

Now you can run
``curl --parallel --parallel-immediate --resolve flask-async-app:80:127.0.0.1 \
http://flask-async-app/io http://flask-async-app/io http://flask-async-app/io \
http://flask-async-app/io http://flask-async-app/io ``
in they will all return at the same time.

.. note::

    It might take a short time for the configuration to take effect.

Clean up environment
====================

We've reached the end of this tutorial. We have created a Flask application,
deployed it locally, exposed it via ingress and integrated it with a database!

If you'd like to reset your working environment, you can run the following
in the root directory for the tutorial:

.. literalinclude:: code/flask-async/task.yaml
    :language: bash
    :start-after: [docs:clean-environment]
    :end-before: [docs:clean-environment-end]
    :dedent: 2

If you created an instance using Multipass, you can also clean it up.
Start by exiting it:

.. code-block:: bash

    exit

And then you can proceed with its deletion:

.. code-block:: bash

    multipass delete charm-dev
    multipass purge

Next steps
==========

.. list-table::
    :widths: 30 30
    :header-rows: 1

    * - If you are wondering...
      - Visit...
    * - "How do I...?"
      - `SDK How-to docs <https://juju.is/docs/sdk/how-to>`_
    * - "How do I debug?"
      - `Charm debugging tools <https://juju.is/docs/sdk/debug-a-charm>`_
    * - "What is...?"
      - `SDK Reference docs <https://juju.is/docs/sdk/reference>`_
    * - "Why...?", "So what?"
      - `SDK Explanation docs <https://juju.is/docs/sdk/explanation>`_

-------------------------
