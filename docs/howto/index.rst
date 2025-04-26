.. _how-to-guides:

How-to guides
=============

Charmcraft's how-to guides provide comprehensive, step-by-step instructions for the most
common charm development tasks--from initializing a project to publishing it on
Charmhub.


Install Charmcraft
------------------

Charmcraft can be installed in just a few short steps, regardless of if you are
installing on Linux, macOS, or an isolated environment. Specific instructions for
installing Charmcraft and setting up your build container can be found in the following
guide:

.. toctree::
    :maxdepth: 2

    manage-charmcraft


Craft charms
------------

Nearly every aspect of your charm can be configured to suit the needs of the application
you are charming. Once you initialize the project with either the default profile or one
of Charmcraft's web app extensions, you can modify a charm's YAML and Ops-powered Python
to include any necessary libraries, parts, or other assets your application may require.

.. toctree::
    :maxdepth: 2

    manage-charms
    Manage builds <build-guides/index>
    Manage 12-factor app charms <manage-web-app-charms/index>
    manage-parts
    manage-resources
    manage-libraries
    manage-extensions
    manage-bundles


Publish charms and manage releases
----------------------------------

When you're ready to share your charm, Charmcraft provides commands to register its
name, publish it to Charmhub, and manage subsequent releases.

.. toctree::
    :maxdepth: 2

    manage-the-current-charmhub-user
    manage-names
    manage-icons
    manage-revisions
    manage-tracks
    manage-channels


Migrate between plugins
-----------------------

Certain charms may benefit from using a plugin other than the default Charm plugin. For
instructions on migrating away from the default Charm plugin, refer to the appropriate
migration guide for your charm:

.. toctree::
    :maxdepth: 2

    migrate-plugins/index
