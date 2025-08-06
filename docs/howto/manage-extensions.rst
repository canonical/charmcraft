.. _manage-extensions:

Manage extensions
=================

   See also: :ref:`extensions`

View all the available extensions
---------------------------------

To view all the available Rockcraft / Charmcraft extensions, run the
``rockcraft list-extensions`` / ``charmcraft list-extensions`` command. For example:

.. code-block:: bash

   $ charmcraft list-extensions
   Extension name    Supported bases    Experimental bases
   ----------------  -----------------  --------------------
   flask-framework                      ubuntu@22.04

..

   See more: :external+rockcraft:ref:`Rockcraft | rockcraft list-extensions
   <ref_commands_list-extensions>`, :ref:`ref_commands_list-extensions`

View details about the extension in use
---------------------------------------

Suppose you've initialised a rock / charm with a profile that comes with
an extension (currently, ``flask-framework``), and your
``rockcraft.yaml`` / ``charmcraft.yaml > extensions`` lists this
extension.

.. collapse:: Example

   .. code-block:: bash

      mkdir my-flask-app-k8s
      cd my-flask-app-k8s/
      charmcraft init --profile flask-framework

  .. terminal::

      Charmed operator package file and directory tree initialised.

      Now edit the following package files to provide fundamental charm metadata
      and other information:

      charmcraft.yaml
      src/charm.py
      README.md

  .. code-block:: bash

      ls -R

  .. terminal::

      .:
      charmcraft.yaml  requirements.txt  src

      ./src:
      charm.py

  .. code-block:: bash

      cat charmcraft.yaml

  .. code-block:: yaml

      name: my-flask-app-k8s

      type: charm

      bases:
        - build-on:
          - name: ubuntu
            channel: "22.04"
          run-on:
          - name: ubuntu
            channel: "22.04"

      # (Required)
      summary: A very short one-line summary of the flask application.

      # (Required)
      description: |
        A comprehensive overview of your Flask application.

      extensions:
        - flask-framework

      # Uncomment the integrations used by your application
      # requires:
      #   mysql:
      #     interface: mysql_client
      #     limit: 1
      #   postgresql:
      #     interface: postgresql_client
      #     limit: 1

To view details about what that extension is adding to your charm, set the
``CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS`` environment variable to ``1``,
then run  ``charmcraft expand-extensions``. For example:

.. collapse:: Expanding an extension

   .. code-block:: bash

      CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=1 charmcraft expand-extensions

  .. terminal::

      *EXPERIMENTAL* extension 'flask-framework' enabled
      name: my-flask-app-k8s
      summary: A very short one-line summary of the flask application.
      description: |
        A comprehensive overview of your Flask application.
      parts:
        charm:
          source: .
          charm-entrypoint: src/charm.py
          charm-binary-python-packages: []
          charm-python-packages: []
          charm-requirements:
          - requirements.txt
          charm-strict-dependencies: false
          plugin: charm
      type: charm
      bases:
      - build-on:
        - name: ubuntu
          channel: '22.04'
        run-on:
        - name: ubuntu
          channel: '22.04'
      actions:
        rotate-secret-key:
          description: Rotate the flask secret key. Users will be forced to log in again.
            This might be useful if a security breach occurs.
      assumes:
      - k8s-api
      containers:
        flask-app:
          resource: flask-app-image
      peers:
        secret-storage:
          interface: secret-storage
      provides:
        metrics-endpoint:
          interface: prometheus_scrape
        grafana-dashboard:
          interface: grafana_dashboard
      requires:
        logging:
          interface: loki_push_api
        ingress:
          interface: ingress
          limit: 1
      resources:
        flask-app-image:
          type: oci-image
          description: flask application image.
      config:
        options:
          webserver-keepalive:
            type: int
            description: Time in seconds for webserver to wait for requests on a Keep-Alive
              connection.
          webserver-threads:
            type: int
            description: Run each webserver worker with the specified number of threads.
          webserver-timeout:
            type: int
            description: Time in seconds to kill and restart silent webserver workers.
          webserver-workers:
            type: int
            description: The number of webserver worker processes for handling requests.
          flask-application-root:
            type: string
            description: Path in which the application / web server is mounted. This configuration
              will set the FLASK_APPLICATION_ROOT environment variable. Run app.config.from_prefixed_env()
              in your Flask application in order to receive this configuration.
          flask-debug:
            type: boolean
            description: Whether Flask debug mode is enabled.
          flask-env:
            type: string
            description: What environment the Flask app is running in, by default it's 'production'.
          flask-permanent-session-lifetime:
            type: int
            description: Time in seconds for the cookie to expire in the Flask application
              permanent sessions. This configuration will set the FLASK_PERMANENT_SESSION_LIFETIME
              environment variable. Run app.config.from_prefixed_env() in your Flask application
              in order to receive this configuration.
          flask-preferred-url-scheme:
            type: string
            default: HTTPS
            description: Scheme for generating external URLs when not in a request context
              in the Flask application. By default, it's "HTTPS". This configuration will
              set the FLASK_PREFERRED_URL_SCHEME environment variable. Run app.config.from_prefixed_env()
              in your Flask application in order to receive this configuration.
          flask-secret-key:
            type: string
            description: The secret key used for securely signing the session cookie and
              for any other security related needs by your Flask application. This configuration
              will set the FLASK_SECRET_KEY environment variable. Run app.config.from_prefixed_env()
              in your Flask application in order to receive this configuration.
          flask-session-cookie-secure:
            type: boolean
            description: Set the secure attribute in the Flask application cookies. This
              configuration will set the FLASK_SESSION_COOKIE_SECURE environment variable.
              Run app.config.from_prefixed_env() in your Flask application in order to
              receive this configuration.

..

   See more: :external+rockcraft:ref:`Rockcraft | rockcraft expand-extensions
   <ref_commands_expand-extensions>`, :ref:`ref_commands_expand-extensions`
