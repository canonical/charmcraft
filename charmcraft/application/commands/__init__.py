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

import craft_application

from charmcraft.application.commands.analyse import Analyse, Analyze
from charmcraft.application.commands.extensions import (
    ListExtensionsCommand,
    ExtensionsCommand,
    ExpandExtensionsCommand,
)
from charmcraft.application.commands.init import InitCommand
from charmcraft.application.commands.lifecycle import (
    get_lifecycle_commands,
    PackCommand,
)
from charmcraft.application.commands.remote import RemoteBuild
from charmcraft.application.commands.store import (
    # auth
    FetchLibs,
    LoginCommand,
    LogoutCommand,
    WhoamiCommand,
    # name handling
    RegisterCharmNameCommand,
    UnregisterNameCommand,
    ListNamesCommand,
    # pushing files and checking revisions
    UploadCommand,
    ListRevisionsCommand,
    # release process, and show status
    CreateTrack,
    ReleaseCommand,
    PromoteCommand,
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
    SetResourceArchitecturesCommand,
    UploadResourceCommand,
)
from charmcraft.application.commands.version import Version


def fill_command_groups(app: craft_application.Application) -> None:
    """Fill in all the command groups for Charmcraft."""
    app.add_command_group(
        "Lifecycle", [*get_lifecycle_commands(), RemoteBuild], ordered=True
    )
    app.add_command_group(
        "Store (account)",
        [
            # auth
            LoginCommand,
            LogoutCommand,
            WhoamiCommand,
            # name handling
            RegisterCharmNameCommand,
            UnregisterNameCommand,
            ListNamesCommand,
        ],
    )
    app.add_command_group(
        "Store (charm)",
        [
            # pushing files and checking revisions
            UploadCommand,
            ListRevisionsCommand,
            # release process, and show status
            CreateTrack,
            ReleaseCommand,
            PromoteCommand,
            StatusCommand,
            CloseCommand,
            # resources support
            ListResourcesCommand,
            ListResourceRevisionsCommand,
            SetResourceArchitecturesCommand,
            UploadResourceCommand,
        ],
    )
    app.add_command_group(
        "Store (libraries)",
        [
            CreateLibCommand,
            PublishLibCommand,
            ListLibCommand,
            FetchLibs,
            FetchLibCommand,
        ],
    )
    app.add_command_group(
        "Extensions",
        [ExpandExtensionsCommand, ExtensionsCommand, ListExtensionsCommand],
    )
    app.add_command_group(
        "Other",
        [
            Analyse,
            Analyze,
            InitCommand,
            Version,
        ],
    )


__all__ = [
    "Analyse",
    "Analyze",
    "ListExtensionsCommand",
    "ExpandExtensionsCommand",
    "ExtensionsCommand",
    "InitCommand",
    "get_lifecycle_commands",
    "PackCommand",
    "LoginCommand",
    "LogoutCommand",
    "WhoamiCommand",
    "RegisterCharmNameCommand",
    "UnregisterNameCommand",
    "ListNamesCommand",
    "UploadCommand",
    "ListRevisionsCommand",
    "CreateTrack",
    "ReleaseCommand",
    "StatusCommand",
    "CloseCommand",
    "CreateLibCommand",
    "PublishLibCommand",
    "ListLibCommand",
    "FetchLibCommand",
    "ListResourcesCommand",
    "ListResourceRevisionsCommand",
    "SetResourceArchitecturesCommand",
    "TestCommand",
    "UploadResourceCommand",
]
