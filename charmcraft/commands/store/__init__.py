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
import textwrap
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
    help_msg = "Login to Ubuntu Single Sign On."
    overview = textwrap.dedent("""
        Log in to the Store using Ubuntu Single Sign On.

        It will open a browser window where you will need to provide the
        relevant credentials.

        See also the "whoami" command to verify you're properly logged in,
        and the "logout" command to clear the session credentials.
    """)

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        store.login()
        logger.info("Login successful.")


class LogoutCommand(BaseCommand):
    """Clear store-related credentials."""
    name = 'logout'
    help_msg = "Clear session credentials."
    overview = textwrap.dedent("""
        Clear the Store session credentials.

        Because of the authentication mechanism used there is no Store-side state
        to clear, so this operation does not contact the Store.

        See also the "whoami" command to verify you're properly logged in,
        and the "login" command to log in to the Store.
    """)

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        store.logout()
        logger.info("Credentials cleared.")


class WhoamiCommand(BaseCommand):
    """Show login information."""
    name = 'whoami'
    help_msg = "Return your login information relevant to the Store."
    overview = textwrap.dedent("""
        Show login information for the current Store user.

        See also the "login" and "logout" commands for more information about
        the authentication cycle.
    """)

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
    help_msg = "Register a charm name in the Store."
    overview = textwrap.dedent("""
        Register a charm name in the Store.

        This is the first step when developing a charm, and needed only once
        for that charm.

        It will automatically take you through the login process if
        your credentials are missing or too old.
    """)
    common = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument('name', help="The name to register in the Store.")

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        store.register_name(parsed_args.name)
        logger.info("Congrats! You are now the publisher of %r.", parsed_args.name)


class ListNamesCommand(BaseCommand):
    """List the charms registered in the Store."""
    name = 'names'
    help_msg = "List the charm names registered in the Store."
    overview = textwrap.dedent("""
        List the names registered to the current Store user, together
        with each package's type, visibility and status.

        It will automatically take you through the login process if
        your credentials are missing or too old.
    """)
    common = True

    def run(self, parsed_args):
        """Run the command."""
        store = Store()
        result = store.list_registered_names()
        if not result:
            logger.info("Nothing found.")
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
    help_msg = "Upload a charm file to the Store."
    overview = textwrap.dedent("""
        Upload the charm file to the Store.

        This command covers both pushing the charm itelf, as well as the
        subsequent status verification actions, and will finish successfully once
        the package is approved by the Store (otherwise it will report the
        verification failure reasons).

        It will automatically take you through the login process if
        your credentials are missing or too old.
    """)
    common = True

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
            help="The path to the charm file to upload.")

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
    help_msg = "List existing revisions for a charm in the Store."
    overview = textwrap.dedent("""
        List existing revisions for a charm in the Store, along with the version
        and status for each, and when they were created.

        It will automatically take you through the login process if
        your credentials are missing or too old.
    """)
    common = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument('--name', help="The name of the charm.")

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
    help_msg = "Release a charm revision to one or more channels."
    overview = textwrap.dedent("""
        Release a charm revision to the indicated channels (one or many).

        Each channel has the [track/]risk[/branch] structure, where the risk
        (stable, candidate, beta or edge) is mandatory, while track (default
        to "latest") and branch are optional.

        Some channel examples:

            stable
            edge
            2.0/candidate
            beta/hotfix

        It will automatically take you through the login process if
        your credentials are missing or too old.
    """)
    common = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument(
            'revision', type=int, help='The revision to release.')
        parser.add_argument(
            'channels', metavar='channel', nargs='+',
            help="The channel(s) to release to.")
        parser.add_argument('--name', help="The name of the charm.")

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

        store.release(charm_name, parsed_args.revision, parsed_args.channels)
        logger.info(
            "Revision %d of charm %r released to %s",
            parsed_args.revision, charm_name, ", ".join(parsed_args.channels))


class StatusCommand(BaseCommand):
    """List released revisions for a charm."""
    name = 'status'
    help_msg = "List released revisions of a package."
    overview = textwrap.dedent("""
        List the released revisions for a package.

        It will show each risk (with all its relevant information) for the
        different tracks, series, etc.

        It will automatically take you through the login process if
        your credentials are missing or too old.
    """)
    common = True

    def fill_parser(self, parser):
        """Add own parameters to the general parser."""
        parser.add_argument('--name', help="The name of the charm.")

    def run(self, parsed_args):
        """Run the command."""
        if parsed_args.name:
            charm_name = parsed_args.name
        else:
            charm_name = get_name_from_metadata()
            if charm_name is None:
                raise CommandError(
                    "Can't access name in 'metadata.yaml' file. The 'status' command needs to "
                    "be executed in a valid project's directory, or indicate the charm name with "
                    "the --name option.")

        store = Store()
        channel_map, channels, revisions = store.list_releases(charm_name)
        if not channel_map:
            logger.info("Nothing found")
            return

        # build easier to access structures
        releases_by_channel = {item.channel: item for item in channel_map}
        revisions_by_revno = {item.revision: item for item in revisions}

        # process and order the channels, while preserving the tracks order
        all_tracks = []
        per_track = {}
        branch_present = False
        for channel in channels:
            # it's super rare to have a more than just a bunch of tracks (furthermore, normally
            # there's only one), so it's ok to do this sequential search
            if channel.track not in all_tracks:
                all_tracks.append(channel.track)

            nonbranches_list, branches_list = per_track.setdefault(channel.track, ([], []))
            if channel.branch is None:
                # insert branch right after its fallback
                for idx, stored in enumerate(nonbranches_list, 1):
                    if stored.name == channel.fallback:
                        nonbranches_list.insert(idx, channel)
                        break
                else:
                    nonbranches_list.append(channel)
            else:
                branches_list.append(channel)
                branch_present = True

        headers = ['Track', 'Channel', 'Version', 'Revision']
        if branch_present:
            headers.append('Expires at')

        # show everything, grouped by tracks, with regular channels at first and
        # branches (if any) after those
        data = []
        for track in all_tracks:
            release_shown_for_this_track = False
            shown_track = track
            channels, branches = per_track[track]

            for channel in channels:
                description = channel.risk

                # get the release of the channel, fallbacking accordingly
                release = releases_by_channel.get(channel.name)
                if release is None:
                    version = revno = '↑' if release_shown_for_this_track else '-'
                else:
                    release_shown_for_this_track = True
                    revno = release.revision
                    revision = revisions_by_revno[revno]
                    version = revision.version

                data.append([shown_track, description, version, revno])

                # stop showing the track name for the rest of the track
                shown_track = ''

            for branch in branches:
                description = '/'.join((branch.risk, branch.branch))
                release = releases_by_channel[branch.name]
                expiration = release.expires_at.isoformat()
                revision = revisions_by_revno[release.revision]
                data.append(['', description, revision.version, release.revision, expiration])

        table = tabulate(data, headers=headers, tablefmt='plain', numalign='left')
        for line in table.splitlines():
            logger.info(line)
