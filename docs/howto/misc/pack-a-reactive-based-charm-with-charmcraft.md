(pack-a-reactive-based-charm-with-charmcraft)=
# How to pack a reactive-based charm with Charmcraft

> See also:
> - {ref}`How to set up a charm project <how-to-set-up-a-charm-project>`
> - {ref}`How to pack your charm using Charmcraft <how-to-pack-a-charm>`
> - {ref}`About charm types, by creation type <charm-taxonomy>`


Suppose you want a reactive-based charm. Such a charm cannot be initialised with Charmcraft. However, it can be *packed* with Charmcraft. This document shows you how.

```{note}

 Introduced in Charmcraft 1.4.

```
```{note}

The reactive way to write a charm represents an old standard. The recommended way to create a charm now is using {ref}`Charmcraft <charmcraft-charmcraft>` and {ref}`Ops <ops-ops>`.

```

To pack a reactive-based charm with Charmcraft, in the charm directory  create a `charmcraft.yaml` file with the part definition for a reactive-based charm:

```yaml
type: "charm"
bases:
  - build-on:
      - name: "ubuntu"
        channel: "20.04"
    run-on:
      - name: "ubuntu"
        channel: "20.04"
parts:
  charm:
    source: .
    plugin: reactive
    build-snaps: [charm]
```

Done. Now you can go ahead and pack your reactive-based charm with Charmcraft in the usual way using `charmcraft pack`.

<!--
**Step 1: Setting up a reactive charm project**

Install the required tools 

```
snap install charm --classic
```

And create a new project:

```
charm create tutorial
```

Change to the `tutorial` directory and modify `metadata.yaml` so it looks like the following:

```yaml
name: tutorial
summary: test
maintainer: maintainer <maintainer@maintenance.com>
description: |
    Longer description than summary
tags:
  - misc
subordinate: false
series: [focal]
```

**Step 2: Create charmcraft.yaml**

Create a `charmcraft.yaml` file with the part definition for the reactive-based charm. The file contents should be:

```yaml
type: "charm"
bases:
  - build-on:
      - name: "ubuntu"
        channel: "20.04"
    run-on:
      - name: "ubuntu"
        channel: "20.04"
parts:
  charm:
    source: .
    plugin: reactive
    build-snaps: [charm]
```

**Step 3: Pack**

To create the charm run the following:

```
$ charmcraft pack
```

The final output should look something like the following:

```
Charms packed:
    tutorial_ubuntu-20.04-amd64.charm
```

**Step 4: Inspecting**

The charm can be analyzed to verify everything is correct, to do so run:

```
$ charmcraft analyze tutorial_ubuntu-20.04-amd64.charm
```

The result should look something like the following:

```
Attributes:                                                                                                      
- language: unknown (https://juju.is/docs/sdk/charmcraft-analyze#heading--language)                              
- framework: reactive (https://juju.is/docs/sdk/charmcraft-analyze#heading--framework)                           
Lint OK:                                                                                                         
- juju-actions: no issues found (https://juju.is/docs/sdk/charmcraft-analyze#heading--juju-actions)              
- juju-config: no issues found (https://juju.is/docs/sdk/charmcraft-analyze#heading--juju-config)                
- metadata: no issues found (https://juju.is/docs/sdk/charmcraft-analyze#heading--metadata)  
```
-->
