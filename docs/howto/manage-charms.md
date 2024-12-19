(manage-charms)=
# How to manage charms

> See first: [`juju` | Charm](https://juju.is/docs/juju/charmed-operator),  [`juju` | Manage charms](https://juju.is/docs/juju/manage-charms-or-bundles)


## Initialise a charm

To initialise a charm project, create a directory for your charm, enter it, then run `charmcraft init` with the `--profile` flag followed by a suitable profile name (for machine charms: `machine`; for Kubernetes charms: `kubernetes`, `simple`, or `flask-framework`); that will create all the necessary files and even prepopulate them with useful content. 

```text
charmcraft init --profile <profile>
```


````{dropdown} See sample session


```bash
$ mkdir my-flask-app-k8s
$ cd my-flask-app-k8s/
$ charmcraft init --profile flask-framework
Charmed operator package file and directory tree initialised.                                                                                                                                
                                                                                                                                                                                             
Now edit the following package files to provide fundamental charm metadata                                                                                                                   
and other information:                                                                                                                                                                       
                                                                                                                                                                                             
charmcraft.yaml                                                                                                                                                                              
src/charm.py                                                                                                                                                                                 
README.md                                                                                                                                                                                    
                                                                                                                                                                                             
$ ls -R
.:
charmcraft.yaml  requirements.txt  src

./src:
charm.py
 

```

````



The command also allows you to not specify any profile (in that case you get the `simple` profile -- a Kubernetes profile with lots of scaffolding, suitable for beginners) and has flags that you can use to specify a different directory to operate in, a charm name different from the name of the root directory, etc. 

> See more: {ref}`ref_commands_revisions`, {ref}`profile`, {ref}`list-of-files-in-a-charm-project`
>
> See more: {ref}`manage-extensions`

## Add charm project metadata, an icon, docs


### Specify that the project is a charm

To specify that the project is a charm (as supposed to a bundle), in your `charmcraft.yaml` file set the `type` key to `charm`:

```text
type: charm
```

### Specify a name

To specify a pack-and-deploy name for your charm, in your charm's `charmcraft.yaml` file specify the `name` key. E.g.,

```yaml
name: traefik-k8s
```

> See more: {ref}`file-charmcraft-yaml-name`

### Specify a title

To specify a title for your charm's page on Charmhub, in your charm's `charmcraft.yaml` file specify a value for the `title` key. E.g., 

```yaml
title: |
  Traefik Ingress Operator for Kubernetes
```

> See more: {ref}`file-charmcraft-yaml-title`

### Add a summary

To add a summary line for your charm, in your charm's `charmcraft.yaml` file specify a value for the `summary` key. E.g., 

```yaml
summary: |
  A Juju charm to run a Traefik-powered ingress controller on Kubernetes.
```

> See more: {ref}`file-charmcraft-yaml-summary`

### Add a description

To add a longer description for your charm, in your charm's `charmcraft.yaml` file specify a value for the `description` key. E.g.,

```yaml
description: |
  A Juju-operated Traefik operator that routes requests from the outside of a
  Kubernetes cluster to Juju units and applications.
  
```

> See more: {ref}`file-charmcraft-yaml-description`

### Add contact information

To add maintainer contact information for a charm, in your charm's `charmcraft.yaml` file specify a value for the `links.contact` key. E.g.,

```yaml
links:
  contact: Please send your answer to Old Pink, care of the Funny Farm, Chalfont
```

> See more: {ref}`file-charmcraft-yaml-contact`

### Add a link to source code

To add a link to the source code for a charm, in your charm's `charmcraft.yaml` file specify an item under the `links.source` key. E.g.,

```yaml
links:
  source:
  - https://github.com/canonical/traefik-k8s-operator
```

> See more: {ref}`file-charmcraft-yaml-links`

### Add a link to the bug tracker

To add a link to the bug tracker for a charm, in your charm's `charmcraft.yaml` file specify an item under the `links.issues` key. E.g.,

```yaml
links:
  issues: 
  - https://github.com/canonical/traefik-k8s-operator/issues
```

> See more: {ref}`file-charmcraft-yaml-links`

### Add a link to the website

If your charm has a website outside of Charmhub, to add a link to this website, in your charm's `charmcraft.yaml` file specify an item under the `links.website` key. E.g.,

```yaml
links:
  website:
  - https://charmed-kubeflow.io/
```

> See more: {ref}`file-charmcraft-yaml-links`

### Add docs and a link to the docs

If you publish your charm on Charmhub, reference documentation about the charm's resources, actions, configurations, relations, and libraries is extracted automatically. However, you should also aim to add further docs, e.g., a tutorial, how-to guides, etc.  To provide a link to these docs, in your charm's `charmcraft.yaml` file specify a value for the `links.documentation` key. Note that at present this must be a Discourse page. E.g., 

```yaml
links:
  documentation: https://discourse.charmhub.io/t/traefik-k8s-docs-index/10778
```

> See more: {ref}`file-charmcraft-yaml-links`

### Add terms of use

To add terms of use for your charm, in your charm's `charmcraft.yaml` file specify a value for the `terms` key. E.g.,

```yaml
terms:
- Butterscotch is regal
- Cara is adorable
```

> See more: {ref}`file-charmcraft-yaml-terms`


### Add an icon

See {ref}`manage-icons`.


## Add runtime details to a charm

### Require a specific Juju version

To require a specific Juju version for your charm, in your charm's `charmcraft.yaml` specify the `assumes` key. E.g.,

```yaml
assumes:
    - juju >= 3.5
```

> See more: {ref}`file-charmcraft-yaml-assumes`

### Require a Kubernetes cloud

To require a Kubernetes cloud for your charm, in your charm's `charmcraft.yaml` file specify the `assumes` key. E.g.,

```yaml
assumes:
    - k8s-api
```

> See more: {ref}`file-charmcraft-yaml-assumes`

### Require a specific base and platforms

To require a specific base and platforms for your charm, in your charm's `charmcraft.yaml` file specify the `base`(,`build-base`,) and the `platforms keys. E.g.,

```{note}
In Charmcraft < 3.0 this was done via a single key: `bases`.

```

```yaml
# The run time base, the base format is <os-name>@<os-release>,
# accepted bases are:
# - ubuntu@24.04
base: <base>
# The build time base, if not defined the base is also the build time 
# base, in addition to valid bases, the build-base can be "devel"
# which would use the latest in development Ubuntu Series.
build-base: <base>

platforms:
     # The supported platforms, may omit build-for if platform-name
     # is a valid arch, valid architectures follow the Debian architecture names,
     # accepted architectures are:
     # - amd64
     # - arm64
     # - armhf
     # - ppc64el
     # - riscv64
     # - s390x
     <platform-name>:
         # The build time architecture
         build-on: <list-of-arch> | <arch>
         # The run time architecture
         build-for: <list-of-arch> | <arch>
```

> See more: {ref}`file-charmcraft-yaml-base`, {ref}`build-base`, {ref}`file-charmcraft-yaml-platforms`

### Specify container requirements

To specify container requirements, in your charm's `charmcraft.yaml` file specify the `containers` key.


> See more: {ref}`file-charmcraft-yaml-containers`


### Specify associated resources

See {ref}`manage-resources`.

### Specify device requirements

> See more: {ref}`file-charmcraft-yaml-devices`

To specify container requirements, in your charm's `charmcraft.yaml` file specify the `devices` key.

### Specify storage requirements

To specify storage requirements, in your charm's `charmcraft.yaml` file specify the `storage` key.

> See more: {ref}`file-charmcraft-yaml-storage`

### Specify extra binding requirements

To specify extra binding requirements, in your charm's `charmcraft.yaml` file specify the `extra-bindings` key.

> See more: {ref}`file-charmcraft-yaml-extra-bindings`

### Require subordinate deployment

To require subordinate deployment for your charm (i.e., for it to be deployed to the same machine as another charm, called its 'principal'), in your charm's `charmcraft.yaml` file specify the `subordinate` key.

> See more: {ref}`file-charmcraft-yaml-subordinate`


### Manage actions

> See first: [`juju` | Action](https://juju.is/docs/juju/action), [`juju` | Manage actions](https://juju.is/docs/juju/manage-actions)


To declare an action in your charm, in your charm's `charmcraft.yaml` file specify the `actions` key.

> See more: {ref}`file-charmcraft-yaml-actions`
>
> See next: [`ops` | Manage actions]()


### Manage configurations

> See first: [`juju` | Application configuration](https://juju.is/docs/juju/configuration#heading--application-configuration), [`juju` | Manage applications > Configure](https://juju.is/docs/juju/manage-applications#configure-an-application)

To declare a configuration option for your charm, in your charm's `charmcraft.yaml` specify the `config` key.


> See more: {ref}`file-charmcraft-yaml-config`
>
> See next: [`ops` | Manage configurations]()



### Manage relations (integrations)

> See first: [`juju` | Relation](https://juju.is/docs/juju/relation), [`juju` | Manage relations](https://juju.is/docs/juju/manage-relations)

To declare a relation endpoint in your charm, in your charm's `charmcraft.yaml` specify the `peers`, `provides`, or `requires` key.

> See more: {ref}`file-charmcraft-yaml-peers-provides-requires`
>
> See more: [`ops` | Manage relations (integrations)]()


### Specify necessary libs

> See first: [`juju` | Library]()


See {ref}`manage-libraries`.

### Manage secrets
> See first: [`juju` | User secret](https://juju.is/docs/juju/secret#heading--user)

To make your charm capable of accepting a user secret, in your charm's `charmcraft.yaml` specify the `config` key with the `type` subkey set to `secret`.

> See more: {ref}`file-charmcraft-yaml-config`
>
> See next: [`ops` | Manage secrets]()

### Specify necessary parts

See {ref}`manage-parts`.

## Pack a charm

To pack a charm directory, in the charm's root directory, run the command below:

```text
charmcraft pack
```

This will fetch any dependencies (from PyPI, based on `requirements.txt`), compile any modules, check that all the key files are in place, and produce a compressed archive with the extension `.charm`. As you can verify, this archive is just a zip file with metadata and the operator code itself. 

````{dropdown} Expand to view a sample session for a charm called microsample-vm


```text
# Pack the charm:
~/microsample-vm$ charmcraft pack
Created 'microsample-vm_ubuntu-22.04-amd64.charm'.                                         
Charms packed:                                                                             
    microsample-vm_ubuntu-22.04-amd64.charm                                                

# (Optional) Verify that this has created a .charm file in your charm's root directory:
~/microsample-vm$ ls
CONTRIBUTING.md  charmcraft.yaml                          requirements.txt  tox.ini
LICENSE          microsample-vm_ubuntu-22.04-amd64.charm  src
README.md        pyproject.toml                           tests

# (Optional) Verify that the .charm file is simply a zip file that contains 
# everything you've packed plus any dependencies:
/microsample-vm$ unzip -l microsample-vm_ubuntu-22.04-amd64.charm | { head; tail;}
Archive:  microsample-vm_ubuntu-22.04-amd64.charm
  Length      Date    Time    Name
---------  ---------- -----   ----
      815  2023-12-05 12:12   README.md
    11337  2023-12-05 12:12   LICENSE
      250  2023-12-05 12:31   manifest.yaml
      102  2023-12-05 12:31   dispatch
      106  2023-12-01 14:59   config.yaml
      717  2023-12-05 12:31   metadata.yaml
      921  2023-12-05 12:26   src/charm.py
      817  2023-12-01 14:44   venv/setuptools/command/__pycache__/upload.cpython-310.pyc
    65175  2023-12-01 14:44   venv/setuptools/command/__pycache__/easy_install.cpython-310.pyc
     4540  2023-12-01 14:44   venv/setuptools/command/__pycache__/py36compat.cpython-310.pyc
     1593  2023-12-01 14:44   venv/setuptools/command/__pycache__/bdist_rpm.cpython-310.pyc
     6959  2023-12-01 14:44   venv/setuptools/command/__pycache__/sdist.cpython-310.pyc
     2511  2023-12-01 14:44   venv/setuptools/command/__pycache__/rotate.cpython-310.pyc
     2407  2023-12-01 14:44   venv/setuptools/extern/__init__.py
     2939  2023-12-01 14:44   venv/setuptools/extern/__pycache__/__init__.cpython-310.pyc
---------                     -------
 20274163                     1538 files


```

````

The command has a number of flags that allow you to specify a different charm directory to pack, whether to force pack if there are linting errors, etc.

> See more: {ref}`ref_commands_pack`

```{caution}

**If you've declared any resources :** This will *not* pack the resources. This means that, when you upload your charm to Charmhub (if you do), you will have to upload the resources separately.

> See more: {ref}`manage-resources`

```

```{important}

When the charm is packed, a series of analyses and lintings will happen, you may receive warnings and even errors to help improve the quality of the charm.

> See more: {ref}`Charmcraft analyzers and linters <charmcraft-analyzers-and-linters>`

```

> See next: [`juju` | Deploy a local charm](https://juju.is/docs/juju/manage-charms-or-bundles#deploy-a-charm-bundle), [`juju` | Debug a charm](), [`juju` | Update a local charm](https://juju.is/docs/juju/manage-charms-or-bundles#update-a-local-charm)

(publish-a-charm)=
## Publish a charm on Charmhub

1. Log in to Charmhub:

```text
charmcraft login
```

> See more: {ref}`manage-the-current-charmhub-user`

2. Register your charm's name (the one you specified in `charmcraft.yaml` > `name`):

```text
charmcraft register my-awesome-charm
```

> See more: {ref}`manage-names`

```{note}
This automatically creates 4 channels, all with track latest but with different risk levels, namely, edge, beta, candidate, stable, respectively. See more: {ref}`manage-channels`.
```

3. Upload the charm to Charmhub:  Use the `charmcraft upload` command followed by the your charm's filepath. E.g., if you are in the charm's root directory,

```text
charmcraft upload my-awesome-charm.charm
Revision 1 of my-awesome-charm created
```

> See more: {ref}`ref_commands_upload`

```{note}
Each time you upload a charm to Charmhub, that creates a revision (unless you upload the exact same file again). See more: {ref}`manage-charm-revisions`.
```


4. If your charm has associated resources: These are not packed with the rest of the charm project, so you must upload them explicitly to Charmhub as well. For example:

```text
$ charmcraft upload-resource my-super-charm someresource --filepath=/tmp/superdb.bin
Revision 1 created of resource 'someresource' for charm 'my-super-charm'
```

> See more: {ref}`manage-resources`

```{note}
Each time you upload a resource to Charmhub, that creates a revision (unless you upload the exact same file again). See more: {ref}`manage-resource-revisions`.
```

5. Release the charm: To release a charm, release your revision of choice to the target release channel. E.g.,

```text
$ charmcraft release my-awesome-charm --revision=1 --channel=beta
Revision 1 of charm 'my-awesome-charm' released to beta
```

> See more: {ref}`manage-charm-revisions`

```{note}

This automatically opens the channel. See more: {ref}`manage-channels`.
```

> See next: [`juju` | Deploy a Charmub charm](https://juju.is/docs/juju/manage-charms-or-bundles#deploy-a-charm-bundle), [`juju` | Update a Charmhub charm](https://juju.is/docs/juju/manage-charms-or-bundles#update-a-charmhub-charm)

```{tip}
To update the charm on Charmhub, repeat the upload and release steps.

```


```{important}

Releasing a charm on Charmhub gives it a public URL. However, the charm will not appear in the Charmhub search results until it has passed formal review. To request formal review, reach out to the community to announce your charm and ask for a review by an experienced community member.

> See more: [Discourse | review requests](https://discourse.charmhub.io/c/charmhub-requests/46)


Also, the point of publishing and having a charm publicly listed on Charmhub is so others can reuse it and potentially contribute to it as well. To publicize your charm:

- [Write a Discourse post to announce your release.](https://discourse.charmhub.io/tags/c/announcements-and-community/33/none) 

- [Schedule a community workshop to demo your charm's capabilities.](https://discourse.charmhub.io/tag/community-workshop)

- [Chat about it with your charmer friends.](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)


```



