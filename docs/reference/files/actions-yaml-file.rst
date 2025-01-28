.. _actions-yaml-file:

``actions.yaml`` file
=====================

.. important::
    Starting with Charmcraft 2.5, this file is created automatically from information
    you provide in the :ref:`charmcraft-yaml-file`. For backwards
    compatibility, Charmcraft will continue to allow the use of this file, but you may
    not duplicate keys across the two files.


The ``actions.yaml`` file in a charm project is an optional file that may be used to
define the :external+juju:ref:`actions <action>` supported by the charm.

The file contains a YAML map for each defined action. Each map starts with an
``<action name>`` key. The rest of this document gives details about this key.


.. collapse:: Expand to view the full spec at once

   .. code-block:: yaml

      <action 1>:
        description: <string>
        parallel: <boolean>
        execution-group: <string>
        params:
          <param 1>: <JSON Schema>
          <param 2>: <JSON Schema>
          …
        <other keys>
      <action name 2>:
        …


.. collapse:: Expand to view a simple example

   The following shows a simple example of an ``actions.yaml`` file, defining three
   actions named ``pause``, ``resume``, and ``snapshot``. The ``snapshot`` action takes
   a single string parameter named ``outfile``:

   .. code-block:: yaml

       pause:
         description: Pause the database.
         additionalProperties: false
       resume:
         description: Resume a paused database.
         additionalProperties: false
       snapshot:
         description: |
           Take a snapshot of the database.
           Descriptions can be extended to multiple lines.
         params:
           outfile:
             type: string
             description: The filename to write to.
         additionalProperties: false

.. collapse:: Expand to view a complex example

    The following example showcases a more complex configuration file that uses
    features of JSON schema to define detailed options. It also makes the
    ``filename`` field mandatory:

    .. code-block:: yaml

        snapshot:
          description: Take a snapshot of the database.
          params:
            filename:
              type: string
              description: The name of the snapshot file.
            compression:
              type: object
              description: The type of compression to use.
              properties:
                kind:
                  type: string
                  enum: [gzip, bzip2, xz]
                quality:
                  description: Compression quality
                  type: integer
                  minimum: 0
                  maximum: 9
          required: [filename]
          additionalProperties: false

    The above action could be run with
    ``juju run <unit> snapshot filename=out.tar.gz compression.kind=gzip``.
    This demonstrates how to pass objects with the CLI.


``<action>``
------------

**Status:** Required, one for each action.

**Purpose:** To define an action supported by the charm. The information stated here
will feed into ``juju actions <charm>`` and ``juju run <charm unit> <action>``,
helping a Juju end user know what actions and action parameters are defined for the
charm.

    See more:
    :external+juju:ref:`Juju | juju actions <command-juju-actions>`,
    :external+juju:ref:`Juju | juju run <command-juju-run>`

**Structure:**

*Name:* The name of the key (``<action name>``) is defined by the charm
author. It must be a valid Python :external+python:ref:`identifier <identifiers>`
that does not collide with Python :external+python:ref:`keywords <keywords>`
except that it may contain hyphens (which will be mapped to underscores in the Python
event handler).

*Type:* Map.

*Value:* A series of keys-value pairs corresponding to action metadata and to parameter
validation, defined as follows:

.. code-block:: yaml

   <action>:
     # Action metadata keys
     description: <string>
     parallel: <boolean>
     execution-group: <string>
     # Parameter validation keys, cf. JSON Schema object
     params:
       <param 1>: <...>
       <param 2>: <...>
       …
     <other key-value pairs>

.. important::

    As you can see, the action definition schema defines a typical JSON Schema object,
    except:

    1. It includes some new keys specific to actions: ``description``, ``parallel``,
       and ``execution-group``.
    2. It does not currently support the JSON Schema concepts ``$schema`` and ``$ref``.
    3. The ``additionalProperties`` and ``required`` keys from JSON Schema can be used
       at the top-level of an action (adjacent to ``description`` and ``params``), but
       also used anywhere within a nested schema.

        See more: `JSON schema <https://www.learnjsonschema.com/>`_


``<action>.description``
------------------------

**Status:** Optional but recommended.

**Purpose:** To describe the action.

**Structure:** *Type:* String.


``<action>.execution-group``
----------------------------

**Status:** Optional, defaults to ``""`` (empty string).

**Purpose:** Sets in which execution group to place tasks created by this action.

**Structure:** *Type:* String.

   See more: :external+juju:ref:`Juju | juju run <command-juju-run>`,
   :external+juju:ref:`Juju | Task <task>`

``<action>.parallel``
---------------------

**Status:** Optional, defaults to false.

**Purpose:** Sets whether to allow tasks created by this action to execute in parallel.

**Structure:** *Type:* Boolean.

   See more: :external+juju:ref:`Juju | juju run <command-juju-run>`,
   :external+juju:ref:`Juju | Task <task>`

``<action>.params``
-------------------

**Status:** Optional.

**Purpose:** To define the fixed parameters for the action. Fixed parameters are those
with a name given by a fixed string.

**Structure:**

*Type:* Map.

*Value:* One or more key-value pairs where each key is a parameter name and each value
is the YAML equivalent of a valid `JSON Schema`_. The entire
map of ``<action>.params`` is inserted into the action schema object as a “properties”
validation keyword. The Juju CLI may read the “description” annotation keyword of each
parameter to present to the user when describing the action.

``<action>.*``
--------------

**Status:** Optional.

**Purpose:** To define additional validation or annotation keywords of the action
schema object.

**Structure:**

*Name:* A valid keyword of a `JSON Schema`_ object instance that will be merged into the
action schema object. For example, ``additionalProperties`` or ``required``.

*Type:* Various.

Juju will parse additional keywords as a `JSON Schema`_ with some limitations:

- The ``$schema`` and ``$ref`` keys are prohibited
- `params <action-params>`_ is treated as a single top-level JSON Schema instance of
  type `object <jsonschema-object>`_ with a map of ``properties`` corresponding to
  each key in ``params``. This instance is what Juju uses to validate user input.

It is highly recommended to provide ``additionalProperties: false`` to avoid user
frustration with accidental typos.

.. _JSON-Schema: https://json-schema.org/
.. _jsonschema-object: https://json-schema.org/understanding-json-schema/reference/object.html
