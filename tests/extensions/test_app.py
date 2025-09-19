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
import copy

import pytest

from charmcraft import extensions
from charmcraft.errors import ExtensionError
from charmcraft.extensions.app import (
    DjangoFramework,
    ExpressJSFramework,
    FastAPIFramework,
    FlaskFramework,
    GoFramework,
    SpringBootFramework,
)

NON_OPTIONAL_OPTIONS = {
    "options": {
        "non-optional-string": {
            "description": "Example of a non-optional string configuration option.",
            "type": "string",
            "optional": False,
        }
    }
}


def make_flask_input_yaml():
    return {
        "type": "charm",
        "name": "test-flask",
        "summary": "test summary",
        "description": "test description",
        "bases": [{"name": "ubuntu", "channel": "22.04"}],
        "extensions": ["flask-framework"],
        "config": copy.deepcopy(NON_OPTIONAL_OPTIONS),
    }


@pytest.fixture(name="flask_input_yaml")
def flask_input_yaml_fixture():
    return make_flask_input_yaml()


def make_spring_boot_input_yaml():
    return {
        "type": "charm",
        "name": "test-springboot",
        "summary": "test summary",
        "description": "test description",
        "base": "ubuntu@24.04",
        "platforms": {"amd64": None},
        "extensions": ["spring-boot-framework"],
        "config": copy.deepcopy(NON_OPTIONAL_OPTIONS),
    }


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
                    {"lib": "loki_k8s.loki_push_api", "version": "1"},
                    {"lib": "data_platform_libs.data_interfaces", "version": "0"},
                    {"lib": "prometheus_k8s.prometheus_scrape", "version": "0"},
                    {"lib": "redis_k8s.redis", "version": "0"},
                    {"lib": "data_platform_libs.s3", "version": "0"},
                    {"lib": "saml_integrator.saml", "version": "0"},
                    {"lib": "tempo_coordinator_k8s.tracing", "version": "0"},
                    {"lib": "smtp_integrator.smtp", "version": "0"},
                    {"lib": "openfga_k8s.openfga", "version": "1"},
                    {"lib": "hydra.oauth", "version": "0"},
                ],
                "config": {
                    "options": {
                        **FlaskFramework.options,
                        **NON_OPTIONAL_OPTIONS["options"],
                    },
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
                "config": NON_OPTIONAL_OPTIONS,
            },
            False,
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
                    {"lib": "loki_k8s.loki_push_api", "version": "1"},
                    {"lib": "data_platform_libs.data_interfaces", "version": "0"},
                    {"lib": "prometheus_k8s.prometheus_scrape", "version": "0"},
                    {"lib": "redis_k8s.redis", "version": "0"},
                    {"lib": "data_platform_libs.s3", "version": "0"},
                    {"lib": "saml_integrator.saml", "version": "0"},
                    {"lib": "tempo_coordinator_k8s.tracing", "version": "0"},
                    {"lib": "smtp_integrator.smtp", "version": "0"},
                    {"lib": "openfga_k8s.openfga", "version": "1"},
                    {"lib": "hydra.oauth", "version": "0"},
                ],
                "config": {
                    "options": {
                        **DjangoFramework.options,
                        **NON_OPTIONAL_OPTIONS["options"],
                    },
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
                "base": "ubuntu@24.04",
                "platforms": {
                    "amd64": None,
                },
                "extensions": ["go-framework"],
                "config": NON_OPTIONAL_OPTIONS,
            },
            True,
            {
                "actions": GoFramework.actions,
                "assumes": ["k8s-api"],
                "base": "ubuntu@24.04",
                "platforms": {
                    "amd64": None,
                },
                "containers": {
                    "app": {"resource": "app-image"},
                },
                "description": "test description",
                "name": "test-go",
                "charm-libs": [
                    {"lib": "traefik_k8s.ingress", "version": "2"},
                    {"lib": "observability_libs.juju_topology", "version": "0"},
                    {"lib": "grafana_k8s.grafana_dashboard", "version": "0"},
                    {"lib": "loki_k8s.loki_push_api", "version": "1"},
                    {"lib": "data_platform_libs.data_interfaces", "version": "0"},
                    {"lib": "prometheus_k8s.prometheus_scrape", "version": "0"},
                    {"lib": "redis_k8s.redis", "version": "0"},
                    {"lib": "data_platform_libs.s3", "version": "0"},
                    {"lib": "saml_integrator.saml", "version": "0"},
                    {"lib": "tempo_coordinator_k8s.tracing", "version": "0"},
                    {"lib": "smtp_integrator.smtp", "version": "0"},
                    {"lib": "openfga_k8s.openfga", "version": "1"},
                    {"lib": "hydra.oauth", "version": "0"},
                ],
                "config": {
                    "options": {
                        **GoFramework.options,
                        **NON_OPTIONAL_OPTIONS["options"],
                    },
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
        (
            {
                "type": "charm",
                "name": "test-fastapi",
                "summary": "test summary",
                "description": "test description",
                "base": "ubuntu@24.04",
                "platforms": {
                    "amd64": None,
                },
                "extensions": ["fastapi-framework"],
                "config": NON_OPTIONAL_OPTIONS,
            },
            True,
            {
                "actions": FastAPIFramework.actions,
                "assumes": ["k8s-api"],
                "base": "ubuntu@24.04",
                "platforms": {
                    "amd64": None,
                },
                "containers": {
                    "app": {"resource": "app-image"},
                },
                "description": "test description",
                "name": "test-fastapi",
                "charm-libs": [
                    {"lib": "traefik_k8s.ingress", "version": "2"},
                    {"lib": "observability_libs.juju_topology", "version": "0"},
                    {"lib": "grafana_k8s.grafana_dashboard", "version": "0"},
                    {"lib": "loki_k8s.loki_push_api", "version": "1"},
                    {"lib": "data_platform_libs.data_interfaces", "version": "0"},
                    {"lib": "prometheus_k8s.prometheus_scrape", "version": "0"},
                    {"lib": "redis_k8s.redis", "version": "0"},
                    {"lib": "data_platform_libs.s3", "version": "0"},
                    {"lib": "saml_integrator.saml", "version": "0"},
                    {"lib": "tempo_coordinator_k8s.tracing", "version": "0"},
                    {"lib": "smtp_integrator.smtp", "version": "0"},
                    {"lib": "openfga_k8s.openfga", "version": "1"},
                    {"lib": "hydra.oauth", "version": "0"},
                ],
                "config": {
                    "options": {
                        **FastAPIFramework.options,
                        **NON_OPTIONAL_OPTIONS["options"],
                    },
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
                        "description": "fastapi application image.",
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
                "name": "test-expressjs",
                "summary": "test summary",
                "description": "test description",
                "base": "ubuntu@24.04",
                "platforms": {
                    "amd64": None,
                },
                "extensions": ["expressjs-framework"],
                "config": NON_OPTIONAL_OPTIONS,
            },
            True,
            {
                "actions": ExpressJSFramework.actions,
                "assumes": ["k8s-api"],
                "base": "ubuntu@24.04",
                "platforms": {
                    "amd64": None,
                },
                "containers": {
                    "app": {"resource": "app-image"},
                },
                "description": "test description",
                "name": "test-expressjs",
                "charm-libs": [
                    {"lib": "traefik_k8s.ingress", "version": "2"},
                    {"lib": "observability_libs.juju_topology", "version": "0"},
                    {"lib": "grafana_k8s.grafana_dashboard", "version": "0"},
                    {"lib": "loki_k8s.loki_push_api", "version": "1"},
                    {"lib": "data_platform_libs.data_interfaces", "version": "0"},
                    {"lib": "prometheus_k8s.prometheus_scrape", "version": "0"},
                    {"lib": "redis_k8s.redis", "version": "0"},
                    {"lib": "data_platform_libs.s3", "version": "0"},
                    {"lib": "saml_integrator.saml", "version": "0"},
                    {"lib": "tempo_coordinator_k8s.tracing", "version": "0"},
                    {"lib": "smtp_integrator.smtp", "version": "0"},
                    {"lib": "openfga_k8s.openfga", "version": "1"},
                    {"lib": "hydra.oauth", "version": "0"},
                ],
                "config": {
                    "options": {
                        **ExpressJSFramework.options,
                        **NON_OPTIONAL_OPTIONS["options"],
                    },
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
                        "description": "expressjs application image.",
                        "type": "oci-image",
                    },
                },
                "summary": "test summary",
                "type": "charm",
            },
        ),
        (
            make_spring_boot_input_yaml(),
            True,
            {
                "actions": SpringBootFramework.actions,
                "assumes": ["k8s-api"],
                "base": "ubuntu@24.04",
                "platforms": {
                    "amd64": None,
                },
                "containers": {
                    "app": {"resource": "app-image"},
                },
                "description": "test description",
                "name": "test-springboot",
                "charm-libs": [
                    {"lib": "traefik_k8s.ingress", "version": "2"},
                    {"lib": "observability_libs.juju_topology", "version": "0"},
                    {"lib": "grafana_k8s.grafana_dashboard", "version": "0"},
                    {"lib": "loki_k8s.loki_push_api", "version": "1"},
                    {"lib": "data_platform_libs.data_interfaces", "version": "0"},
                    {"lib": "prometheus_k8s.prometheus_scrape", "version": "0"},
                    {"lib": "redis_k8s.redis", "version": "0"},
                    {"lib": "data_platform_libs.s3", "version": "0"},
                    {"lib": "saml_integrator.saml", "version": "0"},
                    {"lib": "tempo_coordinator_k8s.tracing", "version": "0"},
                    {"lib": "smtp_integrator.smtp", "version": "0"},
                    {"lib": "openfga_k8s.openfga", "version": "1"},
                    {"lib": "hydra.oauth", "version": "0"},
                ],
                "config": {
                    "options": {
                        **SpringBootFramework.options,
                        **NON_OPTIONAL_OPTIONS["options"],
                    },
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
                        "description": "spring-boot application image.",
                        "type": "oci-image",
                    },
                },
                "summary": "test summary",
                "type": "charm",
            },
        ),
    ],
)
def test_apply_extensions_correct(
    monkeypatch, experimental, tmp_path, input_yaml, expected
):
    if experimental:
        monkeypatch.setenv("CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS", "1")

    applied = extensions.apply_extensions(tmp_path, copy.deepcopy(input_yaml))
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
        extensions.apply_extensions(tmp_path, flask_input_yaml)


