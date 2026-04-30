.. _how-to-guides:

How-to guides
=============

These pages provide directions for completing tasks and solving problems with
Charmcraft.


Install Charmcraft
------------------

Charmcraft can be installed in just a few short steps, regardless of if you are
installing on Linux, macOS, or an isolated environment.

- :ref:`manage-charmcraft`


Craft
-----

Once you initialize the project, you can modify a charm's YAML and Ops-powered Python to
include any necessary libraries, parts, or other assets your application may require.

- :ref:`manage-charms`
- :ref:`Manage 12-factor app charms <manage-12-factor-app-charms>`
- :ref:`select-platforms`
- :ref:`manage-parts`
- :ref:`manage-resources`
- :ref:`manage-libraries`
- :ref:`manage-extensions`


Publish and release
-------------------

When you're ready to distribute your charm, Charmcraft provides commands to register it,
publish it to Charmhub, and manage its releases.

- :ref:`manage-the-current-charmhub-user`
- :ref:`manage-names`
- :ref:`manage-icons`
- :ref:`manage-charm-revisions`
- :ref:`manage-tracks`
- :ref:`manage-channels`


Migrate between plugins
-----------------------

For instructions on migrating away from the default Charm plugin, refer to the
appropriate migration guide for your charm:

- :ref:`howto-migrate-to-poetry`
- :ref:`howto-migrate-to-python`
- :ref:`howto-migrate-to-uv`


Migrate bases
-------------

When a new Ubuntu base becomes available, refer to the appropriate migration guide to
update a charm to the new base:

- :ref:`howto-change-to-ubuntu-26-04`


.. toctree::
    :hidden:

    manage-charmcraft
    manage-charms
    Manage 12-factor app charms <manage-web-app-charms/index>
    select-platforms
    manage-extensions
    manage-resources
    manage-libraries
    manage-parts
    shared-cache
    pack-a-hooks-based-charm-with-charmcraft
    pack-a-reactive-charm-with-charmcraft
    manage-the-current-charmhub-user
    manage-names
    manage-revisions
    manage-channels
    manage-tracks
    manage-icons
    Migrate plugins <migrate-plugins/index>
    Migrate bases <migrate-bases/index>
