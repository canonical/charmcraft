# Copyright 2021-2024 Canonical Ltd.
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

"""Analyze and lint charm structures and files."""

import abc
import ast
import os
import pathlib
import re
import shlex
import subprocess
import sys
import typing
from collections.abc import Collection, Generator
from typing import final

import yaml
from craft_cli import emit

from charmcraft import const, utils
from charmcraft.models.lint import CheckResult, CheckType, LintResult
from charmcraft.models.metadata import CharmMetadataLegacy

# the documentation page for "Analyzers and linters"
BASE_DOCS_URL = "https://juju.is/docs/sdk/charmcraft-analyzers-and-linters"
PYTHON_NAME_REGEX = re.compile(
    r"^([A-Z0-9]([A-Z0-9._-]*[A-Z0-9])?)", flags=re.IGNORECASE
)
MIN_VERSION_REGEX = re.compile(r">=\s*([\d.]+)")
APPROX_VERSION_REGEX = re.compile(r"(?:~=\s*([\d.]+)\.\d|==\s*([\d.]+)\.\*)")
EXACT_VERSION_REGEX = re.compile(r"==\s*([\d.]+)")


def get_entrypoint_from_dispatch(basedir: pathlib.Path) -> pathlib.Path | None:
    """Verify if the charm has a dispatch file pointing to a Python entrypoint.

    :returns: the entrypoint path if all succeeds, None otherwise.
    """
    # get the entrypoint from the last useful dispatch line
    dispatch = basedir / const.DISPATCH_FILENAME
    entrypoint_str = ""
    try:
        with dispatch.open("rt", encoding="utf8") as fh:
            last_line = None
            for line in fh:
                if line.strip():
                    last_line = line
            if last_line:
                entrypoint_str = shlex.split(last_line)[-1]
    except (OSError, UnicodeDecodeError):
        return None
    if not entrypoint_str:
        return None
    return basedir / entrypoint_str


def check_dispatch_with_python_entrypoint(basedir: pathlib.Path) -> pathlib.Path | None:
    """Verify if the charm has a dispatch file pointing to a Python entrypoint.

    :returns: the entrypoint path if all succeeds, None otherwise.
    """
    entrypoint = get_entrypoint_from_dispatch(basedir)
    if entrypoint and entrypoint.suffix == ".py" and os.access(entrypoint, os.X_OK):
        return entrypoint
    return None


class BaseChecker(metaclass=abc.ABCMeta):
    """Base class for checker classes."""

    check_type: CheckType
    name: str
    url: str
    text: str

    exception_result: str

    @abc.abstractmethod
    def run(self, basedir: pathlib.Path) -> str:
        """Run this checker."""
        ...

    @final
    def get_result(self, base_dir: pathlib.Path) -> CheckResult:
        """Get the result of a single checker."""
        try:
            result = self.run(base_dir)
        except Exception as exc:
            result = self.exception_result
            if not self.text:
                self.text = str(exc)
        return CheckResult(
            check_type=self.check_type,
            name=self.name,
            url=self.url,
            text=self.text,
            result=result,
        )

    @final
    def get_ignore_result(self) -> CheckResult:
        """Get the result presuming the checker is ignored."""
        return CheckResult(
            check_type=self.check_type,
            name=self.name,
            url=self.url,
            text="",
            result=LintResult.IGNORED,
        )


class AttributeChecker(BaseChecker, metaclass=abc.ABCMeta):
    """Base attribute checker."""

    check_type = CheckType.ATTRIBUTE
    exception_result = LintResult.UNKNOWN


class Linter(BaseChecker, metaclass=abc.ABCMeta):
    """Base linter class."""

    check_type = CheckType.LINT
    exception_result = LintResult.FATAL
    Result = LintResult


class Language(AttributeChecker):
    """Check the language used to write the charm.

    Currently only Python is detected, if the following checks are true:

    - the charm has a text dispatch with a python call
    - the charm has a `.py` entry point
    - the entry point file is executable
    """

    name = "language"
    url = BASE_DOCS_URL + "#heading--language"
    text = "The charm is written with Python."

    class Result:
        """Possible results for this attribute checker."""

        UNKNOWN = LintResult.UNKNOWN
        PYTHON = "python"

    def run(self, basedir: pathlib.Path) -> str:
        """Run the proper verifications."""
        python_entrypoint = check_dispatch_with_python_entrypoint(basedir)
        if python_entrypoint is None:
            self.text = "Charm language unknown"
            return self.Result.UNKNOWN
        return self.Result.PYTHON


