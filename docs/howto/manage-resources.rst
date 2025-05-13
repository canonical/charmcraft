.. _manage-resources:

Manage resources
================

    See first: :external+juju:ref:`Juju | Resource (charm) <charm-resource>`,
    :external+juju:ref:`Juju | Manage resources <manage-charm-resources>`


Declare a resource
------------------

To declare a resource required by your charm, set the
:ref:`charmcraft-yaml-key-resources` key in its project file.

    See more: :ref:`charmcraft-yaml-key-resources`

    See next: :external+ops:ref:`Ops | Manage resources <manage-resources>`

.. tip::

    During development, it may be useful to specify the resource at deploy time to
    facilitate faster testing without the need to publish a new charm/resource in
    between minor fixes. For example, assuming the resource is a ``/tmp/somefile.txt``
    file, you could pack and the deploy with ``juju deploy … --resource``:

.. code-block:: bash

    echo "TEST" > /tmp/somefile.txt
    charmcraft pack
    juju deploy ./my-charm.charm --resource my-resource=/tmp/somefile.txt


.. _publish-a-resource:

Publish a resource on Charmhub
------------------------------

.. note::

    You must have already published the charm. See more: :ref:`publish-a-charm`.

To publish a resource on its charm's Charmhub page, run ``charmcraft upload-resource``
followed by the name of the charm, the name of the resource (cf. ``charmcraft.yaml``),
and ``--filepath=<path to file resource>`` / ``--image=<OCI image>``. For example:

.. note::

    The option ``--image`` must indicate an OCI image's digest, being it in the short or
    long form (e.g.: ``70aa8983ec5c`` or
    ``sha256:64aa8983ec5cea7bc143af18829836914fa405184d56dcbdfd9df672ade85249``). When
    using the "short form" of the digest, the image needs to be present locally so its
    proper ID (the "long form") can be retrieved.

.. code-block:: bash

   charmcraft upload-resource my-super-charm someresource --filepath=/tmp/superdb.bin

.. terminal::

    Revision 1 created of resource 'someresource' for charm 'my-super-charm'

.. code-block:: bash

    charmcraft upload-resource my-super-charm redis-image --image=sha256:64aa8983ec5cea7bc143af18829836914fa405184d56dcbdfd9df672ade85249

.. terminal::

   Revision 1 created of resource 'redis-image' for charm 'my-super-charm'

Charmcraft will first check if that specific image is available in Canonical's Registry,
and just use it if that's the case. If not, it will try to get it from the developer's
local OCI repository (needs ``dockerd`` to be installed and running), push it to the
Canonical's Registry, and then use it. Either way, when the upload has completed, you
end up with a resource revision.

To update a pre-uploaded resource, run the ``upload-resource`` command again. The result
will be a new revision.

    See more: :ref:`ref_commands_upload-resource`

.. admonition:: Best practice
    :class: hint

    For resources that are binary files, provide binaries for all the CPU
    architectures you intend to support.


View all the resources published on Charmhub
--------------------------------------------

To view all the resources published on Charmhub for a charm, run ``charmcraft
resources`` followed by the charm name:

.. important::

    If you're not logged in to Charmhub, the command will open up a web browser and ask
    you to log in.

.. code-block:: bash

    charmcraft resources mycharm

..

    See more: :ref:`ref_commands_resources`


.. _manage-resource-revisions:

Manage resource revisions
-------------------------


List all the available resource revisions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To view all the revisions for a resource associated with a charm you've uploaded to
Charmhub, run ``charmcraft resource-revisions`` followed by the charm name and the
resource name. For example:

.. code-block:: bash

    charmcraft resource-revisions mycharm myresource

..

    See more: :ref:`ref_commands_resource-revisions`


Set the architectures for a resource revision
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To set the architectures for a revision of a resource associated with a charm you've
uploaded to Charmhub, run ``charmcraft set-resource-architectures`` followed by the name
of the charm, the name of the resource, and the architecture(s), using the
``--resources`` flag to specify the target resource revision. For example:

.. code-block:: bash

    charmcraft set-resource-architectures mycharm myresource --revision=1 arm64,armhf

..

    See more: :ref:`ref_commands_set-resource-architectures`
