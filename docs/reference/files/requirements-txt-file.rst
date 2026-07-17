.. _requirements-txt-file:


``requirements.txt`` file
=========================

Charmcraft only creates this file for 12-factor app profiles targeting Ubuntu 24.04 LTS
or lower. Other profiles use a :ref:`pyproject-toml-file` instead.

This file is a standard Python `requirements file
<https://pip.pypa.io/en/stable/reference/requirements-file-format>`__ that declares and
pins the Python packages that the charm needs.

This file is pre-populated with :external+ops:doc:`Ops <index>`. Any dependencies
specified here are bundled with the charm when it's built with
:ref:`charmcraft pack <ref_commands_pack>`.
