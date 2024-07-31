# Copyright 2023 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For further info, check https://github.com/canonical/charmcraft
import os
from textwrap import dedent

import yaml

from charmcraft import const
from charmcraft.config import load
from charmcraft.metafiles.actions import create_actions_yaml
from charmcraft.metafiles.metadata import create_metadata_yaml


def test_dump_metadata_from_charmcraft_yaml(tmp_path, prepare_charmcraft_yaml):
    """Dump a metadata.yaml with full metadata. (Spec ST087)"""
    prepare_charmcraft_yaml(
        dedent(
            """
            name: test-charm-name
            type: charm
            summary: test-summary
            description: test-description

            bases:
              - name: test-name
                channel: test-channel

            assumes:
              - test-feature
              - any-of:
                  - extra-feature-1
                  - extra-feature-2
                  - all-of:
                    - juju >= 2.9.44
                    - juju < 3
                  - all-of:
                    - juju >= 3.1.6
                    - juju < 4
              - all-of:
                  - test-feature-1
                  - test-feature-2

            containers:
              container-1:
                resource: resource-1
                bases:
                  - name: ubuntu
                    channel: 22.04
                    architectures:
                      - x86_64
                mounts:
                  - storage: storage-1
                    location: /var/lib/storage-1
              container-2:
                resource: resource-2
                bases:
                  - name: ubuntu
                    channel: 22.04
                    architectures:
                      - x86_64
                mounts:
                  - storage: storage-2
                    location: /var/lib/storage-2

            devices:
              test-device-1:
                  type: gpu
                  description: gpu
                  countmin: 1
                  countmax: 10

            title: test-title

            extra-bindings:
              test-binding-1: binding-1

            links:
              issues: https://example.com/issues
              contact:
                - https://example.com/contact
                - contact@example.com
                - "IRC #example"
              documentation: https://example.com/docs
              source:
                - https://example.com/source
                - https://example.com/source2
                - https://example.com/source3
              website:
                - https://example.com/

            peers:
              peer-1:
                interface: eth0
                limit: 1
                optional: true
                scope: global

            provides:
              provide-1:
                interface: eht1
                limit: 1
                optional: true
                scope: global

            requires:
              peer-1:
                interface: eth0
                limit: 1
                optional: true
                scope: global

            resources:
                resource-1:
                type: file
                description: resource-1
                filename: /path/to/resource-1

            storage:
              storage-1:
                type: filesystem
                description: storage-1
                location: /var/lib/storage-1
                shared: true
                read-only: false
                multiple: 5G
                minimum-size: 5G
                properties:
                  - transient

            subordinate: true

            terms:
              - https://example.com/terms
              - https://example.com/terms2
            """
        ),
    )

    config = load(tmp_path)

    create_metadata_yaml(tmp_path, config)

    metadata = yaml.safe_load((tmp_path / const.METADATA_FILENAME).read_text())

    assert metadata == {
        "name": "test-charm-name",
        "summary": "test-summary",
        "description": "test-description",
        "assumes": [
            "test-feature",
            {
                "any-of": [
                    "extra-feature-1",
                    "extra-feature-2",
                    {"all-of": ["juju >= 2.9.44", "juju < 3"]},
                    {"all-of": ["juju >= 3.1.6", "juju < 4"]},
                ]
            },
            {"all-of": ["test-feature-1", "test-feature-2"]},
        ],
        "containers": {
            "container-1": {
                "resource": "resource-1",
                "bases": [{"name": "ubuntu", "channel": 22.04, "architectures": ["x86_64"]}],
                "mounts": [{"storage": "storage-1", "location": "/var/lib/storage-1"}],
            },
            "container-2": {
                "resource": "resource-2",
                "bases": [{"name": "ubuntu", "channel": 22.04, "architectures": ["x86_64"]}],
                "mounts": [{"storage": "storage-2", "location": "/var/lib/storage-2"}],
            },
        },
        "devices": {
            "test-device-1": {"type": "gpu", "description": "gpu", "countmin": 1, "countmax": 10}
        },
        "display-name": "test-title",
        "peers": {
            "peer-1": {"interface": "eth0", "limit": 1, "optional": True, "scope": "global"}
        },
        "provides": {
            "provide-1": {"interface": "eht1", "limit": 1, "optional": True, "scope": "global"}
        },
        "requires": {
            "peer-1": {"interface": "eth0", "limit": 1, "optional": True, "scope": "global"}
        },
        "resources": {
            "resource-1": None,
            "type": "file",
            "description": "resource-1",
            "filename": "/path/to/resource-1",
        },
        "storage": {
            "storage-1": {
                "type": "filesystem",
                "description": "storage-1",
                "location": "/var/lib/storage-1",
                "shared": True,
                "read-only": False,
                "multiple": "5G",
                "minimum-size": "5G",
                "properties": ["transient"],
            }
        },
        "subordinate": True,
        "terms": ["https://example.com/terms", "https://example.com/terms2"],
        "extra-bindings": {"test-binding-1": "binding-1"},
        "docs": "https://example.com/docs",
        "issues": "https://example.com/issues",
        "maintainers": ["https://example.com/contact", "contact@example.com", "IRC #example"],
        "source": [
            "https://example.com/source",
            "https://example.com/source2",
            "https://example.com/source3",
        ],
        "website": ["https://example.com/"],
    }


