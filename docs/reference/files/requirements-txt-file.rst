.. _requirements-txt-file:


``requirements.txt`` file
=========================

The ``requirements.txt`` file is a standard Python `requirements file
<https://pip.pypa.io/en/stable/reference/pip_install/#requirements-file-format>`_
that declares and pins the Python packages that the charm needs.

Charmcraft doesn't create this file for the Kubernetes and machine profiles. They use a
:ref:`pyproject-toml-file` instead.

When a charm is initialized with a 12-factor app profile, Charmcraft creates this file
and pre-populates it with :external+ops:doc:`Ops <index>`. Any dependencies specified
here are bundled with the charm when it's built with
:ref:`charmcraft pack <ref_commands_pack>`.
