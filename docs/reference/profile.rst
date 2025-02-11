.. _profile:


Profile
=======

In the context of building a charm, in Rockcraft and Charmcraft, a **profile** is a name
you can pass as an argument during rock / charm initialisation that will create all the
usual rock/charm project files in a form customised for a specific purpose -- i.e., for
a Kubernetes charm, for a Kubernetes charm for a Flask application etc. -- in order to
speed up development.

The customisation often takes the shape of a specific :ref:`extensions` in the charm's
project file.

    See more: `How to set up a charm
    project <https://juju.is/docs/sdk/set-up-a-charm-project>`_
