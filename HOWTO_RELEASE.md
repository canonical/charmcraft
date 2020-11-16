# Steps

Release early, release often. Don't be lazy.

To use this doc: just replace X.Y.Z with the major.minor.patch version of
the release. The sequence of commands below should be good to copy and
paste, but do please pay attention to details!


## Preparation

- update master and run tests

    git fetch upstream
    git merge upstream/master
    source venv/bin/activate
    ./run_tests
    deactivate

- create a new release branch

    git checkout -b release-X.Y.Z

- create release notes after all main changes from last tag

    git log --first-parent master --decorate

- tag the release (using those release notes)

    git tag -s X.Y.Z


## Check all is ready

- build a tarball to test

    rm -rf dist/
    ./setup.py sdist bdist_wheel

- try the tarball

    mkdir /tmp/testrelease
    cp dist/charmcraft-X.Y.Z.tar.gz /tmp/testrelease/
    cd /tmp/testrelease/
    tar -xf charmcraft-X.Y.Z.tar.gz
    cd ~  # wherever out of the project, to avoid any potential "file mispicking"
    fades -v -d file:///tmp/testrelease/charmcraft-X.Y.Z/ -x charmcraft version

- back in the project, build all the snaps for different architectures

    snapcraft remote-build

- try the snap (for your arch)

    sudo snap install --dangerous charmcraft_X.Y.Z_amd64.snap
    cd ~  # wherever out of the project, to avoid any potential "file mispicking"
    charmcraft version


## Release

- push the tags to upstream

    git push --tags upstream

- release in Github

    xdg-open https://github.com/canonical/charmcraft/tags

    You should see all project tags, the top one should be this release.
    In the menu at right of the tag tag you just created, choose 'create
    release'. Copy the release notes into the release description.

    Attach the `dist/` files

    Click on "Publish release"

- release to PyPI

    fades -d twine -x twine upload --verbose dist/*

- release to Snap Store (for all the archs)

    snapcraft upload charmcraft_X.Y.Z_amd64.snap --release=edge,beta
    snapcraft upload charmcraft_X.Y.Z_s390x.snap --release=edge,beta
    snapcraft upload charmcraft_X.Y.Z_arm64.snap --release=edge,beta
    snapcraft upload charmcraft_X.Y.Z_armhf.snap --release=edge,beta
    snapcraft upload charmcraft_X.Y.Z_ppc64el.snap --release=edge,beta

- verify all archs are consistent:

    snapcraft status charmcraft


## Final details

- update IRC channel topic

- send a mail with "Release X.Y.Z" title and release notes in the body to

    charmcraft@lists.launchpad.net

- write a new post in Discourse about the release:

    https://discourse.juju.is/c/charmcraft

- finally change the version number in `charmcraft/version.py`

- commit, push, create a PR for the branch
