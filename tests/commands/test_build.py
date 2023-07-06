# Copyright 2020-2022 Canonical Ltd.
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

import pathlib
import re
import subprocess
import sys
import zipfile
from textwrap import dedent
from typing import List
from unittest import mock
from unittest.mock import call, patch, MagicMock

import pytest
import yaml
from craft_cli import EmitterMode, emit, CraftError
from craft_providers import bases

from charmcraft import linters, instrum
from charmcraft.charm_builder import relativise
from charmcraft.bases import get_host_as_base
from charmcraft.commands.build import BUILD_DIRNAME, Builder, format_charm_file_name, launch_shell
from charmcraft.models.charmcraft import Base, BasesConfiguration
from charmcraft.config import load
from charmcraft.providers import get_base_configuration
from charmcraft.utils import get_host_architecture


def get_builder(
    config,
    *,
    project_dir=None,
    force=False,
    debug=False,
    shell=False,
    shell_after=False,
    measure=None,
):
    if project_dir is None:
        project_dir = config.project.dirpath

    return Builder(
        config=config,
        debug=debug,
        force=force,
        shell=shell,
        shell_after=shell_after,
        measure=measure,
    )


@pytest.fixture
def basic_project(tmp_path, monkeypatch, prepare_charmcraft_yaml, prepare_metadata_yaml):
    """Create a basic Charmcraft project."""
    build_dir = tmp_path / BUILD_DIRNAME
    build_dir.mkdir()

    # a lib dir
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    ops_lib_dir = lib_dir / "ops"
    ops_lib_dir.mkdir()
    ops_stuff = ops_lib_dir / "stuff.txt"
    ops_stuff.write_bytes(b"ops stuff")

    # simple source code
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    charm_script = src_dir / "charm.py"
    charm_script.write_bytes(b"all the magic")
    charm_script.chmod(0o755)

    # the license file
    license = tmp_path / "LICENSE"
    license.write_text("license content")

    # other optional assets
    icon = tmp_path / "icon.svg"
    icon.write_text("icon content")

    # README
    readme = tmp_path / "README.md"
    readme.write_text("README content")

    # the config
    host_base = get_host_as_base()
    prepare_charmcraft_yaml(
        dedent(
            f"""
            type: charm
            bases:
              - name: {host_base.name}
                channel: "{host_base.channel}"
                architectures: {host_base.architectures!r}
            parts:  # just to avoid "default charm parts" sneaking in
              foo:
                plugin: nil
            """
        )
    )
    prepare_metadata_yaml(
        dedent(
            """\
            name: test-charm-name-from-metadata-yaml
            summary: test summary
            description: test description
            """
        ),
    )
    # paths are relative, make all tests to run in the project's directory
    monkeypatch.chdir(tmp_path)

    yield tmp_path


@pytest.fixture
def basic_project_builder(basic_project, prepare_charmcraft_yaml):
    def _basic_project_builder(bases_configs: List[BasesConfiguration], **builder_kwargs):
        charmcraft_yaml = dedent(
            """
            type: charm
            bases:
            """
        )

        for bases_config in bases_configs:
            charmcraft_yaml += "  - build-on:\n"
            for base in bases_config.build_on:
                charmcraft_yaml += (
                    f"    - name: {base.name!r}\n"
                    f"      channel: {base.channel!r}\n"
                    f"      architectures: {base.architectures!r}\n"
                )

            charmcraft_yaml += "    run-on:\n"
            for base in bases_config.run_on:
                charmcraft_yaml += (
                    f"    - name: {base.name!r}\n"
                    f"      channel: {base.channel!r}\n"
                    f"      architectures: {base.architectures!r}\n"
                )
        charmcraft_yaml += dedent(
            """
            parts:
              foo:
                plugin: nil
            """
        )

        prepare_charmcraft_yaml(charmcraft_yaml)

        config = load(basic_project)
        return get_builder(config, **builder_kwargs)

    return _basic_project_builder


@pytest.fixture
def mock_capture_logs_from_instance():
    with patch("charmcraft.providers.capture_logs_from_instance") as mock_capture:
        yield mock_capture


@pytest.fixture
def mock_launch_shell():
    with patch("charmcraft.commands.build.launch_shell") as mock_shell:
        yield mock_shell


@pytest.fixture
def mock_linters():
    with patch("charmcraft.linters") as mock_linters:
        mock_linters.analyze.return_value = []
        yield mock_linters


@pytest.fixture
def mock_parts():
    with patch("charmcraft.parts") as mock_parts:
        yield mock_parts


@pytest.fixture(autouse=True)
def mock_provider(mock_instance, fake_provider):
    mock_provider = mock.Mock(wraps=fake_provider)
    with patch("charmcraft.providers.get_provider", return_value=mock_provider):
        yield mock_provider


@pytest.fixture()
def mock_ubuntu_buildd_base_configuration():
    with mock.patch("craft_providers.bases.ubuntu.BuilddBase", autospec=True) as mock_base_config:
        yield mock_base_config


@pytest.fixture()
def mock_centos_base_configuration():
    with mock.patch("craft_providers.bases.centos.CentOSBase", autospec=True) as mock_base_config:
        yield mock_base_config


@pytest.fixture()
def mock_instance_name():
    with mock.patch(
        "charmcraft.providers.get_instance_name", return_value="test-instance-name"
    ) as patched:
        yield patched


@pytest.fixture()
def mock_is_base_available():
    with mock.patch(
        "charmcraft.providers.is_base_available",
        return_value=(True, None),
    ) as mock_is_base_available:
        yield mock_is_base_available


# --- (real) build tests