def test_flask_merge_options(flask_input_yaml, tmp_path):
    added_options = {"api_secret": {"type": "string"}}
    flask_input_yaml["config"] = {"options": added_options}
    applied = extensions.apply_extensions(tmp_path, flask_input_yaml)
    assert applied["config"] == {
        "options": {
            **FlaskFramework.options,
            **added_options,
        }
    }


def test_flask_merge_action(flask_input_yaml, tmp_path):
    added_actions = {"foobar": {}}
    flask_input_yaml["actions"] = added_actions
    applied = extensions.apply_extensions(tmp_path, flask_input_yaml)
    assert applied["actions"] == {**FlaskFramework.actions, **added_actions}


def test_flask_merge_relation(flask_input_yaml, tmp_path):
    new_provides = {"provides-foobar": {"interface": "foobar"}}
    new_requires = {"requires-foobar": {"interface": "foobar"}}
    flask_input_yaml["provides"] = new_provides
    flask_input_yaml["requires"] = new_requires
    applied = extensions.apply_extensions(tmp_path, flask_input_yaml)
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
    applied = extensions.apply_extensions(tmp_path, flask_input_yaml)
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
    pytest.param(
        {
            "config": {
                "options": {
                    "non-optional": {
                        "type": "string",
                        "optional": False,
                        "default": "default value",
                    }
                }
            }
        },
        id="non-optional-config-with-default",
    ),
]


