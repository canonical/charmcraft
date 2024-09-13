# Copyright 2023-2024 Canonical Ltd.
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

"""Gunicorn based extensions."""

from typing import Any

from overrides import override

from ..errors import ExtensionError
from .extension import Extension


class _AppBase(Extension):
    """A base class for 12-factor applications."""

    _CHARM_LIBS = [
        {"lib": "traefik_k8s.ingress", "version": "2"},
        {"lib": "observability_libs.juju_topology", "version": "0"},
        {"lib": "grafana_k8s.grafana_dashboard", "version": "0"},
        {"lib": "loki_k8s.loki_push_api", "version": "0"},
        {"lib": "data_platform_libs.data_interfaces", "version": "0"},
        {"lib": "prometheus_k8s.prometheus_scrape", "version": "0"},
        {"lib": "redis_k8s.redis", "version": "0"},
        {"lib": "data_platform_libs.s3", "version": "0"},
        {"lib": "saml_integrator.saml", "version": "0"},
    ]

    @staticmethod
    @override
    def get_supported_bases() -> list[tuple[str, str]]:
        """Return supported bases."""
        return [("ubuntu", "22.04")]

    @staticmethod
    @override
    def is_experimental(base: tuple[str, ...] | None) -> bool:  # noqa: ARG004
        """Check if the extension is in an experimental state."""
        return True

    framework: str
    actions: dict = {
        "rotate-secret-key": {
            "description": "Rotate the secret key. Users will be forced to log in again. This might be useful if a security breach occurs."
        }
    }

    options: dict

    def _get_nested(self, obj: dict, path: str) -> dict:
        """Get a nested object using a path (a dot-separated list of keys)."""
        for key in path.split("."):
            obj = obj.get(key, {})
        return obj

    def _check_input(self) -> None:
        """Check if the extension is applicable for user input charmcraft project file."""
        charm_type = self.yaml_data.get("type")
        if charm_type != "charm":
            raise ExtensionError(
                f"the '{self.framework}-framework' extension is incompatible with "
                f"type {charm_type!r}"
            )
        parts = self.yaml_data.get("parts")
        if parts and "charm" in parts:
            raise ExtensionError(
                f"the '{self.framework}-framework' extension is incompatible with "
                f"customized charm part"
            )
        incompatible_fields = {"devices", "extra-bindings", "storage"} & self.yaml_data.keys()
        if incompatible_fields:
            raise ExtensionError(
                f"the '{self.framework}-framework' extension is incompatible with the provided "
                f"field(s): {', '.join(sorted(incompatible_fields))}"
            )
        root_snippet = self._get_root_snippet()
        for protected in ("assumes", "containers", "resources", "peers"):
            if (
                protected in self.yaml_data
                and self.yaml_data[protected] != root_snippet[protected]
            ):
                raise ExtensionError(
                    f"{protected!r} in charmcraft.yaml conflicts with a reserved field "
                    f"in the {self.framework}-framework extension, please remove it."
                )
        for merging in ("actions", "requires", "provides", "config.options"):
            user_provided: dict[str, Any] = self._get_nested(self.yaml_data, merging)
            if not user_provided:
                continue
            overlap = user_provided.keys() & self._get_nested(root_snippet, merging).keys()
            if overlap:
                raise ExtensionError(
                    f"overlapping keys {overlap} in {merging} of charmcraft.yaml "
                    f"which conflict with the {self.framework}-framework extension, "
                    "please rename or remove it"
                )
        for config in self._get_nested(self.yaml_data, "config.options"):
            for reserved_config_prefix in ("webserver-", f"{self.framework}-"):
                if config.startswith(reserved_config_prefix):
                    raise ExtensionError(
                        f"config.options {config!r} starts with {self.framework}-framework"
                        f" reserved configuration prefix {reserved_config_prefix!r}, "
                        "please rename or remove it"
                    )

    def _get_root_snippet(self) -> dict[str, Any]:
        """Return the root snippet to be merged into the user charmcraft.yaml.

        This method differs from get_root_snippet because it doesn't perform any check.
        """
        return {
            "assumes": ["k8s-api"],
            "containers": {
                self.get_container_name(): {"resource": self.get_image_name()},
            },
            "resources": {
                self.get_image_name(): {
                    "type": "oci-image",
                    "description": f"{self.framework} application image.",
                },
            },
            "charm-libs": self._CHARM_LIBS,
            "peers": {"secret-storage": {"interface": "secret-storage"}},
            "actions": self.actions,
            "requires": {
                "logging": {"interface": "loki_push_api"},
                "ingress": {"interface": "ingress", "limit": 1},
            },
            "provides": {
                "metrics-endpoint": {"interface": "prometheus_scrape"},
                "grafana-dashboard": {"interface": "grafana_dashboard"},
            },
            "config": {"options": self.options},
            "parts": {
                "charm": {
                    "plugin": "charm",
                    "source": ".",
                    "build-snaps": ["rustup"],  # Needed to build pydantic.
                    "override-build": "rustup default stable\ncraftctl default",
                }
            },
        }

    @override
    def get_root_snippet(self) -> dict[str, Any]:
        """Fill in some required root components."""
        self._check_input()
        return self._get_root_snippet()

    @override
    def get_part_snippet(self) -> dict[str, Any]:
        """Return the part snippet to apply to existing parts."""
        return {}

    @override
    def get_parts_snippet(self) -> dict[str, Any]:
        """Return the parts to add to parts."""
        return {}

    def get_container_name(self) -> str:
        """Return name of the container for the app image."""
        return f"{self.framework}-app"

    def get_image_name(self) -> str:
        """Return name of the app image."""
        return f"{self.framework}-app-image"


