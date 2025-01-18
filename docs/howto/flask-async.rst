.. _write-a-kubernetes-charm-for-an-async-flask-app:

How to write a Kubernetes charm for an async Flask app
======================================================

In this how-to guide you will configure a 12-factor Flask
application to use asynchronous Gunicorn workers to be
able to serve to multiple users easily.

Make the rock async
-------------------

To make the rock async, make sure to put the following in its ``requirements.txt``
file:

.. literalinclude:: code/flask-async/requirements.txt

Pack the rock using ``rockcraft pack`` and redeploy the charm with the new rock using
:external+juju:ref:`command-juju-refresh`.

Configure the async application
-------------------------------

Now let's enable async Gunicorn workers. We will
expect this configuration option to be available in the Flask app configuration
under the ``webserver-worker-class`` key. Verify that the new configuration
has been added by running:

.. code:: bash

  juju config flask-async-app | grep -A 6 webserver-worker-class:

The result should contain the key.

The worker class can be changed using Juju:

.. literalinclude:: code/flask-async/task.yaml
    :language: bash
    :start-after: [docs:config-async]
    :end-before: [docs:config-async-end]
    :dedent: 2

Test that the workers are operating in parallel by sending multiple
simultaneous requests with curl:

.. code:: bash

  curl --parallel --parallel-immediate --resolve flask-async-app:80:127.0.0.1 \
  http://flask-async-app/io http://flask-async-app/io http://flask-async-app/io \
  http://flask-async-app/io http://flask-async-app/io

and they will all return at the same time.

The results should arrive simultaneously and contain five instances of ``ok``:

.. terminal::

   ok
   ok
   ok
   ok
   ok

It can take up to a minute for the configuration to take effect. When the
configuration changes, the charm will re-enter the active state.
