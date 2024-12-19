(how-to-manage-charm-bundles)=
# How to manage charm bundles

> See first: [`juju` | Bundle](https://juju.is/docs/juju/bundle)

```{important}
Starting with 1 Jan 2025, bundles are being phased out.

```

## Create a bundle

To create a bundle, create a `<bundle>.yaml` file with your desired configuration.

```{tip}

If you don't want to start from scratch, export the contents of your model to a `<bundle>.yaml` file via `juju export-bundle --filename <bundle>.yaml` or download the `<bundle>.yaml` of an existing bundle from Charmhub.

> See more: [Juju | How to compare and export the contents of a model to a bundle](https://juju.is/docs/juju/manage-models#heading--compare-and-export-the-contents-of-a-model-to-a-bundle)


```

> See more: {ref}`file-bundle-yaml`

## Pack a bundle

To pack a bundle,  in the directory where you have your `bundle.yaml` file (and possibly other files, e.g., a `README.md` file), create a `charmcraft.yaml` file suitable for a bundle (at the minimum: `type: bundle`), then run `charmcraft pack` to pack the bundle. The result is a `.zip` file.

> See more: {ref}`ref_commands_pack`


## Publish a bundle on Charmhub

The process is identical to that for a simple charm except that, at the step where you register the name, for bundles the command is `register-bundle`.


> See more: {ref}`publish-a-charm`


