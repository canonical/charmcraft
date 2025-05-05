.. _icon-svg-file:

``icon.svg`` file
=================

``icon.svg`` is the icon for your charm displayed on your charm's page on `Charmhub`_.


Requirements
------------

- The file must have this exact name: ``icon.svg``.
- The canvas size must be 100x100 pixels.
- The icon must consist of a circle with a flat color and a logo -- any other detail
  is up to you, but it's a good idea to also conform to best practices.


Best practices
--------------

- Icons should have some padding between the edges of the circle and the logo.
- Icons should not be overly complicated. Charm icons are displayed in various sizes
  (from 160x160 to 32x32 pixels) and they should be always legible.
- Symbols should have a similar weight on all icons: Avoid too thin strokes and use
  the whole space available to draw the symbol within the limits defined by the
  padding. However, if the symbol is much wider than it is high, it may overflow onto
  the horizontal padding area to ensure its weight is consistent.
- Do not use glossy materials unless they are parts of a logo that you are not
  allowed to modify.

.. tip::

    In `Inkscape <https://snapcraft.io/inkscape>`_, the 'Icon preview' tool can help
    you check the sharpness of your icons at small sizes.


Examples
~~~~~~~~

- `OpenSearch <https://charmhub.io/opensearch>`_
- `Traefik (Kubernetes) <https://charmhub.io/traefik-k8s>`_


Including the file
------------------

If your file is not in your project directory but not included in the charm, you can
use the :ref:`craft_parts_dump_plugin` to include this file in your charm.

.. collapse:: Example

    This example is the :ref:`charmcraft-yaml-key-parts` key of a project file that uses
    the :ref:`craft_parts_poetry_plugin` to build a charm, augmented to add the charm's
    ``icon.svg`` file.

    .. code-block:: yaml

        parts:
          my-charm:
            plugin: poetry
            source: .
          icon:
            plugin: dump
            source: .
            stage:
              - icon.svg
