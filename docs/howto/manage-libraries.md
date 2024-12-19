(manage-libraries)=
# How to manage libraries
> See first: [`juju` | Library]()


## Initialise a library

> See also: {ref}``charmcraft create-lib` <command-charmcraft-create-lib>`

In your charm's root directory, run `charmcraft create-lib`:

```text
# Initialise a charm library named 'demo'
$ charmcraft create-lib demo
```

```{note}

Before creating a library, you must first register ownership of your charm’s name. See more: {ref}`publish-a-charm`.

```
    
This will create a template file at `$CHARMDIR/lib/charms/demo/v0/demo.py`.


> See more: {ref}`ref_commands_create-lib`, {ref}`file-libname-py`

Edit this file to write your library.

```{important}

A library must comprise a single Python file. If you write a library that feels too "big" for a single file, it is likely that the library should be split up, or that you are actually writing a full-on charm.

```

> See next: [`ops` | Manage libraries]()


(publish-a-library)=
## Publish a library on Charmhub


```{caution}

On Charmhub, a library is always associated with the charm that it was first created for. When you publisht it to Charmhub, it's published to the page of that charm. To be able to publish it, you need to be logged in to Charmhub as a user who owns the charm (see more: {ref}`publish-a-charm`) or as a user who is registered as a contributor to the charm (a status that can be requested via [Discourse](https://discourse.charmhub.io/).

```

To publish a library on Charmhub, in the root directory of the charm that holds the library, run `charmcraft publish-lib` followed by the full library path on the template `charms.<charm-name>.v<api-version>.<library-name>`. For example:

```text
$ charmcraft publish-lib charms.demo.v0.demo
Library charms.demo.v0.demo sent to the store with version 0.1
```

> See more: {ref}`ref_commands_publish-lib`

This will upload the library's content to Charmhub.

To update the library on Charmhub, update the `LIBAPI`/`LIBPATCH` metadata fields inside the library file, then repeat the publish procedure.

```{caution} **About the metadata fields:**

Most times it is enough to just increment `LIBPATCH` but, if you're introducing breaking changes, you must work with the major API version.

Additionally, be mindful of the fact that users of your library will update it automatically to the latest PATCH version with the same API version. To avoid breaking other people's library usage, make sure to increment the `LIBAPI` version but reset `LIBPATCH` to `0`. Also,  before adding the breaking changes and updating these values, make sure to copy the library to the new path; this way you can maintain different major API versions independently, being able to update, for example, your v0 after publishing v1. See more: {ref}`file-libname-py`.
```

> See more: {ref}`ref_commands_publish-lib`


To share your library with other charm developers, navigate to the host charm's Charmhub page, go to Libraries tab, then copy and share the URL at the top of the page.


## View the libs published for a charm

The easiest way to find an existing library for a given charm is via `charmcraft list-lib`, as shown below. This will query Charmhub and show which libraries are published for the specified charm, along with API/patch versions.

    jdoe@machine:/home/jane/autoblog$ charmcraft list-lib blogsystem
    Library name    API    Patch
    superlib        1      0

The listing will not show older API versions; this ensures that new users always start with the latest version. 

Another good way to search for libraries is to explore the charm collection on [Charmhub](https://charmhub.io/).

> See more: {ref}``charmcraft list-lib` <command-charmcraft-list-lib>`


## Use a library

In your charm's `charmcraft.yaml`, specify the `charm-libs` key with the desired libraries.

> See more: {ref}`file-charmcraft-yaml-charm-libs`


In your charm's root directory, run `charmcraft fetch-libs`. Charmcraft will download the libraries to your charm's directory.

> See more: {ref}`ref_commands_fetch-libs`


To use a library in your `src/charm.py`, import it using its fully-qualified path minus the `lib` part:

```python
import charms.demo.v0.demo
```

To update your lib with the latest published version, repeat the process.



