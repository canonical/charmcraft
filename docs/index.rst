:relatedlinks: [Juju](https://documentation.ubuntu.com/juju/), [Ops](https://documentation.ubuntu.com/ops/), [Charmlibs](https://canonical-charmlibs.readthedocs-hosted.com/), [Jubilant](https://documentation.ubuntu.com/jubilant/), [Concierge](https://github.com/canonical/concierge), [Pebble](https://documentation.ubuntu.com/pebble/)


Charmcraft
==========

Charmcraft is the command-line tool for initializing, packaging, and publishing Juju
charms.

For new projects, Charmcraft generates all the necessary files, which can be tailored to
an app by modifying the YAML and Ops-powered Python inside. With extensions, Charmcraft
adapts the template content to languages and frameworks such as Django, Express, and Go.
Then, with a few commands, charm authors can package the charm and publish it to
Charmhub.

With Charmcraft, developers can bypass boilerplate steps and focus on the content of
their charms. Additionally, its integration with tools and platforms such as Ops and
Charmhub provide a complete charm development experience.

Charmcraft is for platform engineers, site reliability engineers, and systems
administrators looking to charm an application for their Juju deployment.


In this documentation
---------------------

.. list-table::
    :widths: 35 65
    :header-rows: 0

    * - **Installation and setup**
      - :ref:`manage-charmcraft`
    * - **Vocabulary and syntax**
      - :ref:`configure-package-information` • :ref:`commands` •
        :ref:`charmcraft.yaml <charmcraft-yaml-file>` •
        :ref:`Part keys <reference-part-properties>`
    * - **Platform compatibility**
      - :ref:`select-platforms` • :ref:`explanation-bases` •
        :ref:`reference-platforms`
    * - **Software integration**
      - :ref:`parts` • :ref:`manage-resources` • :ref:`manage-libraries`
    * - **12-factor web apps**
      - :ref:`tutorial` • :ref:`init-12-factor-charms` •
        :ref:`Configuration <configure-12-factor-charms>` •
        :ref:`Integration <integrate-12-factor-charms>` •
        :ref:`Usage <use-12-factor-charms>` • :ref:`extensions`
    * - **Debugging**
      - :ref:`charmcraft-analyzers-and-linters`
    * - **Distribution**
      - :ref:`publish-a-charm` • :ref:`manage-names` • :ref:`manage-tracks` •
        :ref:`manage-channels` • :ref:`manage-charm-revisions`


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
    :maxdepth: 2
    :hidden:

    tutorial/index
    howto/index
    reference/index
    explanation/index
    contribute-to-this-documentation
    release-notes/index
