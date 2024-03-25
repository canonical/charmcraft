# Steps

Release early, release often. Don't be lazy.

To use this doc: just replace X.Y.Z with the major.minor.patch version of
the release. The sequence of commands below should be good to copy and
paste, but do please pay attention to details!


## Preparation

- update `main` and run tests

    git checkout main
    git pull
    source venv/bin/activate
    ./run_tests
    deactivate

### if it's a minor release (Z == 0)

- tag `main` with only the minor version:

    git tag X.Y
    git push --tags

- create a new release branch

    git checkout -b release-X.Y

- create release notes after all `main` changes from last tag

    git log --first-parent main --decorate > release-X.Y.Z.txt

- tag the release (using those release notes)

    git tag -s X.Y.Z

### if it's a micro release (Z != 0)

- go to the release branch

    git checkout release-X.Y

- cherry pick the needed commits from `main`:

   git cherry-pick -m 1 COMMIT-HASH
   ...

- create release notes from the selected commits

    git log

- tag the release (using those release notes)

    git tag -s X.Y.Z


## Check all is ready

- build a tarball to test

    tox -e clean
    tox -e package

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

    sudo snap install --dangerous --classic charmcraft_X.Y.Z_amd64.snap
    cd ~  # wherever out of the project, to avoid any potential "file mispicking"
    charmcraft version


## Release

- push the tags

    git push --tags

    For a new tag, this will trigger publishing a release of the Python
    package on PyPI via GHA.

- release on GitHub

    xdg-open https://github.com/canonical/charmcraft/tags

    You should see all project tags, the top one should be this release.
    In the menu at right of the tag tag you just created, choose 'create
    release'. Copy the release notes into the release description.

    Attach the `dist/` files

    Click on "Publish release"

- release to Snap Store (for all the archs)

    snapcraft upload charmcraft_X.Y.Z_amd64.snap --release=edge,candidate
    snapcraft upload charmcraft_X.Y.Z_s390x.snap --release=edge,candidate
    snapcraft upload charmcraft_X.Y.Z_arm64.snap --release=edge,candidate
    snapcraft upload charmcraft_X.Y.Z_armhf.snap --release=edge,candidate
    snapcraft upload charmcraft_X.Y.Z_ppc64el.snap --release=edge,candidate

- remember to also release to the **corresponding track**

- verify all archs are consistent:

    snapcraft status charmcraft


## Final details

- write a new post in Discourse about the release:

    https://discourse.juju.is/c/charmcraft
