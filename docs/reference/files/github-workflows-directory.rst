.. meta::
    :description: Reference for the ``.github/workflows`` directory, which includes testing, publication, and security workflows for charms hosted on GitHub.

.. _github-workflows-directory:


``.github/workflows`` directory
===============================

The ``.github/workflows`` directory contains GitHub workflows for charms.
This directory is created in charms initialized with the ``machine`` and
``kubernetes`` profiles. To opt out, delete the ``.github`` directory.

The :external+ops:ref:`set-up-ci` guide contains practical guidance on running your
charm's tests against GitHub pull requests.

``ci.yaml``
-----------

This workflow runs linters and unit tests. It runs with the Python version that matches the charm's base.


.. _github-workflows-directory-integration-yaml:

``integration.yaml``
--------------------

This workflow packs the charm and runs the integration tests.

.. _github-workflows-directory-publish-yaml:

``publish.yaml``
----------------

This workflow uploads the charm to the latest/edge channel on Charmhub every time
there's a push to the main branch.
This workflow requires a ``publish`` `deployment environment <https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments>`__
with a ``CHARMHUB_AUTH`` secret. This secret stores the credential from :ref:`logging into Charmhub <manage-the-current-charmhub-user>`.
The charm must be :ref:`registered on Charmhub <publish-a-charm>`. For the ``kubernetes`` profile, the resource must be :ref:`published <publish-a-resource>` before this workflow runs.

This workflow is meant to be a starting point and should be updated to match the charm's development process.


.. _github-workflows-directory-security-yaml:

``security.yaml``
-----------------

This workflow checks the charm's locked dependencies for vulnerabilities with
`pip-audit <https://github.com/pypa/pip-audit>`__.
Only the runtime dependencies are audited.


.. _github-workflows-directory-dependency-review-yaml:

``dependency-review.yaml``
--------------------------

This workflow checks the dependencies that a pull request changes with the `dependency-review-action <https://github.com/actions/dependency-review-action>`__. It requires the
`dependency graph to be enabled <https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/enable-dependency-graph>`__.

.. _github-workflows-directory-zizmor-yaml:

``zizmor.yaml``
---------------

This workflow checks other workflow files for security issues with
`zizmor <https://docs.zizmor.sh/>`__.
