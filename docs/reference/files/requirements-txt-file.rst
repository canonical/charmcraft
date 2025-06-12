.. _requirements-txt-file:


``requirements.txt`` file
=========================

The ``requirements.txt`` file is a standard Python `requirements file
<https://pip.pypa.io/en/stable/reference/pip_install/#requirements-file-format>`_
used to declare and pin the version of any Python libraries required by a charm in
production. This will be pre-populated with :literalref:`ops`. Any dependencies
specified here will be bundled with the charm when it is built with
:ref:`charmcraft pack <ref_commands_pack>`.

Charmcraft automatically creates this file for the 12-factor profiles,
``django-framework`` and so on. For the ``kubernetes`` and ``machine`` profiles,
Charmcraft creates a dependencies key in the :ref:`pyproject-toml-file` instead.

.. _ops: https://ops.readthedocs.io/en/latest/
