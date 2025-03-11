.. Charmcraft documentation root file

Charmcraft
==========

.. toctree::
    :maxdepth: 2
    :hidden:

    tutorial/index
    howto/index
    reference/index
    release-notes/index

Charmcraft is the official command-line tool for initializing, packaging, and publishing
:external+juju:ref:`Juju charms <charm>`.

When initializing a project, Charmcraft generates all the necessary files, pre-populated
with template content, which can be further catered to an application using Charmcraft's
array of extensions. Packing a charm is similarly streamlined, as Charmcraft will
automatically fetch project dependencies and compile any modules before producing the
final charm artifact. When it comes time to publish a charm on `Charmhub`_, Charmcraft
provides tools for charm authors to register a charm's name, upload its associated
resources, and release revisions to channels.

Charmcraft simplifies every step of the charming process, enabling charm authors to
bypass boilerplate steps and focus on the contents of their charms. Additionally,
Charmcraft's seamless integration with tools such as :external+ops:doc:`Ops <index>` and
Charmhub provides charm authors with a truly comprehensive toolkit for charm
development.

For those looking to add their applications to a Juju deployment, Charmcraft will prove
to be an invaluable tool.


In this documentation
---------------------

.. grid:: 1 1 2 2

    .. grid-item-card:: Tutorial
        :link: tutorial/index
        :link-type: doc

        **Start here**: a hands-on introduction to Example Product for new users


    .. grid-item-card:: How-to guides
        :link: howto/index
        :link-type: doc

        **Step-by-step guides** covering key operations and common tasks

.. grid:: 1 1 2 2
    :reverse:

    .. grid-item-card:: Reference
        :link: reference/index
        :link-type: doc

        **Technical information** - specifications, APIs, architecture

.. grid-item-card: Explanation
    :link: explanation/index
    :link-type: doc

    **Discussion and clarification** of key topics


Project and community
---------------------

Charmcraft is a member of the Canonical family. It's an open source project
that warmly welcomes community projects, contributions, suggestions, fixes
and constructive feedback.

- `Ubuntu Code of Conduct <https://ubuntu.com/community/code-of-conduct>`_.
- `Canonical contributor licenses agreement <https://ubuntu.com/legal/contributors>`_.


Indices and tables
------------------

* :ref:`genindex`
* :ref:`search`
