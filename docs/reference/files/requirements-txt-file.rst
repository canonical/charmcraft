.. _requirements-txt-file:


``requirements.txt`` file
=========================

The ``requirements.txt`` file is a standard Python `requirements file
<https://pip.pypa.io/en/stable/reference/pip_install/#requirements-file-format>`_
used to declare and pin the version of any Python libraries required by a charm in
production. This will be pre-populated with :literalref:`ops`. Any dependencies
specified here will be bundled with the charm when it is built with
:ref:`charmcraft pack <ref_commands_pack>`.

.. _ops: https://ops.readthedocs.io/en/latest/