def test_copy_metadata_from_metadata_yaml(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml
):
    """Copy a metadata.yaml with full metadata. (Spec ST087)"""
    prepare_charmcraft_yaml(
        dedent(
            """
            type: charm
            bases:
              - name: test-name
                channel: test-channel
            """
        )
    )
    prepare_metadata_yaml(
        dedent(
            """
            name: test-charm-name
            summary: test-summary
            description: test-description
            assumes:
              - test-feature
              - any-of:
                  - extra-feature-1
                  - extra-feature-2
                  - all-of:
                    - juju >= 2.9.44
                    - juju < 3
                  - all-of:
                    - juju >= 3.1.6
                    - juju < 4
              - all-of:
                  - test-feature-1
                  - test-feature-2

            containers:
              container-1:
                resource: resource-1
                bases:
                  - name: ubuntu
                    channel: 22.04
                    architectures:
                      - x86_64
                mounts:
                  - storage: storage-1
                    location: /var/lib/storage-1
              container-2:
                resource: resource-2
                bases:
                  - name: ubuntu
                    channel: 22.04
                    architectures:
                      - x86_64
                mounts:
                  - storage: storage-2
                    location: /var/lib/storage-2

            devices:
              test-device-1:
                  type: gpu
                  description: gpu
                  countmin: 1
                  countmax: 10

            display-name: test-title

            docs: https://example.com/docs

            extra-bindings:
              test-binding-1: binding-1

            issues: https://example.com/issues

            maintainers:
              - https://example.com/contact
              - contact@example.com
              - "IRC #example"

            peers:
              peer-1:
                interface: eth0
                limit: 1
                optional: true
                scope: global

            provides:
              provide-1:
                interface: eht1
                limit: 1
                optional: true
                scope: global

            requires:
              peer-1:
                interface: eth0
                limit: 1
                optional: true
                scope: global

            resources:
                resource-1:
                type: file
                description: resource-1
                filename: /path/to/resource-1

            source:
              - https://example.com/source
              - https://example.com/source2
              - https://example.com/source3

            storage:
              storage-1:
                type: filesystem
                description: storage-1
                location: /var/lib/storage-1
                shared: true
                read-only: false
                multiple: 5G
                minimum-size: 5G
                properties:
                  - transient

            subordinate: true

            terms:
              - https://example.com/terms
              - https://example.com/terms2

            website:
              - https://example.com/

            #### TEST-COPY ####
            """
        ),
    )

    config = load(tmp_path)

    os.mkdir(tmp_path / "new")

    create_metadata_yaml(tmp_path / "new", config)

    metadata_yaml = (tmp_path / "new" / const.METADATA_FILENAME).read_text()

    # Copy will preserve the TEST-COPY comment
    assert "TEST-COPY" in metadata_yaml

    metadata = yaml.safe_load(metadata_yaml)

    assert metadata == {
        "name": "test-charm-name",
        "summary": "test-summary",
        "description": "test-description",
        "assumes": [
            "test-feature",
            {
                "any-of": [
                    "extra-feature-1",
                    "extra-feature-2",
                    {"all-of": ["juju >= 2.9.44", "juju < 3"]},
                    {"all-of": ["juju >= 3.1.6", "juju < 4"]},
                ]
            },
            {"all-of": ["test-feature-1", "test-feature-2"]},
        ],
        "containers": {
            "container-1": {
                "resource": "resource-1",
                "bases": [{"name": "ubuntu", "channel": 22.04, "architectures": ["x86_64"]}],
                "mounts": [{"storage": "storage-1", "location": "/var/lib/storage-1"}],
            },
            "container-2": {
                "resource": "resource-2",
                "bases": [{"name": "ubuntu", "channel": 22.04, "architectures": ["x86_64"]}],
                "mounts": [{"storage": "storage-2", "location": "/var/lib/storage-2"}],
            },
        },
        "devices": {
            "test-device-1": {"type": "gpu", "description": "gpu", "countmin": 1, "countmax": 10}
        },
        "display-name": "test-title",
        "peers": {
            "peer-1": {"interface": "eth0", "limit": 1, "optional": True, "scope": "global"}
        },
        "provides": {
            "provide-1": {"interface": "eht1", "limit": 1, "optional": True, "scope": "global"}
        },
        "requires": {
            "peer-1": {"interface": "eth0", "limit": 1, "optional": True, "scope": "global"}
        },
        "resources": {
            "resource-1": None,
            "type": "file",
            "description": "resource-1",
            "filename": "/path/to/resource-1",
        },
        "storage": {
            "storage-1": {
                "type": "filesystem",
                "description": "storage-1",
                "location": "/var/lib/storage-1",
                "shared": True,
                "read-only": False,
                "multiple": "5G",
                "minimum-size": "5G",
                "properties": ["transient"],
            }
        },
        "subordinate": True,
        "terms": ["https://example.com/terms", "https://example.com/terms2"],
        "extra-bindings": {"test-binding-1": "binding-1"},
        "docs": "https://example.com/docs",
        "issues": "https://example.com/issues",
        "maintainers": ["https://example.com/contact", "contact@example.com", "IRC #example"],
        "source": [
            "https://example.com/source",
            "https://example.com/source2",
            "https://example.com/source3",
        ],
        "website": ["https://example.com/"],
    }


