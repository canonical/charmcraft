.. Charmcraft documentation root file

Charmcraft
==========

.. toctree::
    :maxdepth: 2
    :hidden:

    tutorial/index
    howto/index
    explanation/index
    reference/index
    contribute-to-this-documentation
    release-notes/index

Charmcraft is the command-line tool for initializing, packaging, and publishing
:external+juju:ref:`Juju charms <charm>`.

When initializing a project, Charmcraft generates all the necessary files, which can be
further catered to an application by modifying the YAML and :external+ops:doc:`Ops
<index>`-powered Python in the pre-populated template content. For Django, FastAPI,
Flask, and Go applications, Charmcraft's extensions simplify this process further by
only requiring minor YAML changes after initialization. With just a few simple commands,
charm authors can then use Charmcraft to package a charm and publish it to `Charmhub`_.

Charmcraft simplifies every step of the charming process, enabling charm authors to
bypass boilerplate steps and focus on the contents of their charms. Additionally,
Charmcraft's integration with tools and platforms such as Ops and Charmhub provides
charm authors with a complete charm development experience.

Charmcraft offers an efficient and straightforward way for anyone to charm an
application for their Juju deployment, regardless of that application's complexity or
scope.


In this documentation
---------------------

.. grid:: 1 1 2 2

    .. grid-item-card:: Tutorial
        :link: tutorial/index
        :link-type: doc

        **Get started** - a hands-on introduction to Charmcraft for new users

    .. grid-item-card:: How-to guides
        :link: howto/index
        :link-type: doc

        **Step-by-step guides** covering key operations and common tasks

.. grid:: 1 1 2 2
    :reverse:

    .. grid-item-card:: Reference
        :link: reference/index
        :link-type: doc

        **Technical information**, including commands, extensions, and project files

    .. grid-item-card:: Explanation
        :link: explanation/index
        :link-type: doc

        **Discussion and clarification** of key topics


Project and community
---------------------

Charmcraft is a member of the Canonical family. It's an open source project
that warmly welcomes community projects, contributions, suggestions, fixes,
and constructive feedback.

- `Ubuntu Code of Conduct <https://ubuntu.com/community/code-of-conduct>`_
- `Canonical contributor licence agreement <https://ubuntu.com/legal/contributors>`_
