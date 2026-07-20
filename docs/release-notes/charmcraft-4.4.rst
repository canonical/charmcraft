.. meta::
    :description: Learn about the new features, changes, and fixes introduced in Charmcraft 4.4.

.. _release-4.4:

Charmcraft 4.4 release notes
============================

20 July 2026

Learn about the new features, changes, and fixes introduced in Charmcraft 4.4.


Requirements and compatibility
------------------------------

For development and testing, Charmcraft requires a host with a minimum of 4GB RAM
running a Linux distribution compatible with systemd.

All versions of Charmcraft require the following software:

- systemd
- `snapd`_
- Either `LXD`_ or `Multipass`_

We recommend you install the `Charmcraft snap <https://snapcraft.io/charmcraft>`__. It
comes bundled with all its dependencies.

Non-snap installations of Charmcraft have the following dependencies:

- Python 3.10 or higher
- libgit2 1.7
- `skopeo`_
- `Spread`_

What's new
----------

Charmcraft 4.4 brings the following new features.

Ubuntu One authentication
~~~~~~~~~~~~~~~~~~~~~~~~~

Charmcraft now uses Ubuntu One authentication instead of Candid for store
access and publishing workflows. Login is now handled entirely in the CLI,
without a browser-based authentication step.

12-factor extension and profile updates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Charmcraft 4.4 includes several improvements for 12-factor app and profile
workflows:

- Added extension dispatch support for 12-factor extensions.
- Added base support for Flask and Django extensions.
- Updated generated profile tests to treat warnings as errors by default.
- Added validation for ``paas-config.yaml`` inputs.

Documentation improvements
~~~~~~~~~~~~~~~~~~~~~~~~~~

Charmcraft 4.4 includes documentation updates for:

- Kubernetes and machine profile setup and test guidance.
- Charm naming and configuration-option usage guidance.
- Web app charm how-to content and migration references.


Fixed bugs and issues
---------------------

The following issues have been resolved in Charmcraft 4.4.0:

- The Poetry plugin was installing the ``python3-poetry-plugin-export`` package
  even when a ``poetry-deps`` part was included.


Known issues
------------

The following issues were reported and are scheduled to be fixed in upcoming
patch releases.

See individual issue links for any mitigations.

- `#2078 <https://github.com/canonical/charmcraft/issues/2078>`__
  ``charmcraft clean`` does not clean all platforms for a charm
- `#1990 <https://github.com/canonical/charmcraft/issues/1990>`__ Cannot stage
  packages with Charmcraft
- `#2492 <https://github.com/canonical/charmcraft/issues/2492>`__ Internal error when
  uploading a charm outside of a project directory
- `#2788 <https://github.com/canonical/charmcraft/issues/2788>`__
  uv plugin fails on core26: dispatch script uses system Python instead of venv


Contributors
------------

We would like to express a big thank you to all the people who contributed to
this release:

:literalref:`@PraaneshSelvaraj <https://github.com/PraaneshSelvaraj>`,
:literalref:`@alithethird <https://github.com/alithethird>`,
:literalref:`@bepri <https://github.com/bepri>`,
:literalref:`@canon-cat <https://github.com/canon-cat>`,
:literalref:`@cmatsuoka <https://github.com/cmatsuoka>`,
:literalref:`@dwilding <https://github.com/dwilding>`,
:literalref:`@erinecon <https://github.com/erinecon>`,
:literalref:`@florentianayuwono <https://github.com/florentianayuwono>`,
:literalref:`@jahn-junior <https://github.com/jahn-junior>`,
:literalref:`@javierdelapuente <https://github.com/javierdelapuente>`,
:literalref:`@lengau <https://github.com/lengau>`,
:literalref:`@medubelko <https://github.com/medubelko>`,
:literalref:`@mr-cal <https://github.com/mr-cal>`,
:literalref:`@smethnani <https://github.com/smethnani>`,
:literalref:`@tigarmo <https://github.com/tigarmo>`,
:literalref:`@tonyandrewmeyer <https://github.com/tonyandrewmeyer>`,
:literalref:`@tromai <https://github.com/tromai>`,
and :literalref:`@upils <https://github.com/upils>`