def test_copy_metadata_from_metadata_yaml_with_arbitrary_keys(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml
):
    """Copy a metadata.yaml with full metadata. (Spec ST087)"""
    prepare_charmcraft_yaml(
        dedent(
            """
            type: charm
            bases:
              - name: test-name
                channel: test-channel
            """
        )
    )
    prepare_metadata_yaml(
        dedent(
            """
            name: test-charm-name
            summary: test-summary
            description: test-description
            assumes:
              - test-feature
              - any-of:
                  - extra-feature-1
                  - extra-feature-2
              - all-of:
                  - test-feature-1
                  - test-feature-2

            containers:
              container-1:
                resource: resource-1
                bases:
                  - name: ubuntu
                    channel: 22.04
                    architectures:
                      - x86_64
                mounts:
                  - storage: storage-1
                    location: /var/lib/storage-1
              container-2:
                resource: resource-2
                bases:
                  - name: ubuntu
                    channel: 22.04
                    architectures:
                      - x86_64
                mounts:
                  - storage: storage-2
                    location: /var/lib/storage-2

            devices:
              test-device-1:
                  type: gpu
                  description: gpu
                  countmin: 1
                  countmax: 10

            display-name: test-title

            docs: https://example.com/docs

            extra-bindings:
              test-binding-1: binding-1

            issues: https://example.com/issues

            maintainers:
              - https://example.com/contact
              - contact@example.com
              - "IRC #example"

            peers:
              peer-1:
                interface: eth0
                limit: 1
                optional: true
                scope: global

            provides:
              provide-1:
                interface: eht1
                limit: 1
                optional: true
                scope: global

            requires:
              peer-1:
                interface: eth0
                limit: 1
                optional: true
                scope: global

            resources:
                resource-1:
                type: file
                description: resource-1
                filename: /path/to/resource-1

            source:
              - https://example.com/source
              - https://example.com/source2
              - https://example.com/source3

            storage:
              storage-1:
                type: filesystem
                description: storage-1
                location: /var/lib/storage-1
                shared: true
                read-only: false
                multiple: 5G
                minimum-size: 5G
                properties:
                  - transient

            subordinate: true

            terms:
              - https://example.com/terms
              - https://example.com/terms2

            website:
              - https://example.com/

            test-arbitrary-key: test-arbitrary-value
            test-arbitrary-key-2: test-arbitrary-value-2

            #### TEST-COPY ####
            """
        ),
    )

    config = load(tmp_path)

    os.mkdir(tmp_path / "new")

    create_metadata_yaml(tmp_path / "new", config)

    metadata_yaml = (tmp_path / "new" / const.METADATA_FILENAME).read_text()

    # Copy will preserve the TEST-COPY comment
    assert "TEST-COPY" in metadata_yaml

    metadata = yaml.safe_load(metadata_yaml)

    assert metadata == {
        "name": "test-charm-name",
        "summary": "test-summary",
        "description": "test-description",
        "assumes": [
            "test-feature",
            {"any-of": ["extra-feature-1", "extra-feature-2"]},
            {"all-of": ["test-feature-1", "test-feature-2"]},
        ],
        "containers": {
            "container-1": {
                "resource": "resource-1",
                "bases": [{"name": "ubuntu", "channel": 22.04, "architectures": ["x86_64"]}],
                "mounts": [{"storage": "storage-1", "location": "/var/lib/storage-1"}],
            },
            "container-2": {
                "resource": "resource-2",
                "bases": [{"name": "ubuntu", "channel": 22.04, "architectures": ["x86_64"]}],
                "mounts": [{"storage": "storage-2", "location": "/var/lib/storage-2"}],
            },
        },
        "devices": {
            "test-device-1": {"type": "gpu", "description": "gpu", "countmin": 1, "countmax": 10}
        },
        "display-name": "test-title",
        "peers": {
            "peer-1": {"interface": "eth0", "limit": 1, "optional": True, "scope": "global"}
        },
        "provides": {
            "provide-1": {"interface": "eht1", "limit": 1, "optional": True, "scope": "global"}
        },
        "requires": {
            "peer-1": {"interface": "eth0", "limit": 1, "optional": True, "scope": "global"}
        },
        "resources": {
            "resource-1": None,
            "type": "file",
            "description": "resource-1",
            "filename": "/path/to/resource-1",
        },
        "storage": {
            "storage-1": {
                "type": "filesystem",
                "description": "storage-1",
                "location": "/var/lib/storage-1",
                "shared": True,
                "read-only": False,
                "multiple": "5G",
                "minimum-size": "5G",
                "properties": ["transient"],
            }
        },
        "subordinate": True,
        "terms": ["https://example.com/terms", "https://example.com/terms2"],
        "extra-bindings": {"test-binding-1": "binding-1"},
        "docs": "https://example.com/docs",
        "issues": "https://example.com/issues",
        "maintainers": ["https://example.com/contact", "contact@example.com", "IRC #example"],
        "source": [
            "https://example.com/source",
            "https://example.com/source2",
            "https://example.com/source3",
        ],
        "website": ["https://example.com/"],
        "test-arbitrary-key": "test-arbitrary-value",
        "test-arbitrary-key-2": "test-arbitrary-value-2",
    }


