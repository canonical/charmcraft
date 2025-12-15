.. _libname-py-file:

``<libname>.py`` file
=====================

File ``<libname>.py`` is a Python file in your charm project that holds a Charmhub-hosted
charm library -- that is, code that enables charm developers to easily share and reuse
auxiliary logic related to  charms -- for example, logic related to the relations
between charms.

Authors associate libraries with a specific charm and publish them to Charmhub with
a reference to the origin charm. This does not prevent reuse, modification or sharing.

The publishing tools around libraries are deliberately kept simple.
Libraries are however versioned and uniquely identified.

.. admonition:: More information about charm libraries
    :class: hint

    - :external+charmlibs:ref:`Charmlibs | The different kinds of charm libraries <charm-libs>`
    - :external+charmlibs:ref:`Charmlibs | Manage Python package libraries <how-to-manage-charm-libraries>`
    - :ref:`Manage Charmhub-hosted libraries <manage-libraries>`
    - :external+charmlibs:ref:`Charmlibs | General libraries listing <general-libs-listing>`
    - :external+charmlibs:ref:`Charmlibs | Interface libraries listing <interface-libs-listing>`


Location
--------

Charm libraries are located in a subdirectory inside the charm with the following
structure:

.. code-block::

    lib/charms/<charm-name>/v<API>/<libname>.py

where the ``<charm-name>`` placeholder represents the name of charm responsible for
the library (converted to a valid module name), ``<libname>`` represents this
particular library, and ``<API>`` represents the API version of the library.

For example, inside a charm ``mysql``, the library ``db`` with major version 3 will
be in a directory with the structure below:

.. code-block::

    lib/charms/mysql/v3/db.py

When you pack your charm, Charmcraft copies the top ``lib`` directory into the root
directory of the charm. Thus, to import this library in Python use the full path
minus the top ``lib`` directory, as below:

.. code-block:: python

    import charms.mysql.v3.db


Structure
---------

A charm library is a Python file with the following structure:


Docstring
~~~~~~~~~

Your charm file begins with a long docstring. This docstring describes your library.
Charmcraft publishes it as your library's documentation on Charmhub. This
documentation is updated whenever a new version of the library is published.

The docstring is expected to be in the `CommonMark <https://commonmark.org/>`_
dialect of Markdown.


Metadata
~~~~~~~~

After the docstring, there are a few metadata keys, as below.


``LIBID``
^^^^^^^^^

**Status:** Required

**Purpose:** Contains the unique identifier for a library across the entire
universe of charms. The value is assigned by Charmhub to this particular library
automatically at library creation time. This key enables Charmhub and ``charmcraft``
to track the library uniquely even if the charm or the library are renamed, which
allows updates to warn and guide users through the process.

**Type:** ``str``

**Value:** Assigned by :ref:`ref_commands_create-lib`


``LIBAPI``
^^^^^^^^^^

**Status:** Required

**Purpose:** Declares the API version of this charm library.

**Type:** ``int``

**Value:** ``LIBAPI``` is set to an initial state of ``0``. In general,
``LIBAPI`` must match the major version in the import path.


``LIBPATCH``
^^^^^^^^^^^^

**Status:** Required

**Purpose:** Declares the patch version of this charm library.

**Type:** ``int``

**Value:** ``LIBPATCH`` is set to an initial state of ``1``. In general, it must
match the current patch version (needs to be updated when changing).

.. note::

    While ``LIBPATCH`` can be set to ``0``, it is not allowed to set both ``LIBAPI``
    and ``LIBPATCH`` to ``0``. As such, a charm lib may have a version ``0.1`` and
    a version ``1.0``, but not a version ``0.0``.


``PYDEPS``
^^^^^^^^^^

**Status:** Optional

**Purpose:** Declares external Python dependencies for the library.

When using the ``charm`` plugin, Charmcraft will make sure to install them in the
virtual environment created in any charm that includes the library.

**Type:** ``list[str]``

Each string is a regular "pip installable" Python dependency that will be retrieved
from PyPI in the usual way (subject to the user's system configuration) and which
supports all dependency formats (just the package name, a link to a Github project,
etc.).

.. collapse:: Examples

    .. code-block:: python

        PYDEPS=["jinja2"]

    .. code-block:: python

        PYDEPS = ["pyyaml", "httpcore<0.15.0,>=0.14.5"]

    .. code-block:: python

        PYDEPS = [
            "git+https://github.com/canonical/operator/#egg=ops",
            "httpcore<0.15.0,>=0.14.5",
            "requests",
        ]

Note that when called to install all the dependencies from the charm and all the
used libraries, ``pip`` may detect conflicts between the requested packages and
their versions. This is a feature, because it's always better to detect
incompatibilities between dependencies at this moment than when the charm is being
deployed or run after deployment.


Code
^^^^

After the docstring and the metadata, there's the library code.
This is regular Python code.
