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

"""Main entry point module for all the tool functionality."""

import logging
import os
import sys

import craft_providers.errors
import craft_store.errors
from craft_cli import (
    ArgumentParsingError,
    CommandGroup,
    CraftError,
    Dispatcher,
    EmitterMode,
    GlobalArgument,
    ProvideHelpException,
    emit,
)

from charmcraft import config, env, utils
from charmcraft.commands import analyze, clean, extensions, pack, store, version
from charmcraft.application.commands import init
from charmcraft.commands.store.client import ALTERNATE_AUTH_ENV_VAR
from charmcraft.const import SHARED_CACHE_ENV_VAR
from charmcraft.parts import setup_parts

# set up all the libs' loggers in DEBUG level so their content is grabbed by craft-cli's Emitter
for lib_name in ("craft_providers", "craft_parts", "craft_store"):
    logger = logging.getLogger(lib_name)
    logger.setLevel(logging.DEBUG)


# the summary of the whole program
GENERAL_SUMMARY = """
Charmcraft helps build, package and publish operators on Charmhub.

Together with the Python Operator Framework, charmcraft simplifies
operator development and collaboration.

See https://charmhub.io/publishing for more information.
"""

# Collect commands in different groups, for easier human consumption. Note that this is not
# declared in each command because it's much easier to do this separation/grouping in one
# central place and not distributed in several classes/files. Also note that order here is
# important when listing commands and showing help.
_basic_commands = [
    analyze.AnalyzeCommand,
    clean.CleanCommand,
    pack.PackCommand,
    version.VersionCommand,
]
_charmhub_commands = [
    # auth
    store.LoginCommand,
    store.LogoutCommand,
    store.WhoamiCommand,
    # name handling
    store.RegisterCharmNameCommand,
    store.RegisterBundleNameCommand,
    store.UnregisterNameCommand,
    store.ListNamesCommand,
    # pushing files and checking revisions
    store.UploadCommand,
    store.ListRevisionsCommand,
    # release process, and show status
    store.ReleaseCommand,
    store.PromoteBundleCommand,
    store.StatusCommand,
    store.CloseCommand,
    # libraries support
    store.CreateLibCommand,
    store.PublishLibCommand,
    store.ListLibCommand,
    store.FetchLibCommand,
    # resources support
    store.ListResourcesCommand,
    store.UploadResourceCommand,
    store.ListResourceRevisionsCommand,
]
_extensions_commands = [
    extensions.ExtensionsCommand,
    extensions.ListExtensionsCommand,
    extensions.ExpandExtensionsCommand,
]
COMMAND_GROUPS = [
    CommandGroup("Basic", _basic_commands),
    CommandGroup("Charmhub", _charmhub_commands),
    CommandGroup("Extensions", _extensions_commands),
]

# non-charmcraft useful environment variables to log
EXTRA_ENVIRONMENT = ("DESKTOP_SESSION", "XDG_CURRENT_DESKTOP", SHARED_CACHE_ENV_VAR)


def _get_system_details():
    """Produce details about the system."""
    # prepare the useful environment variables: all CHARMCRAFT* (hiding AUTH keys)
    # and desktop/session
    useful_env = {
        name: value
        for name, value in os.environ.items()
        if name.startswith("CHARMCRAFT") or name in EXTRA_ENVIRONMENT
    }
    if ALTERNATE_AUTH_ENV_VAR in useful_env:
        useful_env[ALTERNATE_AUTH_ENV_VAR] = "<hidden>"
    env_string = ", ".join(f"{name}={value!r}" for name, value in sorted(useful_env.items()))
    if not env_string:
        env_string = "None"

    os_platform = utils.get_os_platform()
    return f"System details: {os_platform}; Environment: {env_string}"


def _emit_error(error, cause=None):
    """Emit the error in a centralized way so we can alter it consistently."""
    # set the cause, if any
    if cause is not None:
        error.__cause__ = cause

    # if it's a charmcraft running inside a provided instance, do not report the internal logpath
    if env.is_charmcraft_running_in_managed_mode():
        error.logpath_report = False

    # finally, emit
    emit.error(error)


def main(argv):
    """Provide the main entry point."""
    emit.debug("Starting classic fallback.")

    extra_global_options = [
        GlobalArgument(
            "project_dir",
            "option",
            "-p",
            "--project-dir",
            "Specify the project's directory (defaults to current)",
        ),
    ]

    # process
    try:
        setup_parts()

        # load the dispatcher and put everything in motion
        dispatcher = Dispatcher(
            "charmcraft",
            COMMAND_GROUPS,
            summary=GENERAL_SUMMARY,
            extra_global_args=extra_global_options,
        )
        global_args = dispatcher.pre_parse_args(argv[1:])
        loaded_config = config.load(global_args["project_dir"])
        dispatcher.load_command(loaded_config)
        emit.debug(_get_system_details())
        retcode = dispatcher.run()

    except ArgumentParsingError as err:
        print(err, file=sys.stderr)  # to stderr, as argparse normally does
        emit.ended_ok()
        retcode = 1
    except ProvideHelpException as err:
        print(err, file=sys.stderr)  # to stderr, as argparse normally does
        emit.ended_ok()
        retcode = 0
    except CraftError as err:
        _emit_error(err)
        retcode = err.retcode
    except craft_store.errors.CraftStoreError as err:
        error = CraftError(f"craft-store error: {err}")
        _emit_error(error)
        retcode = 1
    except craft_providers.errors.ProviderError as err:
        _emit_error(CraftError(err.brief, details=err.details, resolution=err.resolution))
        retcode = 1
    except KeyboardInterrupt as exc:
        error = CraftError("Interrupted.")
        _emit_error(error, cause=exc)
        retcode = 1
    except Exception as err:
        error = CraftError(f"charmcraft internal error: {err!r}")
        _emit_error(error, cause=err)
        retcode = 1
    else:
        emit.ended_ok()
        if retcode is None:
            retcode = 0

    return retcode


if __name__ == "__main__":
    if env.is_charmcraft_running_in_managed_mode():
        logpath = env.get_managed_environment_log_path()
    else:
        logpath = None

    emit.init(
        EmitterMode.BRIEF,
        "charmcraft",
        "Starting legacy charmcraft entrypoint",
        log_filepath=logpath,
    )
    sys.exit(main(sys.argv))