def test_copy_bundle_metadata_from_metadata_yaml(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml
):
    """Copy a metadata.yaml when type is bundle."""
    prepare_charmcraft_yaml(
        dedent(
            """
            type: bundle
            """
        ),
    )
    prepare_metadata_yaml(
        dedent(
            """
            name: test-charm-name
            description: This is a test bundle.

            variables:
              data-port:           &data-port            br-ex:eno2
              worker-multiplier:   &worker-multiplier    0.25


            series: bionic

            tags: [monitoring]

            tags: [database, utility]


            applications:
              easyrsa:
                charm: containers-easyrsa
                revision: 8
                channel: latest/edge
                series: bionic

                resources:
                  easyrsa: 5

                resources:
                  easyrsa: ./relative/path/to/file

                resources:
                  easyrsa: /absolute/path/to/file

                num_units: 2

                to: 3, new
                to: ["django/0", "django/1", "django/2"]
                to: ["django"]
                to: ["lxd"]
                to: ["lxd:2", "lxd:3"]
                to: ["lxd:nova-compute/2", "lxd:glance/3"]

                expose: true

                offers:
                  my-offer:
                    endpoints:
                    - apache-website
                    acl:
                      admin: admin
                      user1: read

                options:
                  osd-devices: /dev/sdb
                  worker-multiplier: *worker-multiplier

                annotations:
                  gui-x: 450
                  gui-y: 550

                constraints: root-disk=8G

                constraints: cores=4 mem=4G root-disk=16G

                constraints: zones=us-east-1a

                storage:
                  database: ebs,10G,1

                bindings:
                  "": alpha
                  kube-api-endpoint: internal
                  loadbalancer: dmz

                plan: acme-support/default

            machines:
              "1":
              "2":
                series: bionic
                constraints: cores=2 mem=2G
              "3":
                constraints: cores=3 root-disk=1T

            relations:
            - - kubernetes-master:kube-api-endpoint
              - kubeapi-load-balancer:apiserver
            - - kubernetes-master:loadbalancer
              - kubeapi-load-balancer:loadbalancer

            saas:
              svc1:
                url: localoffer.svc1
              svc2:
                url: admin/localoffer.svc2
              svc3:
                url: othercontroller:admin/offer.svc3

            #### TEST-COPY ####
            """
        ),
    )

    config = load(tmp_path)

    os.mkdir(tmp_path / "new")

    create_metadata_yaml(tmp_path / "new", config)

    metadata_yaml = (tmp_path / "new" / const.METADATA_FILENAME).read_text()

    # Copy will preserve the TEST-COPY comment
    assert "TEST-COPY" in metadata_yaml


