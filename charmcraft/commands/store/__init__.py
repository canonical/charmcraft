# Copyright 2020 Canonical Ltd.
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

"""Commands related to the Store, a thin layer above real functionality."""

import logging
import os
import pathlib
from operator import attrgetter

import yaml
from tabulate import tabulate

from charmcraft.cmdbase import BaseCommand, CommandError

from .store import Store

logger = logging.getLogger('charmcraft.commands.store')


def get_name_from_metadata():
    """Return the name (if present) from metadata file (if there and readable and sane)."""
    try:
        with open('metadata.yaml', 'rb') as fh:
            metadata = yaml.safe_load(fh)
        charm_name = metadata['name']
    except (yaml.error.YAMLError, OSError, KeyError):
        return
    return charm_name


class LoginCommand(BaseCommand):
    """Log into the store."""
    name = 'login'
    help_msg = "login to Ubuntu Single Sign On"

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        store.login()
        logger.info("Login successful")


class LogoutCommand(BaseCommand):
    """Clear store-related credentials."""
    name = 'logout'
    help_msg = "clear session credentials"

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        store.logout()
        logger.info("Credentials cleared")


class WhoamiCommand(BaseCommand):
    """Show login information."""
    name = 'whoami'
    help_msg = "returns your login information relevant to the Store"

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        result = store.whoami()

        data = [
            ('name:', result.name),
            ('username:', result.username),
            ('id:', result.userid),
        ]
        table = tabulate(data, tablefmt='plain')
        for line in table.splitlines():
            logger.info(line)


class RegisterNameCommand(BaseCommand):
    """Register a name in the Store."""
    name = 'register'
    help_msg = "register a name in the Store"

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument('name', help="the name to register in the Store")

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        store.register_name(parsed_args.name)
        logger.info("Congrats! You are now the publisher of %r", parsed_args.name)


class ListNamesCommand(BaseCommand):
    """List the charms registered in the Store."""
    name = 'names'
    help_msg = "list the charm names registered the Store"

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        result = store.list_registered_names()
        if not result:
            logger.info("Nothing found")
            return

        headers = ['Name', 'Visibility', 'Status']
        data = []
        for item in result:
            visibility = 'private' if item.private else 'public'
            data.append([
                item.name,
                visibility,
                item.status,
            ])

        table = tabulate(data, headers=headers, tablefmt='plain')
        for line in table.splitlines():
            logger.info(line)


class UploadCommand(BaseCommand):
    """Upload a charm file to the Store."""
    name = 'upload'
    help_msg = "upload a charm file to the Store"

    def _discover_charm(self, charm_filepath):
        """Discover the charm name and file path.

        If received path is None, a metadata.yaml will be searched in the current directory. If
        path is given the name is taken from the filename.

        """
        if charm_filepath is None:
            # discover the info using project's metadata, asume the file has the project's name
            # with a .charm extension
            charm_name = get_name_from_metadata()
            if charm_name is None:
                raise CommandError(
                    "Can't access name in 'metadata.yaml' file. The 'upload' command needs to be "
                    "executed in a valid project's directory, or point to a charm file with "
                    "the --charm-file option.")

            charm_filepath = pathlib.Path(charm_name + '.charm').absolute()
            if not os.access(str(charm_filepath), os.R_OK):  # access doesnt support pathlib in 3.5
                raise CommandError(
                    "Can't access charm file {!r}. You can indicate a charm file with "
                    "the --charm-file option.".format(str(charm_filepath)))

        else:
            # the path is given, asume the charm name is part of the file name
            # XXX Facundo 2020-06-30: Actually, we need to open the ZIP file, extract the
            # included metadata.yaml file, and read the name from there. Issue: #77.
            charm_filepath = charm_filepath.expanduser()
            if not os.access(str(charm_filepath), os.R_OK):  # access doesnt support pathlib in 3.5
                raise CommandError(
                    "Can't access the indicated charm file: {!r}".format(str(charm_filepath)))
            if not charm_filepath.is_file():
                raise CommandError(
                    "The indicated charm is not a file: {!r}".format(str(charm_filepath)))

            charm_name = charm_filepath.stem

        return charm_name, charm_filepath

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument(
            '--charm-file', type=pathlib.Path,
            help="the path to the charm file to be uploaded")

    def run(self, parsed_args):
        """Run the command."""
        name, path = self._discover_charm(parsed_args.charm_file)
        store = Store()
        result = store.upload(name, path)
        if result.ok:
            logger.info("Revision %s of %r created", result.revision, str(name))
        else:
            # XXX Facundo 2020-06-30: at some point in the future the Store will give us also a
            # reason why it failed, to improve the message. Issue: #78.
            logger.info("Upload failed: got status %r", result.status)


class ListRevisionsCommand(BaseCommand):
    """List existing revisions for a charm."""
    name = 'revisions'
    help_msg = "list existing revisions for a charm in the Store"

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument('--name', help="the name of the charm to get revisions")

    def run(self, parsed_args):
        """Run the command."""
        if parsed_args.name:
            charm_name = parsed_args.name
        else:
            charm_name = get_name_from_metadata()
            if charm_name is None:
                raise CommandError(
                    "Can't access name in 'metadata.yaml' file. The 'revisions' command needs to "
                    "be executed in a valid project's directory, or indicate the charm name with "
                    "the --name option.")

        store = Store()
        result = store.list_revisions(charm_name)
        if not result:
            logger.info("Nothing found")
            return

        headers = ['Revision', 'Version', 'Created at', 'Status']
        data = []
        for item in sorted(result, key=attrgetter('revision'), reverse=True):
            # use just the status or include error message/code in it (if exist)
            if item.errors:
                errors = ("{0.message} [{0.code}]".format(e) for e in item.errors)
                status = "{}: {}".format(item.status, '; '.join(errors))
            else:
                status = item.status

            data.append([
                item.revision,
                item.version,
                item.created_at.strftime('%Y-%m-%d'),
                status,
            ])

        table = tabulate(data, headers=headers, tablefmt='plain', numalign='left')
        for line in table.splitlines():
            logger.info(line)


class ReleaseCommand(BaseCommand):
    """Release a charm revision to specific channels."""
    name = 'release'
    help_msg = "relase a charm revision to one or more channels"

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument(
            'channels', metavar='channel', nargs='+',
            help="the channel(s) to release to")
        parser.add_argument('--name', help="the name of the charm to get revisions")
        parser.add_argument(
            '--revision', type=int,
            help="the revision to release (defaults to latest)")

    def run(self, parsed_args):
        """Run the command."""
        store = Store()

        if parsed_args.name:
            charm_name = parsed_args.name
        else:
            charm_name = get_name_from_metadata()
            if charm_name is None:
                raise CommandError(
                    "Can't access name in 'metadata.yaml' file. The 'release' command needs to "
                    "be executed in a valid project's directory, or indicate the charm name with "
                    "the --name option.")

        if parsed_args.revision:
            revision = parsed_args.revision
        else:
            # find out which is the latest revision for the charm
            revisions = store.list_revisions(charm_name)
            if not revisions:
                raise CommandError(
                    "The charm {!r} doesn't have any uploaded revision to release."
                    .format(charm_name))
            revision = max(rev.revision for rev in revisions)

        store.release(charm_name, revision, parsed_args.channels)
        logger.info(
            "Revision %d of charm %r released ok to %s",
            revision, charm_name, ", ".join(parsed_args.channels))
