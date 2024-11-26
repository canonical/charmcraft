(file-libname-py)=
# File `<libname>.py`

File `<libname>.py` is a Python file (or a Python [module](https://realpython.com/lessons/scripts-modules-packages-and-libraries/)) in your charm project that holds a charm library -- that is, code that enables charm developers to easily share and reuse auxiliary logic related to  charms -- for example, logic related to the relations between charms. 

Authors associate libraries with a specific charm, and publish them to Charmhub with a reference to the origin charm. This does not prevent reuse, modification, and sharing.

The publishing tools around libraries are deliberately kept simple. Libraries are however versioned and uniquely identified.


<!--
SEE IF WE CAN INTEGRATE THIS CONTENT FROM THIS DOC: https://juju.is/docs/sdk/document-your-library 
One of the most distinct features of a charm is the way it can readily relate to another charm. For this interface, there is one charm that will provide information in a specific way, and a charm that will consume information in a matching way to connect and work together. To ensure that the charm interface is a perfect pairing, the operator framework tooling and the store support a mechanism to publish and reuse this logic in a form of simple files, that we’ll call libraries. 
-->


## Location

Charm libraries are located in a  directory inside the charm with the following structure:

    $CHARMDIR/lib/charms/<charm>/v<API>/<libname>.py

where `$CHARMDIR` is the project's root (contains `src/`, `hooks/`, etc.), and the `<charm>` placeholder represents the charm responsible for the library named as `<libname>.py` with API version `<API>`. 

For example, inside a charm `mysql`, the library `db` with major version 3 will be in a directory with the structure below:

   $CHARMDIR/lib/charms/mysql/v3/db.py

When you pack your charm, Charmcraft copies the top `lib` directory into the root directory of the charm. Thus, to import this library in Python use the full path minus the top `lib` directory, as below:

```
import charms.mysql.v3.db
```



## Structure

A charm library is a Python file with the following structure:


### Docstring

Your charm file begins with a long docstring. This docstring describes your library. Charmcraft publishes it as your library's documentation on Charmhub. This documentation is updated whenever a new version of the library is published. 

The docstring supports Markdown, specifically, CommonMark. 


### Metadata

After the docstring, there are a few metadata keys, as below.


#### `LIBID`

The `LIBID` key controls the unique identifier for a library across the entire universe of charms. The value is assigned by Charmhub to this particular library automatically at library creation time. This key enables Charmhub and `charmcraft` to track the library uniquely even if the charm or the library are renamed, which allows updates to warn and guide users through the process.

#### `LIBAPI`

`LIBAPI` is set to an initial state of `0`. In general, `LIBAPI` must match the major version in the import path.

#### `LIBPATCH`

`LIBPATCH` is set to an initial state of `1`. In general, it must match the current patch version (needs to be updated when changing). 

#### `PYDEPS`

The `PYDEPS` key is an optional key that allows you to declare external Python dependencies. Charmcraft will make sure to add them to the dependencies required for your charm. 

The key maps to a list of strings. Each string is a regular "pip installable" Python dependency that will be retrieved from PyPI in the usual way (subject to the user's system configuration) and which supports all dependency formats (just the package name, a link to a Github project, etc.).

Some examples of possible PYDEPS declarations are as below:

```
PYDEPS=["jinja2"]

PYDEPS = ["pyyaml", "httpcore<0.15.0,>=0.14.5"]

PYDEPS = [
    "git+https://github.com/canonical/operator/#egg=ops",
    "httpcore<0.15.0,>=0.14.5",
    "requests",
]
```

Of course, only one `PYDEPS` declaration is allowed.

Charmcraft will collect the dependencies from all libraries included in the charm and install them from source in the virtual environment inside the `.charm` file, together with all the other Python dependencies declared by the charm itself.

Note that, when called to install all the dependencies from the charm and all the used libraries, `pip` may detect conflicts between the requested packages and their versions. This is a feature, because it's always better to detect incompatibilities between dependencies at this moment than when the charm is being deployed or run after deployment.


### Code

After the docstring and the metadata, there's the library code. This is regular Python code.

## Popular library index


This is an index of the charm libraries that are currently known to be available.

```{note}

This list may be missing libraries from charms that are not publicly listed on Charmhub. If you would like to add a library to the list, please drop a comment using the feedback link below.

```

### Libraries that define relations

The following libraries provide programmatic instructions for relating to a specific charm.

| Library | Used in | Description |
| --- | --- | --- |
| [fluentbit](https://charmhub.io/fluentbit/libraries/fluentbit) | [fluentbit](https://charmhub.io/fluentbit/libraries/fluentbit) | Defines both sides of a relation interface to the [fluentbit charm](https://charmhub.io/fluentbit/libraries/fluentbit). |
| [redis](https://charmhub.io/redis-k8s/libraries/redis) |  | Import RedisRequires from this lib to relate your charm to the [redis-k8s charm](https://charmhub.io/redis-k8s). |
| [grafana-dashboard](https://charmhub.io/grafana-k8s/libraries/grafana-dashboard) | | Defines a relation interface for charms that provide a dashboard to the [grafana-k8s charm](https://charmhub.io/grafana-k8s). |
| [grafana-source](https://charmhub.io/grafana-k8s/libraries/grafana-source) | | Defines a relation interface for charms that serve as a data source for the [grafana-k8s charm](https://charmhub.io/grafana-k8s). |
| [prometheus-scrape](https://charmhub.io/prometheus-k8s/libraries/prometheus_scrape) | | Defines a relation interface for charms that want to expose metrics endpoints to the [prometheus charm](https://charmhub.io/prometheus-k8s). |
|[alertmanager-dispatch](https://charmhub.io/alertmanager-k8s/libraries/alertmanager_dispatch) | | Defines a relation to the [alertmanager-dispatch charm](https://charmhub.io/alertmanager-k8s). |
|[karma_dashboard](https://charmhub.io/karma-k8s/libraries/karma_dashboard) | [karma-k8s](https://charmhub.io/karma-k8s) | Defines an interface for charms wishing to consume or provide a karma-dashboard relation. |
| [loki_push_api](https://charmhub.io/loki-k8s/libraries/loki_push_api) | [loki_k8s](https://charmhub.io/loki-k8s) | Defines a relation interface for charms wishing to provide or consume the Loki Push API---e.g., a charm that wants to send logs to Loki. | 
| [log_proxy](https://charmhub.io/loki-k8s/libraries/log_proxy) | [loki_k8s](https://charmhub.io/loki-k8s) |  Defines a relation interface that allows a charm to act as a Log Proxy for Loki (via the Loki Push API). |
| [guacd](https://charmhub.io/apache-guacd/libraries/guacd) | [apache-guacd](https://charmhub.io/apache-guacd/) | Defines a relation for charms wishing to set up a native server side proxy for Apache Guacamole. |

### Libraries that provide tools

These libraries provide reusable tooling, typically to interact with cloud services, or to perform operations common to several charms.
| Library | Used in | Description |
| --- | --- | --- |
| [cert](https://charmhub.io/kubernetes-dashboard/libraries/cert) | [kubernetes-dashboard](https://charmhub.io/kubernetes-dashboard) | Generates a self signed certificate.  |
| [capture_events](https://discourse.charmhub.io/t/harness-recipe-capture-events/6581) | [traefik-k8s](https://charmhub.io/traefik-k8s), [data-platform-libs](https://github.com/canonical/data-platform-libs/) | Helper for unittesting events.  |
| [networking](https://discourse.charmhub.io/t/harness-and-network-mocks/6633) | <your charm here?> | Provides tools for mocking networks.  |
| [compound-status](https://charmhub.io/compound-status) | <your charm here?> | Provides utilities to track multiple independent statuses in charms.  |
| [resurrect](https://github.com/PietroPasotti/resurrect) | [github-runner-image-builder](https://github.com/canonical/github-runner-image-builder-operator) | Provides utilities to periodically trigger charm hooks.  |


#### Libraries that provide tools for Kubernetes charms

These libraries provide tooling for charms that run on top of Kubernetes clouds.

| Library | Used in | Description |
| --- | --- | --- |
| [kubernetes_service_patch](https://charmhub.io/observability-libs/libraries/kubernetes_service_patch) | [cos-configuration-k8s](https://charmhub.io/cos-configuration-k8s), [alertmanager-k8s](https://charmhub.io/alertmanager-k8s), [grafana-agent-k8s](https://charmhub.io/grafana-agent-k8s), [prometheus-k8s](https://charmhub.io/prometheus-k8s), [loki-k8s](https://charmhub.io/loki-k8s), [traefik-k8s](https://charmhub.io/traefik-k8s) | Allows charm authors to simply and elegantly define service overrides that persist through a charm upgrade. |
| [ingress](https://charmhub.io/nginx-ingress-integrator/libraries/ingress) | [nginx-ingress-integrator](https://charmhub.io/nginx-ingress-integrator) | Configures nginx to use an existing Kubernetes Ingress. |
| [ingress-per-unit](https://charmhub.io/traefik-k8s/libraries/ingress_per_unit) | [traefik-k8s](https://charmhub.io/traefik-k8s) | Configures traefik to provide per-unit routing. |

#### Libraries that provide tools for machine charms

These libraries contain tools meant for use in machine charms, e.g., libraries that interact with package managers or other CLI tools that are often not present in containers.

| Library | Used in | Description |
| --- | --- | --- |
| [apt](https://charmhub.io/operator-libs-linux/libraries/apt) | [mysql](https://charmhub.io/mysql), [zookeeper](https://charmhub.io/zookeeper), [cos-proxy](https://charmhub.io/cos-proxy), [kafka](https://charmhub.io/kafka), [ceph-mon](https://charmhub.io/ceph-mon) | Install and manage packages via `apt`. |
| [dnf](https://charmhub.io/operator-libs-linux/libraries/dnf) | | Install and manage packages via `dnf`. |
| [grub](https://charmhub.io/operator-libs-linux/libraries/grub) | | Manage kernel configuration via `grub`. |
| [passwd](https://charmhub.io/operator-libs-linux/libraries/passwd) | | Manage users and groups on a Linux system. |
| [snap](https://charmhub.io/operator-libs-linux/libraries/snap) | [mongodb](https://charmhub.io/mongodb), [mongodb-k8s](https://charmhub.io/mongodb-k8s), [postgresql](https://charmhub.io/postgresql), [grafana-agent-k8s](https://charmhub.io/grafana-agent-k8s), [kafka](https://charmhub.io/kafka) | Install and manage packages via `snapd`. |
| [sysctl](https://charmhub.io/operator-libs-linux/libraries/sysctl) | [kafka](https://charmhub.io/kafka) | Manage sysctl configuration. |
| [systemd](https://charmhub.io/operator-libs-linux/libraries/systemd) | [mongodb](https://charmhub.io/mongodb), [pgbouncer](https://charmhub.io/pgbouncer), [cos-proxy](https://charmhub.io/cos-proxy), [ceph-mon](https://charmhub.io/ceph-mon), [calico](https://charmhub.io/calico) | Interact with services via `systemd`. |

