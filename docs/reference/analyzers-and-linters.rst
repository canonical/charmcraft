.. _charmcraft-analyzers-and-linters:


Analysers and linters
=====================

The following are the different checks that Charmcraft will run
explicitly (when the user executes its ``analyse`` method) or implicitly
(when packing charms).

Any linter or analysis can be set in the
`config <https://juju.is/docs/sdk/charmcraft-config>`_ to be excluded
from the normal execution. Also note that if any linter ends in error it
will block the charm packing (you can pack it anyway using the
``--force`` option).

You can read more about these checks in the `Charmcraft Analyze
Specification <https://discourse.charmhub.io/t/proposal-charmcraft-analyze/4792>`_.


Language attribute
------------------

If through analysis, the charm can be detected as being a Python based
charm, then language shall be set to ``python``. If not, it shall be set
to ``unknown``.

When working with Python, it is possible to only publish byte-code. By
doing so, troubleshooting is a harder task. Charms with Python sources
delivered are preferred.

This attribute meets the requirements to be set to ``python`` when:

-  the charm has a text dispatch which executes a .py
-  the charm has a .py entry point
-  the entry point file is executable


Framework attribute
-------------------

When using ``ops``, it is best to import it from a common path and not
make customisation or package forks from it. If ``ops`` code is detected
in the charm sources, this attribute's value shall be set to
``operator``. If not, the charm may be using the Reactive Framework, and
in this case the attribute value will be ``reactive``. Else, it shall be
set to ``unknown``.

This check hint meets the requirements for ``ops`` when:

- language attribute is set to ``python``
- the charm contains ``venv/ops``
- the charm imports ``ops`` in the entry point

The requirements for the Reactive Framework are:

…or the Reactive Framework is used, if the charm…

- has a metadata.yaml with ``name`` in it
- has a ``reactive/<name>.py`` file that imports ``charms.reactive``
- has a file name that starts with ``charms.reactive-`` inside the
  ``wheelhouse`` directory


Juju metadata linter
--------------------

This linter verifies that the ``metadata.yaml`` file exists and is sane.

The charm is considered to have a valid metadata if the following checks
are true:

- the ``metadata.yaml`` is present
- it is a valid YAML file
- it has at least the following fields: ``name``, ``summary``, and
  ``description``


Juju actions linter
-------------------

*(new in 1.4)*

This linter verifies that the ``actions.yaml`` file, if exists, is a
valid YAML file. The file is optional. The file contents are not
verified.


Juju config linter
------------------

*(new in 1.4)*

This linter verifies that the ``config.yaml`` file, if exists, is valid.
This file is optional.

If the file exists, it is considered valid if the following checks are
true:

- it has the ``options`` key
- it is a dictionary
- each item inside has the mandatory ``type`` key

Check how to `create config.yaml and configure charms
<https://discourse.charmhub.io/t/creating-config-yaml-and-configuring-charms/1039>`_
for more information.


Charm entrypoint linter
-----------------------

*(new in 2.1)*

Check the entry point is correct. Note that even if most modern charms
has a typical ``src/charm.py`` entry point, not all charms have one, as
Juju has different ways to deliver its events.

This linter validates that, if an entry point is called from the
``dispatch`` file, that entry point…

- exists
- is a file
- is executable

The entry point content is *not* validated.
