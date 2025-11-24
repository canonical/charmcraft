:relatedlinks: https://ubuntu.com/about/release-cycle

.. _explanation-bases:

Bases
=====

Every charm runs on a *base*, which defines the baseline system that the charm runs on.
The systems are generally Ubuntu releases.

The base is declared in the project file by the
:literalref:`base <charmcraft_yaml_base>` or ``platforms`` keys.

.. _explanation-bases-lts-and-interim-bases:

LTS and interim bases
~~~~~~~~~~~~~~~~~~~~~

Ubuntu bases are divided into *LTS* and *interim* bases. An LTS base contains an Ubuntu
LTS release and has a 10-year support window. An interim base contains an interim Ubuntu
release and is supported for nine months.

Interim bases have shorter lifespans and contain upcoming or experimental features. For
charms, they are most suitable for preparing for compatibility with the next Ubuntu LTS
release. As such, they have further limitations that do not apply to LTS bases:

- The packing behaviour of the same :ref:`charmcraft-yaml-file` file may change
  between minor releases. These changes represent changes made to how Charmcraft will
  work when packing for the next LTS release.
- The :literalref:`build-base <charmcraft-yaml-key-build-base>` field is mandatory.