def test_build_error_without_metadata_yaml(basic_project):
    """Validate error if trying to build project without metadata.yaml."""
    metadata = basic_project / "metadata.yaml"
    metadata.unlink()

    with pytest.raises(CraftError) as exc_info:
        config = load(basic_project)

        get_builder(config)

    assert exc_info.value.args[0] == (
        "Cannot read the metadata.yaml file: FileNotFoundError(2, 'No such file or directory')"
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_with_charmcraft_yaml_destructive_mode(basic_project_builder, emitter, monkeypatch):
    host_base = get_host_as_base()
    builder = basic_project_builder(
        [BasesConfiguration(**{"build-on": [host_base], "run-on": [host_base]})],
        force=True,  # to ignore any linter issue
    )

    zipnames = builder.run(destructive_mode=True)

    host_arch = host_base.architectures[0]
    assert zipnames == [
        "test-charm-name-from-metadata-yaml_"
        f"{host_base.name}-{host_base.channel}-{host_arch}.charm"
    ]

    emitter.assert_debug("Building for 'bases[0]' as host matches 'build-on[0]'.")


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_with_charmcraft_yaml_managed_mode(
    basic_project_builder, emitter, monkeypatch, tmp_path
):
    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    host_base = get_host_as_base()
    builder = basic_project_builder(
        [BasesConfiguration(**{"build-on": [host_base], "run-on": [host_base]})],
        force=True,  # to ignore any linter issue
    )

    with patch("charmcraft.env.get_managed_environment_home_path", return_value=tmp_path / "root"):
        zipnames = builder.run()

    host_arch = host_base.architectures[0]
    assert zipnames == [
        "test-charm-name-from-metadata-yaml_"
        f"{host_base.name}-{host_base.channel}-{host_arch}.charm"
    ]

    emitter.assert_debug("Building for 'bases[0]' as host matches 'build-on[0]'.")


def test_build_checks_provider(basic_project, mock_provider, mock_capture_logs_from_instance):
    """Test cases for base-index parameter."""
    config = load(basic_project)
    builder = get_builder(config)

    try:
        builder.run()
    except CraftError:
        # 'No suitable 'build-on' environment...' error will be raised on some test platforms
        pass

    mock_provider.ensure_provider_is_available.assert_called_once()


def test_build_with_debug_no_error(
    basic_project_builder,
    mock_linters,
    mock_parts,
    mock_launch_shell,
):
    host_base = get_host_as_base()
    builder = basic_project_builder(
        [BasesConfiguration(**{"build-on": [host_base], "run-on": [host_base]})],
        debug=True,
    )

    charms = builder.run(destructive_mode=True)

    assert len(charms) == 1
    assert mock_launch_shell.mock_calls == []


def test_build_with_debug_with_error(
    basic_project_builder,
    mock_linters,
    mock_parts,
    mock_launch_shell,
):
    mock_parts.PartsLifecycle.return_value.run.side_effect = CraftError("fail")
    host_base = get_host_as_base()
    builder = basic_project_builder(
        [BasesConfiguration(**{"build-on": [host_base], "run-on": [host_base]})],
        debug=True,
    )

    with pytest.raises(CraftError):
        builder.run(destructive_mode=True)

    assert mock_launch_shell.mock_calls == [mock.call()]


def test_build_with_shell(basic_project_builder, mock_parts, mock_provider, mock_launch_shell):
    host_base = get_host_as_base()
    builder = basic_project_builder(
        [BasesConfiguration(**{"build-on": [host_base], "run-on": [host_base]})],
        shell=True,
    )

    charms = builder.run(destructive_mode=True)

    assert charms == []
    assert mock_launch_shell.mock_calls == [mock.call()]


def test_build_with_shell_after(
    basic_project_builder,
    mock_linters,
    mock_parts,
    mock_launch_shell,
):
    host_base = get_host_as_base()
    builder = basic_project_builder(
        [BasesConfiguration(**{"build-on": [host_base], "run-on": [host_base]})],
        shell_after=True,
    )

    charms = builder.run(destructive_mode=True)

    assert len(charms) == 1
    assert mock_launch_shell.mock_calls == [mock.call()]


def test_build_checks_provider_error(basic_project, mock_provider):
    """Test cases for base-index parameter."""
    mock_provider.ensure_provider_is_available.side_effect = RuntimeError("foo")
    config = load(basic_project)
    builder = get_builder(config)

    with pytest.raises(RuntimeError, match="foo"):
        builder.run()


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_multiple_with_charmcraft_yaml_destructive_mode(basic_project_builder, emitter):
    """Build multiple charms for multiple matching bases, skipping one unmatched config."""
    host_base = get_host_as_base()
    unmatched_base = Base(
        name="unmatched-name",
        channel="unmatched-channel",
        architectures=["unmatched-arch1"],
    )
    matched_cross_base = Base(
        name="cross-name",
        channel="cross-channel",
        architectures=["cross-arch1"],
    )
    builder = basic_project_builder(
        [
            BasesConfiguration(**{"build-on": [host_base], "run-on": [host_base]}),
            BasesConfiguration(**{"build-on": [unmatched_base], "run-on": [unmatched_base]}),
            BasesConfiguration(**{"build-on": [host_base], "run-on": [matched_cross_base]}),
        ],
        force=True,
    )

    zipnames = builder.run(destructive_mode=True)

    host_arch = host_base.architectures[0]
    assert zipnames == [
        "test-charm-name-from-metadata-yaml_"
        f"{host_base.name}-{host_base.channel}-{host_arch}.charm",
        "test-charm-name-from-metadata-yaml_" "cross-name-cross-channel-cross-arch1.charm",
    ]

    reason = f"name 'unmatched-name' does not match host {host_base.name!r}."
    emitter.assert_interactions(
        [
            call("debug", "Building for 'bases[0]' as host matches 'build-on[0]'."),
            call("progress", f"Skipping 'bases[1].build-on[0]': {reason}"),
            call(
                "progress",
                "No suitable 'build-on' environment found in 'bases[1]' configuration.",
                permanent=True,
            ),
            call("debug", "Building for 'bases[2]' as host matches 'build-on[0]'."),
        ]
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_multiple_with_charmcraft_yaml_managed_mode(
    basic_project_builder, monkeypatch, emitter, tmp_path
):
    """Build multiple charms for multiple matching bases, skipping one unmatched config."""
    host_base = get_host_as_base()
    unmatched_base = Base(
        name="unmatched-name",
        channel="unmatched-channel",
        architectures=["unmatched-arch1"],
    )
    matched_cross_base = Base(
        name="cross-name",
        channel="cross-channel",
        architectures=["cross-arch1"],
    )
    builder = basic_project_builder(
        [
            BasesConfiguration(**{"build-on": [host_base], "run-on": [host_base]}),
            BasesConfiguration(**{"build-on": [unmatched_base], "run-on": [unmatched_base]}),
            BasesConfiguration(**{"build-on": [host_base], "run-on": [matched_cross_base]}),
        ],
        force=True,
    )

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with patch("charmcraft.env.get_managed_environment_home_path", return_value=tmp_path / "root"):
        zipnames = builder.run()

    host_arch = host_base.architectures[0]
    assert zipnames == [
        "test-charm-name-from-metadata-yaml_"
        f"{host_base.name}-{host_base.channel}-{host_arch}.charm",
        "test-charm-name-from-metadata-yaml_" "cross-name-cross-channel-cross-arch1.charm",
    ]

    reason = f"name 'unmatched-name' does not match host {host_base.name!r}."
    emitter.assert_interactions(
        [
            call("debug", "Building for 'bases[0]' as host matches 'build-on[0]'."),
            call("progress", f"Skipping 'bases[1].build-on[0]': {reason}"),
            call(
                "progress",
                "No suitable 'build-on' environment found in 'bases[1]' configuration.",
                permanent=True,
            ),
            call("debug", "Building for 'bases[2]' as host matches 'build-on[0]'."),
        ]
    )


@pytest.mark.parametrize(
    "charmcraft_yaml_template, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - name: ubuntu
                    channel: "18.04"
                    architectures: {arch}
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_build_project_is_cwd(
    basic_project,
    prepare_charmcraft_yaml,
    prepare_metadata_yaml,
    charmcraft_yaml_template,
    metadata_yaml,
    emitter,
    mock_capture_logs_from_instance,
    mock_instance,
    mock_provider,
    mock_instance_name,
    mock_ubuntu_buildd_base_configuration,
    mock_is_base_available,
    mocker,
):
    """Test cases for base-index parameter."""
    emit.set_mode(EmitterMode.BRIEF)
    host_base = get_host_as_base()
    host_arch = host_base.architectures[0]
    prepare_charmcraft_yaml(charmcraft_yaml_template.format(arch=host_base.architectures))
    prepare_metadata_yaml(metadata_yaml)

    config = load(basic_project)
    project_managed_path = pathlib.Path("/root/project")
    builder = get_builder(config)
    base_configuration = get_base_configuration(
        alias=bases.ubuntu.BuilddBaseAlias.BIONIC, instance_name=mock_instance_name()
    )
    mock_base_get_base_configuration = mocker.patch("charmcraft.providers.get_base_configuration")
    mock_base_get_base_configuration.return_value = base_configuration

    zipnames = builder.run([0])

    assert zipnames == [
        f"test-charm-name-from-metadata-yaml_ubuntu-18.04-{host_arch}.charm",
    ]
    assert mock_provider.mock_calls == [
        call.is_provider_installed(),
        call.ensure_provider_is_available(),
        call.launched_environment(
            project_name="test-charm-name-from-metadata-yaml",
            project_path=basic_project,
            base_configuration=base_configuration,
            instance_name=mock_instance_name(),
            allow_unstable=False,
        ),
    ]
    assert mock_instance.mock_calls == [
        call.mount(host_source=basic_project, target=project_managed_path),
        call.execute_run(
            ["charmcraft", "pack", "--bases-index", "0", "--verbosity=brief"],
            check=True,
            cwd=project_managed_path,
        ),
    ]
    assert mock_is_base_available.mock_calls == [
        call.is_base_available(
            Base(name="ubuntu", channel="18.04", architectures=[host_arch]),
        )
    ]


@pytest.mark.parametrize(
    "charmcraft_yaml_template, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - name: ubuntu
                    channel: "18.04"
                    architectures: {arch}
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_build_project_is_not_cwd(
    basic_project,
    prepare_charmcraft_yaml,
    prepare_metadata_yaml,
    charmcraft_yaml_template,
    metadata_yaml,
    mock_capture_logs_from_instance,
    mock_instance,
    mock_provider,
    monkeypatch,
    mock_instance_name,
    mock_ubuntu_buildd_base_configuration,
    mock_is_base_available,
    mocker,
):
    """Test cases for base-index parameter."""
    emit.set_mode(EmitterMode.BRIEF)
    host_base = get_host_as_base()
    host_arch = host_base.architectures[0]
    prepare_charmcraft_yaml(charmcraft_yaml_template.format(arch=host_base.architectures))
    prepare_metadata_yaml(metadata_yaml)

    config = load(basic_project)
    builder = get_builder(config)
    base_configuration = get_base_configuration(
        alias=bases.ubuntu.BuilddBaseAlias.BIONIC, instance_name=mock_instance_name()
    )
    mock_base_get_base_configuration = mocker.patch("charmcraft.providers.get_base_configuration")
    mock_base_get_base_configuration.return_value = base_configuration

    monkeypatch.chdir("/")  # make the working directory NOT the project's one
    zipnames = builder.run([0])

    assert zipnames == [
        f"test-charm-name-from-metadata-yaml_ubuntu-18.04-{host_arch}.charm",
    ]
    assert mock_provider.mock_calls == [
        call.is_provider_installed(),
        call.ensure_provider_is_available(),
        call.launched_environment(
            project_name="test-charm-name-from-metadata-yaml",
            project_path=basic_project,
            base_configuration=base_configuration,
            instance_name=mock_instance_name(),
            allow_unstable=False,
        ),
    ]
    assert mock_instance.mock_calls == [
        call.mount(host_source=basic_project, target=pathlib.Path("/root/project")),
        call.execute_run(
            ["charmcraft", "pack", "--bases-index", "0", "--verbosity=brief"],
            check=True,
            cwd=pathlib.Path("/root"),
        ),
        call.pull_file(
            source=pathlib.Path("/root") / zipnames[0],
            destination=pathlib.Path.cwd() / zipnames[0],
        ),
    ]
    assert mock_is_base_available.mock_calls == [
        call.is_base_available(
            Base(name="ubuntu", channel="18.04", architectures=[host_arch]),
        )
    ]


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
@pytest.mark.parametrize(
    "mode,cmd_flags",
    [
        (EmitterMode.VERBOSE, ["--verbosity=verbose"]),
        (EmitterMode.QUIET, ["--verbosity=quiet"]),
        (EmitterMode.DEBUG, ["--verbosity=debug"]),
        (EmitterMode.TRACE, ["--verbosity=trace"]),
        (EmitterMode.BRIEF, ["--verbosity=brief"]),
    ],
)
@pytest.mark.parametrize(
    "charmcraft_yaml_template, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - name: ubuntu
                    channel: "18.04"
                    architectures: {arch}
                  - name: ubuntu
                    channel: "20.04"
                    architectures: {arch}
                  - name: centos
                    channel: "7"
                    architectures: {arch}
                  - name: ubuntu
                    channel: "unsupported-channel"
                    architectures: {arch}
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_build_bases_index_scenarios_provider(
    mode,
    cmd_flags,
    basic_project,
    prepare_charmcraft_yaml,
    prepare_metadata_yaml,
    charmcraft_yaml_template,
    metadata_yaml,
    emitter,
    mock_capture_logs_from_instance,
    mock_instance,
    mock_provider,
    mock_instance_name,
    mock_ubuntu_buildd_base_configuration,
    mock_centos_base_configuration,
    mock_is_base_available,
    mocker,
):
    """Test cases for base-index parameter."""
    emit.set_mode(mode)
    host_base = get_host_as_base()
    host_arch = host_base.architectures[0]
    project_managed_path = pathlib.Path("/root/project")
    prepare_charmcraft_yaml(charmcraft_yaml_template.format(arch=host_base.architectures))
    config = load(basic_project)
    builder = get_builder(config)
    base_bionic_configuration = get_base_configuration(
        alias=bases.ubuntu.BuilddBaseAlias.BIONIC, instance_name=mock_instance_name()
    )
    base_focal_configuration = get_base_configuration(
        alias=bases.ubuntu.BuilddBaseAlias.FOCAL, instance_name=mock_instance_name()
    )
    base_centos_configuration = get_base_configuration(
        alias=bases.centos.CentOSBaseAlias.SEVEN, instance_name=mock_instance_name()
    )
    mock_base_get_base_configuration = mocker.patch("charmcraft.providers.get_base_configuration")
    mock_base_get_base_configuration.side_effect = [
        base_bionic_configuration,
        base_focal_configuration,
        base_centos_configuration,
    ]

    zipnames = builder.run([0])
    assert zipnames == [
        f"test-charm-name-from-metadata-yaml_ubuntu-18.04-{host_arch}.charm",
    ]

    assert mock_provider.mock_calls == [
        call.is_provider_installed(),
        call.ensure_provider_is_available(),
        call.launched_environment(
            project_name="test-charm-name-from-metadata-yaml",
            project_path=basic_project,
            base_configuration=base_bionic_configuration,
            instance_name=mock_instance_name(),
            allow_unstable=False,
        ),
    ]
    assert mock_instance.mock_calls == [
        call.mount(host_source=basic_project, target=project_managed_path),
        call.execute_run(
            ["charmcraft", "pack", "--bases-index", "0"] + cmd_flags,
            check=True,
            cwd=project_managed_path,
        ),
    ]
    assert mock_is_base_available.mock_calls == [
        call(Base(name="ubuntu", channel="18.04", architectures=[host_arch]))
    ]
    emitter.assert_progress(
        "Launching environment to pack for base "
        "name='ubuntu' channel='18.04' architectures=['amd64'] "
        "(may take a while the first time but it's reusable)"
    )
    emitter.assert_progress("Packing the charm")
    mock_provider.reset_mock()
    mock_instance.reset_mock()
    mock_is_base_available.reset_mock()
    mock_base_get_base_configuration.reset_mock()
    mock_base_get_base_configuration.side_effect = [
        base_bionic_configuration,
        base_focal_configuration,
        base_centos_configuration,
    ]

    zipnames = builder.run([1])
    assert zipnames == [
        f"test-charm-name-from-metadata-yaml_ubuntu-20.04-{host_arch}.charm",
    ]
    assert mock_provider.mock_calls == [
        call.is_provider_installed(),
        call.ensure_provider_is_available(),
        call.launched_environment(
            project_name="test-charm-name-from-metadata-yaml",
            project_path=basic_project,
            base_configuration=base_focal_configuration,
            instance_name=mock_instance_name(),
            allow_unstable=False,
        ),
    ]
    assert mock_instance.mock_calls == [
        call.mount(host_source=basic_project, target=project_managed_path),
        call.execute_run(
            ["charmcraft", "pack", "--bases-index", "1"] + cmd_flags,
            check=True,
            cwd=project_managed_path,
        ),
    ]
    assert mock_is_base_available.mock_calls == [
        call(Base(name="ubuntu", channel="20.04", architectures=[host_arch]))
    ]
    mock_provider.reset_mock()
    mock_instance.reset_mock()
    mock_is_base_available.reset_mock()
    mock_base_get_base_configuration.reset_mock()
    mock_base_get_base_configuration.side_effect = [
        base_bionic_configuration,
        base_focal_configuration,
        base_centos_configuration,
    ]

    zipnames = builder.run([0, 1])
    assert zipnames == [
        f"test-charm-name-from-metadata-yaml_ubuntu-18.04-{host_arch}.charm",
        f"test-charm-name-from-metadata-yaml_ubuntu-20.04-{host_arch}.charm",
    ]
    assert mock_provider.mock_calls == [
        call.is_provider_installed(),
        call.ensure_provider_is_available(),
        call.launched_environment(
            project_name="test-charm-name-from-metadata-yaml",
            project_path=basic_project,
            base_configuration=base_bionic_configuration,
            instance_name=mock_instance_name(),
            allow_unstable=False,
        ),
        call.launched_environment(
            project_name="test-charm-name-from-metadata-yaml",
            project_path=basic_project,
            base_configuration=base_focal_configuration,
            instance_name=mock_instance_name(),
            allow_unstable=False,
        ),
    ]
    assert mock_instance.mock_calls == [
        call.mount(host_source=basic_project, target=project_managed_path),
        call.execute_run(
            ["charmcraft", "pack", "--bases-index", "0"] + cmd_flags,
            check=True,
            cwd=project_managed_path,
        ),
        call.mount(host_source=basic_project, target=project_managed_path),
        call.execute_run(
            ["charmcraft", "pack", "--bases-index", "1"] + cmd_flags,
            check=True,
            cwd=project_managed_path,
        ),
    ]
    assert mock_is_base_available.mock_calls == [
        call(Base(name="ubuntu", channel="18.04", architectures=[host_arch])),
        call(Base(name="ubuntu", channel="20.04", architectures=[host_arch])),
    ]

    mock_provider.reset_mock()
    mock_instance.reset_mock()
    mock_is_base_available.reset_mock()
    mock_base_get_base_configuration.reset_mock()
    mock_base_get_base_configuration.side_effect = [
        base_focal_configuration,
        base_centos_configuration,
    ]

    zipnames = builder.run([1, 2])
    assert zipnames == [
        f"test-charm-name-from-metadata-yaml_ubuntu-20.04-{host_arch}.charm",
        f"test-charm-name-from-metadata-yaml_centos-7-{host_arch}.charm",
    ]
    assert mock_provider.mock_calls == [
        call.is_provider_installed(),
        call.ensure_provider_is_available(),
        call.launched_environment(
            project_name="test-charm-name-from-metadata-yaml",
            project_path=basic_project,
            base_configuration=base_focal_configuration,
            instance_name=mock_instance_name(),
            allow_unstable=False,
        ),
        call.launched_environment(
            project_name="test-charm-name-from-metadata-yaml",
            project_path=basic_project,
            base_configuration=base_centos_configuration,
            instance_name=mock_instance_name(),
            allow_unstable=True,
        ),
    ]
    assert mock_instance.mock_calls == [
        call.mount(host_source=basic_project, target=project_managed_path),
        call.execute_run(
            ["charmcraft", "pack", "--bases-index", "1"] + cmd_flags,
            check=True,
            cwd=project_managed_path,
        ),
        call.mount(host_source=basic_project, target=project_managed_path),
        call.execute_run(
            ["charmcraft", "pack", "--bases-index", "2"] + cmd_flags,
            check=True,
            cwd=project_managed_path,
        ),
    ]
    assert mock_is_base_available.mock_calls == [
        call(Base(name="ubuntu", channel="20.04", architectures=[host_arch])),
        call(Base(name="centos", channel="7", architectures=[host_arch])),
    ]
    mock_provider.reset_mock()
    mock_instance.reset_mock()
    mock_is_base_available.reset_mock()
    mock_base_get_base_configuration.reset_mock()
    mock_base_get_base_configuration.side_effect = [
        base_bionic_configuration,
        base_focal_configuration,
        base_centos_configuration,
    ]

    with pytest.raises(
        CraftError,
        match=r"No suitable 'build-on' environment found in any 'bases' configuration.",
    ):
        builder.run([4])

    mock_provider.reset_mock()
    mock_instance.reset_mock()
    mock_is_base_available.reset_mock()
    mock_base_get_base_configuration.reset_mock()
    mock_base_get_base_configuration.side_effect = [
        base_bionic_configuration,
        base_focal_configuration,
    ]

    expected_msg = re.escape("Failed to build charm for bases index '0'.")
    with pytest.raises(
        CraftError,
        match=expected_msg,
    ):
        mock_instance.execute_run.side_effect = subprocess.CalledProcessError(
            -1,
            ["charmcraft", "pack", "..."],
            "some output",
            "some error",
        )
        builder.run([0])

    assert mock_instance.mock_calls == [
        call.mount(host_source=basic_project, target=project_managed_path),
        call.execute_run(
            ["charmcraft", "pack", "--bases-index", "0"] + cmd_flags,
            check=True,
            cwd=project_managed_path,
        ),
    ]
    # it was called seven times, for success and errors
    assert mock_capture_logs_from_instance.mock_calls == [call(mock_instance)] * 7


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_bases_index_scenarios_managed_mode(basic_project_builder, monkeypatch, tmp_path):
    """Test cases for base-index parameter."""
    host_base = get_host_as_base()
    host_arch = host_base.architectures[0]
    host_base = get_host_as_base()
    unmatched_base = Base(
        name="unmatched-name",
        channel="unmatched-channel",
        architectures=["unmatched-arch1"],
    )
    matched_cross_base = Base(
        name="cross-name",
        channel="cross-channel",
        architectures=["cross-arch1"],
    )
    builder = basic_project_builder(
        [
            BasesConfiguration(**{"build-on": [host_base], "run-on": [host_base]}),
            BasesConfiguration(**{"build-on": [unmatched_base], "run-on": [unmatched_base]}),
            BasesConfiguration(**{"build-on": [host_base], "run-on": [matched_cross_base]}),
        ],
        force=True,
    )

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with patch("charmcraft.env.get_managed_environment_home_path", return_value=tmp_path / "root"):
        zipnames = builder.run([0])
    assert zipnames == [
        "test-charm-name-from-metadata-yaml_"
        f"{host_base.name}-{host_base.channel}-{host_arch}.charm",
    ]

    with pytest.raises(
        CraftError,
        match=r"No suitable 'build-on' environment found in any 'bases' configuration.",
    ):
        builder.run([1])

    with patch("charmcraft.env.get_managed_environment_home_path", return_value=tmp_path / "root"):
        zipnames = builder.run([2])
    assert zipnames == [
        "test-charm-name-from-metadata-yaml_cross-name-cross-channel-cross-arch1.charm",
    ]


@patch(
    "charmcraft.bases.get_host_as_base",
    return_value=Base(name="xname", channel="xchannel", architectures=["xarch"]),
)
@pytest.mark.parametrize(
    "charmcraft_yaml, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - name: unmatched-name
                    channel: xchannel
                    architectures: [xarch]
                  - name: xname
                    channel: unmatched-channel
                    architectures: [xarch]
                  - name: xname
                    channel: xchannel
                    architectures: [unmatched-arch1, unmatched-arch2]
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_build_error_no_match_with_charmcraft_yaml(
    mock_host_base,
    basic_project,
    prepare_charmcraft_yaml,
    prepare_metadata_yaml,
    charmcraft_yaml,
    metadata_yaml,
    monkeypatch,
    emitter,
):
    """Error when no charms are buildable with host base, verifying each mismatched reason."""
    prepare_charmcraft_yaml(charmcraft_yaml)
    prepare_metadata_yaml(metadata_yaml)

    config = load(basic_project)
    builder = get_builder(config)

    # Managed bases build.
    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with pytest.raises(
        CraftError,
        match=r"No suitable 'build-on' environment found in any 'bases' configuration.",
    ):
        builder.run()

    emitter.assert_interactions(
        [
            call(
                "progress",
                "Skipping 'bases[0].build-on[0]': "
                "name 'unmatched-name' does not match host 'xname'.",
            ),
            call(
                "progress",
                "No suitable 'build-on' environment found in 'bases[0]' configuration.",
                permanent=True,
            ),
            call(
                "progress",
                "Skipping 'bases[1].build-on[0]': "
                "channel 'unmatched-channel' does not match host 'xchannel'.",
            ),
            call(
                "progress",
                "No suitable 'build-on' environment found in 'bases[1]' configuration.",
                permanent=True,
            ),
            call(
                "progress",
                "Skipping 'bases[2].build-on[0]': "
                "host architecture 'xarch' not in base architectures "
                "['unmatched-arch1', 'unmatched-arch2'].",
            ),
            call(
                "progress",
                "No suitable 'build-on' environment found in 'bases[2]' configuration.",
                permanent=True,
            ),
        ]
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
@pytest.mark.parametrize(
    "builder_flag,cmd_flag",
    [
        ("debug", "--debug"),
        ("shell", "--shell"),
        ("shell_after", "--shell-after"),
        ("force", "--force"),
    ],
)
def test_build_arguments_managed_charmcraft_simples(
    builder_flag,
    cmd_flag,
    mock_capture_logs_from_instance,
    mock_instance,
    basic_project_builder,
):
    """Check that the command to run charmcraft inside the environment is properly built."""
    emit.set_mode(EmitterMode.BRIEF)
    host_base = Base(name="ubuntu", channel="18.04", architectures=[get_host_architecture()])
    bases_config = [BasesConfiguration(**{"build-on": [host_base], "run-on": [host_base]})]
    project_managed_path = pathlib.Path("/root/project")

    kwargs = {builder_flag: True}
    builder = basic_project_builder(bases_config, **kwargs)
    builder.pack_charm_in_instance(
        build_on=bases_config[0].build_on[0],
        bases_index=0,
        build_on_index=0,
    )
    expected_cmd = ["charmcraft", "pack", "--bases-index", "0", "--verbosity=brief", cmd_flag]
    assert mock_instance.mock_calls == [
        call.mount(host_source=builder.config.project.dirpath, target=project_managed_path),
        call.execute_run(expected_cmd, check=True, cwd=project_managed_path),
    ]


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_arguments_managed_charmcraft_measure(
    mock_capture_logs_from_instance,
    mock_instance,
    basic_project_builder,
    tmp_path,
):
    """Check that the command to run charmcraft inside the environment is properly built."""
    emit.set_mode(EmitterMode.BRIEF)
    host_base = Base(name="ubuntu", channel="18.04", architectures=[get_host_architecture()])
    bases_config = [BasesConfiguration(**{"build-on": [host_base], "run-on": [host_base]})]
    project_managed_path = pathlib.Path("/root/project")

    # fake a dumped mesure to be pulled from the instance
    fake_local_m = tmp_path / "local.json"
    instrum._Measurements().dump(fake_local_m)

    # specially patch the context manager
    fake_inst_m = tmp_path / "inst.json"
    mock_instance.temporarily_pull_file = MagicMock()
    mock_instance.temporarily_pull_file.return_value = fake_local_m

    builder = basic_project_builder(bases_config, measure=tmp_path)
    with patch("charmcraft.env.get_managed_environment_metrics_path", return_value=fake_inst_m):
        builder.pack_charm_in_instance(
            build_on=bases_config[0].build_on[0],
            bases_index=0,
            build_on_index=0,
        )
    cmd_flag = f"--measure={str(fake_inst_m)}"
    expected_cmd = ["charmcraft", "pack", "--bases-index", "0", "--verbosity=brief", cmd_flag]
    assert mock_instance.mock_calls == [
        call.mount(host_source=builder.config.project.dirpath, target=project_managed_path),
        call.execute_run(expected_cmd, check=True, cwd=project_managed_path),
        call.temporarily_pull_file(fake_inst_m),
    ]


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_package_tree_structure(tmp_path, config):
    """The zip file is properly built internally."""
    # the metadata
    metadata_data = {"name": "test-charm-name-from-metadata-yaml"}
    metadata_file = tmp_path / "metadata.yaml"
    with metadata_file.open("wt", encoding="ascii") as fh:
        yaml.dump(metadata_data, fh)

    # create some dirs and files! a couple of files outside, and the dir we'll zip...
    file_outside_1 = tmp_path / "file_outside_1"
    with file_outside_1.open("wb") as fh:
        fh.write(b"content_out_1")
    file_outside_2 = tmp_path / "file_outside_2"
    with file_outside_2.open("wb") as fh:
        fh.write(b"content_out_2")
    to_be_zipped_dir = tmp_path / BUILD_DIRNAME
    to_be_zipped_dir.mkdir()

    # ...also outside a dir with a file...
    dir_outside = tmp_path / "extdir"
    dir_outside.mkdir()
    file_ext = dir_outside / "file_ext"
    with file_ext.open("wb") as fh:
        fh.write(b"external file")

    # ...then another file inside, and another dir...
    file_inside = to_be_zipped_dir / "file_inside"
    with file_inside.open("wb") as fh:
        fh.write(b"content_in")
    dir_inside = to_be_zipped_dir / "somedir"
    dir_inside.mkdir()

    # ...also inside, a link to the external dir...
    dir_linked_inside = to_be_zipped_dir / "linkeddir"
    dir_linked_inside.symlink_to(dir_outside)

    # ...and finally another real file, and two symlinks
    file_deep_1 = dir_inside / "file_deep_1"
    with file_deep_1.open("wb") as fh:
        fh.write(b"content_deep")
    file_deep_2 = dir_inside / "file_deep_2"
    file_deep_2.symlink_to(file_inside)
    file_deep_3 = dir_inside / "file_deep_3"
    file_deep_3.symlink_to(file_outside_1)

    # zip it
    bases_config = BasesConfiguration(
        **{
            "build-on": [],
            "run-on": [Base(name="xname", channel="xchannel", architectures=["xarch1"])],
        }
    )
    builder = get_builder(config)
    zipname = builder.handle_package(to_be_zipped_dir, bases_config)

    # check the stuff outside is not in the zip, the stuff inside is zipped (with
    # contents!), and all relative to build dir
    zf = zipfile.ZipFile(zipname)
    assert "file_outside_1" not in [x.filename for x in zf.infolist()]
    assert "file_outside_2" not in [x.filename for x in zf.infolist()]
    assert zf.read("file_inside") == b"content_in"
    assert zf.read("somedir/file_deep_1") == b"content_deep"  # own
    assert zf.read("somedir/file_deep_2") == b"content_in"  # from file inside
    assert zf.read("somedir/file_deep_3") == b"content_out_1"  # from file outside 1
    assert zf.read("linkeddir/file_ext") == b"external file"  # from file in the outside linked dir


def test_build_package_name(tmp_path, config):
    """The zip file name comes from the config."""
    to_be_zipped_dir = tmp_path / BUILD_DIRNAME
    to_be_zipped_dir.mkdir()

    # the metadata
    metadata_data = {"name": "name-from-metadata-yaml"}
    metadata_file = tmp_path / "metadata.yaml"
    with metadata_file.open("wt", encoding="ascii") as fh:
        yaml.dump(metadata_data, fh)

    # zip it
    bases_config = BasesConfiguration(
        **{
            "build-on": [],
            "run-on": [Base(name="xname", channel="xchannel", architectures=["xarch1"])],
        }
    )
    builder = get_builder(config)
    zipname = builder.handle_package(to_be_zipped_dir, bases_config)

    assert zipname == "name-from-metadata-yaml_xname-xchannel-xarch1.charm"


@pytest.mark.parametrize(
    "charmcraft_yaml_template, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - build-on:
                      - name: {base_name}
                        channel: "{base_channel}"
                    run-on:
                      - name: {base_name}
                        channel: "{base_channel}"
                parts:
                  charm:
                    charm-entrypoint: my_entrypoint.py
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_build_postlifecycle_validation_is_properly_called(
    basic_project,
    prepare_charmcraft_yaml,
    prepare_metadata_yaml,
    charmcraft_yaml_template,
    metadata_yaml,
    monkeypatch,
):
    """Check how the entrypoint validation helper is called."""
    host_base = get_host_as_base()
    prepare_charmcraft_yaml(
        charmcraft_yaml_template.format(base_name=host_base.name, base_channel=host_base.channel)
    )
    config = load(basic_project)
    builder = get_builder(config)

    entrypoint = basic_project / "my_entrypoint.py"
    entrypoint.touch(mode=0o700)

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with patch("charmcraft.parts.PartsLifecycle") as mock_lifecycle:
        mock_lifecycle.return_value = mock_lifecycle_instance = MagicMock()
        mock_lifecycle_instance.prime_dir = basic_project
        mock_lifecycle_instance.run().return_value = None
        with patch("charmcraft.linters.analyze"):
            with patch.object(Builder, "show_linting_results"):
                builder.run([0])


@pytest.mark.parametrize(
    "charmcraft_yaml_template, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - build-on:
                      - name: {base_name}
                        channel: "{base_channel}"
                    run-on:
                      - name: {base_name}
                        channel: "{base_channel}"

                parts:
                  charm:
                    charm-entrypoint: src/charm.py
                    charm-python-packages: ["foo", "bar"]
                    charm-binary-python-packages: ["baz"]
                    charm-requirements: ["reqs.txt"]
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_build_part_from_config(
    basic_project,
    prepare_charmcraft_yaml,
    prepare_metadata_yaml,
    charmcraft_yaml_template,
    metadata_yaml,
    monkeypatch,
):
    """Check that the "parts" are passed to the lifecycle correctly."""
    host_base = get_host_as_base()
    prepare_charmcraft_yaml(
        charmcraft_yaml_template.format(base_name=host_base.name, base_channel=host_base.channel)
    )
    prepare_metadata_yaml(metadata_yaml)

    reqs_file = basic_project / "reqs.txt"
    reqs_file.write_text("somedep")
    config = load(basic_project)
    builder = get_builder(config, force=True)

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with patch("charmcraft.parts.PartsLifecycle", autospec=True) as mock_lifecycle:
        mock_lifecycle.side_effect = SystemExit()
        with pytest.raises(SystemExit):
            builder.run([0])
    mock_lifecycle.assert_has_calls(
        [
            call(
                {
                    "charm": {
                        "plugin": "charm",
                        "prime": [
                            "src",
                            "venv",
                            "metadata.yaml",
                            "dispatch",
                            "hooks",
                            "lib",
                            "LICENSE",
                            "icon.svg",
                            "README.md",
                        ],
                        "charm-entrypoint": "src/charm.py",
                        "charm-python-packages": ["foo", "bar"],
                        "charm-binary-python-packages": ["baz"],
                        "source": str(basic_project),
                        "charm-requirements": ["reqs.txt"],
                    }
                },
                work_dir=pathlib.Path("/root"),
                project_dir=basic_project,
                project_name="test-charm-name-from-metadata-yaml",
                ignore_local_sources=["*.charm"],
            )
        ]
    )


@pytest.mark.parametrize(
    "charmcraft_yaml_template, metadata_yaml",
    [
        [
            dedent(
                """\
                type: charm
                bases:
                  - build-on:
                      - name: {base_name}
                        channel: "{base_channel}"
                    run-on:
                      - name: {base_name}
                        channel: "{base_channel}"

                parts:
                  charm:
                    charm-entrypoint: src/charm.py
                """
            ),
            dedent(
                """\
                name: test-charm-name-from-metadata-yaml
                summary: test summary
                description: test description
                """
            ),
        ],
    ],
)
def test_build_part_include_venv_pydeps(
    basic_project,
    prepare_charmcraft_yaml,
    prepare_metadata_yaml,
    charmcraft_yaml_template,
    metadata_yaml,
    monkeypatch,
):
    """Include the venv directory even if only charmlib python dependencies exist."""
    host_base = get_host_as_base()
    prepare_charmcraft_yaml(
        charmcraft_yaml_template.format(base_name=host_base.name, base_channel=host_base.channel)
    )
    prepare_metadata_yaml(metadata_yaml)

    charmlib = basic_project / "lib" / "charms" / "somecharm" / "v1" / "somelib.py"
    charmlib.parent.mkdir(parents=True)
    charmlib.write_text(
        dedent(
            """
            LIBID = "asdasds"
            LIBAPI = 1
            LIBPATCH = 1
            PYDEPS = ["foo"]
            """
        )
    )
    config = load(basic_project)
    builder = get_builder(config, force=True)

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with patch("charmcraft.parts.PartsLifecycle", autospec=True) as mock_lifecycle:
        mock_lifecycle.side_effect = SystemExit()
        with pytest.raises(SystemExit):
            builder.run([0])
    mock_lifecycle.assert_has_calls(
        [
            call(
                {
                    "charm": {
                        "plugin": "charm",
                        "prime": [
                            "src",
                            "venv",
                            "metadata.yaml",
                            "dispatch",
                            "hooks",
                            "lib",
                            "LICENSE",
                            "icon.svg",
                            "README.md",
                        ],
                        "charm-entrypoint": "src/charm.py",
                        "charm-python-packages": [],
                        "charm-binary-python-packages": [],
                        "source": str(basic_project),
                        "charm-requirements": [],
                    }
                },
                work_dir=pathlib.Path("/root"),
                project_dir=basic_project,
                project_name="test-charm-name-from-metadata-yaml",
                ignore_local_sources=["*.charm"],
            )
        ]
    )


@pytest.mark.skipif(sys.platform == "win32", reason="Windows not [yet] supported")
def test_build_using_linters_attributes(basic_project_builder, monkeypatch, tmp_path):
    """Generic use of linters, pass them ok to their proceessor and save them in the manifest."""
    host_base = get_host_as_base()
    builder = basic_project_builder(
        [BasesConfiguration(**{"build-on": [host_base], "run-on": [host_base]})],
        force=True,  # to ignore any linter issue
    )

    # the results from the analyzer
    linting_results = [
        linters.CheckResult(
            name="check-name-1",
            check_type=linters.CheckType.attribute,
            url="url",
            text="text",
            result="check-result-1",
        ),
        linters.CheckResult(
            name="check-name-2",
            check_type=linters.CheckType.attribute,
            url="url",
            text="text",
            result=linters.IGNORED,
        ),
    ]

    monkeypatch.setenv("CHARMCRAFT_MANAGED_MODE", "1")
    with patch("charmcraft.env.get_managed_environment_home_path", return_value=tmp_path / "root"):
        with patch("charmcraft.linters.analyze") as mock_analyze:
            with patch.object(Builder, "show_linting_results") as mock_show_lint:
                mock_analyze.return_value = linting_results
                zipnames = builder.run()

    # check the analyze and processing functions were called properly
    mock_analyze.assert_called_with(builder.config, tmp_path / "root" / "prime")
    mock_show_lint.assert_called_with(linting_results)

    # the manifest should have all the results (including the ignored one)
    zf = zipfile.ZipFile(zipnames[0])
    manifest = yaml.safe_load(zf.read("manifest.yaml"))
    expected = {
        "attributes": [
            {"name": "check-name-1", "result": "check-result-1"},
            {"name": "check-name-2", "result": "ignored"},
        ]
    }
    assert manifest["analysis"] == expected


def test_show_linters_attributes(basic_project, emitter, config):
    """Show the linting results, only attributes, one ignored."""
    builder = get_builder(config)

    # fake results from the analyzer
    linting_results = [
        linters.CheckResult(
            name="check-name-1",
            check_type=linters.CheckType.attribute,
            url="url",
            text="text",
            result="check-result-1",
        ),
        linters.CheckResult(
            name="check-name-2",
            check_type=linters.CheckType.attribute,
            url="url",
            text="text",
            result=linters.IGNORED,
        ),
    ]

    builder.show_linting_results(linting_results)

    expected = "Check result: check-name-1 [attribute] check-result-1 (text; see more at url)."
    emitter.assert_verbose(expected)


def test_show_linters_lint_warnings(basic_project, emitter, config):
    """Show the linting results, some warnings."""
    builder = get_builder(config)

    # fake result from the analyzer
    linting_results = [
        linters.CheckResult(
            name="check-name",
            check_type=linters.CheckType.lint,
            url="check-url",
            text="Some text",
            result=linters.WARNINGS,
        ),
    ]

    builder.show_linting_results(linting_results)

    emitter.assert_interactions(
        [
            call("progress", "Lint Warnings:", permanent=True),
            call("progress", "- check-name: Some text (check-url)", permanent=True),
        ]
    )


def test_show_linters_lint_errors_normal(basic_project, emitter, config):
    """Show the linting results, have errors."""
    builder = get_builder(config)

    # fake result from the analyzer
    linting_results = [
        linters.CheckResult(
            name="check-name",
            check_type=linters.CheckType.lint,
            url="check-url",
            text="Some text",
            result=linters.ERRORS,
        ),
    ]

    with pytest.raises(CraftError) as cm:
        builder.show_linting_results(linting_results)
    exc = cm.value
    assert str(exc) == "Aborting due to lint errors (use --force to override)."
    assert exc.retcode == 2

    emitter.assert_interactions(
        [
            call("progress", "Lint Errors:", permanent=True),
            call("progress", "- check-name: Some text (check-url)", permanent=True),
        ]
    )


def test_show_linters_lint_errors_forced(basic_project, emitter, config):
    """Show the linting results, have errors but the packing is forced."""
    builder = get_builder(config, force=True)

    # fake result from the analyzer
    linting_results = [
        linters.CheckResult(
            name="check-name",
            check_type=linters.CheckType.lint,
            url="check-url",
            text="Some text",
            result=linters.ERRORS,
        ),
    ]

    builder.show_linting_results(linting_results)

    emitter.assert_interactions(
        [
            call("progress", "Lint Errors:", permanent=True),
            call("progress", "- check-name: Some text (check-url)", permanent=True),
            call("progress", "Packing anyway as requested.", permanent=True),
        ]
    )


# --- tests for relativise helper


def test_relativise_sameparent():
    """Two files in the same dir."""
    src = pathlib.Path("/tmp/foo/bar/src.txt")
    dst = pathlib.Path("/tmp/foo/bar/dst.txt")
    rel = relativise(src, dst)
    assert rel == pathlib.Path("dst.txt")


def test_relativise_src_under():
    """The src is in subdirectory of dst's parent."""
    src = pathlib.Path("/tmp/foo/bar/baz/src.txt")
    dst = pathlib.Path("/tmp/foo/dst.txt")
    rel = relativise(src, dst)
    assert rel == pathlib.Path("../../dst.txt")


def test_relativise_dst_under():
    """The dst is in subdirectory of src's parent."""
    src = pathlib.Path("/tmp/foo/src.txt")
    dst = pathlib.Path("/tmp/foo/bar/baz/dst.txt")
    rel = relativise(src, dst)
    assert rel == pathlib.Path("bar/baz/dst.txt")


def test_relativise_different_parents_shallow():
    """Different parents for src and dst, but shallow."""
    src = pathlib.Path("/tmp/foo/bar/src.txt")
    dst = pathlib.Path("/tmp/foo/baz/dst.txt")
    rel = relativise(src, dst)
    assert rel == pathlib.Path("../baz/dst.txt")


def test_relativise_different_parents_deep():
    """Different parents for src and dst, in a deep structure."""
    src = pathlib.Path("/tmp/foo/bar1/bar2/src.txt")
    dst = pathlib.Path("/tmp/foo/baz1/baz2/baz3/dst.txt")
    rel = relativise(src, dst)
    assert rel == pathlib.Path("../../baz1/baz2/baz3/dst.txt")


def test_format_charm_file_name_basic():
    """Basic entry."""
    bases_config = BasesConfiguration(
        **{
            "build-on": [],
            "run-on": [Base(name="xname", channel="xchannel", architectures=["xarch1"])],
        }
    )

    assert (
        format_charm_file_name("charm-name", bases_config)
        == "charm-name_xname-xchannel-xarch1.charm"
    )


def test_format_charm_file_name_multi_arch():
    """Multiple architectures."""
    bases_config = BasesConfiguration(
        **{
            "build-on": [],
            "run-on": [
                Base(
                    name="xname",
                    channel="xchannel",
                    architectures=["xarch1", "xarch2", "xarch3"],
                )
            ],
        }
    )

    assert (
        format_charm_file_name("charm-name", bases_config)
        == "charm-name_xname-xchannel-xarch1-xarch2-xarch3.charm"
    )


def test_format_charm_file_name_multi_run_on():
    """Multiple run-on entries."""
    bases_config = BasesConfiguration(
        **{
            "build-on": [],
            "run-on": [
                Base(name="x1name", channel="x1channel", architectures=["x1arch"]),
                Base(
                    name="x2name",
                    channel="x2channel",
                    architectures=["x2arch1", "x2arch2"],
                ),
            ],
        }
    )

    assert (
        format_charm_file_name("charm-name", bases_config)
        == "charm-name_x1name-x1channel-x1arch_x2name-x2channel-x2arch1-x2arch2.charm"
    )


def test_launch_shell(emitter):
    """Check bash is called while Emitter is paused."""

    def fake_run(command, check, cwd):
        """MITM to verify parameters and that emitter is paused when it's called."""
        assert command == ["bash"]
        assert check is False
        assert cwd is None
        assert emitter.paused

    with mock.patch("subprocess.run", fake_run):
        launch_shell()
