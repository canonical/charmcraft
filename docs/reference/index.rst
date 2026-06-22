.. _reference:

Reference
=========

References describe the structure and function of the individual components in
Charmcraft.


Commands
--------

Charmcraft is operated from the command line, with a command for each function.

- :ref:`reference-lifecycle-commands`
- :ref:`reference-store-commands`
- :ref:`reference-account-commands`
- :ref:`reference-charm-commands`
- :ref:`reference-library-commands`
- :ref:`reference-extension-commands`
- :ref:`reference-other-commands`


Files
-----

The following files are initialized and packed in a Charmcraft project:

Project file
~~~~~~~~~~~~

- :ref:`charmcraft-yaml-file`


Project information
~~~~~~~~~~~~~~~~~~~

- :ref:`license-file`
- :ref:`readme-md-file`
- :ref:`contributing-md-file`
- :ref:`icon-svg-file`


Python modules
~~~~~~~~~~~~~~

- :ref:`src-charm-py-file`
- :ref:`src-workload-py-file`
- :ref:`libname-py-file`


Dependency management
~~~~~~~~~~~~~~~~~~~~~

- :ref:`pyproject-toml-file`
- :ref:`requirements-txt-file`
- :ref:`uv-lock-file`


Testing
~~~~~~~

- :ref:`tests-integration-conftest-py-file`
- :ref:`tests-integration-test-charm-py-file`
- :ref:`tests-unit-test-charm-py-file`


Plugins and extensions
----------------------

Extensions initialize your project with YAML and Ops catered to supported web
frameworks.

- :ref:`profile`
- :ref:`extensions`
- :ref:`plugins`


.. toctree::
    :hidden:

    analyzers-and-linters
    commands/index
    extensions/index
    files/index
    parts/index
    platforms
    profile
    changelog