class Framework(AttributeChecker):
    """Check the framework the charm is based on.

    Currently it detects if the Operator Framework is used, if...

    - the language attribute is set to python
    - the charm contains venv/ops
    - the charm imports ops in the entry point.

    ...or the Reactive Framework is used, if the charm...

    - has a metadata.yaml with "name" in it
    - has a reactive/<name>.py file that imports "charms.reactive"
    - has a file name that starts with "charms.reactive-" inside the "wheelhouse" directory
    """

    name = "framework"
    url = BASE_DOCS_URL + "#heading--framework"

    class Result:
        """Possible results for this attribute checker."""

        OPERATOR = "operator"
        REACTIVE = "reactive"
        UNKNOWN = LintResult.UNKNOWN

    # different texts to be exposed as `text` (see the property below)
    result_texts = {
        Result.OPERATOR: "The charm is based on the Operator Framework.",
        Result.REACTIVE: "The charm is based on the Reactive Framework.",
        Result.UNKNOWN: "The charm is not based on any known Framework.",
    }

    def __init__(self):
        self.result = None
        self.__text = None

    @property
    def text(self) -> str:
        """Return a text in function of the result state."""
        if self.__text:
            return self.__text
        if self.result is None:
            return ""
        return self.result_texts[self.result]

    @text.setter
    def text(self, value: str) -> None:
        self.__text = value

    def _get_imports(self, filepath: pathlib.Path) -> Generator[list[str], None, None]:
        """Parse a Python filepath and yield its imports.

        If the file does not exist or cannot be parsed, return empty. Otherwise
        return the name for each imported module, split by possible dots.
        """
        if not os.access(filepath, os.R_OK):
            return
        try:
            parsed = ast.parse(filepath.read_bytes())
        except SyntaxError:
            return

        for node in ast.walk(parsed):
            if isinstance(node, ast.Import):
                for name in node.names:
                    yield name.name.split(".")
            elif isinstance(node, ast.ImportFrom):
                yield node.module.split(".")

    def _check_operator(self, basedir: pathlib.Path) -> bool:
        """Detect if the Operator Framework is used."""
        python_entrypoint = check_dispatch_with_python_entrypoint(basedir)
        if python_entrypoint is None:
            return False

        opsdir = basedir / const.VENV_DIRNAME / "ops"
        if not opsdir.exists() or not opsdir.is_dir():
            return False

        for import_parts in self._get_imports(python_entrypoint):
            if import_parts[0] == "ops":
                return True
        return False

    def _check_reactive(self, basedir: pathlib.Path) -> bool:
        """Detect if the Reactive Framework is used."""
        try:
            metadata = CharmMetadataLegacy.from_yaml_file(
                basedir / const.METADATA_FILENAME
            )
        except Exception:
            # file not found, corrupted, or mandatory "name" not present
            return False

        wheelhouse_dir = basedir / "wheelhouse"
        if not wheelhouse_dir.exists():
            return False
        if not any(
            f.name.startswith("charms.reactive-") for f in wheelhouse_dir.iterdir()
        ):
            return False

        module_basename = metadata.name.replace("-", "_")
        entrypoint = basedir / "reactive" / f"{module_basename}.py"
        for import_parts in self._get_imports(entrypoint):
            if import_parts[0] == "charms" and import_parts[1] == "reactive":
                return True
        return False

    def run(self, basedir: pathlib.Path) -> str:
        """Run the proper verifications."""
        self.result = self.Result.UNKNOWN
        if self._check_operator(basedir):
            self.result = self.Result.OPERATOR
        elif self._check_reactive(basedir):
            self.result = self.Result.REACTIVE
        return self.result


class JujuMetadata(Linter):
    """Check that the metadata.yaml file exists and is valid.

    The charm is considered to have a valid metadata if the following checks are true:

    - the metadata.yaml is present
    - it is a valid YAML file
    - it has at least the following fields: name, summary, and description
    """

    name = "metadata"
    url = BASE_DOCS_URL + "#heading--metadata"

    def __init__(self):
        self.text = ""

    def run(self, basedir: pathlib.Path) -> str:
        """Run the proper verifications."""
        try:
            with (basedir / const.METADATA_FILENAME).open("rt") as md_file:
                metadata = yaml.safe_load(md_file)
        except yaml.YAMLError:
            self.text = "The metadata.yaml file is not a valid YAML file."
            return self.Result.ERROR
        except Exception:
            self.text = "Cannot read the metadata.yaml file."
            return self.Result.ERROR

        # check required attributes
        missing_fields = {"name", "summary", "description"} - set(metadata)
        if missing_fields:
            missing = utils.humanize_list(missing_fields, "and")
            self.text = f"The metadata.yaml file is missing the following attribute(s): {missing}."
            return self.Result.ERROR

        if "series" in metadata:
            self.text = (
                "The metadata.yaml file contains the deprecated attribute: series."
                "This attribute will be rejected starting in Juju 4.0."
            )
            return self.Result.WARNING

        return self.Result.OK