@pytest.mark.parametrize("modification", INCOMPATIBLE_FIELDS_TEST_PARAMETERS)
def test_flask_incompatible_fields(modification, flask_input_yaml, tmp_path):
    charm = copy.deepcopy(flask_input_yaml)
    charm.update(modification)
    with pytest.raises(ExtensionError):
        extensions.apply_extensions(tmp_path, copy.deepcopy(charm))


def test_handle_charm_part_requires_no_parts(flask_input_yaml, tmp_path):
    # Currently, in the flask-framework extension, we will reject any project that
    # includes a charm part. This is to prevent issues where a non-default charm part is
    # incompatible with extensions.this extension. This might change in the future.
    # For the same reason, the Flask-Framework extension will also add a default charm part.
    flask_input_yaml["parts"] = {"charm": {}}
    with pytest.raises(ExtensionError):
        extensions.apply_extensions(tmp_path, flask_input_yaml)


def test_handle_charm_part_adds_part(flask_input_yaml, tmp_path):
    applied = extensions.apply_extensions(tmp_path, flask_input_yaml)
    assert applied["parts"]["charm"] == {
        "plugin": "charm",
        "source": ".",
        "build-snaps": ["rustup"],
        "override-build": "rustup default stable\ncraftctl default",
    }


@pytest.mark.parametrize(
    ("input_yaml", "requires", "expected_options"),
    [
        pytest.param(
            make_flask_input_yaml(),
            {"oidc-foobar": {"interface": "oauth"}},
            {
                **FlaskFramework.options,
                **NON_OPTIONAL_OPTIONS["options"],
                "oidc-foobar-redirect-path": {
                    "type": "string",
                    "description": "The path that the user will be redirected upon completing login.",
                    "default": "/callback",
                },
                "oidc-foobar-scopes": {
                    "type": "string",
                    "description": "A list of scopes with spaces in between.",
                    "default": "openid profile email",
                },
            },
            id="one-oauth-relation-flask",
        ),
        pytest.param(
            make_spring_boot_input_yaml(),
            {"oidc-foobar": {"interface": "oauth"}},
            {
                **SpringBootFramework.options,
                **NON_OPTIONAL_OPTIONS["options"],
                "oidc-foobar-redirect-path": {
                    "type": "string",
                    "description": "The path that the user will be redirected upon completing login.",
                    "default": "/login/oauth2/code/oidc-foobar",
                },
                "oidc-foobar-scopes": {
                    "type": "string",
                    "description": "A list of scopes with spaces in between.",
                    "default": "openid profile email",
                },
                "oidc-foobar-user-name-attribute": {
                    "default": "sub",
                    "description": "The name of the attribute returned in the UserInfo Response that "
                    "references the Name or Identifier of the end-user.",
                    "type": "string",
                },
            },
            id="one-oauth-relation-spring-boot",
        ),
        pytest.param(
            make_flask_input_yaml(),
            {
                "oidc-foobar": {"interface": "oauth"},
                "other-oidc": {"interface": "oauth"},
            },
            {
                **FlaskFramework.options,
                **NON_OPTIONAL_OPTIONS["options"],
                "oidc-foobar-redirect-path": {
                    "type": "string",
                    "description": "The path that the user will be redirected upon completing login.",
                    "default": "/callback",
                },
                "oidc-foobar-scopes": {
                    "type": "string",
                    "description": "A list of scopes with spaces in between.",
                    "default": "openid profile email",
                },
                "other-oidc-redirect-path": {
                    "type": "string",
                    "description": "The path that the user will be redirected upon completing login.",
                    "default": "/callback",
                },
                "other-oidc-scopes": {
                    "type": "string",
                    "description": "A list of scopes with spaces in between.",
                    "default": "openid profile email",
                },
            },
            id="two-oauth-relations",
        ),
    ],
)
def test_oauth_relation(tmp_path, input_yaml, requires, expected_options):
    input_yaml["requires"] = requires
    applied = extensions.apply_extensions(tmp_path, input_yaml)
    assert applied["config"] == {
        "options": {
            **expected_options,
        }
    }
