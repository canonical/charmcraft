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
"""Unit tests for lifecycle commands."""
import argparse
import pathlib

import craft_cli
import pytest

from charmcraft import application, services
from charmcraft.application.commands import lifecycle


def get_namespace(
    *,
    bases_index=None,
    debug=False,
    destructive_mode=False,
    force=None,
    shell=False,
    shell_after=False,
    format=None,
    measure=None,
    include_all_charms: bool = False,
    include_charm: list[pathlib.Path] | None = None,
    output_bundle: pathlib.Path | None = None,
    parts: list[str] | None = None,
) -> argparse.Namespace:
    if bases_index is None:
        bases_index = []

    return argparse.Namespace(
        bases_index=bases_index,
        debug=debug,
        destructive_mode=destructive_mode,
        force=force,
        shell=shell,
        shell_after=shell_after,
        format=format,
        measure=measure,
        include_all_charms=include_all_charms,
        include_charm=include_charm,
        output_bundle=output_bundle,
        parts=parts,
    )


@pytest.fixture
def pack(service_factory: services.ServiceFactory) -> lifecycle.PackCommand:
    return lifecycle.PackCommand({"app": application.APP_METADATA, "services": service_factory})


@pytest.mark.parametrize(
    ("platform", "expected"),
    [
        ("linux", False),
        ("macos", True),
        ("win32", True),
    ],
)
def test_pack_run_managed_bundle_by_os(monkeypatch, new_path, platform, expected):
    """When packing a bundle, run_managed should return False if and only if we're on posix."""
    monkeypatch.setattr("sys.platform", platform)
    (new_path / "charmcraft.yaml").write_text("type: bundle")

    pack = lifecycle.PackCommand(None)

    result = pack.run_managed(argparse.Namespace(destructive_mode=False))

    assert result == expected


@pytest.mark.parametrize(
    ("command_args", "message_start", "project_type"),
    [
        pytest.param(
            get_namespace(include_all_charms=True),
            "--include-all-charms can only be used when packing a bundle. Currently trying ",
            "charm",
            id="include_all_charms_on_charm",
        ),
        pytest.param(
            get_namespace(include_charm=[pathlib.Path("a")]),
            "--include-charm can only be used when packing a bundle. Currently trying to pack: ",
            "charm",
            id="include_charm_on_charm",
        ),
        pytest.param(
            get_namespace(output_bundle=pathlib.Path("output.yaml")),
            "--output-bundle can only be used when packing a bundle. Currently trying to pack: ",
            "charm",
            id="output_bundle_on_charm",
        ),
    ],
)
def test_pack_invalid_arguments(
    monkeypatch,
    pack: lifecycle.PackCommand,
    command_args: argparse.Namespace,
    message_start: str,
    project_type,
) -> None:
    monkeypatch.setattr("craft_parts.utils.os_utils.OsRelease.id", lambda: "ubuntu")

    with pytest.raises(craft_cli.ArgumentParsingError) as exc_info:
        pack.run(command_args)

    assert exc_info.value.args[0].startswith(message_start)
