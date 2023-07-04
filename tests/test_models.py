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

from textwrap import dedent

import pytest
from craft_cli import CraftError
from pydantic import AnyHttpUrl
from pydantic.tools import parse_obj_as

from charmcraft.models.charmcraft import (
    Base,
    BasesConfiguration,
    Links,
)
from charmcraft.config import load
from charmcraft.utils import get_host_architecture
from charmcraft.metafiles.metadata import parse_charm_metadata_yaml


def test_load_minimal_metadata_from_charmcraft_yaml(tmp_path, prepare_charmcraft_yaml):
    """Load a mimimal charmcraft.yaml with full metadata. (Spec ST087)"""
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
            """
        )
    )

    config = load(tmp_path)

    assert config.name == "test-charm-name"
    assert config.type == "charm"
    assert config.summary == "test-summary"
    assert config.description == "test-description"
    assert config.bases == [
        BasesConfiguration(
            **{
                "build-on": [
                    Base(
                        name="test-name",
                        channel="test-channel",
                        architectures=[get_host_architecture()],
                    )
                ],
                "run-on": [
                    Base(
                        name="test-name",
                        channel="test-channel",
                        architectures=[get_host_architecture()],
                    )
                ],
            }
        )
    ]
    assert not config.metadata_legacy


def test_load_minimal_metadata_from_charmcraft_yaml_missing_name(
    tmp_path, prepare_charmcraft_yaml
):
    """Load a mimimal charmcraft.yaml with metadata. But missing name."""
    prepare_charmcraft_yaml(
        dedent(
            """
            type: charm
            summary: test-summary
            description: test-description

            bases:
              - name: test-name
                channel: test-channel
            """
        )
    )

    with pytest.raises(CraftError, match="needs value in field 'name'"):
        load(tmp_path)


def test_load_minimal_metadata_from_charmcraft_yaml_missing_type(
    tmp_path, prepare_charmcraft_yaml
):
    """Load a mimimal charmcraft.yaml with metadata. But missing type."""
    prepare_charmcraft_yaml(
        dedent(
            """
            name: test-charm-name
            summary: test-summary
            description: test-description

            bases:
              - name: test-name
                channel: test-channel
            """
        ),
    )

    with pytest.raises(CraftError, match="field 'type' required in top-level configuration"):
        load(tmp_path)


def test_load_minimal_metadata_from_charmcraft_yaml_missing_summary(
    tmp_path, prepare_charmcraft_yaml
):
    """Load a mimimal charmcraft.yaml with metadata. But missing summary."""
    prepare_charmcraft_yaml(
        dedent(
            """
            name: test-charm-name
            type: charm
            description: test-description

            bases:
              - name: test-name
                channel: test-channel
            """
        ),
    )

    with pytest.raises(CraftError, match="needs value in field 'summary'"):
        load(tmp_path)


def test_load_minimal_metadata_from_charmcraft_yaml_missing_description(
    tmp_path, prepare_charmcraft_yaml
):
    """Load a mimimal charmcraft.yaml with metadata. But missing description."""
    prepare_charmcraft_yaml(
        dedent(
            """
            name: test-charm-name
            type: charm
            summary: test-summary

            bases:
              - name: test-name
                channel: test-channel
            """
        ),
    )

    with pytest.raises(CraftError, match="needs value in field 'description'"):
        load(tmp_path)


def test_load_minimal_metadata_from_metadata_yaml(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml
):
    """Load a mimimal charmcraft.yaml with full metadata. (Spec ST087)"""
    prepare_charmcraft_yaml(
        dedent(
            """
            type: charm

            bases:
              - name: test-name
                channel: test-channel
            """
        ),
    )
    prepare_metadata_yaml(
        dedent(
            """
            name: test-charm-name
            summary: test-summary
            description: test-description
            """
        ),
    )

    config = load(tmp_path)

    assert config.name == "test-charm-name"
    assert config.type == "charm"
    assert config.summary == "test-summary"
    assert config.description == "test-description"
    assert config.bases == [
        BasesConfiguration(
            **{
                "build-on": [
                    Base(
                        name="test-name",
                        channel="test-channel",
                        architectures=[get_host_architecture()],
                    )
                ],
                "run-on": [
                    Base(
                        name="test-name",
                        channel="test-channel",
                        architectures=[get_host_architecture()],
                    )
                ],
            }
        )
    ]
    assert config.metadata_legacy


def test_load_minimal_metadata_from_metadata_yaml_missing_name(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml
):
    """Load a mimimal charmcraft.yaml with metadata.yaml. But missing name."""
    prepare_charmcraft_yaml(
        dedent(
            """
            type: charm
            bases:
              - name: test-name
                channel: test-channel
            """
        ),
    )
    prepare_metadata_yaml(
        dedent(
            """
            summary: test-summary
            description: test-description
            """
        ),
    )

    with pytest.raises(CraftError, match="field 'name' required in top-level configuration"):
        load(tmp_path)


def test_load_minimal_metadata_from_metadata_yaml_missing_type(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml
):
    """Load a mimimal charmcraft.yaml with metadata.yaml. But missing type."""
    prepare_charmcraft_yaml(
        dedent(
            """
            bases:
              - name: test-name
                channel: test-channel
            """
        ),
    )
    prepare_metadata_yaml(
        dedent(
            """
            name: test-charm-name
            summary: test-summary
            description: test-description
            """
        ),
    )

    with pytest.raises(CraftError, match="field 'type' required in top-level configuration"):
        load(tmp_path)


def test_load_minimal_metadata_from_metadata_yaml_missing_summary(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml
):
    """Load a mimimal charmcraft.yaml with metadata.yaml. But missing summary."""
    prepare_charmcraft_yaml(
        dedent(
            """
            type: charm

            bases:
                - name: test-name
                  channel: test-channel
            """
        ),
    )
    prepare_metadata_yaml(
        dedent(
            """
            name: test-charm-name
            description: test-description
            """
        ),
    )

    with pytest.raises(CraftError, match="field 'summary' required in top-level configuration"):
        load(tmp_path)


def test_load_minimal_metadata_from_metadata_yaml_missing_description(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml
):
    """Load a mimimal charmcraft.yaml with metadata.yaml. But missing description."""
    prepare_charmcraft_yaml(
        dedent(
            """
            type: charm

            bases:
              - name: test-name
                channel: test-channel
            """
        ),
    )
    prepare_metadata_yaml(
        dedent(
            """
            name: test-charm-name
            summary: test-summary
            """
        ),
    )

    with pytest.raises(
        CraftError, match="field 'description' required in top-level configuration"
    ):
        load(tmp_path)


def test_load_full_metadata_from_charmcraft_yaml(tmp_path, prepare_charmcraft_yaml):
    """Load a charmcraft.yaml with full metadata. (Spec ST087)"""
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
                interface: eth1
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
    config_dict = config.dict()

    # remove unrelated keys. but they should exist in the config

    del config_dict["actions"]
    del config_dict["analysis"]
    del config_dict["charmhub"]
    del config_dict["config"]
    del config_dict["project"]
    del config_dict["parts"]

    assert config_dict == {
        "name": "test-charm-name",
        "type": "charm",
        "summary": "test-summary",
        "description": "test-description",
        "bases": [
            BasesConfiguration(
                **{
                    "build-on": [
                        Base(
                            name="test-name",
                            channel="test-channel",
                            architectures=[get_host_architecture()],
                        )
                    ],
                    "run-on": [
                        Base(
                            name="test-name",
                            channel="test-channel",
                            architectures=[get_host_architecture()],
                        )
                    ],
                }
            )
        ],
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
        "title": "test-title",
        "peers": {
            "peer-1": {"interface": "eth0", "limit": 1, "optional": True, "scope": "global"}
        },
        "provides": {
            "provide-1": {"interface": "eth1", "limit": 1, "optional": True, "scope": "global"}
        },
        "requires": {
            "peer-1": {"interface": "eth0", "limit": 1, "optional": True, "scope": "global"}
        },
        "resources": {
            "resource-1": {
                "type": "file",
                "description": "resource-1",
                "filename": "/path/to/resource-1",
            },
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
        "extra_bindings": {"test-binding-1": "binding-1"},
        "links": Links(
            contact=["https://example.com/contact", "contact@example.com", "IRC #example"],
            documentation=parse_obj_as(AnyHttpUrl, "https://example.com/docs"),
            issues=parse_obj_as(AnyHttpUrl, "https://example.com/issues"),
            source=[
                parse_obj_as(AnyHttpUrl, "https://example.com/source"),
                parse_obj_as(AnyHttpUrl, "https://example.com/source2"),
                parse_obj_as(AnyHttpUrl, "https://example.com/source3"),
            ],
            website=[parse_obj_as(AnyHttpUrl, "https://example.com/")],
        ),
        "metadata_legacy": False,
    }


def test_load_full_metadata_from_metadata_yaml(
    tmp_path, prepare_charmcraft_yaml, prepare_metadata_yaml
):
    """Load a charmcraft.yaml with full metadata.yaml. (Legacy)"""
    prepare_charmcraft_yaml(
        dedent(
            """
            type: charm
            bases:
              - name: test-name
                channel: test-channel
            """
        ),
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
                interface: eth1
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
            """
        ),
    )

    config = load(tmp_path)
    metadata = parse_charm_metadata_yaml(tmp_path)

    assert config.name == "test-charm-name"
    assert config.type == "charm"
    assert config.summary == "test-summary"
    assert config.description == "test-description"
    assert config.bases == [
        BasesConfiguration(
            **{
                "build-on": [
                    Base(
                        name="test-name",
                        channel="test-channel",
                        architectures=[get_host_architecture()],
                    )
                ],
                "run-on": [
                    Base(
                        name="test-name",
                        channel="test-channel",
                        architectures=[get_host_architecture()],
                    )
                ],
            }
        )
    ]
    assert config.metadata_legacy

    metadata_dict = metadata.dict()
    assert metadata_dict == {
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
        "display_name": "test-title",
        "peers": {
            "peer-1": {"interface": "eth0", "limit": 1, "optional": True, "scope": "global"}
        },
        "provides": {
            "provide-1": {"interface": "eth1", "limit": 1, "optional": True, "scope": "global"}
        },
        "requires": {
            "peer-1": {"interface": "eth0", "limit": 1, "optional": True, "scope": "global"}
        },
        "resources": {
            "resource-1": {
                "type": "file",
                "description": "resource-1",
                "filename": "/path/to/resource-1",
            },
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
        "extra_bindings": {"test-binding-1": "binding-1"},
        "docs": parse_obj_as(AnyHttpUrl, "https://example.com/docs"),
        "issues": parse_obj_as(AnyHttpUrl, "https://example.com/issues"),
        "maintainers": ["https://example.com/contact", "contact@example.com", "IRC #example"],
        "source": [
            parse_obj_as(AnyHttpUrl, "https://example.com/source"),
            parse_obj_as(AnyHttpUrl, "https://example.com/source2"),
            parse_obj_as(AnyHttpUrl, "https://example.com/source3"),
        ],
        "website": [parse_obj_as(AnyHttpUrl, "https://example.com/")],
    }


def test_load_full_actions_in_charmcraft_yaml(tmp_path, prepare_charmcraft_yaml):
    """Load a charmcraft.yaml with full actions."""
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
        )
    )

    config = load(tmp_path)

    assert config.actions.dict(include={"actions"}, exclude_none=True, by_alias=True)[
        "actions"
    ] == {
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


def test_load_full_actions_in_actions_yaml(
    tmp_path, prepare_charmcraft_yaml, prepare_actions_yaml
):
    """Load a charmcraft.yaml with full actions."""
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
            """
        ),
    )

    config = load(tmp_path)

    assert config.actions.dict(include={"actions"}, exclude_none=True, by_alias=True)[
        "actions"
    ] == {
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


@pytest.mark.parametrize(
    "bad_name",
    [
        "is",
        "-snapshot",
        "111snapshot",
    ],
)
def test_load_bad_actions_in_charmcraft_yaml(tmp_path, prepare_charmcraft_yaml, bad_name):
    """Load a bad actions in charmcraft.yaml."""
    prepare_charmcraft_yaml(
        dedent(
            f"""
            name: test-charm-name
            type: charm
            bases:
              - name: test-name
                channel: test-channel
            actions:
              pause:
                description: Pause the database.
              resume:
                description: Resume a paused database.
              {bad_name}:
                description: Take a snapshot of the database.
            """
        )
    )

    with pytest.raises(CraftError):
        load(tmp_path)


@pytest.mark.parametrize(
    "bad_name",
    [
        "is",
        "-snapshot",
        "111snapshot",
    ],
)
def test_load_bad_actions_in_actions_yaml(
    tmp_path, prepare_charmcraft_yaml, prepare_actions_yaml, bad_name
):
    """Load a bad actions in actions.yaml."""
    prepare_charmcraft_yaml(
        dedent(
            """
            name: test-charm-name
            type: charm
            bases:
              - name: test-name
                channel: test-channel
            """
        )
    )
    prepare_actions_yaml(
        dedent(
            f"""\
            actions:
              pause:
                description: Pause the database.
              resume:
                description: Resume a paused database.
              {bad_name}:
                description: Take a snapshot of the database.
            """
        )
    )

    with pytest.raises(CraftError):
        load(tmp_path)


def test_load_actions_in_charmcraft_yaml_and_actions_yaml(
    tmp_path, prepare_charmcraft_yaml, prepare_actions_yaml
):
    """Load actions in charmcraft.yaml and actions.yaml at the same time."""
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
    prepare_actions_yaml(
        dedent(
            """
            pause:
              description: Pause the database.
            """
        ),
    )

    msg = (
        "'actions.yaml' file not allowed when an 'actions' section "
        "is defined in 'charmcraft.yaml' in field 'actions'"
    )

    with pytest.raises(CraftError, match=msg):
        load(tmp_path)


def test_load_config_in_charmcraft_yaml(tmp_path, prepare_charmcraft_yaml):
    """Load a config in charmcraft.yaml."""
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

            config:
              options:
                test-int:
                  default: 123
                  description: test-1
                  type: int
                test-string:
                  description: test-2
                  type: string
                test-float:
                  default: 1.23
                  type: float
                test-bool:
                  default: true
                  type: boolean
            """
        )
    )
    config = load(tmp_path)

    assert config.config.dict(include={"options"}, by_alias=True) == {
        "options": {
            "test-int": {"default": 123, "description": "test-1", "type": "int"},
            "test-string": {"description": "test-2", "type": "string"},
            "test-float": {"default": 1.23, "type": "float"},
            "test-bool": {"default": True, "type": "boolean"},
        },
    }


