# Copyright 2024 Canonical Ltd.
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
import datetime

import pydantic
from craft_store import models


def get_fake_revision(**kwargs) -> models.resource_revision_model.CharmResourceRevision:
    data = {
        "bases": [],
        "created_at": datetime.datetime(2024, 1, 2, 4, 8, 16),
        "name": "my-resource",
        "revision": 0,
        "sha256": "sha256",
        "sha3_384": "sha3_384",
        "sha384": "sha384",
        "sha512": "sha512",
        "size": pydantic.ByteSize(0),
        "type": "file",
    }
    data.update(kwargs)
    return models.resource_revision_model.CharmResourceRevision(**data)