def test_dump_actions_from_charmcraft_yaml(tmp_path, prepare_charmcraft_yaml):
    """Dump a actions.yaml from charmcraft.yaml."""
    prepare_charmcraft_yaml(
        dedent(
            """
            name: test-charm-name
            type: charm
            summary: test-summary
            description: test-description

            bases:
              - name: test-name
                channel: test-channel

            actions:
              pause:
                description: Pause the database.
              resume:
                description: Resume a paused database.
              snapshot:
                description: Take a snapshot of the database.
                params:
                  filename:
                    type: string
                    description: The name of the snapshot file.
                  compression:
                    type: object
                    description: The type of compression to use.
                    properties:
                      kind:
                        type: string
                        enum: [gzip, bzip2, xz]
                      quality:
                        description: Compression quality
                        type: integer
                        minimum: 0
                        maximum: 9
                required: [filename]
                additionalProperties: false
            """
        ),
    )

    config = load(tmp_path)

    create_actions_yaml(tmp_path, config)

    actions = yaml.safe_load((tmp_path / const.JUJU_ACTIONS_FILENAME).read_text())

    assert actions == {
        "pause": {"description": "Pause the database."},
        "resume": {"description": "Resume a paused database."},
        "snapshot": {
            "description": "Take a snapshot of the database.",
            "params": {
                "filename": {
                    "type": "string",
                    "description": "The name of the snapshot file.",
                },
                "compression": {
                    "type": "object",
                    "description": "The type of compression to use.",
                    "properties": {
                        "kind": {"type": "string", "enum": ["gzip", "bzip2", "xz"]},
                        "quality": {
                            "description": "Compression quality",
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 9,
                        },
                    },
                },
            },
            "required": ["filename"],
            "additionalProperties": False,
        },
    }


def test_copy_actions_from_actions_yaml(tmp_path, prepare_charmcraft_yaml, prepare_actions_yaml):
    """Dump a actions.yaml from charmcraft.yaml."""
    prepare_charmcraft_yaml(
        dedent(
            """
            name: test-charm-name
            type: charm
            summary: test-summary
            description: test-description
            """
        ),
    )
    prepare_actions_yaml(
        dedent(
            """
            pause:
              description: Pause the database.
            resume:
              description: Resume a paused database.
            snapshot:
              description: Take a snapshot of the database.
              params:
                filename:
                  type: string
                  description: The name of the snapshot file.
                compression:
                  type: object
                  description: The type of compression to use.
                  properties:
                    kind:
                      type: string
                      enum: [gzip, bzip2, xz]
                    quality:
                      description: Compression quality
                      type: integer
                      minimum: 0
                      maximum: 9
              required: [filename]
              additionalProperties: false
            #### TEST-COPY ####
            """
        ),
    )

    config = load(tmp_path)

    os.mkdir(tmp_path / "new")

    create_actions_yaml(tmp_path / "new", config)

    actions_yaml = (tmp_path / "new" / const.JUJU_ACTIONS_FILENAME).read_text()

    # Copy will preserve the TEST-COPY comment
    assert "TEST-COPY" in actions_yaml

    actions = yaml.safe_load(actions_yaml)

    assert actions == {
        "pause": {"description": "Pause the database."},
        "resume": {"description": "Resume a paused database."},
        "snapshot": {
            "description": "Take a snapshot of the database.",
            "params": {
                "filename": {
                    "type": "string",
                    "description": "The name of the snapshot file.",
                },
                "compression": {
                    "type": "object",
                    "description": "The type of compression to use.",
                    "properties": {
                        "kind": {"type": "string", "enum": ["gzip", "bzip2", "xz"]},
                        "quality": {
                            "description": "Compression quality",
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 9,
                        },
                    },
                },
            },
            "required": ["filename"],
            "additionalProperties": False,
        },
    }
