.. _manage-the-current-charmhub-user:

Manage the current Charmhub user
================================

    See first: `Charmhub`_


Log in to Charmhub
------------------


Local environments
~~~~~~~~~~~~~~~~~~

To log in to Charmhub, run ``charmcraft login``:

.. code-block:: bash

   charmcraft login

.. terminal::

    Opening an authorization web page in your browser.
    If it does not open, please open this URL:
    ...

..

   See more: :ref:`ref_commands_login`


Remote environments
~~~~~~~~~~~~~~~~~~~

   Introduced in Charmcraft 1.3

When working locally with Charmcraft, the developer will use ``charmcraft login`` to get
authentication tokens from Charmhub, which would be stored in the local keyring and used
on all operations that need them.

This is fine for local environments, but for remote ones (e.g. a CI/CD system) on one
hand it's desirable to not login using the standard method (a browser opening an
authentication web page to insert user, password, and *2FA*), and on the other hand the
authentication tokens should be limited in different ways.

The alternative login method is implemented through the ``CHARMCRAFT_AUTH`` environment
variable, which needs to be set to useful credentials (which are obtained using the
``--export`` option, see below).

If that variable is set Charmcraft will use it for all operations that needs
authentication against Charmhub. Note that in this case the ``login`` and ``logout``
commands can not be used.

To obtain credentials to be used in ``CHARMCRAFT_AUTH``, the ``login`` command has the
``--export`` option, which accepts a file path. If specified, it will override the
regular behaviour of storing the credentials in the user's keyring, and those will be
exported to the given file path. The content of this file is what should be used
verbatim in the environment variable.

As mentioned at the beginning, it's also a good idea to use restricted credentials in a
remote system. For this situation, the Charmcraft's ``login`` command provides different
options to attenuate the obtained authentication tokens:

- ``--charm``: the charm name on which the permission will apply (can be specified
  multiple times)
- ``--bundle``: the bundle name on which the permission will apply (can be specified
  multiple times)
- ``--permission``: what action can be done on the specified package(s) (see below for a
  list; can be specified multiple times)
- ``--channel``: the channel on which the package can be released (can be specified
  multiple times)
- ``--ttl``: the time, in seconds, that the granted token will be useful (defaults to 30
  days)

All these indications are optional, and default to no restrictions applied on each
category (except indicated the time-to-live, as indicated above). Note also that these
restrictions can only be used if the credentials are exported to a file with the
``--export`` option.

The available permissions are:

- ``account-register-package``: register/request a new package name
- ``account-view-packages``: list packages owned by the account or for which this
  account has collaborator rights
- ``package-manage``: meta permission that includes all the ``package-manage-*`` ones
- ``package-manage-acl``: add/invite/remove collaborators
- ``package-manage-metadata``: edit metadata, add/remove media, etc.
- ``package-manage-releases``: release revisions and close channels
- ``package-manage-revisions``: upload new blobs, check for upload status
- ``package-view``: meta permission that includes all the ``package-view-*`` ones
- ``package-view-acl``: list the collaborators for a package, return privacy settings
- ``package-view-metadata``: view the metadata for a package, including media
- ``package-view-metrics``: view the metrics of a package
- ``package-view-releases``: list the current releases (channel map) and the history of
  releases for a package
- ``package-view-revisions``: list the existing revisions for a package, along with
  status information

So, an example sequence for requesting/using credentials to set up a CI/CD system that
will push and release a charm could be:

- Get the specific credentials in a file:

  .. code-block:: bash

        charmcraft login --export=secrets.auth --charm=my-super-charm --permission=package-manage --channel=edge --ttl=2592000

- Test that all is fine; for this get the content:

  .. code-block:: bash

        CHARMCRAFT_AUTH=`cat test1`
        charmcraft whoami

  .. terminal::

        name: J. Doe
        username: jdoe-superdev
        id: VTLZAToLcdaIPtisVBjfiQYCXbpKwbCc
        charms:
        - my-super-charm
        permissions:
        - package-manage
        channels:
        - edge
        time to live (s): 2592000

- To use this authorization token on a CI/CD system, set the environment variable
  CHARMCRAFT_AUTH with the content of ``secrets.auth`` file, and use Charmcraft as
  normal:

    .. code-block:: bash

        export CHARMCRAFT_AUTH=<a long chunk of chars>
        ...
        charmcraft upload my-super-charm.charm --release edge


Check the currently logged in user
----------------------------------

To check the currently logged in user, run ``charmcraft whoami``.

    See more: :ref:`ref_commands_whoami`


Log out of Charmhub
-------------------

To log out of Charmhub, run ``charmcraft logout``.

    See more: :ref:`ref_commands_logout`