def test_load_config_in_config_yaml(tmp_path, prepare_charmcraft_yaml, prepare_config_yaml):
    """Load a config in config.yaml."""
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
    prepare_config_yaml(
        dedent(
            """
            options:
              test-int:
                default: 123
                description: test-1
                type: int
              test-string:
                description: test-2
                type: string
              test-float:
                default: 1.23
                type: float
              test-bool:
                default: true
                type: boolean
            """
        ),
    )
    config = load(tmp_path)

    assert config.config.dict(include={"options"}, by_alias=True) == {
        "options": {
            "test-int": {"default": 123, "description": "test-1", "type": "int"},
            "test-string": {"description": "test-2", "type": "string"},
            "test-float": {"default": 1.23, "type": "float"},
            "test-bool": {"default": True, "type": "boolean"},
        },
    }


def test_load_bad_config_in_charmcraft_yaml(tmp_path, prepare_charmcraft_yaml):
    """Load a config in charmcraft.yaml."""
    prepare_charmcraft_yaml(
        dedent(
            """
            name: test-charm-name
            type: charm
            summary: test-summary
            description: test-description

            config:
              options:
                test-int:
                  default: 123
                  descriptionn: test-1
                  type: int
                test-string:
                  description: test-2
                  type: string
                test-float:
                  default: 1.23
                  type: float
                test-bool:
                  default: true
                  type: boolean
            """
        )
    )

    with pytest.raises(
        CraftError,
        match=r"'test-int' has an invalid key\(s\): {'descriptionn'} in field 'config.options'",
    ):
        load(tmp_path)