class JujuActions(Linter):
    """Check that the actions.yaml file is valid YAML if it exists."""

    name = "juju-actions"
    url = BASE_DOCS_URL + "#heading--juju-actions"
    text = "The actions.yaml file is not a valid YAML file."

    def run(self, basedir: pathlib.Path) -> str:
        """Run the proper verifications."""
        filepath = basedir / const.JUJU_ACTIONS_FILENAME
        if not filepath.exists():
            self.text = ""
            # it's optional
            return self.Result.OK

        try:
            with filepath.open("rt", encoding="utf8") as fh:
                yaml.safe_load(fh)
        except Exception:
            return self.Result.ERROR

        self.text = "Valid actions.yaml file."
        return self.Result.OK


class JujuConfig(Linter):
    """Check that the config.yaml file (if it exists) is valid.

    The file is considered valid if the following checks are true:

    - has an 'options' key
    - it is a dictionary
    - each item inside has the mandatory 'type' key
    """

    name = "juju-config"
    url = BASE_DOCS_URL + "#heading--juju-config"

    def __init__(self):
        self.text = ""

    def run(self, basedir: pathlib.Path) -> str:
        """Run the proper verifications."""
        filepath = basedir / const.JUJU_CONFIG_FILENAME
        if not filepath.exists():
            # it's optional
            return self.Result.OK

        try:
            with filepath.open("rt", encoding="utf8") as fh:
                content = yaml.safe_load(fh)
        except Exception:
            self.text = "The config.yaml file is not a valid YAML file."
            return self.Result.ERROR

        options = content.get("options")
        if not isinstance(options, dict):
            self.text = "Error in config.yaml: must have an 'options' dictionary."
            return self.Result.ERROR

        for value in options.values():
            if "type" not in value:
                self.text = "Error in config.yaml: items under 'options' must have a 'type' key."
                return self.Result.ERROR

        return self.Result.OK


class NamingConventions(Linter):
    """Check that charm follows naming conventions.

    More information can be found at https://juju.is/docs/sdk/styleguide#heading--naming.
    """

    name = "naming-conventions"
    url = "https://juju.is/docs/sdk/styleguide#heading--naming"

    exception_result = LintResult.WARNING

    def __init__(self):
        self.text = ""

    @staticmethod
    def check_naming_convention(names: typing.Iterable[str], scope: str) -> str | None:
        """Check adherence to naming convention.

        :returns: string with warning if present, otherwise None
        """
        snake_keys = [key for key in names if "_" in key]

        if snake_keys:
            hyphen_keys = [key for key in names if "-" in key]

            if hyphen_keys:
                return (
                    f"Some {scope} ({', '.join(snake_keys)}) are in snake case, "
                    f"while others  ({', '.join(hyphen_keys)}) are with hyphens."
                )
            else:
                return (
                    f"Some {scope} ({', '.join(snake_keys)}) are using "
                    "snake case naming convention."
                )

        return None

    @staticmethod
    def _config_options_check(config_file: pathlib.Path) -> list[str]:
        # This is safe as the compliance with YAML is done in the JujuConfig linter
        warnings = []

        if not config_file.exists():
            return warnings

        with config_file.open("rt", encoding="utf8") as fh:
            options = (
                content.get("options", {}) if (content := yaml.safe_load(fh)) else {}
            )

        if check := NamingConventions.check_naming_convention(
            options.keys(), "config-options"
        ):
            warnings.append(check)

        return warnings

    @staticmethod
    def _actions_check(action_file: pathlib.Path) -> list[str]:
        # This is safe as the compliance with YAML is done in the JujuConfig linter
        warnings = []

        if not action_file.exists():
            return warnings

        # This is safe as the compliance with YAML is done in the JujuConfig linter
        with action_file.open("rt", encoding="utf8") as fh:
            if content := yaml.safe_load(fh):
                actions_names = list(dict(content).keys())
            else:
                actions_names = []

        if check := NamingConventions.check_naming_convention(actions_names, "actions"):
            warnings.append(check)

        actions_params = [
            param
            for action_name in actions_names
            if isinstance(content[action_name], dict)
            for param in content.get(action_name, {}).get("params", [])
        ]

        if check := NamingConventions.check_naming_convention(
            actions_params, "action params"
        ):
            warnings.append(check)

        return warnings

    def run(self, basedir: pathlib.Path) -> str:
        """Run the proper verifications."""
        # Check naming convention on config options

        warnings = NamingConventions._config_options_check(
            basedir / const.JUJU_CONFIG_FILENAME
        ) + NamingConventions._actions_check(basedir / const.JUJU_ACTIONS_FILENAME)

        if warnings:
            all_warning_string = "\n".join(warnings)
            self.text = f"Naming conventions breaks:\n{all_warning_string}"
            return self.exception_result

        return self.Result.OK


