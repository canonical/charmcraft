# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Charmcraft's declarative plugin for craft-parts."""

import io
import pathlib
import zipfile

import jinja2
import json
import jsonschema
import requests
import yaml
from craft_cli import emit, CraftError


# TODO: probably this copyright should be removed/adapted
METADATA_TEMPLATE = """# Copyright 2021 Ubuntu
# See LICENSE file for licensing details.
name: {{name}}
description: |
  {{description}}
summary: |
  {{summary}}
containers:
  application:
    resource: application-image

requires:
{%- for relation in requires %}
  {{ relation.name }}:
    interface: {{ relation.interface }}
{%- endfor %}

resources:
  application-image:
    type: oci-image
    description: |
      OCI image containing the application to run.
      Must have been built with Cloud Native Buildpacks (https://buildpacks.io)

"""


def prepare_charm(project_dir):
    """Build a declarative charm.

    Tthe build process is as follows:

    - Get the remote base declarative charm with proper schema.

    - Load the manifest and validate it with the retrieved schema.

    - Generate the config files from manifest content.

    - Pack the charm as a regular one.
    """
    emit.trace(f"Declarative building started from dir {project_dir}.")

    manifest_filepath = project_dir / "manifest.yaml"
    if not manifest_filepath.exists():
        raise CraftError("Cannot find mandatory 'manifest.yaml' file.")
    manifest_content = yaml.safe_load(manifest_filepath.read_text())
    emit.trace("Manifest loaded ok.")

    # TODO: we need to define a proper versioned location for this
    emit.trace("Getting cnb-operator.")
    url = "https://github.com/facundobatista/cnb-operator/archive/refs/heads/charmcraft-poc.zip"
    resp = requests.get(url)
    project_zipfile = zipfile.ZipFile(io.BytesIO(resp.content))
    project_zipfile.extractall(project_dir)

    # project inside the zip is under a project name directory, we want everything directly
    intermediated_dir = project_dir / project_zipfile.filelist[0].filename
    for path in intermediated_dir.iterdir():
        path.rename(pathlib.Path(*path.parts[:-2], path.name))
    intermediated_dir.rmdir()
    emit.trace(f"Content extracted ok to {project_dir}.")
    breakpoint()

    schema_filepath = project_dir / "schema.json"
    schema_content = json.loads(schema_filepath.read_text())
    try:
        jsonschema.validate(manifest_content, schema_content)
    except Exception as exc:
        raise CraftError(f"Manifest failed the schema validation: {exc}") from exc
    schema_filepath.unlink()
    emit.trace("Manifest validated ok.")

    application_name = manifest_content["name"]
    required_relations = []
    for consumed_relation_name in manifest_content.get("requires", []):
        required_relations.append({
            "name": consumed_relation_name,
            "interface": manifest_content["requires"][consumed_relation_name]["interface"]
        })
    summary = manifest_content.get("summary", "")
    description = manifest_content.get("description", "")
    data_for_metadata = {
        "name": application_name,
        "summary": summary,
        "description": description,
        "requires": required_relations
    }
    template_env = jinja2.Environment()
    metadata_content = template_env.from_string(METADATA_TEMPLATE, data_for_metadata).render()
    (project_dir / "metadata.yaml").write_text(metadata_content)
    emit.trace("Metadata generated ok.")

    config = {
        "environment": manifest_content.get("environment", {}),
        "files": manifest_content.get("files", {}),
    }
    (project_dir / "src" / "config.json").write_text(json.dumps(config))
    emit.trace("Config generated ok.")

    # remove "original" files
    manifest_filepath.unlink()
    (project_dir / "charmcraft.yaml").unlink()
