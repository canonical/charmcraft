.. _explanation_cryptographic-technology:

Cryptographic technology in Charmcraft
======================================

Charmcraft uses cryptographic technologies to fetch arbitrary files over the internet,
communicate with local processes, and store credentials. It does not directly implement
its own cryptography, but it does depend on external libraries to do so.

Charmcraft is built on `Craft Application`_ and derives much of its functionality from
it, so much of Charmcraft's cryptographic functionality is described in `Cryptographic
technology in Craft Application`_. The additional cryptography functionality in
Charmcraft is documented below.

Local Docker images
~~~~~~~~~~~~~~~~~~~

If a Docker instance is installed or running on the host and a user references a local
Docker image in the ``upload-resource`` command, Charmcraft uses the `Docker SDK for
Python`_ to communicate with it. The SDK communicates with Docker over a
Unix-domain socket if the user running Charmcraft has the necessary permission.

Container image registries
~~~~~~~~~~~~~~~~~~~~~~~~~~

Every installation of Charmcraft comes with a bundled copy of `skopeo`_. This tool is
available to run as ``charmcraft.skopeo`` for creating local container image registries
during development. Skopeo is additionally used internally as part of the charm building
process. Charmcraft only uses the internal, pre-packaged copy of skopeo for this
purpose.

.. _Craft Application: https://canonical-craft-application.readthedocs-hosted.com/en/latest/
.. _Cryptographic technology in Craft Application: https://canonical-craft-application.readthedocs-hosted.com/en/latest/explanation/cryptography.html
.. _Docker SDK for Python: https://docker-py.readthedocs.io/en/stable/
.. _umoci: https://umo.ci/