class Entrypoint(Linter):
    """Check the entrypoint is correct.

    It validates that the entrypoint, if used by 'dispatch', ...

    - exists
    - is a file
    - is executable
    """

    name = "entrypoint"
    url = BASE_DOCS_URL + "#heading--entrypoint"

    def __init__(self):
        self.text = ""

    def run(self, basedir: pathlib.Path) -> str:
        """Run the proper verifications."""
        entrypoint = get_entrypoint_from_dispatch(basedir)
        if entrypoint is None:
            self.text = (
                "Cannot find a proper 'dispatch' script pointing to an entrypoint."
            )
            return self.Result.NONAPPLICABLE

        if not entrypoint.exists():
            self.text = f"Cannot find the entrypoint file: {str(entrypoint)!r}"
            return self.Result.ERROR

        if not entrypoint.is_file():
            self.text = f"The entrypoint is not a file: {str(entrypoint)!r}"
            return self.Result.ERROR

        if not os.access(entrypoint, os.X_OK):
            self.text = f"The entrypoint file is not executable: {str(entrypoint)!r}"
            return self.Result.ERROR

        return self.Result.OK


class OpsMainCall(Linter):
    """Check that the entrypoint contains call to ops.main()."""

    name = "ops-main-call"
    url = f"{BASE_DOCS_URL}#heading--ops-main-call"
    text = ""

    def run(self, basedir: pathlib.Path) -> str:
        """Check preconditions and validate there's an ops.main() call."""
        if Framework().run(basedir) != Framework.Result.OPERATOR:
            self.text = "The charm is not based on the operator framework"
            return self.Result.NONAPPLICABLE

        entrypoint = get_entrypoint_from_dispatch(basedir)
        if entrypoint is None:
            self.text = (
                "Cannot find a proper 'dispatch' script pointing to an entrypoint."
            )
            return self.Result.NONAPPLICABLE

        if not entrypoint.exists():
            self.text = f"Cannot find the entrypoint file: {str(entrypoint)!r}"
            return self.Result.NONAPPLICABLE

        if not self._check_main_calls(entrypoint.read_text()):
            self.text = f"The ops.main() call missing from {str(entrypoint)!r}."
            return self.Result.ERROR

        return self.Result.OK

    def _check_main_calls(self, code: str):
        tree = ast.parse(code)
        imports = self._ops_main_imports(tree)
        return self._detect_main_calls(tree, imports=imports)

    def _ops_main_imports(self, tree: ast.AST) -> dict[str, str]:
        """Analyze imports and return a mapping {local_name: imported thing}."""
        rv = {}

        class ImportVisitor(ast.NodeVisitor):
            def visit_Import(self, node: ast.Import):
                for alias in node.names:
                    # Detect statements like `import ops`
                    if alias.name == "ops":
                        rv[alias.asname or alias.name] = "ops"
                    if alias.name == "ops.main" and alias.asname:
                        rv[alias.asname] = "ops.main"
                    elif alias.name.startswith("ops.") and not alias.asname:
                        rv["ops"] = "ops"

            def visit_ImportFrom(self, node: ast.ImportFrom):
                for alias in node.names:
                    # Detect statements like `from ops import main [as ops_main]`
                    if node.module in ("ops", "ops.main") and alias.name == "main":
                        rv[alias.asname or alias.name] = f"{node.module}.main"

        ImportVisitor().visit(tree)
        return rv

    def _detect_main_calls(self, tree: ast.AST, *, imports: dict[str, str]) -> bool:
        main_call_sites = []

        class OpsMainFinder(ast.NodeVisitor):
            def visit_Call(self, node: ast.Call):
                match node.func:
                    # Matches statements like `ops.main.main(...)`
                    case ast.Attribute(
                        value=ast.Attribute(value=ast.Name(id=first), attr=second),
                        attr=third,
                    ):
                        call_site = f"{first}.{second}.{third}(...)"
                    # Matches statements like `ops.main(...)`
                    case ast.Attribute(value=ast.Name(id=first), attr=second):
                        call_site = f"{first}.{second}(...)"
                    # Matches statements like `main(...)`
                    case ast.Name(id=first):
                        call_site = f"{first}(...)"
                    case _:
                        call_site = "_dummy()"

                match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)(.*)", call_site)
                if not match:
                    raise ValueError("impossible")
                alias, rest = match.groups()
                resolved = f"{imports.get(alias, '_dummy')}{rest}"

                if resolved in ("ops.main(...)", "ops.main.main(...)"):
                    main_call_sites.append(call_site)

                self.generic_visit(node)

        OpsMainFinder().visit(tree)
        return any(main_call_sites)


