(write-your-first-kubernetes-charm-for-a-fastapi-app)=
# Write your first Kubernetes charm for a FastAPI app

**What you'll need:**

- A workstation, e.g., a laptop, with amd64 architecture which has sufficient resources to launch a virtual machine with 4 CPUs, 4 GB RAM, and a 50 GB disk
    - Note that a workstation with arm64 architecture can complete the majority of this tutorial.
- Familiarity with Linux
- About 90 minutes of free time.

**What you'll do:**

Create a FastAPI application. Use that to create a rock with `rockcraft`. Use that to create a charm with `charmcraft`. Use that to test-deploy, configure, etc., your Django application on a local Kubernetes cloud, `microk8s`, with `juju`. All of that multiple times, mimicking a real development process. 

```{note} 

**rock** 

An Ubuntu LTS-based OCI compatible container image designed to meet security, stability, and reliability requirements for cloud-native software.

**charm** 

A package consisting of YAML files + Python code that will automate every aspect of an application's lifecycle so it can be easily orchestrated with Juju.

**`juju`** 

An orchestration engine for charmed applications.

```


```{important}

**Should you get stuck or notice issues:** Please get in touch on [Matrix](https://matrix.to/#/#12-factor-charms:ubuntu.com) or [Discourse](https://discourse.charmhub.io/).

```


## Set things up

Install Multipass.

