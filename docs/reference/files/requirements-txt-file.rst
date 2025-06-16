.. _requirements-txt-file:


``requirements.txt`` file
=========================

The ``requirements.txt`` file is a standard Python `requirements file
<https://pip.pypa.io/en/stable/reference/pip_install/#requirements-file-format>`_
used to declare and pin the version of any Python packages required by your charm.

For :ref:`ref_commands_init` with the ``kubernetes`` or ``machine`` profile, Charmcraft
doesn't create this file. Instead, Charmcraft creates a dependencies key in the
:ref:`pyproject-toml-file`.

For ``init`` with a 12-factor profile (``django-framework`` and so on), Charmcraft
creates this file and pre-populates it with :external+ops:doc:`Ops <index>`. Any
dependencies specified here will be bundled with the charm when it is built with
:ref:`charmcraft pack <ref_commands_pack>`.
