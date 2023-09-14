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

"""The flask extension."""

from typing import Any, Dict, List, Optional, Tuple

from overrides import override

from ..errors import ExtensionError
from .extension import Extension

ACTIONS = {
    "rotate-secret-key": {
        "description": "Rotate the flask secret key. Users will be forced to log in again. This might be useful if a security breach occurs.\n"
    }
}
OPTIONS = {
    "database_migration_script": {
        "type": "string",
        "description": "Specifies the relative path from /srv/flask/app that points to a shell script executing database migrations for the Flask application. This script is designed to run once for each Flask container unit. However, users must ensure: 1. The script can be executed multiple times without issues; 2. Concurrent migrations from different units are safe. In case of migration failure, the charm will re-attempt during the  update-status event. Successful database migration in a container ensures that any configuration updates won't trigger another migration unless  the Flask container is upgraded or restarted.",
    },
    "flask_application_root": {
        "type": "string",
        "description": "Path in which the application / web server is mounted. This configuration will set the FLASK_APPLICATION_ROOT environment variable. Run `app.config.from_prefixed_env()` in your Flask application in order to receive this configuration.",
    },
    "flask_debug": {
        "type": "boolean",
        "description": "Whether Flask debug mode is enabled.",
    },
    "flask_env": {
        "type": "string",
        "description": "What environment the Flask app is running in, by default it's 'production'.",
    },
    "flask_permanent_session_lifetime": {
        "type": "int",
        "description": "Time in seconds for the cookie to expire in the Flask application permanent sessions. This configuration will set the FLASK_PERMANENT_SESSION_LIFETIME environment variable. Run `app.config.from_prefixed_env()` in your Flask application in order to receive this configuration.",
    },
    "flask_preferred_url_scheme": {
        "type": "string",
        "default": "HTTPS",
        "description": 'Scheme for generating external URLs when not in a request context in the Flask application. By default, it\'s "HTTPS". This configuration will set the FLASK_PREFERRED_URL_SCHEME environment variable. Run `app.config.from_prefixed_env()` in your Flask application in order to receive this configuration.',
    },
    "flask_secret_key": {
        "type": "string",
        "description": "The secret key used for securely signing the session cookie and for any other security related needs by your Flask application. This configuration will set the FLASK_SECRET_KEY environment variable. Run `app.config.from_prefixed_env()` in your Flask application in order to receive this configuration.",
    },
    "flask_session_cookie_secure": {
        "type": "boolean",
        "description": "Set the secure attribute in the Flask application cookies. This configuration will set the FLASK_SESSION_COOKIE_SECURE environment variable. Run `app.config.from_prefixed_env()` in your Flask application in order to receive this configuration.",
    },
    "webserver_keepalive": {
        "type": "int",
        "description": "Time in seconds for webserver to wait for requests on a Keep-Alive connection.",
    },
    "webserver_threads": {
        "type": "int",
        "description": "Run each webserver worker with the specified number of threads.",
    },
    "webserver_timeout": {
        "type": "int",
        "description": "Time in seconds to kill and restart silent webserver workers.",
    },
    "webserver_workers": {
        "type": "int",
        "description": "The number of webserver worker processes for handling requests.",
    },
    "webserver_wsgi_path": {
        "type": "string",
        "default": "app:app",
        "description": 'The WSGI application path. By default, it\'s set to "app:app".',
    },
}


class Flask(Extension):
    @staticmethod
    @override
    def get_supported_bases() -> List[Tuple[str, ...]]:
        """Return supported bases."""
        return [("ubuntu", "22.04")]

    @staticmethod
    @override
    def is_experimental(base: Optional[Tuple[str, ...]]) -> bool:
        """Check if the extension is in an experimental state."""
        return True

    @override
    def get_root_snippet(self) -> Dict[str, Any]:
        """Fill in some required root components for Flask."""
        protected_fields = {
            "type": "charm",
            "assumes": ["k8s-api"],
            "containers": {
                "flask-app": {"resource": "flask-app-image"},
                "statsd-prometheus-exporter": {"resource": "statsd-prometheus-exporter-image"},
            },
            "resources": {
                "flask-app-image": {
                    "type": "oci-image",
                    "description": "Flask application image.",
                },
                "statsd-prometheus-exporter-image": {
                    "type": "oci-image",
                    "description": "Prometheus exporter for statsd data",
                    "upstream-source": "prom/statsd-exporter:v0.24.0",
                },
            },
            "peers": {"secret-storage": {"interface": "secret-storage"}},
        }
        merging_fields = {
            "actions": ACTIONS,
            "options": OPTIONS,
        }
        incompatible_fields = ("devices", "extra-bindings", "storage")
        for incompatible_field in incompatible_fields:
            if incompatible_field in self.yaml_data:
                raise ExtensionError(
                    f"the flask extension is incompatible with the field {incompatible_field!r}"
                )
        snippet = protected_fields
        for protected, protected_value in protected_fields.items():
            if protected in self.yaml_data and self.yaml_data[protected] != protected_value:
                raise ExtensionError(
                    f"{protected!r} in charmcraft.yaml conflicts with a reserved field "
                    f"in the flask extension, please remove it."
                )
        for merging_field, merging_field_value in merging_fields.items():
            if merging_field not in self.yaml_data:
                snippet[merging_field] = merging_field_value
                continue
            user_provided = self.yaml_data[merging_field]
            overlap = user_provided.keys() & merging_field_value.keys()
            if overlap:
                raise ExtensionError(
                    f"overlapping keys {overlap} in {merging_field} of charmcraft.yaml "
                    f"which conflict with the flask extension, please rename or remove it"
                )
            snippet[merging_field] = {**merging_field_value, **user_provided}
        return snippet

    @override
    def get_part_snippet(self) -> Dict[str, Any]:
        """Return the part snippet to apply to existing parts."""
        return {}

    @override
    def get_parts_snippet(self) -> Dict[str, Any]:
        """Return the parts to add to parts."""
        return {}
