.. _manage-charms:

Manage charms
=============

    See first: :external+juju:ref:`Juju | Charm <charm>`,
    :external+juju:ref:`Juju | Manage charms <manage-charms>`

.. _initialise-a-charm:

Initialise a charm
------------------

.. admonition:: Best practice
    :class: hint

    If you're setting up a ``git`` repository: name it using the pattern
    ``<charm name>-operator``. For the charm name, see :ref:`specify-a-name`.

To initialise a charm project, create a directory for your charm, enter it, then run
``charmcraft init`` with the ``--profile`` flag followed by a suitable profile name (for
machine charms: ``machine``; for Kubernetes charms: ``kubernetes`` or
``flask-framework``); that will create all the necessary files and even prepopulate them
with useful content.

.. code-block:: bash

    charmcraft init --profile <profile>

.. collapse:: Example session

    .. code-block:: bash

        mkdir my-flask-app-k8s
        cd my-flask-app-k8s/
        charmcraft init --profile flask-framework

    .. terminal::

        Charmed operator package file and directory tree initialised
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

The command also allows you to not specify any profile (in that case you get the
``kubernetes`` profile -- a minimal profile with scaffolding for a Kubernetes charm)
and has flags that you can use to specify a different directory to operate
in, a charm name different from the name of the root directory, etc.

    See more: :ref:`ref_commands_revisions`, :ref:`profile`, :ref:`files`

    See more: :ref:`manage-extensions`

.. _add-charm-project-metadata-an-icon-docs:

Add charm project metadata, an icon, docs
-----------------------------------------


Specify that the project is a charm
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To specify that the project is a charm, set the ``type`` key to ``charm`` in
your project file:

.. code-block:: yaml

    type: charm

..

    See more: :ref:`charmcraft-yaml-key-type`

.. _specify-a-name:

Specify a name
~~~~~~~~~~~~~~

To specify a pack-and-deploy name for your charm, in your charm's project file, specify
the ``name`` key. E.g.,

.. code-block:: yaml

    name: traefik-k8s

..

    See more: :ref:`charmcraft-yaml-key-name`


Specify a title
~~~~~~~~~~~~~~~

To specify a title for your charm's page on Charmhub, in your charm's project file,
specify a value for the ``title`` key. E.g.,

.. code-block:: yaml

    title: |
      Traefik Ingress Operator for Kubernetes

..

    See more: :ref:`charmcraft-yaml-key-title`


Add a summary
~~~~~~~~~~~~~

To add a summary line for your charm, in your charm's project file, specify a
value for the ``summary`` key. E.g.,

.. code-block:: yaml

    summary: |
      A Juju charm to run a Traefik-powered ingress controller on Kubernetes.

..

    See more: :ref:`charmcraft-yaml-key-summary`


Add a description
~~~~~~~~~~~~~~~~~

To add a longer description for your charm, in your charm's project
file, specify a value for the ``description`` key. E.g.,

.. code-block:: yaml

    description: |
      A Juju-operated Traefik operator that routes requests from the outside of a
      Kubernetes cluster to Juju units and applications.

..


    See more: :ref:`charmcraft-yaml-key-description`


Add contact information
~~~~~~~~~~~~~~~~~~~~~~~

To add maintainer contact information for a charm, in your charm's project
file, specify a value for the :ref:`links.contact <charmcraft-yaml-key-links-contact>`
key. E.g.,

.. code-block:: yaml

    links:
      contact: Please send your answer to Old Pink, care of the Funny Farm, Chalfont

..

    See more: :ref:`charmcraft-yaml-key-contact`


Add a link to source code
~~~~~~~~~~~~~~~~~~~~~~~~~

To add a link to the source code for a charm, in your charm's project
file, specify an item under the :ref:`links.source <charmcraft-yaml-key-links-source>`
key. E.g.,

.. code-block:: yaml

    links:
      source:
      - https://github.com/canonical/traefik-k8s-operator

..

    See more: :ref:`charmcraft-yaml-key-links`


Add a link to the bug tracker
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To add a link to the bug tracker for a charm, in your charm's project
file, specify an item under the :ref:`links.issues <charmcraft-yaml-key-links-website>`
key. E.g.,

.. code-block:: yaml

    links:
      issues:
        - https://github.com/canonical/traefik-k8s-operator/issues

..

    See more: :ref:`charmcraft-yaml-key-links`


Add a link to the website
~~~~~~~~~~~~~~~~~~~~~~~~~

