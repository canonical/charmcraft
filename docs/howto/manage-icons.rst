.. _manage-icons:

Manage icons
============

Learn about icon requirements and best practices
------------------------------------------------

  See more: :ref:`icon-svg-file`

Create an icon
--------------

Before you start you will need:

-  A vector graphic editor. We strongly recommend the cross-platform and
   most excellent `Inkscape <http://www.inkscape.org>`__ for all your
   vector graphic needs.
-  `The template
   file. <https://assets.ubuntu.com/v1/fc0260eb-icon.svg>`__
   (right-click > Save link as…)
-  An existing logo you can import, or the ability to draw one in
   Inkscape.

Once you have those, fire up Inkscape and we can begin!

1. Open the template
~~~~~~~~~~~~~~~~~~~~

From Inkscape load the ``icon.svg`` file. Select the Layer called
“Background Circle”, either from the drop down at the bottom, or from
the layer dialog.

.. figure:: https://assets.ubuntu.com/v1/067f88a5-manage-icons-create-1.png
   :alt: Open the template

   Open the template

3. Add colour
~~~~~~~~~~~~~

In the menu, select **Object** and then **Fill and Stroke** to adjust
the colour.

.. figure:: https://assets.ubuntu.com/v1/0bff03c4-manage-icons-create-2.png
   :alt: Add color


2. Draw something
~~~~~~~~~~~~~~~~~

Draw your shape within the circle. If you already have a vector logo,
you can import it and scale it within the guides. Inkscape also has
plenty of drawing tools for creating complex images.

If you import a bitmap image to use, be sure to convert it into a vector
file and delete the bitmap.

.. figure:: https://assets.ubuntu.com/v1/2ef5c7f5-manage-icons-create-3.png
   :alt: Draw something

*Cloud icon: “Cloud by unlimicon from the Noun Project” [CC BY]*

Validate an icon
----------------

You can validate your icon at
`charmhub.io/icon-validator <https://charmhub.io/icon-validator>`_. The
page checks the most basic issues that prevent icons working.

.. figure:: https://assets.ubuntu.com/v1/cc23c12a-manage-icons-validate.png
   :alt: Validate

Add an icon to its charm's Charmhub page
----------------------------------------

To add the icon to the charm's Charmhub page, save it as ``icon.svg``, place it
in the root directory of the charm, and then publish the charm to a channel of the
form ``<track>/stable`` (e.g., ``latest/stable``). Note that the track that you publish
the icon to needs to be the default track for the icon to be displayed on Charmhub.
Please raise a
`CharmHub request <https://discourse.charmhub.io/c/charmhub-requests/46>`_
on Discourse to set a track as the default track.

.. note::
   That is because Charmhub only updates the metadata for a charm on stable channel
   releases (`by design
   <https://snapcraft.io/blog/better-snap-metadata-handling-coming-your-way-soon>`_).
   So either release the revision with the icon to a ``stable`` channel and then
   roll it back, or wait until your charm is ready for a "stable" ``stable`` release.

..

   See more: :ref:`publish-a-charm`
