# Steps

Release early, release often. Don't be lazy.


## Preparation

- update master and run tests

    git fetch upstream
    git merge upstream/master
    source venv/bin/activate
    ./run_tests 

- create a new release branch

    git checkout -b release-0.3.0

- create release notes after all main changes from last tag 

    git log --first-parent master --decorate 

- tag the release (using those release notes)

    git tag -s 0.3.0


## Check all is ready

- build a tarball to test

    rm -rf dist/
    ./setup.py sdist bdist_wheel

- try the tarball

    mkdir /tmp/testrelease
    cp dist/charmcraft-0.3.0.tar.gz /tmp/testrelease/
    cd /tmp/testrelease/
    tar -xf charmcraft-0.3.0.tar.gz
    cd ~  # wherever out of the project, to avoid any potential "file mispicking"
    fades -v -d file:///tmp/testrelease/charmcraft-0.3.0/ -x charmcraft version

- back in the project, build a snap

    snapcraft clean
    snapcraft

- try the snap

    sudo snap install --dangerous charmcraft_0.3.0_amd64.snap
    cd ~  # wherever out of the project, to avoid any potential "file mispicking"
    charmcraft version


## Release

- push the tags to upstream

    git push --tags upstream

- release in Github

    xdg-open https://github.com/canonical/charmcraft/tags
    (you should see all project tags, the top one should be this release's one)
    In the menu at right of the tag tag you just created, choose 'create release'
    Copy the release notes into the release description
    Attach the `dist/` files
    Click on "Publish release"

- release to PyPI

    fades -d twine -x twine upload --verbose dist/*

- release to Snap Store

    snapcraft push charmcraft_0.3.0_amd64.snap
    snapcraft release charmcraft 7 beta
    # FIXME: what about other archs


## Final details

- update IRC channel topic

- finally change the version number in `charmcraft/version.py`

- commit, push, create a PR for the branch
