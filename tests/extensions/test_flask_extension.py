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
from charmcraft.extensions.flask import ACTIONS, OPTIONS


@pytest.fixture(name="input_yaml")
def input_yaml_fixture(monkeypatch, tmp_path):
    monkeypatch.setenv("CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS", "1")
    return {
        "type": "charm",
        "name": "test-flask",
        "summary": "test summary",
        "description": "test description",
        "bases": [{"name": "ubuntu", "channel": "22.04"}],
        "extensions": ["flask-framework"],
    }


def test_flask_extension(input_yaml, tmp_path):
    applied = apply_extensions(tmp_path, input_yaml)
    assert applied == {
        "actions": ACTIONS,
        "assumes": ["k8s-api"],
        "bases": [{"channel": "22.04", "name": "ubuntu"}],
        "containers": {
            "flask-app": {"resource": "flask-app-image"},
            "statsd-prometheus-exporter": {"resource": "statsd-prometheus-exporter-image"},
        },
        "description": "test description",
        "name": "test-flask",
        "config": {"options": OPTIONS},
        "parts": {},
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
            "flask-app-image": {"description": "Flask application image.", "type": "oci-image"},
            "statsd-prometheus-exporter-image": {
                "description": "Prometheus exporter for statsd data",
                "type": "oci-image",
                "upstream-source": "prom/statsd-exporter:v0.24.0",
            },
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
def test_flask_protected_fields(modification, input_yaml, tmp_path):
    input_yaml.update(modification)
    with pytest.raises(ExtensionError):
        apply_extensions(tmp_path, input_yaml)


def test_flask_merge_options(input_yaml, tmp_path):
    added_options = {"api_secret": {"type": "string"}}
    input_yaml["config"] = {"options": added_options}
    applied = apply_extensions(tmp_path, input_yaml)
    assert applied["config"] == {"options": {**OPTIONS, **added_options}}


def test_flask_merge_action(input_yaml, tmp_path):
    added_actions = {"foobar": {}}
    input_yaml["actions"] = added_actions
    applied = apply_extensions(tmp_path, input_yaml)
    assert applied["actions"] == {**ACTIONS, **added_actions}


def test_flask_merge_relation(input_yaml, tmp_path):
    new_provides = {"provides-foobar": {"interface": "foobar"}}
    new_requires = {"requires-foobar": {"interface": "foobar"}}
    input_yaml["provides"] = new_provides
    input_yaml["requires"] = new_requires
    applied = apply_extensions(tmp_path, input_yaml)
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
        {"config": {"options": {"webserver_wsgi_path": {"type": "string"}}}},
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
]


@pytest.mark.parametrize("modification", INCOMPATIBLE_FIELDS_TEST_PARAMETERS)
def test_flask_incompatible_fields(modification, input_yaml, tmp_path):
    input_yaml.update(modification)
    with pytest.raises(ExtensionError):
        apply_extensions(tmp_path, input_yaml)
