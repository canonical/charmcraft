.. _manage-libraries:

Manage libraries
================


Initialise a library
--------------------

   See also: :ref:`ref_commands_create-lib`

In your charm's root directory, run ``charmcraft create-lib``. In this example we use
the name ``demo``.

.. code-block:: bash

    charmcraft create-lib demo

.. note::

    Before creating a library, you must first register ownership of your charm's name.
    See more: :ref:`publish-a-charm`.


This will create a template file at ``$CHARMDIR/lib/charms/demo/v0/demo.py``.

    See more: :ref:`ref_commands_create-lib`, :ref:`libname-py-file`

Edit this file to write your library.

.. important::

    A library must comprise a single Python file. If you write a library that feels too
    "big" for a single file, it is likely that the library should be split up, or that
    you are actually writing a full-on charm.

..

    See next: :external+ops:ref:`Ops | Manage libraries <manage-libraries>`


.. _publish-a-library:

Publish a library on Charmhub
-----------------------------

.. caution::

    On Charmhub, a library is always associated with the charm that it was first created
    for. When you publisht it to Charmhub, it's published to the page of that charm. To
    be able to publish it, you need to be logged in to Charmhub as a user who owns the
    charm (see more: :ref:`publish-a-charm`) or as a user who is registered as a
    contributor to the charm (a status that can be requested via `Discourse`_).


To publish a library on Charmhub, in the root directory of the charm that holds the
library, run ``charmcraft publish-lib`` followed by the full library path on the
template ``charms.<charm-name>.v<api-version>.<library-name>``. For example:

.. code-block:: bash

    charmcraft publish-lib charms.demo.v0.demo

This will upload the library's content to Charmhub.

To update the library on Charmhub, update the ``LIBAPI`` or ``LIBPATCH`` metadata fields
inside the library file, then repeat the publish procedure.

  See more: :ref:`ref_commands_publish-lib`


.. caution::  **About the metadata fields:**

    Most times it is enough to just increment ``LIBPATCH`` but, if you're introducing
    breaking changes, you must work with the major API version. Additionally, be mindful
    of the fact that users of your library will update it automatically to the latest
    PATCH version with the same API version. To avoid breaking other people's library
    usage, make sure toincrement the ``LIBAPI`` version but reset ``LIBPATCH`` to ``0``.
    Also, before adding the breaking changes and updating these values, make sureto copy
    the library to the new path; this way you can maintain different major API versions
    independently, being able to update, for example, your v0 after publishing v1. See
    more: :ref:`libname-py-file`.

..

To share your library with other charm developers, navigate to the host charm's Charmhub
page, go to **Libraries** tab, then copy and share the URL at the top of the page.


View the libs published for a charm
-----------------------------------

The easiest way to find an existing library for a given charm is via ``charmcraft
list-lib``, as shown below. This will query Charmhub and show which libraries are
published for the specified charm, along with API/patch versions.

.. code-block:: bash

   charmcraft list-lib blogsystem

.. terminal::

   Library name    API    Patch
   superlib        1      0

The listing will not show older API versions; this ensures that new users always start
with the latest version.

Another good way to search for libraries is to explore the charm collection on
`Charmhub`_.

    See more: :ref:`ref_commands_list-lib`


Use a library
-------------

In your charm's project file, specify the ``charm-libs`` key with the desired
libraries.

    See more: :ref:`charmcraft-yaml-key-charm-libs`


In your charm's root directory, run ``charmcraft fetch-libs``. Charmcraft will download
the libraries to your charm's directory.

    See more: :ref:`ref_commands_fetch-libs`


To use a library in your ``src/charm.py``, import it using its fully-qualified path
minus the ``lib`` part:

.. code-block:: python

   import charms.demo.v0.demo

To update your lib with the latest published version, repeat the process.