GUNICORN_WEBSERVER_OPTIONS = {
    "webserver-keepalive": {
        "type": "int",
        "description": "Time in seconds for webserver to wait for requests on a Keep-Alive connection.",
    },
    "webserver-threads": {
        "type": "int",
        "description": "Run each webserver worker with the specified number of threads.",
    },
    "webserver-timeout": {
        "type": "int",
        "description": "Time in seconds to kill and restart silent webserver workers.",
    },
    "webserver-workers": {
        "type": "int",
        "description": "The number of webserver worker processes for handling requests.",
    },
}


class FlaskFramework(_AppBase):
    """Extension for 12-factor Flask applications."""

    framework = "flask"
    options = {
        **GUNICORN_WEBSERVER_OPTIONS,
        "flask-application-root": {
            "type": "string",
            "description": "Path in which the application / web server is mounted. This configuration will set the FLASK_APPLICATION_ROOT environment variable. Run `app.config.from_prefixed_env()` in your Flask application in order to receive this configuration.",
        },
        "flask-debug": {
            "type": "boolean",
            "description": "Whether Flask debug mode is enabled.",
        },
        "flask-env": {
            "type": "string",
            "description": "What environment the Flask app is running in, by default it's 'production'.",
        },
        "flask-permanent-session-lifetime": {
            "type": "int",
            "description": "Time in seconds for the cookie to expire in the Flask application permanent sessions. This configuration will set the FLASK_PERMANENT_SESSION_LIFETIME environment variable. Run `app.config.from_prefixed_env()` in your Flask application in order to receive this configuration.",
        },
        "flask-preferred-url-scheme": {
            "type": "string",
            "default": "HTTPS",
            "description": 'Scheme for generating external URLs when not in a request context in the Flask application. By default, it\'s "HTTPS". This configuration will set the FLASK_PREFERRED_URL_SCHEME environment variable. Run `app.config.from_prefixed_env()` in your Flask application in order to receive this configuration.',
        },
        "flask-secret-key": {
            "type": "string",
            "description": "The secret key used for securely signing the session cookie and for any other security related needs by your Flask application. This configuration will set the FLASK_SECRET_KEY environment variable. Run `app.config.from_prefixed_env()` in your Flask application in order to receive this configuration.",
        },
        "flask-session-cookie-secure": {
            "type": "boolean",
            "description": "Set the secure attribute in the Flask application cookies. This configuration will set the FLASK_SESSION_COOKIE_SECURE environment variable. Run `app.config.from_prefixed_env()` in your Flask application in order to receive this configuration.",
        },
    }

    @staticmethod
    @override
    def is_experimental(base: tuple[str, ...] | None) -> bool:  # noqa: ARG004
        """Check if the extension is in an experimental state."""
        return False


class DjangoFramework(_AppBase):
    """Extension for 12-factor Django applications."""

    framework = "django"
    actions = {
        **_AppBase.actions,
        "create-superuser": {
            "description": "Create a new Django superuser account.",
            "params": {"username": {"type": "string"}, "email": {"type": "string"}},
            "required": ["username", "email"],
        },
    }
    options = {
        **GUNICORN_WEBSERVER_OPTIONS,
        "django-debug": {
            "type": "boolean",
            "default": False,
            "description": "Whether Django debug mode is enabled.",
        },
        "django-secret-key": {
            "type": "string",
            "description": "The secret key used for securely signing the session cookie and for any other security related needs by your Django application. This configuration will set the DJANGO_SECRET_KEY environment variable.",
        },
        "django-allowed-hosts": {
            "type": "string",
            "description": "A comma-separated list of host/domain names that this Django site can serve. This configuration will set the DJANGO_ALLOWED_HOSTS environment variable with its content being a JSON encoded list.",
        },
    }


class GoFramework(_AppBase):
    """Extension for 12-factor Go applications."""

    framework = "go"
    options = {
        "app-port": {
            "type": "int",
            "default": 8080,
            "description": "Default port where the application will listen on.",
        },
        "metrics-port": {
            "type": "int",
            "default": 8080,
            "description": "Port where the prometheus metrics will be scraped.",
        },
        "metrics-path": {
            "type": "string",
            "default": "/metrics",
            "description": "Path where the prometheus metrics will be scraped.",
        },
        "app-secret-key": {
            "type": "string",
            "description": "Long secret you can use for sessions, csrf or any other thing where you need a random secret shared by all units",
        },
    }

    @staticmethod
    @override
    def get_supported_bases() -> list[tuple[str, str]]:
        """Return supported bases."""
        return [("ubuntu", "24.04")]

    @override
    def get_image_name(self) -> str:
        """Return name of the app image."""
        return "app-image"

    @override
    def get_container_name(self) -> str:
        """Return name of the container for the app image."""
        return "app"