If your charm has a website outside of Charmhub, to add a link to this website, in your
charm's project file, specify an item under the :ref:`links.website
<charmcraft-yaml-key-links-website>` key. E.g.,

.. code-block:: yaml

    links:
      website:
      - https://charmed-kubeflow.io/

..

    See more: :ref:`charmcraft-yaml-key-links`

.. _add-docs:

Add docs
~~~~~~~~

If you publish your charm on Charmhub, reference documentation about the charm's
resources, actions, configurations, relations, and libraries is generated and
published automatically in respective tabs.

To add content to the **Description** tab,
create a `Discourse <https://discourse.charmhub.io/>`_ topic and include its URL
in your charm's project file under the
:ref:`links.documentation <charmcraft-yaml-key-documentation>` key:

.. code-block:: yaml

    links:
      documentation: https://discourse.charmhub.io/t/traefik-k8s-docs-index/10778

..

    See more: :ref:`charmcraft-yaml-key-links`

The **Description** tab can contain additional documentation, such as tutorials or
how-to guides.

.. note::
   A charm's documentation should focus on the charm itself.
   For workload-specific or Juju-related content, link to the appropriate upstream
   documentation.

A smaller charm can have single-page documentation for its description.
A bigger charm, that needs multi-page documentation, can have either
a brief description with a link to an external documentation set, or
a full `Diátaxis <https://diataxis.fr/>`_ navigation tree in the **Description** tab.

.. admonition:: Best practice
    :class: hint

    Smaller charm documentation examples:

    * `Azure storage integrator <https://charmhub.io/azure-storage-integrator>`_ charm
    * `Repo policy compliance <https://charmhub.io/repo-policy-compliance>`_ charm

.. admonition:: Best practice
    :class: hint

    Bigger charm documentation examples:

    * `OpenSearch <https://charmhub.io/opensearch>`_ charm
    * `Wordpress-k8s <https://charmhub.io/wordpress-k8s>`_ charm

Add terms of use
~~~~~~~~~~~~~~~~

To add terms of use for your charm, in your charm's project file, specify a
value for the ``terms`` key. E.g.,

.. code-block:: yaml

    terms:
      - Butterscotch is regal
      - Cara is adorable

..

    See more: :ref:`charmcraft-yaml-key-terms`


Add an icon
~~~~~~~~~~~

    See more: :ref:`manage-icons`


.. _add-runtime-details-to-a-charm:

Add runtime details to a charm
------------------------------


Require a specific Juju version
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To require a specific Juju version for your charm, in your charm's project file,
specify the ``assumes`` key. E.g.,

.. code-block:: yaml

    assumes:
      - juju >= 3.5

..

    See more: :ref:`charmcraft-yaml-key-assumes`


Require a Kubernetes cloud
~~~~~~~~~~~~~~~~~~~~~~~~~~

To require a Kubernetes cloud for your charm, in your charm's
project file, specify the ``assumes`` key. E.g.,

.. code-block:: yaml

    assumes:
      - k8s-api

..


  See more: :ref:`charmcraft-yaml-key-assumes`

Require a specific base and platforms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To require a specific base and platforms for your charm, in your charm's
project file, specify the ``base``, and ``platforms`` keys. E.g.,

.. note::
    In Charmcraft < 3.0 this was done via a single key: ``bases``.

.. code-block:: yaml

    # The run time base, the base format is <os-name>@<os-release>,
    # accepted bases are:
    # - ubuntu@24.04
    base: <base>
    # The build time base, if not defined the base is also the build time
    # base, in addition to valid bases, the build-base can be "devel"
    # which would use the latest in development Ubuntu Series.
    build-base: <base>

    platforms:
      # The supported platforms, may omit build-for if platform-name
      # is a valid arch, valid architectures follow the Debian architecture names,
      # accepted architectures are:
      # - amd64
      # - arm64
      # - armhf
      # - ppc64el
      # - riscv64
      # - s390x
      <platform-name>:
        # The build time architecture
        build-on: <list-of-arch> | <arch>
        # The run time architecture
        build-for: <list-of-arch> | <arch>

..

    See more: :ref:`charmcraft-yaml-key-base`, :ref:`charmcraft-yaml-key-build-base`


Specify container requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To specify container requirements, in your charm's project file, specify the
``containers`` key.

    See more: :ref:`charmcraft-yaml-key-containers`


Specify associated resources
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To specify the resources associated with the charm, in your charm's project
file, specify the ``resources`` key.

    See :ref:`manage-resources`.


Specify device requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~~

To specify device requirements, in your charm's project file, specify the
``devices`` key.

    See more: :ref:`charmcraft-yaml-key-devices`

.. _manage-storage:

Manage storage
~~~~~~~~~~~~~~

To specify storage requirements, in your charm's project file, specify
the ``storage`` key.

    See more: :ref:`charmcraft-yaml-key-storage`


