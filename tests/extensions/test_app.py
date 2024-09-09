# Copyright 2023 Canonical Ltd.
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
import pytest

from charmcraft.errors import ExtensionError
from charmcraft.extensions import apply_extensions
from charmcraft.extensions.app import (
    DjangoFramework,
    FlaskFramework,
    GoFramework,
)


def make_flask_input_yaml():
    return {
        "type": "charm",
        "name": "test-flask",
        "summary": "test summary",
        "description": "test description",
        "bases": [{"name": "ubuntu", "channel": "22.04"}],
        "extensions": ["flask-framework"],
    }


@pytest.fixture(name="flask_input_yaml")
def flask_input_yaml_fixture():
    return make_flask_input_yaml()


@pytest.mark.parametrize(
    ("input_yaml", "experimental", "expected"),
    [
        (
            make_flask_input_yaml(),
            False,
            {
                "actions": FlaskFramework.actions,
                "assumes": ["k8s-api"],
                "bases": [{"channel": "22.04", "name": "ubuntu"}],
                "containers": {
                    "flask-app": {"resource": "flask-app-image"},
                },
                "description": "test description",
                "name": "test-flask",
                "charm-libs": [
                    {"lib": "traefik_k8s.ingress", "version": "2"},
                    {"lib": "observability_libs.juju_topology", "version": "0"},
                    {"lib": "grafana_k8s.grafana_dashboard", "version": "0"},
                    {"lib": "loki_k8s.loki_push_api", "version": "0"},
                    {"lib": "data_platform_libs.data_interfaces", "version": "0"},
                    {"lib": "prometheus_k8s.prometheus_scrape", "version": "0"},
                    {"lib": "redis_k8s.redis", "version": "0"},
                    {"lib": "data_platform_libs.s3", "version": "0"},
                    {"lib": "saml_integrator.saml", "version": "0"},
                ],
                "config": {
                    "options": {**FlaskFramework.options},
                },
                "parts": {
                    "charm": {
                        "plugin": "charm",
                        "source": ".",
                        "build-snaps": ["rustup"],
                        "override-build": "rustup default stable\ncraftctl default",
                    }
                },
                "peers": {"secret-storage": {"interface": "secret-storage"}},
                "provides": {
                    "metrics-endpoint": {"interface": "prometheus_scrape"},
                    "grafana-dashboard": {"interface": "grafana_dashboard"},
                },
                "requires": {
                    "logging": {"interface": "loki_push_api"},
                    "ingress": {"interface": "ingress", "limit": 1},
                },
                "resources": {
                    "flask-app-image": {
                        "description": "flask application image.",
                        "type": "oci-image",
                    },
                },
                "summary": "test summary",
                "type": "charm",
            },
        ),
        (
            {
                "type": "charm",
                "name": "test-django",
                "summary": "test summary",
                "description": "test description",
                "base": "ubuntu@22.04",
                "platforms": {
                    "amd64": None,
                    "arm64": None,
                    "armhf": None,
                    "ppc64el": None,
                    "riscv64": None,
                    "s390x": None,
                },
                "extensions": ["django-framework"],
            },
            True,
            {
                "actions": DjangoFramework.actions,
                "assumes": ["k8s-api"],
                "base": "ubuntu@22.04",
                "platforms": {
                    "amd64": None,
                    "arm64": None,
                    "armhf": None,
                    "ppc64el": None,
                    "riscv64": None,
                    "s390x": None,
                },
                "containers": {
                    "django-app": {"resource": "django-app-image"},
                },
                "description": "test description",
                "name": "test-django",
                "charm-libs": [
                    {"lib": "traefik_k8s.ingress", "version": "2"},
                    {"lib": "observability_libs.juju_topology", "version": "0"},
                    {"lib": "grafana_k8s.grafana_dashboard", "version": "0"},
                    {"lib": "loki_k8s.loki_push_api", "version": "0"},
                    {"lib": "data_platform_libs.data_interfaces", "version": "0"},
                    {"lib": "prometheus_k8s.prometheus_scrape", "version": "0"},
                    {"lib": "redis_k8s.redis", "version": "0"},
                    {"lib": "data_platform_libs.s3", "version": "0"},
                    {"lib": "saml_integrator.saml", "version": "0"},
                ],
                "config": {
                    "options": {**DjangoFramework.options},
                },
                "parts": {
                    "charm": {
                        "plugin": "charm",
                        "source": ".",
                        "build-snaps": ["rustup"],
                        "override-build": "rustup default stable\ncraftctl default",
                    }
                },
                "peers": {"secret-storage": {"interface": "secret-storage"}},
                "provides": {
                    "metrics-endpoint": {"interface": "prometheus_scrape"},
                    "grafana-dashboard": {"interface": "grafana_dashboard"},
                },
                "requires": {
                    "logging": {"interface": "loki_push_api"},
                    "ingress": {"interface": "ingress", "limit": 1},
                },
                "resources": {
                    "django-app-image": {
                        "description": "django application image.",
                        "type": "oci-image",
                    },
                },
                "summary": "test summary",
                "type": "charm",
            },
        ),
        (
            {
                "type": "charm",
                "name": "test-go",
                "summary": "test summary",
                "description": "test description",
                "bases": [{"name": "ubuntu", "channel": "24.04"}],
                "extensions": ["go-framework"],
            },
            True,
            {
                "actions": GoFramework.actions,
                "assumes": ["k8s-api"],
                "bases": [{"channel": "24.04", "name": "ubuntu"}],
                "containers": {
                    "app": {"resource": "app-image"},
                },
                "description": "test description",
                "name": "test-go",
                "charm-libs": [
                    {"lib": "traefik_k8s.ingress", "version": "2"},
                    {"lib": "observability_libs.juju_topology", "version": "0"},
                    {"lib": "grafana_k8s.grafana_dashboard", "version": "0"},
                    {"lib": "loki_k8s.loki_push_api", "version": "0"},
                    {"lib": "data_platform_libs.data_interfaces", "version": "0"},
                    {"lib": "prometheus_k8s.prometheus_scrape", "version": "0"},
                    {"lib": "redis_k8s.redis", "version": "0"},
                    {"lib": "data_platform_libs.s3", "version": "0"},
                    {"lib": "saml_integrator.saml", "version": "0"},
                ],
                "config": {
                    "options": {**GoFramework.options},
                },
                "parts": {
                    "charm": {
                        "plugin": "charm",
                        "source": ".",
                        "build-snaps": ["rustup"],
                        "override-build": "rustup default stable\ncraftctl default",
                    }
                },
                "peers": {"secret-storage": {"interface": "secret-storage"}},
                "provides": {
                    "metrics-endpoint": {"interface": "prometheus_scrape"},
                    "grafana-dashboard": {"interface": "grafana_dashboard"},
                },
                "requires": {
                    "logging": {"interface": "loki_push_api"},
                    "ingress": {"interface": "ingress", "limit": 1},
                },
                "resources": {
                    "app-image": {
                        "description": "go application image.",
                        "type": "oci-image",
                    },
                },
                "summary": "test summary",
                "type": "charm",
            },
        ),
    ],
)
def test_apply_extensions_correct(monkeypatch, experimental, tmp_path, input_yaml, expected):
    if experimental:
        monkeypatch.setenv("CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS", "1")

    applied = apply_extensions(tmp_path, input_yaml)
    assert applied == expected


