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
from charmcraft.extensions.gunicorn import DjangoFramework, FlaskFramework


@pytest.fixture(name="flask_input_yaml")
def flask_input_yaml_fixture(monkeypatch, tmp_path):
    monkeypatch.setenv("CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS", "1")
    return {
        "type": "charm",
        "name": "test-flask",
        "summary": "test summary",
        "description": "test description",
        "bases": [{"name": "ubuntu", "channel": "22.04"}],
        "extensions": ["flask-framework"],
    }


def test_flask_extension(flask_input_yaml, tmp_path):
    applied = apply_extensions(tmp_path, flask_input_yaml)
    assert applied == {
        "actions": FlaskFramework.actions,
        "assumes": ["k8s-api"],
        "bases": [{"channel": "22.04", "name": "ubuntu"}],
        "containers": {
            "flask-app": {"resource": "flask-app-image"},
        },
        "description": "test description",
        "name": "test-flask",
        "config": {"options": {**FlaskFramework.options, **FlaskFramework._WEBSERVER_OPTIONS}},
        "parts": {"charm": {"plugin": "charm", "source": "."}},
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
            "flask-app-image": {"description": "flask application image.", "type": "oci-image"},
        },
        "summary": "test summary",
        "type": "charm",
    }


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
            **FlaskFramework._WEBSERVER_OPTIONS,
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


def test_django_extension(monkeypatch, tmp_path):
    monkeypatch.setenv("CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS", "1")
    input_yaml = {
        "type": "charm",
        "name": "test-django",
        "summary": "test summary",
        "description": "test description",
        "bases": [{"name": "ubuntu", "channel": "22.04"}],
        "extensions": ["django-framework"],
    }

    applied = apply_extensions(tmp_path, input_yaml)
    assert applied == {
        "actions": DjangoFramework.actions,
        "assumes": ["k8s-api"],
        "bases": [{"channel": "22.04", "name": "ubuntu"}],
        "containers": {
            "django-app": {"resource": "django-app-image"},
        },
        "description": "test description",
        "name": "test-django",
        "config": {"options": {**DjangoFramework.options, **DjangoFramework._WEBSERVER_OPTIONS}},
        "parts": {"charm": {"plugin": "charm", "source": "."}},
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
            "django-app-image": {"description": "django application image.", "type": "oci-image"},
        },
        "summary": "test summary",
        "type": "charm",
    }
