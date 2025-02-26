PROJECT=charmcraft
ifneq ($(wildcard /etc/os-release),)
include /etc/os-release
export
endif

ifneq ($(VERSION_CODENAME),)
SETUP_TESTS_EXTRA_ARGS=--extra apt-$(VERSION_CODENAME)
endif

UV_FROZEN=true

include common.mk

.PHONY: format
format: format-ruff format-codespell  ## Run all automatic formatters

.PHONY: lint
lint: lint-ruff lint-codespell lint-mypy lint-pyright lint-shellcheck lint-yaml lint-docs lint-twine  ## Run all linters

.PHONY: pack
pack: pack-pip pack-snap  ## Build all packages

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

.PHONY: setup
setup: install-uv setup-precommit ## Set up a development environment
	uv sync --frozen $(SETUP_TESTS_EXTRA_ARGS) --extra docs --extra lint --extra types

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

.PHONY: install-lint-build-deps
install-lint-build-deps:
ifeq ($(shell which apt-get),)
	$(warning apt-get not found. Please install lint dependencies yourself.)
else
	sudo $(APT) install python-apt-dev libapt-pkg-dev clang
endif

.PHONY: install-linux-build-deps
install-linux-build-deps:
ifneq ($(shell which snap),)
	sudo snap install lxd
	sudo lxd init --auto
endif

.PHONY: install-macos-build-deps
install-macos-build-deps:
ifneq ($(OS),Darwin)
else ifeq ($(shell which brew),)
	$(warning brew not installed. Please install dependencies yourself.)
else
	brew install libgit2@1.7  # For building pygit2
	sudo cp -R /usr/local/opt/libgit2@1.7/* /usr/local
	brew install multipass
	brew install skopeo
endif

.PHONY: schema
schema: install-uv
	uv run tools/schema.py > schema/charmcraft.json
