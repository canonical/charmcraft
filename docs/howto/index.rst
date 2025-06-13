.. _how-to-guides:

How-to guides
=============

Charmcraft's how-to guides provide comprehensive, step-by-step instructions for the most
common charm development tasks -- from initializing a project to publishing it on
Charmhub.


Install Charmcraft
------------------

Charmcraft can be installed in just a few short steps, regardless of if you are
installing on Linux, macOS, or an isolated environment. Specific instructions for
installing Charmcraft and setting up your build container can be found in
:ref:`manage-charmcraft`.


Craft charms
------------

Nearly every aspect of your charm can be configured to suit the needs of the application
you are charming. Once you initialize the project with either the default profile or one
of Charmcraft's web app extensions, you can modify a charm's YAML and Ops-powered Python
to include any necessary libraries, parts, or other assets your application may require.

* :ref:`manage-charms`
* :ref:`Manage builds <howto-build-guides>`
* :ref:`Manage 12-factor app charms <manage-12-factor-app-charms>`
* :ref:`manage-parts`
* :ref:`manage-resources`
* :ref:`manage-libraries`
* :ref:`manage-extensions`


Publish charms and manage releases
----------------------------------

When you're ready to distribute your charm, Charmcraft provides commands to register it,
publish it to Charmhub, and manage its releases.

* :ref:`manage-the-current-charmhub-user`
* :ref:`manage-names`
* :ref:`manage-icons`
* :ref:`manage-charm-revisions`
* :ref:`manage-tracks`
* :ref:`manage-channels`


Migrate between plugins
-----------------------

Certain charms may benefit from using a plugin other than the default Charm plugin. For
instructions on migrating away from the default Charm plugin, refer to the appropriate
migration guide for your charm:

* :ref:`howto-migrate-to-poetry`
* :ref:`howto-migrate-to-python`
* :ref:`howto-migrate-to-uv`


.. toctree::
   :hidden:

   manage-charmcraft
   manage-charms
   Manage 12-factor app charms <manage-web-app-charms/index>
   manage-extensions
   manage-resources
   manage-libraries
   manage-parts
   manage-the-current-charmhub-user
   manage-names
   manage-revisions
   manage-channels
   manage-tracks
   manage-icons
   Migrate plugins <migrate-plugins/index>
   Build <build-guides/index>
