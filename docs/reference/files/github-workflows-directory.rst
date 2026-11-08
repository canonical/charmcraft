.. meta::
    :description: Reference for the ``.github/workflows`` directory, which includes testing, publication, and security workflows for charms hosted on GitHub.

.. _github-workflows-directory:


``.github/workflows`` directory
===============================

The ``.github/workflows`` directory contains GitHub workflows for charms.
This directory is created by the ``github-ci`` profile. To add it to a charm
initialized with the ``machine`` or ``kubernetes`` profile, run
``charmcraft init --profile github-ci`` in the charm's project directory.

The :external+ops:ref:`set-up-ci` guide contains practical guidance on running your
charm's tests against GitHub pull requests.

The workflows assume a ``ci`` dependency group in ``pyproject.toml`` with the required
tools. If your charm doesn't have the group, add it with:

.. code-block:: bash

    uv add --group ci "pip-audit>=2.10,<3" "tox>=4.64,<5" "tox-uv>=1.36,<2" "zizmor>=1.30,<2"

You can raise each lower bound to the latest minor version of the tool.


.. _github-workflows-directory-ci-yaml:

``ci.yaml``
-----------

This workflow runs linters and unit tests. If they pass, it calls the
:ref:`integration.yaml <github-workflows-directory-integration-yaml>`
workflow. On a push to the main branch, it also calls the
:ref:`publish.yaml <github-workflows-directory-publish-yaml>`
workflow if the integration tests pass.

The integration workflow takes a `concierge preset <https://canonical.com/juju/docs/concierge/reference/presets/>`_
input: ``k8s`` for a Kubernetes charm, ``machine`` for a machine charm. By default,
``ci.yaml`` passes the ``k8s`` preset. For a machine charm, change the
``concierge-preset`` value in ``ci.yaml`` to ``machine``.

The ``UV_PYTHON`` environment variable of this workflow sets the Python
version for running linters and unit tests. It should match the Python version of
the charm's base.


.. _github-workflows-directory-integration-yaml:

``integration.yaml``
--------------------

This workflow packs the charm and runs the integration tests. It prepares the
matching environment with `concierge <https://canonical.com/juju/docs/concierge/reference/presets/>`_,
based on the ``concierge-preset`` input : ``k8s`` for a
Kubernetes charm, ``machine`` for a machine charm.

.. _github-workflows-directory-publish-yaml:

``publish.yaml``
----------------

This workflow uploads the charm to the latest/edge channel on Charmhub every time
there's a push to the main branch.

This workflow requires a ``publish`` `deployment environment <https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments>`__
with a ``CHARMHUB_TOKEN`` secret. This secret stores the credential from :ref:`logging in to Charmhub <manage-the-current-charmhub-user>`.
The charm must be :ref:`registered on Charmhub <publish-a-charm>`.

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
