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
"""Charmcraft commands."""

from charmcraft.application.commands.init import InitCommand
from charmcraft.application.commands.lifecycle import (
    get_lifecycle_command_group,
    BuildCommand,
    CleanCommand,
    PackCommand,
    PullCommand,
    PrimeCommand,
    StageCommand,
)
from charmcraft.application.commands.store import (
    # auth
    LoginCommand,
    LogoutCommand,
    WhoamiCommand,
    # name handling
    RegisterCharmNameCommand,
    RegisterBundleNameCommand,
    UnregisterNameCommand,
    ListNamesCommand,
    # pushing files and checking revisions
    UploadCommand,
    ListRevisionsCommand,
    # release process, and show status
    ReleaseCommand,
    PromoteBundleCommand,
    StatusCommand,
    CloseCommand,
    # libraries support
    CreateLibCommand,
    PublishLibCommand,
    ListLibCommand,
    FetchLibCommand,
    # resources support
    ListResourcesCommand,
    ListResourceRevisionsCommand,
    UploadResourceCommand,
)
from charmcraft.application.commands.version import Version

__all__ = [
    "InitCommand",
    "get_lifecycle_command_group",
    "BuildCommand",
    "CleanCommand",
    "PackCommand",
    "PrimeCommand",
    "PullCommand",
    "StageCommand",
    "LoginCommand",
    "LogoutCommand",
    "WhoamiCommand",
    "RegisterCharmNameCommand",
    "RegisterBundleNameCommand",
    "UnregisterNameCommand",
    "ListNamesCommand",
    "UploadCommand",
    "ListRevisionsCommand",
    "ReleaseCommand",
    "PromoteBundleCommand",
    "StatusCommand",
    "CloseCommand",
    "CreateLibCommand",
    "PublishLibCommand",
    "ListLibCommand",
    "FetchLibCommand",
    "ListResourcesCommand",
    "ListResourceRevisionsCommand",
    "UploadResourceCommand",
]
