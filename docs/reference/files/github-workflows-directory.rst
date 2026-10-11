.. _github-workflows-directory:


``.github/workflows`` directory
===============================

The ``.github/workflows`` directory contains GitHub Actions configuration for charms
that are hosted on GitHub. This directory is created only when the
profile is ``machine`` or ``kubernetes``. To opt out, simply delete the ``.github``
directory.


.. _github-workflows-directory-ci-yaml:

``ci.yaml``
-----------

This workflow runs linting and unit tests. It runs with the Python versions matching what is available in the Charm's base.

    See more:

    :external+ops:ref:`Ops | Tool versions <tool-versions>`


.. _github-workflows-directory-integration-yaml:

``integration.yaml``
--------------------

This workflow packs the charm and runs the integration tests.

.. _github-workflows-directory-publish-yaml:

``publish.yaml``
----------------

This workflow uploads the charm to ``latest/edge`` on Charmhub for every push to the main branch.
This workflow requires a ``publish`` environment with a ``CHARMHUB_TOKEN`` secret.
The charm must be registered, and for the ``kubernetes`` profile, the resource must
already be uploaded first.

This worfklow is meant to be a starting point, and should be updated to match the Charm's development process.

    See more:

    `GitHub | Managing environments for deployment
    <https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments>`__,
    :ref:`Manage the current Charmhub user <manage-the-current-charmhub-user>`,
    :ref:`Publish a resource on Charmhub <publish-a-resource>`


.. _github-workflows-directory-security-yaml:

``security.yaml``
-----------------

This workflow scans the charm's locked dependencies for vulnerabilities with ``pip-audit``.
Only the runtime dependencies should be audited.

    See more:

    `pip-audit <https://github.com/pypa/pip-audit>`__


.. _github-workflows-directory-dependency-review-yaml:

``dependency-review.yaml``
--------------------------

This workflow reviews the dependencies that a pull request changes. It requires Dependency graph enabled.


    See more:

    `dependency-review-action <https://github.com/actions/dependency-review-action>`__
    `GitHub | Enabling the dependency graph <https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/enable-dependency-graph>`__

.. _github-workflows-directory-zizmor-yaml:

``zizmor.yaml``
---------------

This workflow analyses other workflow files for security issues with ``zizmor``.

    See more:

    `zizmor <https://docs.zizmor.sh/>`__