Specify extra binding requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To specify extra binding requirements, in your charm's project file,
specify the ``extra-bindings`` key.

    See more: :ref:`charmcraft-yaml-key-extra-bindings`


Require subordinate deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To require subordinate deployment for your charm (i.e., for it to be deployed to the
same machine as another charm, called its *principal*), in your charm's
project file, specify the ``subordinate`` key.

    See more: :ref:`charmcraft-yaml-key-subordinate`

.. _manage-actions:

Manage actions
~~~~~~~~~~~~~~

    See first: :external+juju:ref:`Juju | Action <action>`,
    :external+juju:ref:`Juju | Manage actions <manage-actions>`

To declare an action in your charm, in your charm's project file,
specify the ``actions`` key.

    See more: :ref:`charmcraft-yaml-key-actions`

    See next: :external+ops:ref:`Ops | Manage actions <manage-actions>`

.. _manage-the-app-configuration:

Manage the app configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    See first: :external+juju:ref:`Juju | Configuration > Application configuration
    <application-configuration>`,
    :external+juju:ref:`Juju | Manage applications > Configure
    <configure-an-application>`

To declare a configuration option for your charm, in your charm's project file,
specify the ``config`` key.


    See more: :ref:`charmcraft-yaml-key-config`

    See next: :external+ops:ref:`Ops | Manage configuration <manage-configuration>`

.. _manage-relations:

Manage relations
~~~~~~~~~~~~~~~~

    See first: :external+juju:ref:`Juju | Relation <relation>`,
    :external+juju:ref:`Juju | Manage relations <manage-relations>`

    To declare a relation endpoint in your charm, in your charm's project file,
    specify the ``peers``, ``provides``, or ``requires`` key.

    See more: :ref:`charmcraft-yaml-key-peers`

    See more: :external+ops:ref:`Ops | Manage relations <manage-relations>`


Specify necessary libs
~~~~~~~~~~~~~~~~~~~~~~

    See more: :ref:`manage-libraries`

.. _manage-secrets:

Manage secrets
~~~~~~~~~~~~~~

    See first: :external+juju:ref:`Juju | Manage secrets <manage-secrets>`,
    :external+juju:ref:`Juju | Secret <secret>`

To make your charm capable of accepting a user secret, in your charm's
project file, specify the ``config`` key with the ``type`` subkey set to
``secret``.

    See more: :ref:`charmcraft-yaml-key-config`

    See next: :external+ops:ref:`Ops | Manage secrets <manage-secrets>`


Specify necessary parts
~~~~~~~~~~~~~~~~~~~~~~~

    See more: :ref:`manage-parts`

.. _pack-a-charm:

Pack a charm
------------

To pack a charm directory, in the charm's root directory, run the command below:

.. code-block:: bash

    charmcraft pack

This will fetch any dependencies (from PyPI, based on ``requirements.txt``),
compile any modules, check that all the key files are in place, and produce a
compressed archive with the extension ``.charm``. As you can verify, this archive
is just a zip file with metadata and the operator code itself.

.. collapse:: Example session for a charm called microsample-vm

    Pack the charm:

    .. code-block:: bash

        charmcraft pack

    .. terminal::

        Created 'microsample-vm_ubuntu-22.04-amd64.charm'.
        Charms packed:
          microsample-vm_ubuntu-22.04-amd64.charm

    Optionally, verify that this has created a .charm file in your charm's root directory:

    .. code-block:: bash

        ls

    .. terminal::

        CONTRIBUTING.md  charmcraft.yaml                          requirements.txt  tox.ini
        LICENSE          microsample-vm_ubuntu-22.04-amd64.charm  src
        README.md        pyproject.toml                           tests

    Optionally, verify that the .charm file is simply a zip file that contains
    everything you've packed plus any dependencies:

    .. code-block:: bash

        unzip -l microsample-vm_ubuntu-22.04-amd64.charm | { head; tail;}

    .. terminal::

        Archive:  microsample-vm_ubuntu-22.04-amd64.charm
          Length      Date    Time    Name
        ---------  ---------- -----   ----
              815  2023-12-05 12:12   README.md
            11337  2023-12-05 12:12   LICENSE
              250  2023-12-05 12:31   manifest.yaml
              102  2023-12-05 12:31   dispatch
              106  2023-12-01 14:59   config.yaml
              717  2023-12-05 12:31   metadata.yaml
              921  2023-12-05 12:26   src/charm.py
              817  2023-12-01 14:44   venv/setuptools/command/__pycache__/upload.cpython-310.pyc
            65175  2023-12-01 14:44   venv/setuptools/command/__pycache__/easy_install.cpython-310.pyc
             4540  2023-12-01 14:44   venv/setuptools/command/__pycache__/py36compat.cpython-310.pyc
             1593  2023-12-01 14:44   venv/setuptools/command/__pycache__/bdist_rpm.cpython-310.pyc
             6959  2023-12-01 14:44   venv/setuptools/command/__pycache__/sdist.cpython-310.pyc
             2511  2023-12-01 14:44   venv/setuptools/command/__pycache__/rotate.cpython-310.pyc
             2407  2023-12-01 14:44   venv/setuptools/extern/__init__.py
             2939  2023-12-01 14:44   venv/setuptools/extern/__pycache__/__init__.cpython-310.pyc
        ---------                     -------
        20274163                     1538 files

