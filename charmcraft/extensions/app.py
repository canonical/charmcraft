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

import copy
from typing import Any

from overrides import override

from ..errors import ExtensionError
from .extension import Extension

APP_PORT_OPTION = {
    "app-port": {
        "type": "int",
        "default": 8080,
        "description": "Default port where the application will listen on.",
    }
}
METRICS_OPTIONS = {
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
}
SECRET_OPTIONS = {
    "app-secret-key": {
        "type": "string",
        "description": "Long secret you can use for sessions, csrf or any other thing where you need a random secret shared by all units",
    },
    "app-secret-key-id": {
        "type": "secret",
        "description": "This configuration is similar to `app-secret-key`, but instead accepts a Juju user secret ID. "
        'The secret should contain a single key, "value", which maps to the actual application secret key. '
        "To create the secret, run the following command: `juju add-secret my-app-secret-key value=<secret-string> && juju grant-secret my-app-secret-key my-app`, "
        "and use the output secret ID to configure this option.",
    },
}
OAUTH_DYNAMIC_OPTIONS = {
    "{endpoint_name}-redirect-path": {
        "type": "string",
        "description": "The path that the user will be redirected upon completing login.",
        "default": "/callback",
    },
    "{endpoint_name}-scopes": {
        "type": "string",
        "description": "A list of scopes with spaces in between.",
        "default": "openid profile email",
    },
}


