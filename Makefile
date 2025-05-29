PROJECT=charmcraft
# Define when more than the main package tree requires coverage
# like is the case for snapcraft (snapcraft and snapcraft_legacy):
# COVERAGE_SOURCE="starcraft"
UV_TEST_GROUPS := "--group=dev"
UV_DOCS_GROUPS := "--group=docs"
UV_LINT_GROUPS := "--group=lint" "--group=types"
UV_TICS_GROUPS := "--group=tics"

# If you have dev dependencies that depend on your distro version, uncomment these:
ifneq ($(wildcard /etc/os-release),)
include /etc/os-release
endif
ifdef VERSION_CODENAME
UV_TEST_GROUPS += "--group=dev-$(VERSION_CODENAME)"
UV_DOCS_GROUPS += "--group=dev-$(VERSION_CODENAME)"
UV_LINT_GROUPS += "--group=dev-$(VERSION_CODENAME)"
UV_TICS_GROUPS += "--group=dev-$(VERSION_CODENAME)"
endif

include common.mk

# common.mk globs too much, such as test expectations
PRETTIER_FILES="tests/spread/**/task.yaml" "*.yaml" "*.md" "snap/snapcraft.yaml" ".github/**/*.{yml,yaml}"

.PHONY: format
format: format-ruff format-codespell format-prettier  ## Run all automatic formatters

.PHONY: lint
lint: lint-ruff lint-codespell lint-mypy lint-pyright lint-shellcheck lint-prettier lint-docs lint-twine  ## Run all linters

.PHONY: pack
pack: pack-pip  ## Build all packages

.PHONY: pack-snap
pack-snap: snap/snapcraft.yaml  ##- Build snap package
ifeq ($(shell which snapcraft),)
	sudo snap install --classic snapcraft
endif
	snapcraft pack

.PHONY: publish
publish: publish-pypi  ## Publish packages

.PHONY: publish-pypi
publish-pypi: clean package-pip lint-twine  ##- Publish Python packages to pypi
	uv tool run twine upload dist/*

# Find dependencies that need installing
APT_PACKAGES :=
ifeq ($(wildcard /usr/share/doc/libapt-pkg-dev/copyright),)
APT_PACKAGES += libapt-pkg-dev
endif
ifeq ($(wildcard /usr/share/doc/libffi-dev/copyright),)
APT_PACKAGES += libffi-dev
endif
ifeq ($(wildcard /usr/share/doc/libgit2-dev/copyright),)
APT_PACKAGES += libgit2-dev
endif
ifeq ($(wildcard /usr/include/libxml2/libxml/xpath.h),)
APT_PACKAGES += libxml2-dev
endif
ifeq ($(wildcard /usr/include/libxslt/xslt.h),)
APT_PACKAGES += libxslt1-dev
endif
ifeq ($(wildcard /usr/share/doc/libyaml-dev/copyright),)
APT_PACKAGES += libyaml-dev
endif
ifeq ($(wildcard /usr/share/doc/python3-dev/copyright),)
APT_PACKAGES += python3-dev
endif
ifeq ($(wildcard /usr/share/doc/python3-pip/copyright),)
APT_PACKAGES += python3-pip
endif
ifeq ($(wildcard /usr/share/doc/python3-setuptools/copyright),)
APT_PACKAGES += python3-setuptools
endif
ifeq ($(wildcard /usr/share/doc/python3-venv/copyright),)
APT_PACKAGES += python3-venv
endif
ifeq ($(wildcard /usr/share/doc/python3-wheel/copyright),)
APT_PACKAGES += python3-wheel
endif
ifeq ($(shell which skopeo),)
APT_PACKAGES += skopeo
endif
ifeq ($(shell which cargo),)
APT_PACKAGES += cargo
endif

# Used for installing build dependencies in CI.
.PHONY: install-build-deps
install-build-deps: install-linux-build-deps install-macos-build-deps
	# Ensure the system pip is new enough. If we get an error about breaking system packages, it is.
	sudo pip install 'pip>=22.2' 2> /dev/null || true
ifeq ($(APT_PACKAGES),)
else ifeq ($(shell which apt-get),)
	$(warning Cannot install build dependencies without apt.)
	$(warning Please ensure the equivalents to these packages are installed: $(APT_PACKAGES))
else
	sudo $(APT) install $(APT_PACKAGES)
endif

# If additional build dependencies need installing in order to build the linting env.
.PHONY: install-lint-build-deps
install-lint-build-deps:
ifeq ($(shell which apt-get),)
	$(warning apt-get not found. Please install lint dependencies yourself.)
else
	sudo $(APT) install python-apt-dev libapt-pkg-dev clang
endif

.PHONY: install-linux-build-deps
install-linux-build-deps:
ifneq ($(wildcard /snap/bin/lxd),)
else ifneq ($(shell which snap),)
	sudo snap install lxd
	sudo lxd init --auto
else
	$(warning lxd not installed and snap is not available. Please install snap and lxd)
endif

.PHONY: install-macos-build-deps
install-macos-build-deps:
ifneq ($(OS),Darwin)
else ifeq ($(shell which brew),)
	$(warning brew not installed. Please install dependencies yourself.)
else
	brew install multipass
	# Work around installation conflict in GH CI.
	if [ "${CI:-nope}" != "nope" ]; then sudo rm -f /usr/local/bin/idle* /usr/local/bin/pip* /usr/local/bin/py* ; fi
	brew install skopeo
	brew install libgit2@1.7  # For building pygit2
	sudo cp -R /usr/local/opt/libgit2@1.7/* /usr/local
endif

.PHONY: schema
schema: install-uv
	uv run tools/schema.py > schema/charmcraft.json