The command has a number of flags that allow you to specify a different charm directory
to pack, whether to force pack if there are linting errors, etc.

   See more: :ref:`ref_commands_pack`

.. caution::

    **If you've declared any resources :** This will *not* pack the resources.
    This means that, when you upload your charm to Charmhub (if you do), you will
    have to upload the resources separately. See more: :ref:`manage-resources`.

.. important::

    When the charm is packed, a series of analyses and lintings will happen,
    you may receive warnings and even errors to help improve the quality of the
    charm. See more:
    :ref:`Charmcraft analyzers and linters <charmcraft-analyzers-and-linters>`

..

    See next: :external+juju:ref:`Juju | Manage charms <manage-charms>`

.. _publish-a-charm:

Publish a charm on Charmhub
---------------------------

1. Log in to Charmhub:

   .. code-block:: bash

       charmcraft login

..

   See more: :ref:`manage-the-current-charmhub-user`

2. Register your charm's name (the one you specified in ``charmcraft.yaml`` > ``name``):

   .. code-block:: bash

       charmcraft register my-awesome-charm

   ..

   See more: :ref:`manage-names`

   .. note::

       This automatically creates 4 channels, all with track ``latest`` but with
       different risk levels, namely, edge, beta, candidate, stable, respectively.

   See more: :ref:`manage-channels`.

3. Upload the charm to Charmhub: Use the ``charmcraft upload`` command followed by the
   your charm's filepath. E.g., if you are in the charm's root directory,

   .. code-block:: bash

       charmcraft upload my-awesome-charm.charm

   .. terminal::

       Revision 1 of my-awesome-charm created

   ..

   See more: :ref:`ref_commands_upload`

   .. note::

       Each time you upload a charm to Charmhub, that creates a revision (unless
       you upload the exact same file again). See more: :ref:`manage-charm-revisions`.

4. If your charm has associated resources: These are not packed with the rest of the
   charm project, so you must upload them explicitly to Charmhub as well. For example:

   .. code-block:: bash

       charmcraft upload-resource my-awesome-charm someresource
       --filepath=/tmp/superdb.bin

   .. terminal::

       Revision 1 created of resource 'someresource' for charm 'my-awesome-charm'

   ..

   See more: :ref:`manage-resources`

   .. note::

       Each time you upload a resource to Charmhub, that creates a revision (unless you
       upload the exact same file again). See more: :ref:`manage-resource-revisions`.

5. Release the charm: To release a charm, release your revision of choice to the
   target release channel. For a charm that has a resource, also specify the
   resource and its revision. E.g.,

   .. code-block:: bash

       charmcraft release my-awesome-charm --revision=1 --channel=beta
       --resource someresource:1

   .. terminal::

       Revision 1 of charm 'my-awesome-charm' released to beta (attaching resources: 'someresource' r1)

..

   See more: :ref:`manage-charm-revisions`

   .. note::

       This automatically opens the channel. See more: :ref:`manage-channels`.

   ..

   See next: :external+juju:ref:`Juju | Deploy a charm <deploy-a-charm>`,
   :external+juju:ref:`Juju | Update a charm <update-a-charm>`

.. tip::

    To update the charm on Charmhub, repeat the upload and release steps.

.. important::

    Releasing a charm on Charmhub gives it a public URL. However, the charm will not
    appear in the Charmhub search results until it has passed formal review. To request
    formal review, reach out to the community to announce your charm and ask for a
    review by an experienced community member. See more: `Discourse | review requests
    <https://discourse.charmhub.io/c/charmhub-requests/46>`_.

    Also, the point of publishing and having a charm publicly listed on Charmhub is so
    others can reuse it and potentially contribute to it as well. To publicise your
    charm:

    - `Write a Discourse post to announce your release.
      <https://discourse.charmhub.io/tags/c/announcements-and-community/33/none>`_

    - `Schedule a community workshop to demo your charm's capabilities.
      <https://discourse.charmhub.io/tag/community-workshop>`_

    - `Chat about it with your charmer friends.
      <https://matrix.to/#/#charmhub-charmdev:ubuntu.com>`_