class AdditionalFiles(Linter):
    """Check that the charm does not contain any additional files in the prime directory.

    A few generated files and basic charm files are ignored.
    """

    name = "additional-files"
    text = "No additional files found in the charm."
    url = "https://juju.is/docs/sdk/include-extra-files-in-a-charm"

    IGNORE_FILES: set[pathlib.Path] = {
        pathlib.Path(f)
        for f in (
            {const.CHARMCRAFT_FILENAME, const.MANIFEST_FILENAME}
            | const.CHARM_MANDATORY_FILES
            | const.CHARM_OPTIONAL_FILES
        )
    }

    def _check_additional_files(
        self, stage_dir: pathlib.Path, prime_dir: pathlib.Path
    ) -> str:
        """Compare the staged files with the prime files."""
        errors: list[str] = []
        stage_dir = stage_dir.absolute()
        prime_dir = prime_dir.absolute()

        stage_files = {f.relative_to(stage_dir) for f in stage_dir.rglob("*")}
        prime_files = {f.relative_to(prime_dir) for f in prime_dir.rglob("*")}

        prime_files = prime_files - self.IGNORE_FILES

        for prime_file in prime_files:
            if prime_file not in stage_files:
                errors.append(f"File '{prime_file}' is not staged but in the charm.")

        if errors:
            self.text = "Error: Additional files found in the charm:\n" + "\n".join(
                errors
            )
            return self.Result.ERROR

        return self.Result.OK

    def run(self, basedir: pathlib.Path) -> str:
        """Run the proper verifications."""
        stage_dir = basedir.parent / "stage"
        if not stage_dir.exists() or not stage_dir.is_dir():
            # Does not work without the build environment
            self.text = (
                "Additional files check not applicable without a build environment."
            )
            return self.Result.NONAPPLICABLE

        return self._check_additional_files(stage_dir, basedir)


class PipCheck(Linter):
    """Check that the pip virtual environment is valid."""

    name = "pip-check"
    text = "Virtual environment is valid."
    url = "https://pip.pypa.io/en/stable/cli/pip_check/"

    def run(self, basedir: pathlib.Path) -> str:
        """Run pip check."""
        venv_dir = basedir / "venv"
        if not venv_dir.is_dir():
            self.text = "Charm does not contain a Python venv."
            return self.Result.NONAPPLICABLE
        if not (venv_dir / "lib").is_dir():
            self.text = "Python venv is not valid."
            return self.Result.NONAPPLICABLE
        python_exe = venv_dir / "bin" / "python"
        delete_parent = False
        if not python_exe.parent.exists():
            delete_parent = True
            python_exe.parent.mkdir()
        if not python_exe.exists():
            delete_python_exe = True
            python_exe.symlink_to(sys.executable)
        else:
            delete_python_exe = False

        pip_cmd = [sys.executable, "-m", "pip", "--python", str(python_exe), "check"]
        try:
            check = subprocess.run(
                pip_cmd,
                text=True,
                capture_output=True,
                check=False,
            )
            if check.returncode == os.EX_OK:
                result = self.Result.OK
            else:
                self.text = check.stdout
                result = self.Result.WARNING
        except (FileNotFoundError, PermissionError) as e:
            self.text = (
                f"{e.strerror}: Could not run Python executable at {sys.executable}."
            )
            result = self.Result.NONAPPLICABLE
        finally:
            if delete_python_exe:
                python_exe.unlink()
            if delete_parent:
                python_exe.parent.rmdir()

        return result


