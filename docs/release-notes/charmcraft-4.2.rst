.. _release-4.2:

Charmcraft 4.2 release notes
============================

17 March 2026

Learn about the new features, changes, and fixes introduced in Charmcraft 4.2.


Requirements and compatibility
------------------------------

For development and testing, Charmcraft requires a host with a minimum of 4GB RAM
running a Linux distribution compatible with systemd.

All versions of Charmcraft require the following software:

- systemd
- `snapd`_
- Either `LXD`_ or `Multipass`_

We recommend you install the `Charmcraft snap <https://snapcraft.io/charmcraft>`_. It
comes bundled with all its dependencies.

Non-snap installations of Charmcraft have the following dependencies:

- Python 3.10 or higher
- libgit2 1.7
- `skopeo`_
- `Spread`_

What's new
----------

Charmcraft 4.2 brings the following new features.

Init template updates
~~~~~~~~~~~~~~~~~~~~~

Charmcraft 4.2 sets Ubuntu 24.04 as the default base for new charms using the
machine, kubernetes, :ref:`django-framework <django-framework-extension>`,
and :ref:`flask-framework <flask-framework-extension>` init templates.

The machine and kubernetes templates also now assume Juju 3.6 or newer.

Faster startup for new charms or after cleaning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When installed as a Snap, Charmcraft now injects not just itself, but also the
core24 snap into the created container from the host machine, speeding up initial
builds and reducing the download time.

uv plugin compiles bytecode
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :ref:`craft_parts_uv_plugin` now compiles bytecode for installed Python files
by default. To disable this for your charm, set ``UV_COMPILE_BYTECODE: false`` in
the part's :ref:`reference-part-properties-build-environment` key.

Better documentation
~~~~~~~~~~~~~~~~~~~~

The :ref:`how-to-guides` have been improved, and two new documents have been added:

- :doc:`How to use a database with your 12-factor charm </howto/manage-web-app-charms/use-a-database>`
- :doc:`Part properties reference </common/craft-parts/reference/part_properties>`

Known issues
------------

The following issues were reported and are scheduled to be fixed in upcoming
patch releases.

See individual issue links for any mitigations.

- `#2078 <https://github.com/canonical/charmcraft/issues/2078>`_
  ``charmcraft clean`` does not clean all platforms for a charm.
- `#1990 <https://github.com/canonical/charmcraft/issues/1990>`_ Cannot stage
  packages with Charmcraft
- `#2493 <https://github.com/canonical/charmcraft/issues/2493>`_ Packing fails when
  using a separate metadata.yaml file and the ``--project-dir`` argument.
- `#2492 <https://github.com/canonical/charmcraft/issues/2492>`_ Internal error when
  uploading a charm outside of a project directory.


.. Fixed bugs and issues
.. ---------------------

Contributors
------------

We would like to express a big thank you to all the people who contributed to
this release:

:literalref:`@activus-d <https://github.com/activus-d>`,
:literalref:`@alithethird <https://github.com/alithethird>`,
:literalref:`@arturo-seijas <https://github.com/arturo-seijas>`,
:literalref:`@bepri <https://github.com/bepri>`,
:literalref:`@dwilding <https://github.com/dwilding>`,
:literalref:`@f-atwi <https://github.com/f-atwi>`,
:literalref:`@jahn-junior <https://github.com/jahn-junior>`,
:literalref:`@james-garner-canonical <https://github.com/james-garner-canonical>`,
:literalref:`@javierdelapuente <https://github.com/javierdelapuente>`,
:literalref:`@jonathan-conder <https://github.com/jonathan-conder>`,
:literalref:`@lengau <https://github.com/lengau>`,
:literalref:`@medubelko <https://github.com/medubelko>`,
:literalref:`@mr-cal <https://github.com/mr-cal>`,
:literalref:`@smethnani <https://github.com/smethnani>`,
:literalref:`@tigarmo <https://github.com/tigarmo>`,
:literalref:`@tonyandrewmeyer <https://github.com/tonyandrewmeyer>`,
:literalref:`@unknown <https://github.com/unknown>`,
and :literalref:`@zhijie-yang <https://github.com/zhijie-yang>`
