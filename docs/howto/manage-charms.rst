.. _manage-charms:

Manage charms
=============

This guide shows how to initialise, configure, pack, and publish a
:external+juju:ref:`charm <charm>`.

This guide assumes familiarity with charms. If you're new to charming,
start with :external+juju:ref:`manage-charms` in Juju.

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

The command also allows you to not specify any :ref:`profile <profile>`
(in that case you get the ``kubernetes`` profile -- a minimal profile
with scaffolding for a Kubernetes charm) and has flags that you can use
for other operations. For example, to specify:

- a different directory to operate in
- a charm name different from the name of the root directory.

.. _add-charm-project-metadata-an-icon-docs:

Add charm project metadata, an icon, docs
-----------------------------------------

Project information such as the name, description, web sites, and icon
are set in the charm's project file, ``charmcraft.yaml``.

Specify that the project is a charm
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To specify that the project is a charm, set the
:ref:`charmcraft-yaml-key-type` key to ``charm`` in your project file:

.. code-block:: yaml

    type: charm

.. _specify-a-name:

Specify a name
~~~~~~~~~~~~~~


To specify your charm's name, set the :ref:`charmcraft-yaml-key-name` key:

.. code-block:: yaml

    name: traefik-k8s


Specify a title
~~~~~~~~~~~~~~~

To specify the ``title`` for your charm's page on Charmhub, set the
:ref:`charmcraft-yaml-key-title` key:

.. code-block:: yaml

    title: |
      Traefik Ingress Operator for Kubernetes


Add a summary
~~~~~~~~~~~~~

To add a ``summary`` line for your charm, set
the :ref:`charmcraft-yaml-key-summary` key in your charm's project file:

.. code-block:: yaml

    summary: |
      A Juju charm to run a Traefik-powered ingress controller on Kubernetes.

Add a description
~~~~~~~~~~~~~~~~~

To add a longer ``description`` for your charm, set the
:ref:`charmcraft-yaml-key-description` key in your charm's project file:

.. code-block:: yaml

    description: |
      A Juju-operated Traefik operator that routes requests from the outside of a
      Kubernetes cluster to Juju units and applications.

Add contact information
~~~~~~~~~~~~~~~~~~~~~~~

To add maintainer contact information for a charm, set the
:ref:`links.contact <charmcraft-yaml-key-links-contact>` key:

.. code-block:: yaml

    links:
      contact: Please send your answer to Old Pink, care of the Funny Farm, Chalfont

Add a link to source code
~~~~~~~~~~~~~~~~~~~~~~~~~

To add a :ref:`link <charmcraft-yaml-key-links>` to the source code for a charm,
set an item under the :ref:`links.source <charmcraft-yaml-key-links-source>`
key in your charm's project file:

.. code-block:: yaml

    links:
      source:
      - https://github.com/canonical/traefik-k8s-operator


Add a link to the bug tracker
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To add a ``link`` to the bug tracker for a charm, set an item under the
:ref:`links.issues <charmcraft-yaml-key-links-website>` key in your
charm's project file:

.. code-block:: yaml

    links:
      issues:
        - https://github.com/canonical/traefik-k8s-operator/issues

Add a link to the website
~~~~~~~~~~~~~~~~~~~~~~~~~

If your charm has a website outside of Charmhub and you want to add a ``link``
to it, set an item under the :ref:`links.website
<charmcraft-yaml-key-links-website>` key in your charm's project file:

.. code-block:: yaml

    links:
      website:
      - https://charmed-kubeflow.io/

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

.. admonition:: Examples of good documentation in small charms

    * `Azure storage integrator <https://charmhub.io/azure-storage-integrator>`_ charm
    * `Repo policy compliance <https://charmhub.io/repo-policy-compliance>`_ charm

.. admonition:: Examples of good documentation in big charms

    * `OpenSearch <https://charmhub.io/opensearch>`_ charm
    * `Wordpress-k8s <https://charmhub.io/wordpress-k8s>`_ charm

Add terms of use
~~~~~~~~~~~~~~~~

To add :ref:`charmcraft-yaml-key-terms` of use for your charm, in your
charm's project file, specify a value for the ``terms`` key. For example:

To add ``terms of use`` for your charm, set the
:ref:`charmcraft-yaml-key-terms` key in your charm's project file:

.. code-block:: yaml

    terms:
      - Butterscotch is regal
      - Cara is adorable

Add an icon
~~~~~~~~~~~

:ref:`manage-icons` describes how to add and manage icons.


.. _add-runtime-details-to-a-charm:

Add runtime details to a charm
------------------------------

You can specify runtime requirements, resource needs, and operational
features for your charm.

Require a specific Juju version
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To require a specific Juju version for your charm, set the
:ref:`charmcraft-yaml-key-assumes` key in your charm's project file:

.. code-block:: yaml

    assumes:
      - juju >= 3.5


Require a Kubernetes cloud
~~~~~~~~~~~~~~~~~~~~~~~~~~

To require a Kubernetes cloud for your charm, set the ``assumes`` key
in your charm's project file:

.. code-block:: yaml

    assumes:
      - k8s-api

Require a specific base and platforms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To require a specific ``base`` and platforms for your
charm, set the :ref:`charmcraft-yaml-key-base` and ``platforms``
keys in your charm's project file:

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

If the ``base`` is a development base, use :ref:`charmcraft-yaml-key-build-base`.


Specify container requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To specify ``containers`` requirements, set the
:ref:`container <charmcraft-yaml-key-containers>` key in your charm's project file.

Specify associated resources
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To specify the ``resources`` associated with the charm, set the
:ref:`resources <manage-resources>` key in your charm's project file.

Specify device requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~~

