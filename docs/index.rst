.. meta::
    :description: Charmcraft is the command-line tool for initializing, packaging, and
                  publishing Juju charms.

:relatedlinks: [Juju](https://documentation.ubuntu.com/juju/), [Ops](https://documentation.ubuntu.com/ops/), [Charmlibs](https://canonical-charmlibs.readthedocs-hosted.com/), [Jubilant](https://documentation.ubuntu.com/jubilant/), [Concierge](https://github.com/canonical/concierge), [Pebble](https://documentation.ubuntu.com/pebble/)


Charmcraft
==========

**Charmcraft** is the command-line tool for building Juju charms.

It provides commands to build, pack, and publish charms and integrates with Ops and
Charmhub.

Charmcraft supports popular languages and web app frameworks such as Django, Express,
Python, and Go through its extensions. These create language-specific scaffolding so
developers can focus on the content of their charms.

Charmcraft is for platform engineers, site reliability engineers, and systems
administrators looking to charm an application for their Juju deployment.


In this documentation
---------------------

First steps
~~~~~~~~~~~

.. domain::

    .. slice:: Installation

        :doc:`Install Charmcraft <howto/manage-charmcraft>`

    .. slice:: Crafting language

        :doc:`/reference/commands/index`
        :doc:`charmcraft.yaml <reference/files/charmcraft-yaml-file>`


Charm development
~~~~~~~~~~~~~~~~~

.. domain::

    .. slice:: Platform compatibility

        :doc:`Select platforms <howto/select-platforms>`
        :doc:`explanation/bases`
        :doc:`reference/platforms`

    .. slice:: Parts

        :doc:`YAML keys <common/craft-parts/reference/part_properties>`
        :doc:`reference/plugins/index`
        :doc:`Lifecycle reference <reference/parts/lifecycle>`
        :doc:`common/craft-parts/explanation/filesets`
        :doc:`Environment variables <common/craft-parts/reference/step_execution_environment>`

    .. slice:: Environment management

        :doc:`Poetry <reference/plugins/poetry_plugin>`
        :doc:`Python <reference/plugins/python_plugin>`
        :doc:`uv <reference/plugins/uv_plugin>`
        :doc:`Migrate from the Charm plugin <howto/migrate-plugins/index>`

    .. slice:: Resources and libraries

        :doc:`howto/manage-resources`
        :doc:`howto/manage-libraries`

    .. slice:: Debugging

        :doc:`reference/analyzers-and-linters`


12-factor app development
~~~~~~~~~~~~~~~~~~~~~~~~~

.. domain::

    .. slice:: Overview

        :doc:`Initialize <howto/manage-web-app-charms/index>`
        :doc:`Configure <howto/manage-web-app-charms/configure-web-app-charm>`
        :doc:`Integrate <howto/manage-web-app-charms/integrate-web-app-charm>`
        :doc:`Use <howto/manage-web-app-charms/use-web-app-charm>`
        :doc:`Connect databases <howto/manage-web-app-charms/use-a-database>`
        :doc:`Manage extensions <howto/manage-extensions>`

    .. slice:: Django

        :doc:`Charm a Django app <tutorial/kubernetes-charm-django>`
        :doc:`Django extension <reference/extensions/django-framework-extension>`

    .. slice:: Express

        :doc:`Charm an Express app <tutorial/kubernetes-charm-express>`
        :doc:`Express extension <reference/extensions/express-framework-extension>`

    .. slice:: FastAPI

        :doc:`Charm a FastAPI app <tutorial/kubernetes-charm-fastapi>`
        :doc:`FastAPI extension <reference/extensions/fastapi-framework-extension>`

    .. slice:: Flask

        :doc:`Charm a Flask app <tutorial/kubernetes-charm-flask>`
        :doc:`Flask extension <reference/extensions/flask-framework-extension>`

    .. slice:: Go

        :doc:`Charm a Go app <tutorial/kubernetes-charm-go>`
        :doc:`Go extension <reference/extensions/go-framework-extension>`

    .. slice:: Spring Boot

        :doc:`Charm a Spring Boot app <tutorial/kubernetes-charm-spring-boot>`
        :doc:`Spring Boot extension <reference/extensions/spring-boot-framework-extension>`


Charm builds
~~~~~~~~~~~~

.. domain::

    .. slice:: Optimization

        :doc:`howto/shared-cache`

    .. slice:: Scaling

        :doc:`howto/build-remotely`
        :doc:`Remote build reference <reference/remote-builds>`

    .. slice:: Legacy support

        :doc:`howto/pack-a-reactive-charm-with-charmcraft`
        :doc:`howto/pack-a-hooks-based-charm-with-charmcraft`


Publication
~~~~~~~~~~~

.. domain::

    .. slice:: Accounts

        :doc:`howto/manage-the-current-charmhub-user`

    .. slice:: Registration and releases

        :doc:`Register a charm <howto/manage-names>`
        :doc:`howto/manage-tracks`
        :doc:`howto/manage-channels`
        :doc:`howto/manage-revisions`


How this documentation is organized
-----------------------------------

The Charmcraft documentation embodies the `Diátaxis framework <https://diataxis.fr/>`__.

* The :ref:`tutorials <tutorial>` are lessons that steps through the main process of
  packaging a charm.
* :ref:`how-to-guides` contain directions for crafting charms.
* :ref:`References <reference>` describe the structure and function of the individual
  components in Charmcraft.
* :ref:`Explanations <explanation>` aid in understanding the concepts and relationships
  of Charmcraft as a system.


Project and community
---------------------

Charmcraft is a member of the Canonical family. It's an open source project that warmly
welcomes community projects, contributions, suggestions, fixes and constructive
feedback.


Get involved
~~~~~~~~~~~~

* `Charmcraft Matrix channel <https://matrix.to/#/#charmcraft:ubuntu.com>`__
* `Charmcraft forum <https://discourse.charmhub.io/c/charmcraft/3>`__
* `Contribute to Charmcraft development <https://github.com/canonical/charmcraft/blob/main/CONTRIBUTING.md>`__
* :ref:`contribute-to-this-documentation`


Governance and policies
~~~~~~~~~~~~~~~~~~~~~~~

* `Ubuntu Code of Conduct <https://ubuntu.com/community/docs/ethos/code-of-conduct>`__
* `Canonical Contributor License Agreement
  <https://ubuntu.com/legal/contributors>`__


.. toctree::
    :hidden:

    tutorial/index
    howto/index
    reference/index
    explanation/index

.. toctree::
    :hidden:

    release-notes/index
    contribute-to-this-documentation