> See more: [Multipass | How to install Multipass](https://multipass.run/docs/install-multipass)

Use Multipass to launch an Ubuntu VM with the name `charm-dev` from the 24.04 blueprint:

```bash
multipass launch --cpus 4 --disk 50G --memory 4G --name charm-dev 24.04
```

Once the VM is up, open a shell into it:

```bash
multipass shell charm-dev
```

In order to create the rock, you'll need to install Rockcraft:

```bash
sudo snap install rockcraft --channel latest/edge --classic
```

`LXD` will be required for building the rock. Make sure it is installed and initialised:

```bash
sudo snap install lxd
lxd init --auto
```

In order to create the charm, you'll need to install Charmcraft:

```bash
sudo snap install charmcraft --channel latest/edge --classic
```

MicroK8s is required to deploy the FastAPI application on Kubernetes. Install MicroK8s:

```bash
sudo snap install microk8s --channel 1.31-strict/stable
sudo adduser $USER snap_microk8s
newgrp snap_microk8s
```

Wait for MicroK8s to be ready using `sudo microk8s status --wait-ready`. Several MicroK8s add-ons are required for deployment:

```bash
sudo microk8s enable hostpath-storage
# Required to host the OCI image of the FastAPI application
sudo microk8s enable registry
# Required to expose the FastAPI application
sudo microk8s enable ingress
```

> See more: [ingress](https://microk8s.io/docs/ingress)

Juju is required to deploy the FastAPI application. Install Juju and bootstrap a development controller:

```bash
sudo snap install juju --channel 3.5/stable
mkdir -p ~/.local/share
juju bootstrap microk8s dev-controller
```

Finally, create a new directory for this tutorial and go inside it:

```bash
mkdir fastapi-hello-world
cd fastapi-hello-world
```

```{note}

This tutorial requires version `3.0.0` or later of Charmcraft. Check the version of Charmcraft using `charmcraft --version` If you have an older version of Charmcraft installed, use `sudo snap refresh charmcraft --channel latest/edge` to get the latest edge version of Charmcraft.

This tutorial requires version `1.5.4` or later of Rockcraft. Check the version of Rockcraft using `rockcraft --version` If you have an older version of Rockcraft installed, use `sudo snap refresh rockcraft --channel latest/edge` to get the latest edge version of Rockcraft.

```

## Create the FastAPI application

Start by creating the "Hello, world" FastAPI application that will be used for this tutorial.

Create a `requirements.txt` file, copy the following text into it and then save it:

```
fastapi[standard]
```

In the same directory, copy and save the following into a text file called `app.py`:

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}
```

## Run the FastAPI application locally

Install `python3-venv` and create a virtual environment:

```bash
sudo apt-get update && sudo apt-get install python3-venv -y
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Now that we have a virtual environment with all the dependencies, let's run the FastAPI application to verify that it works:

```bash
fastapi dev app.py --port 8080
```

Test the FastAPI application by using `curl` to send a request to the root endpoint. You may need a new terminal for this; if you are using Multipass use `multipass shell charm-dev` to get another terminal:

```bash
curl localhost:8080
```

The FastAPI application should respond with `{"message":"Hello World"}`. The FastAPI application looks good, so we can stop for now using <kbd>ctrl</kbd> + <kbd>c</kbd>.

## Pack the FastAPI application into a rock

First, we'll need a `rockcraft.yaml` file. Rockcraft will automate its creation and tailoring for a FastAPI application by using the `fastapi-framework` profile:

```bash
rockcraft init --profile fastapi-framework
```

The `rockcraft.yaml` file will automatically be created and set the name based on your working directory. Open the file in a text editor and check that the `name` is `fastapi-hello-world`. Ensure that `platforms` includes the architecture of your host. For example, if your host uses the ARM architecture, include `arm64` in `platforms`.

```{note}

For this tutorial, we'll use the `name` "fastapi-hello-world" and assume you are on the `amd64` platform. Check the architecture of your system using `dpkg --print-architecture`. Choosing a different name or running on a different platform will influence the names of the files generated by Rockcraft.

```

Pack the rock:

```bash
ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true rockcraft pack
```

```{note}

Depending on your system and network, this step can take a couple of minutes to finish.

``ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS`` is required whilst the FastAPI extension is experimental.

```

Once Rockcraft has finished packing the FastAPI rock, you'll find a new file in your working directory with the `.rock` extension:

```bash
ls *.rock -l
```

```{note}

If you changed the `name` or `version` in `rockcraft.yaml` or are not on an `amd64` platform, the name of the `.rock` file will be different for you.

```

The rock needs to be copied to the MicroK8s registry so that it can be deployed in the Kubernetes cluster:

```bash
rockcraft.skopeo --insecure-policy copy --dest-tls-verify=false \
   oci-archive:fastapi-hello-world_0.1_amd64.rock \
   docker://localhost:32000/fastapi-hello-world:0.1
```

> See more: [skopeo](https://manpages.ubuntu.com/manpages/jammy/man1/skopeo.1.html)

## Create the charm

Create a new directory for the charm and go inside it:

```bash
mkdir charm
cd charm
```

We'll need a `charmcraft.yaml`, `requirements.txt` and source code for the charm. The source code contains the logic required to operate the FastAPI application. Charmcraft will automate the creation of these files by using the `fastapi-framework` profile:

```bash
charmcraft init --profile fastapi-framework --name fastapi-hello-world
```

The files will automatically be created in your working directory. 

The charm depends on several libraries. Download the libraries and pack the charm:

```bash
CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true charmcraft fetch-libs
CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true charmcraft pack
```

```{note}

Depending on your system and network, this step can take a couple of minutes to finish.

``CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS`` is required whilst the FastAPI extension is experimental.

```

Once Charmcraft has finished packing the charm, you'll find a new file in your working directory with the `.charm` extension:

```bash
ls *.charm -l
```

```{note}

If you changed the name in charmcraft.yaml or are not on the amd64 platform, the name of the `.charm` file will be different for you.

```

## Deploy the FastAPI application

A Juju model is needed to deploy the application. Let's create a new model:

```bash
juju add-model fastapi-hello-world
```

Now the FastAPI application can be deployed using Juju:

```bash
juju deploy ./fastapi-hello-world_amd64.charm fastapi-hello-world \
   --resource app-image=localhost:32000/fastapi-hello-world:0.1
```

```{note}

It will take a few minutes to deploy the FastAPI application. You can monitor the progress using `juju status --watch 5s`. Once the status of the App has gone to `active`, you can stop watching using <kbd>ctrl</kbd> + <kbd>c</kbd>.

> See more: {ref}`juju status <ref_commands_status>`

```

The FastAPI application should now be running. We can monitor the status of the deployment using `juju status` which should be similar to the following output:

```
Model                Controller      Cloud/Region        Version  SLA          Timestamp
fastapi-hello-world  dev-controller  microk8s/localhost  3.5.4    unsupported  13:45:18+10:00

App                  Version  Status  Scale  Charm                Channel  Rev  Address        Exposed  Message
fastapi-hello-world           active      1  fastapi-hello-world             0  10.152.183.53  no       

Unit                    Workload  Agent  Address      Ports  Message
fastapi-hello-world/0*  active    idle   10.1.157.75
```

The deployment is finished when the status shows `active`. Let's expose the application using ingress. Deploy the `nginx-ingress-integrator` charm and integrate it with the FastAPI app:

```bash
juju deploy nginx-ingress-integrator
juju integrate nginx-ingress-integrator fastapi-hello-world
```

The hostname of the app needs to be defined so that it is accessible via the ingress. We will also set the default route to be the root endpoint:

```bash
juju config nginx-ingress-integrator \
   service-hostname=fastapi-hello-world path-routes=/
```

Monitor `juju status` until everything has a status of `active`. Use `curl http://fastapi-hello-world  --resolve fastapi-hello-world:80:127.0.0.1` to send a request via the ingress. It should return the `{"message":"Hello World"}` greeting.

```{note}

The `--resolve fastapi-hello-world:80:127.0.0.1` option to the `curl` command is a way of resolving the hostname of the request without setting a DNS record.

```

## Configure the FastAPI application

Now let's customise the greeting using a configuration option. We will expect this configuration option to be available in the environment variable `APP_GREETING`. Go back out to the root directory of the project using `cd ..` and copy the following code into `app.py`:

```python
import os

from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"message": os.getenv("APP_GREETING", "Hello World")}
```

Open `rockcraft.yaml` and update the version to `0.2`. Run `ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true rockcraft pack` again, then upload the new OCI image to the MicroK8s registry:

```bash
rockcraft.skopeo --insecure-policy copy --dest-tls-verify=false \
   oci-archive:fastapi-hello-world_0.2_amd64.rock \
   docker://localhost:32000/fastapi-hello-world:0.2
```

Change back into the charm directory using `cd charm`. The `fastapi-framework` Charmcraft extension supports adding configurations to `charmcraft.yaml` which will be passed as environment variables to the FastAPI application. Add the following to the end of the `charmcraft.yaml` file:

```yaml
config:
  options:
    greeting:
      description: |
        The greeting to be returned by the FastAPI application.
      default: "Hello, world!"
      type: string
```

```{note}

Configuration options are automatically capitalised and `-` are replaced by `_`. A `APP_` prefix will also be added to ensure that environment variables are namespaced.

```

Run `CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true charmcraft pack` again. The deployment can now be refreshed to make use of the new code:

```bash
juju refresh fastapi-hello-world \
   --path=./fastapi-hello-world_amd64.charm \
   --resource app-image=localhost:32000/fastapi-hello-world:0.2
```

Wait for `juju status` to show that the App is `active` again. Verify that the new configuration has been added using `juju config fastapi-hello-world | grep -A 6 greeting:` which should show the configuration option.

```{note}

The `grep` command extracts a portion of the configuration to make it easier to check whether the configuration option has been added.

```

Running `curl http://fastapi-hello-world  --resolve fastapi-hello-world:80:127.0.0.1` shows that the response is still `{"message":"Hello, world!"}` as expected. The greeting can be changed using Juju:

```bash
juju config fastapi-hello-world greeting='Hi!'
```

`curl http://fastapi-hello-world  --resolve fastapi-hello-world:80:127.0.0.1` now returns the updated `{"message":"Hi!"}` greeting.

```{note}

It might take a short time for the configuration to take effect.

```

## Integrate with a database

Now let's keep track of how many visitors your application has received. This will require integration with a database to keep the visitor count. This will require a few changes:

* We will need to create a database migration that creates the `visitors` table
* We will need to keep track how many times the root endpoint has been called in the database
* We will need to add a new endpoint to retrieve the number of visitors from the database

The charm created by the `fastapi-framework` extension will execute the `migrate.py` script if it exists. This script should ensure that the database is initialised and ready to be used by the application. We will create a `migrate.py` file containing this logic.

Go back out to the tutorial root directory using `cd ..`. Create the `migrate.py` file using a text editor and paste the following code into it:

```python
import os

import psycopg2

DATABASE_URI = os.environ["POSTGRESQL_DB_CONNECT_STRING"]

def migrate():
    with psycopg2.connect(DATABASE_URI) as conn, conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS visitors (
                timestamp TIMESTAMP NOT NULL,
                user_agent TEXT NOT NULL
            );
        """)
        conn.commit()


if __name__ == "__main__":
    migrate()
```

```{note}

The charm will pass the Database connection string in the `POSTGRESQL_DB_CONNECT_STRING` environment variable once postgres has been integrated with the charm.

```

Open the `rockcraft.yaml` file in a text editor and update the version to `0.3`.

To be able to connect to postgresql from the FastAPI app the `psycopg2-binary` dependency needs to be added in `requirements.txt`. The app code also needs to be updated to keep track of the number of visitors and to include a new endpoint to retrieve the number of visitors to the app. Open `app.py` in a text editor and replace its contents with the following code:

```python
import datetime
import os
from typing import Annotated

from fastapi import FastAPI, Header
import psycopg2

app = FastAPI()
DATABASE_URI = os.environ["POSTGRESQL_DB_CONNECT_STRING"]


@app.get("/")
async def root(user_agent: Annotated[str | None, Header()] = None):
    with psycopg2.connect(DATABASE_URI) as conn, conn.cursor() as cur:
        timestamp = datetime.datetime.now()

        cur.execute(
            "INSERT INTO visitors (timestamp, user_agent) VALUES (%s, %s)",
            (timestamp, user_agent)
        )
        conn.commit()

    return {"message": os.getenv("APP_GREETING", "Hello World")}


@app.get("/visitors")
async def visitors():
    with psycopg2.connect(DATABASE_URI) as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM visitors")
        total_visitors = cur.fetchone()[0]

    return {"count": total_visitors}
```

Run `ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true rockcraft pack` and upload the newly created rock to the MicroK8s registry:

```bash
rockcraft.skopeo --insecure-policy copy --dest-tls-verify=false \
   oci-archive:fastapi-hello-world_0.3_amd64.rock \
   docker://localhost:32000/fastapi-hello-world:0.3
```

The FastAPI app now requires a database which needs to be declared in the `charmcraft.yaml` file. Go back into the charm directory using `cd charm`. Open `charmcraft.yaml` in a text editor and add the following section to the end:

```yaml
requires:
  postgresql:
    interface: postgresql_client
    optional: false
```

Pack the charm using `CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true charmcraft pack` and refresh the deployment using Juju:

```bash
juju refresh fastapi-hello-world \
   --path=./fastapi-hello-world_amd64.charm \
   --resource app-image=localhost:32000/fastapi-hello-world:0.3
```

Deploy `postgresql-k8s` using Juju and integrate it with `fastapi-hello-world`:

```bash
juju deploy postgresql-k8s --trust
juju integrate fastapi-hello-world postgresql-k8s
```

Wait for `juju status` to show that the App is `active` again. `curl http://fastapi-hello-world  --resolve fastapi-hello-world:80:127.0.0.1` should still return the `{"message":"Hi!"}` greeting. To check the total visitors, use `curl http://fastapi-hello-world/visitors  --resolve fastapi-hello-world:80:127.0.0.1` which should return `{"count":1}` after the previous request to the root endpoint and should be incremented each time the root endpoint is requested. If we perform another request to `curl http://fastapi-hello-world  --resolve fastapi-hello-world:80:127.0.0.1`, `curl http://fastapi-hello-world/visitors  --resolve fastapi-hello-world:80:127.0.0.1` will return `{"count":2}`.

## Tear things down

We've reached the end of this tutorial. We have created a FastAPI application, deployed it locally, integrated it with a database and exposed it via ingress!

If you'd like to reset your working environment, you can run the following in the root directory for the tutorial:

```bash
# exit and delete the virtual environment
deactivate
rm -rf charm .venv __pycache__
# delete all the files created during the tutorial
rm fastapi-hello-world_0.1_amd64.rock fastapi-hello-world_0.2_amd64.rock \
   fastapi-hello-world_0.3_amd64.rock rockcraft.yaml app.py \
   requirements.txt migrate.py
# Remove the juju model
juju destroy-model fastapi-hello-world --destroy-storage
```

If you created an instance using Multipass, you can also clean it up. Start by exiting it:

```bash
exit
```

And then you can proceed with its deletion:

```bash
multipass delete charm-dev
multipass purge
```


## Next steps

By the end of this tutorial you will have built a charm and evolved it in a number of typical ways. But there is a lot more to explore:

If you are wondering... | Visit...
-|-
"How do I...?" | {ref}`how-to-guides`
"What is...?" | {ref}`reference`