To specify ``devices`` requirements, set the
:ref:`device <charmcraft-yaml-key-devices>` key in your charm's project file.

Manage storage
~~~~~~~~~~~~~~

To specify ``storage`` requirements, set the :ref:`charmcraft-yaml-key-storage`
key in your charm's project file.


Specify extra binding requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To specify :ref:`extra binding <charmcraft-yaml-key-extra-bindings>`
requirements, in your charm's project file, specify the ``extra-bindings`` key.

To specify ``extra-bindings`` requirements, set the
:ref:`extra binding <charmcraft-yaml-key-extra-bindings>` key in your charm's
project file.

Require subordinate deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To require :ref:`charmcraft-yaml-key-subordinate` deployment for your charm
(i.e., for it to be deployed to the same machine as another charm, called
its *principal*), in your charm's project file, specify the ``subordinate`` key.

To require ``subordinate`` deployment for your charm (i.e., for it to be
deployed to the same machine as another charm, called
its *principal*), set the :ref:`charmcraft-yaml-key-subordinate` key in
your charm's project file.

.. _manage-actions:

Manage actions
~~~~~~~~~~~~~~

First, understand :external+juju:ref:`how to manage actions <manage-actions>` in Juju.

To declare an :external+juju:ref:`action <action>` in your charm, set the
:ref:`charmcraft-yaml-key-actions` key in your charm's project file.

.. _manage-the-app-configuration:

Manage the app configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First, see :external+juju:ref:`application-configuration` and
:external+juju:ref:`configure-an-application` for guidance on how to
configure an application.

To declare a configuration option for your charm, set the
:ref:`charmcraft-yaml-key-config` key in your charm's project file.

.. _manage-relations:

Manage relations
~~~~~~~~~~~~~~~~

First, review :external+juju:ref:`how to manage relations <manage-relations>`
in Juju.

To declare a :external+juju:ref:`relation <relation>` endpoint in your
charm, set the ``peers``, ``provides``, or ``requires`` key in your charm's
project file.


Specify necessary libs
~~~~~~~~~~~~~~~~~~~~~~

:ref:`manage-libraries` describes how to specify the necessary libraries.

.. _manage-secrets:

Manage secrets
~~~~~~~~~~~~~~

During operation, Juju mediates charm secrets.
:external+juju:ref:`manage-secrets` in the Juju documentation describes
how users work with charm secrets.

To provide a user-defined secret in your charm, add an entry to the
:ref:`config.options <charmcraft-yaml-key-config>` key, with ``type: secret``.

Specify necessary parts
~~~~~~~~~~~~~~~~~~~~~~~

:ref:`manage-parts` describes how to specify the necessary parts.

.. _pack-a-charm:

Pack a charm
------------

To :ref:`ref_commands_pack` a charm directory, in the charm's root directory,
run:

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

.. _publish-a-charm:

Publish a charm on Charmhub
---------------------------

1. Log in to Charmhub:

   .. code-block:: bash

       charmcraft login

..

2. Register your charm's name (the one you specified in ``charmcraft.yaml`` > ``name``):

   .. code-block:: bash

       charmcraft register my-awesome-charm

   ..

   .. note::

       This automatically creates 4 channels, all with track ``latest`` but with
       different risk levels, namely, edge, beta, candidate, stable, respectively.

3. :ref:`Upload <ref_commands_upload>` the charm to Charmhub. Use the
``charmcraft upload`` command followed by the your charm's filepath.
For example, if you are in the charm's root directory:

   .. code-block:: bash

       charmcraft upload my-awesome-charm.charm

   .. terminal::

       Revision 1 of my-awesome-charm created

   ..

   .. note::

       Each time you upload a charm to Charmhub, that creates a
       :ref:`revision <manage-charm-revisions>` (unless you upload the exact
       same file again).

4. If your charm has associated :ref:`resources <manage-resources>`,
upload them explicitly to Charmhub as well. They aren't packed with the
rest of the charm project. For example:

   .. code-block:: bash

       charmcraft upload-resource my-awesome-charm someresource
       --filepath=/tmp/superdb.bin

   .. terminal::

       Revision 1 created of resource 'someresource' for charm 'my-awesome-charm'

   .. note::

       Each time you upload a resource to Charmhub, that creates a
       :ref:`revision <manage-resource-revisions>` (unless you upload the
       exact same file again).

5. Release the charm: To release a charm, release your revision of choice to the
   target release channel. For a charm that has a resource, also specify the
   resource and its revision. For example:

   .. code-block:: bash

       charmcraft release my-awesome-charm --revision=1 --channel=beta
       --resource someresource:1

   .. terminal::

       Revision 1 of charm 'my-awesome-charm' released to beta (attaching resources: 'someresource' r1)

   .. note::

       This automatically opens the :ref:`channel <manage-channels>`.

   .. tip::

       To update the charm on Charmhub, repeat the upload and release steps.

.. important::

    Releasing a charm on Charmhub gives it a public URL. However, the charm will not
    appear in the Charmhub search results until it has passed formal review. To
    :external+ops:ref:`make your charm discoverable <make-your-charm-discoverable>`,
    reach out to the community to announce your charm and ask for a review
    by an experienced community member.

    Also, the point of publishing and having a charm publicly listed on Charmhub is so
    others can reuse it and potentially contribute to it as well. To publicise your
    charm:

    - `Write a Discourse post to announce your release.
      <https://discourse.charmhub.io/tags/c/announcements-and-community/33/none>`_

    - `Schedule a community workshop to demo your charm's capabilities.
      <https://discourse.charmhub.io/tag/community-workshop>`_

    - `Chat about it with your charmer friends.
      <https://matrix.to/#/#charmhub-charmdev:ubuntu.com>`_
