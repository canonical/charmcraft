(file-bundle-yaml)=
# File `<bundle>.yaml`

> <small> {ref}`Bundle <bundle>` > File `<bundle>.yaml`</small>
>
> Source for the keys used by Juju: [Schema](https://github.com/juju/charm/blob/v12/bundledata.go), [Examples from test files](https://github.com/juju/charm/blob/v12/bundledata_test.go)
>
> (The metadata keys `docs`, `issues`, `source`, and `website` are only used by Charmhub.)

File `<bundle>.yaml` is the file in your bundle directory where you define your bundle.

**For overlay bundles:**

- Instead of providing overlays as external files, you may alternatively leverage Juju's support for multi-document YAML files and provide both the base overlay and any required overlays as a _single file_, appending the contents of the overlay after the base bundle using the special  YAML document separator token `---` as the delimiter. Juju will treat the first document as the base bundle and any subsequent document as an overlay.


````{dropdown} Example base and overlay in the same file

``` yaml
applications:
  mysql:
    charm: "mysql"
    num_units: 1
    to: ["lxd:wordpress/0"]
--- # This is part of overlay 1
applications:
  mysql:
    num_units: 1
--- # This is part of overlay 2
applications:
  mysql:
    trust: true
```

````

- Relative paths are resolved relative to the path of the entity that describes them. That is, relative to the overlay bundle file itself. <!--????-->
- An application is removed from the base bundle by defining the application name in the application section, but omitting any values. Removing an application also removes all the relations for that application.
- If a machines section is specified in an overlay bundle, it replaces the corresponding section of the base bundle. No merging of machine information is attempted. Multiple overlay bundles can be specified and they are processed in the order they appear on the command line.
- Overlays can include new integrations, which are normally required for any new charms which have been added. Existing integrations cannot be removed however, except in the case where the referenced application is also removed by the overlay.


````{dropdown} Example 'bundle.yaml file -- Kubernetes

```text
bundle: kubernetes
applications:
  postgresql:
    charm: postgresql-k8s
    scale: 3
    constraints: mem=1G
    storage:
      database: postgresql-pv,20M
  mattermost:
    charm: mattermost-k8s
    placement: foo=bar
    scale: 1
relations:
  - - postgresql:db
    - mattermost:db
```

````



````{dropdown} Example 'bundle.yaml' file -- machines

A bundle for deployment on machines, for example, the [`kubernetes-core`](https://jaas.ai/kubernetes-core/) bundle, looks as follows:

```yaml
description: A highly-available, production-grade Kubernetes cluster.
issues: https://bugs.launchpad.net/charmed-kubernetes-bundles
series: jammy
source: https://github.com/charmed-kubernetes/bundle
website: https://ubuntu.com/kubernetes/charmed-k8s
name: charmed-kubernetes
applications:
  calico:
    annotations:
      gui-x: '475'
      gui-y: '605'
    channel: 1.26/stable
    charm: calico
    options:
      vxlan: Always
  containerd:
    annotations:
      gui-x: '475'
      gui-y: '800'
    channel: 1.26/stable
    charm: containerd
  easyrsa:
    annotations:
      gui-x: '90'
      gui-y: '420'
    channel: 1.26/stable
    charm: easyrsa
    constraints: cores=1 mem=4G root-disk=16G
    num_units: 1
  etcd:
    annotations:
      gui-x: '800'
      gui-y: '420'
    channel: 1.26/stable
    charm: etcd
    constraints: cores=2 mem=8G root-disk=16G
    num_units: 3
    options:
      channel: 3.4/stable
  kubeapi-load-balancer:
    annotations:
      gui-x: '450'
      gui-y: '250'
    channel: 1.26/stable
    charm: kubeapi-load-balancer
    constraints: cores=1 mem=4G root-disk=16G
    expose: true
    num_units: 1
  kubernetes-control-plane:
    annotations:
      gui-x: '800'
      gui-y: '850'
    channel: 1.26/stable
    charm: kubernetes-control-plane
    constraints: cores=2 mem=8G root-disk=16G
    num_units: 2
    options:
      channel: 1.26/stable
  kubernetes-worker:
    annotations:
      gui-x: '90'
      gui-y: '850'
    channel: 1.26/stable
    charm: kubernetes-worker
    constraints: cores=2 mem=8G root-disk=16G
    expose: true
    num_units: 3
    options:
      channel: 1.26/stable
relations:
- - kubernetes-control-plane:loadbalancer-external
  - kubeapi-load-balancer:lb-consumers
- - kubernetes-control-plane:loadbalancer-internal
  - kubeapi-load-balancer:lb-consumers
- - kubernetes-control-plane:kube-control
  - kubernetes-worker:kube-control
- - kubernetes-control-plane:certificates
  - easyrsa:client
- - etcd:certificates
  - easyrsa:client
- - kubernetes-control-plane:etcd
  - etcd:db
- - kubernetes-worker:certificates
  - easyrsa:client
- - kubeapi-load-balancer:certificates
  - easyrsa:client
- - calico:etcd
  - etcd:db
- - calico:cni
  - kubernetes-control-plane:cni
- - calico:cni
  - kubernetes-worker:cni
- - containerd:containerd
  - kubernetes-worker:container-runtime
- - containerd:containerd
  - kubernetes-control-plane:container-runtime
```

````


The rest of this document describes each key in this file.

```{note}

A bundle for deployment on Kubernetes differs from a standard bundle in the following ways:

- key 'bundle' is given the value of 'kubernetes'
- key 'num_units' is replaced by key 'scale'
- key 'to' is replaced by key 'placement'

The value of 'placement' is a key=value pair and is used as a Kubernetes node selector.

```

## `applications`

**Purpose:** Holds all the applications in your bundle.

**Value:** Mapping. Keys are application names.

<a href="#heading--applications-application"><h2 id="heading--applications-application">`applications.<application>`</h2></a>

**Purpose:** Holds your application definition.

**Name:** The name of the application. User-defined, usually identical to [`applications.<application>.charm`](#heading--applications-application-charm)

<a href="#heading--applications-application-annotations"><h2 id="heading--applications-application-annotations">`applications.<application>.annotations`</h2></a>

```text
    #
    # annotations:
    #
    # Affects the GUI only. It provides horizontal and vertical placement of
    # the application's icon on the GUI's canvas. Annotations are expressed in
    # terms of 'x' and 'y' coordinates.
    #

    annotations:
      gui-x: 450
      gui-y: 550

```

## `applications.<application>.base`

## `applications.<application>.bindings`

```text
    #
    # bindings:
    #
    # Maps endpoints to network spaces. Used to constrain relations to specific
    # subnets in environments where machines have multiple network devices.
    # The empty ("") key represents all endpoints and can be used to specify the
    # default space for any endpoint that is not explicitly bound to a space.

    bindings:
      "": alpha
      kube-api-endpoint: internal
      loadbalancer: dmz
    
```

## `applications.<application>.channel`

**Purpose:** States what the preferred channel should be used when deploying a non-local charm. **Note:** Charmhub charms expect `<track>/<risk>/<branch>` format (e.g., `latest/stable`).

**Example:**

```text
channel: latest/edge
```

## `applications.<application>.charm`

**Purpose:**     States what charm to use for the application. **If you're defining a public bundle:** Use a fully qualified charm URI.

**Example:**

```text
charm: containers-easyrsa
```
   
<!--??? from https://discourse.charmhub.io/t/how-to-set-up-subordinate-charms-inside-a-bundle/5700

To set up a subordinate charm, do not use the placement key `to` and do not specify any units with the `num_units` key. The vital part with a subordinate is to create the relation between it and the principal charm under the `relations` element.
-->

## `applications.<application>.constraints`

```text
    #
    # constraints:
    #
    # Sets standard constraints for the application. As per normal behaviour,
    # these become the application's default constraints (i.e. units added
    # subsequent to bundle deployment will have these constraints applied).
    #

    constraints: root-disk=8G

    constraints: cores=4 mem=4G root-disk=16G

    constraints: zones=us-east-1a

    constraints: "arch=amd64 mem=4G cores=4"

```

## `applications.<application>.devices`

## `applications.<application>.expose`

```text
    #
    # expose:
    #
    # Exposes the application using a boolean value. The default value is
    # 'false'. 
    #
    # In order to use the granular per-endpoint expose settings feature
    # (Juju 2.9 or newer) by specifying an "exposed-endpoints" section, the 
    # expose field must either be set to false or omitted from the bundle.  
    #

    expose: true

```



## `applications.<application>.exposed-endpoints`

```text

    # exposed-endpoints:
    # 
    # Specifies the set of CIDRs and/or spaces that are allowed to access the
    # port ranges opened by the application. Expose settings can be
    # specified both for the entire application using the wildcard ("") key 
    # and for individual endpoints.
    # 
    # NOTES:
    # - This is a deployment-specific field and can only be specified
    #   as part of an overlay.
    # - This field is supported since Juju 2.9.

```
Since Juju 2.9, operators can control the expose parameters (CIDRs and/or spaces that are allowed access to the port ranges opened by exposed applications) for the entire application and/or on a per-endpoint basis. 

Application expose parameters can also be specified in bundles. However, as expose parameters are deployment-specific, they can only be provided as part of an overlay. Consider the following multi-document bundle:

```yaml
applications:
  mysql:
    charm: "mysql"
    num_units: 1
--- # overlay
applications:
  mysql:
    exposed-endpoints:
      "":
        expose-to-cidrs:
        - 0.0.0.0/0
        - ::/0
      db-admin:
        expose-to-spaces:
        - dmz
        expose-to-cidrs:
        - 192.168.0.0/24
```

This is equivalent to the following commands:

```text
juju deploy mysql
juju expose mysql --to-cidrs 0.0.0.0/0,::/0
juju expose mysql --endpoints db-admin --to-spaces dmz --to-cidrs 192.168.0.0/24
```

As a result of the above commands, the mysql application will be exposed and:
- All port ranges opened by the charm for any endpoint **except** `db-admin` will be reachable by **any** IP address.
- Port ranges opened by the charm for the `db-admin` endpoint will only be reachable by IPs that are part of the `192.168.0.0/24` block or belong to a subnet associated with the `dmz` space.

```{note}

When using this particular feature, the bundle must not also contain an `expose: true` field or Juju will display an error when attempting to deploy the bundle.

This constraint prevents operators from accidentally exposing **all** ports for an application when attempting to deploy such a bundle to a pre 2.9 controller as older controllers would honor the `expose: true` flag but would not interpret the `exposed-endpoints` field.

In addition,  2.9 (and newer) Juju clients will also display an error when attempting to deploy a bundle containing an `exposed-endpoints` section to a pre 2.9 controller.

```

## `applications.<application>.exposed-endpoints.expose-to-cidrs`

## `applications.<application>.exposed-endpoints.expose-to-spaces`


## `applications.<application>.num_units`

**Purpose: Specifies the number of units to deploy. 

**Value:** Integer = the number of units. Default: '0'. 

**Example:**

```text
num_units: 2
```

## `applications.<application>.offers.<offer>`
## `applications.<application>.offers.<offer>.acl`
## `applications.<application>.offers.<offer>.endpoints`
## `applications.<application>.offers`

```text

    # offers:
    # 
    # Specifies a list of offers for the application endpoints that can be 
    # consumed by other models. Each offer entry is identified by a unique
    # name and must include a list of application endpoints to be exposed
    # as part of the offer. In addition, each offer may optionally define an
    # "acl" block to control, on a per-user level, the permissions granted to 
    # the consumer side. The "acl" block keys are user names and values are  
    # permission levels.
    #
    # NOTES:
    # - This is a deployment-specific field and can only be specified
    #   as part of an overlay.
    # - This field is supported since Juju 2.7.
    #

    offers: 
      my-offer:
        endpoints:
        - apache-website
        acl:
          admin: admin
          user1: read

```

## `applications.<application>.options`

```text
    #
    # options:
    #
    # Sets configuration options for the application. The keys are
    # application-specific and are found within the corresponding charm's
    # metadata.yaml file. An alias (a string prefixed by an asterisk) may be
    # used to refer to a previously defined anchor (see the 'variables'
    # element).
    #

    options:
      osd-devices: /dev/sdb
      worker-multiplier: *worker-multiplier

```

Values for options and annotations can also be read from a file. For binary files, such as binary certificates, there is an option to base64-encode the contents. A file location can be expressed with an absolute or relative (to the bundle file) path. For example:

``` yaml
applications:
  my-app:
    charm: some-charm
    options:
      config: include-file://my-config.yaml
      cert: include-base64://my-cert.crt
```

## `applications.<application>.placement`
## `applications.<application>.plan`

```text

    #
    # plan:
    #
    # This is for third-party Juju support only. It sets the "managed
    # solutions" plan for the application. The string has the format
    # '<reseller-name>/<plan name>'.
    #

    plan: acme-support/default

```

## `applications.<application>.resources`

**Purpose:** States what charm resource to use.

**Value:** Map. Keys are individual resources.


Bundles support charm resources (see {ref}`Using resources <5679md>`) through the use of the `resources` key. Consider the following charm `metadata.yaml` file that includes a resource called `pictures`:

``` yaml
name: example-charm
summary: "example charm."
description: This is an example charm.
resources:
  pictures:
    type: file
    filename: pictures.zip
    description: "This charm needs pictures.zip to operate"
```

It might be desirable to use a specific resource revision in a bundle:

``` yaml
applications:
  example-charm:
   charm: "example-charm"
   series: trusty
   resources:
     pictures: 1
```

So here we specify a revision of '1' from Charmhub.

The `resources` key can also specify a local path to a resource instead:

``` yaml
applications:
  example-charm:
   charm: "example-charm"
   series: trusty
   resources:
     pictures: "./pictures.zip"
```

Local resources can be useful in network restricted environments where the controller is unable to contact Charmhub.
  
## `applications.<application>.resources.<resource>`

**Purpose:** Defines individual resources.

**Name:** Application specific. Cf. the charm's `metadata.yaml`.

**Value:**  Integer = the resource revision stored in the Charmhub or String = absolute or relative file path to local resource.

**Examples:**

```text
easyrsa: 5
```
```text
easyrsa: ./relative/path/to/file
```


## `applications.<application>.revision`

**Purpose:** States the revision of the charm should be used when deploying a non-local charm. Use requires a channel to be specified, indicating  which channel should be used when refreshing the charm. 
 
**Example:**

```text
revision: 8
```

<a href="#heading--applications-application-scale"><h2 id="heading--applications-application-scale">`applications.<application>.scale`
<a href="#heading--applications-application-series"><h2 id="heading--applications-application-series`applications.<application>.series`
<a href="#heading--applications-application-storage"><h2 id="heading--applications-application-stora`applications.<application>.storage`

```text
    #
    # storage:
    #
    # Sets storage constraints for the application. There are three such
    # constraints: 'pool', 'size', and 'count'. The key (label) is
    # application-specific and are found within the corresponding charm's
    # metadata.yaml file. A value string is one that would be used in the
    # argument to the `--storage` option for the `deploy` command.
    #

    storage:
      database: ebs,10G,1

```

`applications.<application>.to`


```
    #
    # to:
    #
    # Dictates the placement (destination) of the deployed units in terms of
    # machines, applications, units, and containers that are defined elsewhere
    # in the bundle. The number of destinations cannot be greater than the
    # number of requested units (see 'numb_units' above). Zones are not
    # supported; see the 'constraints' element instead. The value types are
    # given below.
    #
    #  new
    #     Unit is placed on a new machine. This is the default value type; it
    #     does not require stating. This type also gets used if the number of
    #     destinations is less than than 'num_units'.
    #
    #  <machine>
    #     Unit is placed on an existing machine denoted by its (unquoted) ID.
    #

    to: 3, new

    #
    #  <unit>
    #     Unit is placed on the same machine as the specified unit. Doing so
    #     must not create a loop in the placement logic. The specified unit
    #     must be for an application that is different from the one being
    #     placed.
    #
    
    to: ["django/0", "django/1", "django/2"]

    #
    #  <application>
    #     The application's existing units are iterated over in ascending
    #     order, with each one being assigned as the destination for a unit to
    #     be placed. New machines are used when 'num_units' is greater than the
    #     number of available units. The same results can be obtained by
    #     stating the units explicitly with the 'unit' type above.
    #

    to: ["django"]

    #
    #  <container-type>:new
    #     Unit is placed inside a container on a new machine. The value for
    #     `<container-type>` can be either 'lxd' or 'kvm'. A new machine is the
    #     default and does not require stating, so ["lxd:new"] or just ["lxd"].
    #

    to: ["lxd"]

    #
    #  <container-type>:<machine>
    #     Unit is placed inside a new container on an existing machine.
    #

    to: ["lxd:2", "lxd:3"]

    #
    #  <container-type>:<unit>
    #     Unit is placed inside a container on the machine that hosts the
    #     specified unit. If the specified unit itself resides within a
    #     container, then the resulting container becomes a peer (sibling) of
    #     the other (i.e. no nested containers).
    #

    to: ["lxd:nova-compute/2", "lxd:glance/3"]
```

<a href="#heading--applications-application-trust"><h2 id="heading--applications-application-trust">`applications.<application>.trust`</h2></a>

<a href="#heading--bundle"><h2 id="heading--bundle">`bundle`</h2></a>

If set to `kubernetes`, indicates a Kubernetes bundle.

<a href="#heading--default-base"><h2 id="heading--default-base">`default-base`</h2></a>

<a href="#heading--description"><h2 id="heading--description">`description`</h2></a>

**Purpose:** Sets the bundle description visible on Charmhub.

**Examples:**

```text
description: This is a test bundle.
```

```text
description: |

  This description is long and has multiple lines. Use the vertical bar as
  shown in this example.
```


## `docs`


```text
# (Optional) A link to a documentation cover page on Discourse
# More details at https://juju.is/docs/sdk/charm-documentation
docs: <url>

```

## `issues`

**Example:**

```text
# (Optional) A string (or a list of strings) containing a link (or links) to the bundle bug tracker.
issues: <url> | [<urls>]
```


## `machines`

```text

# machines:
#
# Provides machines that have been targeted by the 'to' key under the
# '<application name>' element. A machine is denoted by that same machine ID,
# and must be quoted. Keys for 'constraints', 'annotations', and 'series' can
# optionally be added to each machine. Containers are not valid machines in
# this context.
#

machines:
  "1":
  "2":
    series: bionic
    constraints: cores=2 mem=2G
  "3":
    constraints: cores=3 root-disk=1T


```

## `machines.<machine>.annotations`



## `machines.<machine>.base`
## `machines.<machine>.constraints`
## `machines.<machine>.series`
## `name`

**Example:**

```text
# name:
#
# Name defines an optional name for the bundle. Used only for Charmhub
# Store and is omitted for other stores (charmstore, private) and local 
# deployments.
#

name: foo
```


## `relations`


**Example:**

```text
#
# relations:
#
# States the relations to add between applications. Each relation consists of a
# pair of lines, where one line begins with two dashes and the other begins
# with a single dash. Each side of a relation (each line) has the format
# '<application>:<endpoint>', where 'application' must also be represented
# under the 'applications' element. Including the endpoint is not strictly
# necessary as it might be determined automatically. However, it is best
# practice to do so.
#

relations:
- - kubernetes-master:kube-api-endpoint
  - kubeapi-load-balancer:apiserver
- - kubernetes-master:loadbalancer
  - kubeapi-load-balancer:loadbalancer

```

## `saas`

**Example:**

```text
#
# saas:
#
# Specifies a set of offers (from the local or a remote controller)  to consume
# when the bundle is deployed. Each entry in the list is identified via a unique
# name and a URL to the offered service. Offer URLs have the following format:
# [<controller name>:][<model owner>/]<model name>.<application name>
#
# If the controller name is omitted, Juju will use the currently active controller.
# Similarly, if the model owner is omitted, Juju will use the user that is currently
# logged in to the controller providing the offer.
#

saas:
  svc1:
    url: localoffer.svc1
  svc2:
    url: admin/localoffer.svc2
  svc3:
    url: othercontroller:admin/offer.svc3
```


## `saas.<saas>`
## `saas.<saas>.url`
## `series`

```text
# series:
#
# Sets the default series for all applications in the bundle. This also affects
# machines devoid of applications. See 'Charm series' above for how a final
# series is determined.
```

**Example:**

```text
series: bionic
```

What series a charm will use can be influenced in several ways. Some of these are set within the bundle file while some are not. When using bundles, the series is determined using rules of precedence (most preferred to least):

- the series stated for a machine that an application unit has been assigned to (see `series` under the `<machines>` element)
- the series stated for an application (see `series` under the `<application name>` element)
- the series given by the top level `series` element
- the top-most series specified in a charm's `metadata.yaml` file
- the most recent LTS release



## `source`

**Example:**

```text

# (Optional) A string (or a list of strings) containing a link (or links) to the bundle source code.
source: <url> | [<urls>]
```

## `tags`

```text
# tags:
#
# Sets descriptive tags. A tag is used for organisational purposes in the
# Charm Store. See https://docs.jujucharms.com/authors-charm-metadata
# for the list of valid tags.
```

**Examples:**

```text
tags: [monitoring]
```

```text
tags: [database, utility]
```


## `type`

## `variables`


```text
# variables:
#
# Includes the optional definition of variables using anchors. Corresponding
# values are later manifested with the use of aliases. An anchor is a string
# prefixed with an ampersand (&) whereas an alias is the same string prefixed
# by an asterisk (*). The alias will typically be used to specify a value for an
# application option (see element 'options'). 
```

**Example:**

```text
variables:
  data-port:           &data-port            br-ex:eno2
  worker-multiplier:   &worker-multiplier    0.25

```

## `website`


```text
# (Optional) A string (or a list of strings) containing a link (or links) to project websites.
# In general this is likely to be the upstream project website, or the formal website for the
# charmed bundle.
website: <url> | [<urls>]

```
