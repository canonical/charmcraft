.. _config-yaml-file:

``config.yaml`` file
====================

.. important::

    Starting with Charmcraft 2.5, this file is created automatically from information
    you provide in the :ref:`charmcraft-yaml-file`. For backwards
    compatibility, Charmcraft will continue to allow the use of this file, but you may
    not duplicate keys across the two files.

The ``config.yaml`` in a charm's root directory is an optional file that may be used
to define the configuration options supported by a charm.

The definitions are collected under a single YAML map called ``options``. The rest of
this doc gives details about this map.


``options``
-----------

**Status:** Required if the file exists.

**Purpose:** The ``options`` key allows charm authors to declare the configuration
options that they have defined for a charm.

**Structure:** The key contains a definition block for each option, where each
definition consists of a charm-author-defined option name and an option description,
given in 3 fields -- type, description, and default value:

.. code-block:: yaml

    options:
      <option name>:
        default: <default value>
        description: <description>
        type: <type>
      <option name>:
        default: <default value>
        description: <description>
        type: <type>
      ...

In some cases, it may be awkward or impossible to provide a sensible default.
In these cases, ensure that it is noted in the description of the configuration
option. It is acceptable to provide ``null`` configuration defaults or omit the
``default`` field.

.. collapse:: Example

    .. code-block:: yaml

        options:
          name:
            default: Wiki
            description: The name, or Title of the Wiki
            type: string
          skin:
            default: vector
            description: skin for the Wiki
            type: string
          logo:
            default:
            description: URL to fetch logo from
            type: string
          admins:
            default:
            description: Comma-separated list of admin users to create: user:pass[,user:pass]+
            type: string
          debug:
            default: false
            type: boolean
            description: turn on debugging features of mediawiki
