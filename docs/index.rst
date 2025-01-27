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

Charmcraft is a tool designed to simplify the creation, building, and sharing of a
:external+juju:ref:`Juju charm <charm>`.

When you initialise a charm with Charmcraft, you automatically get all the crucial
project files, pre-populated with helpful template content. These files are such that
they can be packed right away; however, to make them meaningul for the application you
are charming, you'll want to customise the YAML and
:external+ops:doc:`ops <index>`-powered Python in these files. For certain types of
applications (Django, FastAPI, Flask, Go), if you initialise with a suitable
Charmcraft extension, things are even easier -- just tweak a few values in the
YAML and you get a fully functioning charm. Either way, once you're pleased with
what you've got, you can again use Charmcraft to publish your charm
on `Charmhub`_.

You can create, build, and share a charm any way you want, but with Charmcraft you get
state-of-the-art results in record time.

If you're a charm author, you *must* use Charmcraft!


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