PROTECTED_FIELDS_TEST_PARAMETERS = [
    pytest.param({"type": "bundle"}, id="type"),
    pytest.param({"containers": {"foobar": {"resource": "foobar"}}}, id="containers"),
    pytest.param({"peers": {"foobar": {"interface": "foobar"}}}, id="peers"),
    pytest.param({"resources": {"foobar": {"type": "oci-image"}}}, id="resources"),
]


@pytest.mark.parametrize("modification", PROTECTED_FIELDS_TEST_PARAMETERS)
def test_flask_protected_fields(modification, flask_input_yaml, tmp_path):
    flask_input_yaml.update(modification)
    with pytest.raises(ExtensionError):
        apply_extensions(tmp_path, flask_input_yaml)


def test_flask_merge_options(flask_input_yaml, tmp_path):
    added_options = {"api_secret": {"type": "string"}}
    flask_input_yaml["config"] = {"options": added_options}
    applied = apply_extensions(tmp_path, flask_input_yaml)
    assert applied["config"] == {
        "options": {
            **FlaskFramework.options,
            **added_options,
        }
    }


def test_flask_merge_action(flask_input_yaml, tmp_path):
    added_actions = {"foobar": {}}
    flask_input_yaml["actions"] = added_actions
    applied = apply_extensions(tmp_path, flask_input_yaml)
    assert applied["actions"] == {**FlaskFramework.actions, **added_actions}