class _AppBase(Extension):
    """A base class for 12-factor applications."""

    _CHARM_LIBS = [
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

    endpoint_dynamic_options: dict[str, dict[str, Any]] = {
        "oauth": OAUTH_DYNAMIC_OPTIONS
    }

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
        incompatible_fields = {
            "devices",
            "extra-bindings",
            "storage",
        } & self.yaml_data.keys()
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
            overlap = (
                user_provided.keys() & self._get_nested(root_snippet, merging).keys()
            )
            if overlap:
                raise ExtensionError(
                    f"overlapping keys {overlap} in {merging} of charmcraft.yaml "
                    f"which conflict with the {self.framework}-framework extension, "
                    "please rename or remove it"
                )
        invalid_non_optionals = []
        for config in self._get_nested(self.yaml_data, "config.options"):
            for reserved_config_prefix in ("webserver-", f"{self.framework}-"):
                if config.startswith(reserved_config_prefix):
                    raise ExtensionError(
                        f"config.options {config!r} starts with {self.framework}-framework"
                        f" reserved configuration prefix {reserved_config_prefix!r}, "
                        "please rename or remove it"
                    )
            config_option_dict = self._get_nested(
                self.yaml_data, f"config.options.{config}"
            )
            if config_option_dict.get("optional") is False and config_option_dict.get(
                "default"
            ):
                invalid_non_optionals.append(config)

        if invalid_non_optionals:
            raise ExtensionError(
                "Non-optional configuration options can not have default values.\n"
                f"Please either remove the default value or set optional field to true or remove it for the {', '.join(invalid_non_optionals)} configuration option(s)."
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
            "config": {"options": copy.deepcopy(self.options)},
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
        root_snippet = self._get_root_snippet()
        for interface_name, config_options in self.endpoint_dynamic_options.items():
            dynamic_config_options = self._get_dynamic_config_options(
                root_snippet, interface_name, config_options
            )
            root_snippet["config"]["options"].update(dynamic_config_options)
        return root_snippet

    def _get_dynamic_config_options(
        self,
        root_snippet: dict[str, Any],
        interface_name: str,
        config_options: dict[str, Any],
    ) -> dict[str, Any]:
        dynamic_endpoint_names = []
        requires = self._get_nested(self.yaml_data, "requires")
        for endpoint_name, require in requires.items():
            current_interface_name = require.get("interface")
            if current_interface_name == interface_name:
                dynamic_endpoint_names.append(endpoint_name)

        dynamic_config_options = {}
        for endpoint_name in dynamic_endpoint_names:
            updated_config_options = self._get_updated_dynamic_config_options(
                endpoint_name, config_options
            )
            dynamic_config_options.update(updated_config_options)
        return dynamic_config_options

    def _get_updated_dynamic_config_options(
        self, endpoint_name: str, config_options: dict[str, dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        updated_config_options = {}
        for option, value in config_options.items():
            updated_option = option.format(endpoint_name=endpoint_name)
            updated_value = copy.deepcopy(value)
            for value_key, value_item in value.items():
                if isinstance(value_item, str):
                    updated_value[value_key] = value_item.format(
                        endpoint_name=endpoint_name
                    )
            updated_config_options[updated_option] = updated_value
        return updated_config_options

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
    "webserver-worker-class": {
        "type": "string",
        "description": "The webserver worker process class for handling requests. Can be either 'gevent' or 'sync'.",
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
        "flask-secret-key-id": {
            "type": "secret",
            "description": "This configuration is similar to `flask-secret-key`, but instead accepts a Juju user secret ID. "
            'The secret should contain a single key, "value", which maps to the actual Flask secret key. '
            "To create the secret, run the following command: `juju add-secret my-flask-secret-key value=<secret-string> && juju grant-secret my-flask-secret-key flask-k8s`, "
            "and use the output secret ID to configure this option.",
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
        "django-secret-key-id": {
            "type": "secret",
            "description": "This configuration is similar to `django-secret-key`, but instead accepts a Juju user secret ID. "
            'The secret should contain a single key, "value", which maps to the actual Django secret key. '
            "To create the secret, run the following command: `juju add-secret my-django-secret-key value=<secret-string> && juju grant-secret my-django-secret-key django-k8s`, "
            "and use the output secret ID to configure this option.",
        },
        "django-allowed-hosts": {
            "type": "string",
            "description": "A comma-separated list of host/domain names that this Django site can serve. This configuration will set the DJANGO_ALLOWED_HOSTS environment variable with its content being a JSON encoded list.",
        },
    }

    @staticmethod
    @override
    def is_experimental(base: tuple[str, ...] | None) -> bool:  # noqa: ARG004
        """Check if the extension is in an experimental state."""
        return False


class GoFramework(_AppBase):
    """Extension for 12-factor Go applications."""

    framework = "go"
    options = {
        **APP_PORT_OPTION,
        **METRICS_OPTIONS,
        **SECRET_OPTIONS,
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


class FastAPIFramework(_AppBase):
    """Extension for 12-factor FastAPI applications."""

    framework = "fastapi"
    options = {
        "webserver-workers": {
            "type": "int",
            "default": 1,
            "description": "Number of workers for uvicorn. Sets env variable WEB_CONCURRENCY. See https://www.uvicorn.org/#command-line-options.",
        },
        "webserver-port": {
            "type": "int",
            "default": 8080,
            "description": "Bind to a socket with this port. Default: 8000. Sets env variable  UVICORN_PORT.",
        },
        "webserver-log-level": {
            "type": "string",
            "default": "info",
            "description": "Set the log level. Options: 'critical', 'error', 'warning', 'info', 'debug', 'trace'. Sets the env variable UVICORN_LOG_LEVEL.",
        },
        **METRICS_OPTIONS,
        **SECRET_OPTIONS,
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


class ExpressJSFramework(_AppBase):
    """Extension for 12-factor ExpressJS applications."""

    framework = "expressjs"
    options = {
        **APP_PORT_OPTION,
        **METRICS_OPTIONS,
        **SECRET_OPTIONS,
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


class SpringBootFramework(_AppBase):
    """Extension for 12-factor Spring Boot applications."""

    framework = "spring-boot"
    options = {
        **APP_PORT_OPTION,
        "metrics-port": {
            "type": "int",
            "default": 8080,
            "description": "Port where the prometheus metrics will be scraped.",
        },
        "metrics-path": {
            "type": "string",
            "default": "/actuator/prometheus",
            "description": "Path where the prometheus metrics will be scraped.",
        },
        **SECRET_OPTIONS,
    }
    endpoint_dynamic_options: dict[str, dict[str, Any]] = {
        "oauth": {
            **OAUTH_DYNAMIC_OPTIONS,
            "{endpoint_name}-redirect-path": {
                "default": "/login/oauth2/code/{endpoint_name}",
                "description": "The path that the user will be redirected upon completing login.",
                "type": "string",
            },
            "{endpoint_name}-user-name-attribute": {
                "type": "string",
                "description": "The name of the attribute returned in the UserInfo Response "
                "that references the Name or Identifier of the end-user.",
                "default": "sub",
            },
        }
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
