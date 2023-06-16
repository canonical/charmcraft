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

import yaml

from charmcraft.config import load
from charmcraft.metafiles.actions import create_actions_yaml


def test_create_actions_yaml(create_config, tmp_path):
    """create actions.yaml."""
    actions = {
        "actions": {
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
    }

    yaml_data = yaml.safe_dump(actions)

    create_config({"charmcraft.yaml_ext": "type: charm\n" + yaml_data})
    config = load(tmp_path)

    actions_file = create_actions_yaml(tmp_path, config)

    assert yaml.safe_load(actions_file.read_text()) == actions["actions"]


def test_create_actions_yaml_none(create_config, tmp_path):
    """create actions.yaml with None, the file should not exist."""
    create_config({"charmcraft.yaml_ext": "type: charm"})
    config = load(tmp_path)
    actions_file = create_actions_yaml(tmp_path, config)

    assert actions_file is None
    assert not os.path.exists(tmp_path / "actions.yaml")
