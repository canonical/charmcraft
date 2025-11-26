:relatedlinks: https://ubuntu.com/about/release-cycle

.. _explanation-bases:

Bases
=====

A charm runs on a baseline software system, known as its *base*.
The systems are most commonly Ubuntu releases.

The base is declared in the project file by the
:literalref:`base <charmcraft_yaml_base>` or ``platforms`` keys.

.. _explanation-bases-lts-and-interim-bases:

LTS and interim bases
~~~~~~~~~~~~~~~~~~~~~

Ubuntu bases are divided into *LTS* and *interim* bases. An LTS base contains an Ubuntu
LTS release and has a 10-year support window. An interim base contains an interim Ubuntu
release and is supported for nine months.

Interim bases have shorter lifespans and contain upcoming or experimental features. For
charms, they are most suitable for compatibility testing for the next Ubuntu LTS
release. As such, they have special limitations:

- Between minor releases of Charmcraft, repacking a charm might produce differences in
  the artifact because of changes to the :ref:`charmcraft.yaml <charmcraft-yaml-file>`
  schema. These differences are an accurate preview of how Charmcraft will pack the
  project in the next Ubuntu LTS release.
- The :literalref:`build-base <charmcraft-yaml-key-build-base>` key is mandatory.
