======================================================
How to write a Kubernetes charm for an Async Flask app
======================================================

In this how-to guide we will configure a 12-factor Flask
application to use asynchronous Gunicorn workers to be
able to serve to multiple users easily.

Make the rock async
===================

Before packing the rock make sure to put the following in ``requirements.txt``
file:

.. literalinclude:: code/flask-async/requirements.txt

Configure the async application
===============================

Now let's enable async Gunicorn workers using a configuration option. We will
expect this configuration option to be available in the Flask app configuration
under the keyword ``webserver-worker-class``. Verify that the new configuration
has been added using
``juju config flask-async-app | grep -A 6 webserver-worker-class:`` which should
show the configuration option.

The worker class can be changed using Juju:

.. literalinclude:: code/flask-async/task.yaml
    :language: bash
    :start-after: [docs:config-async]
    :end-before: [docs:config-async-end]
    :dedent: 2

Now you can run
``curl --parallel --parallel-immediate --resolve flask-async-app:80:127.0.0.1 \
http://flask-async-app/io http://flask-async-app/io http://flask-async-app/io \
http://flask-async-app/io http://flask-async-app/io``
in they will all return at the same time.

Output will be similar to following:

.. code-block:: bash

   ok
   ok
   ok
   ok
   ok

.. note::

    It might take a short time for the configuration to take effect.
