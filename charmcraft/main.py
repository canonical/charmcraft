# Copyright 2020-2021 Canonical Ltd.
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
import sys

from craft_cli import emit, EmitterMode, CraftError
from fake_craft_cli import (
    ArgumentParsingError,
    CommandGroup,
    Dispatcher,
    GlobalArgument,
    ProvideHelpException,
)

from charmcraft import config, __version__
from charmcraft.cmdbase import CommandError
from charmcraft.commands import build, clean, init, pack, store, version, analyze
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
    build.BuildCommand,
    clean.CleanCommand,
    pack.PackCommand,
    init.InitCommand,
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
    store.ListNamesCommand,
    # pushing files and checking revisions
    store.UploadCommand,
    store.ListRevisionsCommand,
    # release process, and show status
    store.ReleaseCommand,
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
COMMAND_GROUPS = [
    CommandGroup("Basic", _basic_commands),
    CommandGroup("Charmhub", _charmhub_commands),
]


def main(argv=None):
    """Provide the main entry point."""
    emit.init(EmitterMode.NORMAL, "charmcraft", f"Starting charmcraft version {__version__}")

    if argv is None:
        argv = sys.argv

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
        command = dispatcher.load_command(loaded_config)
        if command.needs_config and not loaded_config.project.config_provided:
            raise ArgumentParsingError(
                "The specified command needs a valid 'charmcraft.yaml' configuration file (in "
                "the current directory or where specified with --project-dir option); see "
                "the reference: https://discourse.charmhub.io/t/charmcraft-configuration/4138"
            )
        retcode = dispatcher.run()

    except ArgumentParsingError as err:
        print(err, file=sys.stderr)  # to stderr, as argparse normally does
        emit.ended_ok()
        retcode = 1
    except ProvideHelpException as err:
        print(err, file=sys.stderr)  # to stderr, as argparse normally does
        emit.ended_ok()
        retcode = 0
    except CommandError as err:
        emit.error(err)
        retcode = err.retcode
    except KeyboardInterrupt as exc:
        error = CraftError("Interrupted.")
        error.__cause__ = exc
        emit.error(error)
        retcode = 1
    except Exception as err:
        error = CraftError(f"charmcraft internal error: {err!r}")
        error.__cause__ = err
        emit.error(error)
        retcode = 1
    else:
        emit.ended_ok()
        if retcode is None:
            retcode = 0

    return retcode


if __name__ == "__main__":
    sys.exit(main(sys.argv))