def test_flask_merge_relation(flask_input_yaml, tmp_path):
    new_provides = {"provides-foobar": {"interface": "foobar"}}
    new_requires = {"requires-foobar": {"interface": "foobar"}}
    flask_input_yaml["provides"] = new_provides
    flask_input_yaml["requires"] = new_requires
    applied = apply_extensions(tmp_path, flask_input_yaml)
    assert applied["provides"] == {
        "metrics-endpoint": {"interface": "prometheus_scrape"},
        "grafana-dashboard": {"interface": "grafana_dashboard"},
        **new_provides,
    }
    assert applied["requires"] == {
        "logging": {"interface": "loki_push_api"},
        "ingress": {"interface": "ingress", "limit": 1},
        **new_requires,
    }


def test_flask_merge_charm_libs(flask_input_yaml, tmp_path):
    added_charm_libs = [{"lib": "smtp_integrator.smtp", "version": "0"}]
    flask_input_yaml["charm-libs"] = added_charm_libs
    applied = apply_extensions(tmp_path, flask_input_yaml)
    assert applied["charm-libs"] == [*FlaskFramework._CHARM_LIBS, *added_charm_libs]


INCOMPATIBLE_FIELDS_TEST_PARAMETERS = [
    pytest.param({"devices": {"gpu": {"type": "gpu"}}}, id="devices"),
    pytest.param({"extra-bindings": {"foobar": {}}}, id="extra-bindings"),
    pytest.param({"storage": {"foobar": {"type": "filesystem"}}}, id="storage"),
    pytest.param(
        {"config": {"options": {"webserver-wsgi-path": {"type": "string"}}}},
        id="duplicate-options",
    ),
    pytest.param(
        {"requires": {"ingress": {"interface": "ingress"}}},
        id="duplicate-requires",
    ),
    pytest.param(
        {"provides": {"metrics-endpoint": {"interface": "prometheus_scrape"}}},
        id="duplicate-provides",
    ),
    pytest.param(
        {"config": {"options": {"webserver-foobar": {"type": "string"}}}},
        id="reserved-config-prefix-webserver",
    ),
    pytest.param(
        {"config": {"options": {"flask-foobar": {"type": "string"}}}},
        id="reserved-config-prefix-flask",
    ),
]


@pytest.mark.parametrize("modification", INCOMPATIBLE_FIELDS_TEST_PARAMETERS)
def test_flask_incompatible_fields(modification, flask_input_yaml, tmp_path):
    flask_input_yaml.update(modification)
    with pytest.raises(ExtensionError):
        apply_extensions(tmp_path, flask_input_yaml)


def test_handle_charm_part(flask_input_yaml, tmp_path):
    # Currently, in the flask-framework extension, we will reject any project that
    # includes a charm part. This is to prevent issues where a non-default charm part is
    # incompatible with this extension. This might change in the future.
    # For the same reason, the Flask-Framework extension will also add a default charm part.
    flask_input_yaml["parts"] = {"charm": {}}
    with pytest.raises(ExtensionError):
        apply_extensions(tmp_path, flask_input_yaml)
    del flask_input_yaml["parts"]
    applied = apply_extensions(tmp_path, flask_input_yaml)
    assert applied["parts"]["charm"] == {
        "plugin": "charm",
        "source": ".",
        "build-snaps": ["rustup"],
        "override-build": "rustup default stable\ncraftctl default",
    }
