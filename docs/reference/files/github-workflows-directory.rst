.. meta::
    :description: Reference for the ``.github/workflows`` directory, which includes testing, publication, and security workflows for charms hosted on GitHub.

.. _github-workflows-directory:


``.github/workflows`` directory
===============================

The ``.github/workflows`` directory contains GitHub workflows for charms initialized
with the ``github-ci`` profile. This directory can be added to new and existing charms
by running:

.. code-block:: bash

    charmcraft init --profile github-ci

The :external+ops:ref:`set-up-ci` guide contains practical guidance on running your
charm's tests against GitHub pull requests.

The workflows assume that your project's :ref:`pyproject-toml-file` lists the required
tools in a ``ci`` dependency group.

.. _github-workflows-directory-ci-yaml:

``ci.yaml``
-----------

This workflow runs linters and unit tests. If they pass, it calls the
:ref:`integration.yaml <github-workflows-directory-integration-yaml>`
workflow. On a push to the main branch, it also calls the
:ref:`publish.yaml <github-workflows-directory-publish-yaml>`
workflow if the integration tests pass.

The integration workflow takes a :external+concierge:ref:`Concierge preset
<reference-presets>` input, which defaults to ``k8s``. For machine charms, the
``concierge-preset`` value must be changed to ``machine``.

The ``UV_PYTHON`` environment variable sets the workflow's Python interpreter version.
It should match the Python version used by the charm's base.


.. _github-workflows-directory-integration-yaml:

``integration.yaml``
--------------------

This workflow packs the charm and runs its integration tests. It prepares the matching
environment based on the ``concierge-preset`` input, which should be set to ``k8s`` for
Kubernetes charms and ``machine`` for machine charms.

.. _github-workflows-directory-publish-yaml:

``publish.yaml``
----------------

This workflow uploads the charm to the latest/edge channel on Charmhub every time
there's a push to the main branch.

This workflow requires a ``publish`` `deployment environment
<https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments>`__
with a ``CHARMHUB_TOKEN`` secret containing :ref:`exported Charmhub user credentials
<login-remote-environments>`. The charm must also be :ref:`registered on Charmhub
<publish-a-charm>`.

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