class PyDeps(Linter):
    """Check that all pydeps from all libs are available."""

    name = "pydeps"
    text = "All charmlibs dependencies are included"
    url = "https://documentation.ubuntu.com/charmcraft/stable/howto/manage-libraries/"

    @staticmethod
    def convert_to_fs(name: str) -> str:
        """Convert a package name into its on-disk form.

        This method will match the appearance a module's name would have in
        a site-packages directory.

        This turns "craft-cli", "craft_cli", "Craft-Cli" and "craft.cli" all into "craft_cli".
        """
        return re.sub(r"[-_.]+", "_", name).lower()

    @staticmethod
    def get_version_tuple(version_str: str) -> tuple[int | str, ...]:
        """Get a version tuple from a version string."""

        def coerce_to_int(s: str) -> str | int:
            try:
                return int(s)
            except ValueError:
                return s

        return tuple(coerce_to_int(s) for s in version_str.split("."))

    @classmethod
    def version_matches(
        cls, dep_spec: str, version: tuple[int | str, ...]
    ) -> bool | None:
        """Check if the given version matches the dependency specifier."""
        spec_matched = False
        for match in MIN_VERSION_REGEX.finditer(dep_spec):
            spec_matched = True
            if version >= cls.get_version_tuple(match.group(1)):
                return True
        for match in EXACT_VERSION_REGEX.finditer(dep_spec):
            spec_matched = True
            if version == cls.get_version_tuple(match.group(1)):
                return True
        for match in APPROX_VERSION_REGEX.finditer(dep_spec):
            spec_matched = True
            versions = set(match.group(1, 2)) - {None}
            match_version = cls.get_version_tuple(versions.pop())
            if version[: len(match_version)] == match_version:
                return True

        return not spec_matched

    @classmethod
    def _get_missing_deps(
        cls, deps: Collection[str], venv_path: pathlib.Path
    ) -> tuple[set[str], set[str]]:
        """Get the missing dependencies for a charmlib."""
        libs_path = next((venv_path / "lib").glob("python*")) / "site-packages"

        missing = set()
        non_matching_version = set()
        for dep in deps:
            match = PYTHON_NAME_REGEX.match(dep)
            if not match:
                continue
            name = cls.convert_to_fs(match.group(1))

            # If the package is installed as a distribution, we'll check the version.
            if infos := set(libs_path.glob(f"{name}*.dist-info")):
                info = infos.pop()
                # Trim the ".dist-info" off of the directory name, then extract
                # everything past the last "-" as that will always be the version.
                version_str = info.name[:-10].rpartition("-")[2]
                version = cls.get_version_tuple(version_str)
                if cls.version_matches(dep, version):
                    continue
                non_matching_version.add(dep)
                continue
            # Check if dependency exists as a top-level module
            if (libs_path / name).is_dir() or (libs_path / f"{name}.py").is_file():
                continue
            missing.add(match.group(1))

        return missing, non_matching_version

    def run(self, basedir: pathlib.Path) -> str:
        """Run the pydeps checker."""
        venv_dir = basedir / "venv"
        if not venv_dir.is_dir():
            self.text = "Charm does not contain a Python venv."
            return self.Result.NONAPPLICABLE
        lib_dir = basedir / "lib/charms"
        if not lib_dir.is_dir():
            self.text = "Charm does not have any charmlibs."
            return self.Result.NONAPPLICABLE

        deps = utils.collect_charmlib_pydeps(basedir=basedir)
        try:
            missing_deps, non_matching_versions = self._get_missing_deps(deps, venv_dir)
        except Exception as exc:
            self.text = str(exc)
            emit.debug(exc)
            return self.Result.UNKNOWN

        if missing_deps:
            missing_deps_str = ", ".join(sorted(missing_deps))
            self.text = f"Missing charmlibs dependencies: {missing_deps_str}"
            return self.Result.ERROR

        if non_matching_versions:
            non_matching_versions_str = "\n".join(sorted(non_matching_versions))
            self.text = f"Installed packages don't match charmlibs PYDEPS:\n{non_matching_versions_str}"
            return self.Result.WARNING

        return self.Result.OK


# all checkers to run; the order here is important, as some checkers depend on the
# results from others
CHECKERS: list[type[BaseChecker]] = [
    Language,
    JujuActions,
    JujuConfig,
    JujuMetadata,
    NamingConventions,
    Framework,
    Entrypoint,
    OpsMainCall,
    AdditionalFiles,
    PipCheck,
    PyDeps,
]
