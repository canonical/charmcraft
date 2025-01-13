(write-your-first-kubernetes-charm-for-a-django-app)=

# Write your first Kubernetes charm for a Django app


## What you'll need

- A working station, e.g., a laptop, with amd64 architecture which has sufficient resources to launch a virtual machine with 4 CPUs, 4 GB RAM, and a 50 GB disk
   - Note that a workstation with arm64 architecture can complete the majority of this
     tutorial.
- Familiarity with Linux.
- About an hour of free time.


## What you'll do

Create a Django application. Use that to create a rock with `rockcraft`. Use that to
create a charm with `charmcraft`. Use that to test-deploy, configure, etc., your Django
application on a local Kubernetes cloud, `microk8s`, with `juju`. All of that multiple
times, mimicking a real development process.

```{note}
**rock**

An Ubuntu LTS-based OCI compatible container image designed to meet security, stability,
and reliability requirements for cloud-native software.

**charm**

A package consisting of YAML files + Python code that will automate every aspect of an
application's lifecycle so it can be easily orchestrated with Juju.

**Juju**

An orchestration engine for charmed applications.
```

```{important}
Should you get stuck or notice issues, please get in touch on
[Matrix](https://matrix.to/#/#12-factor-charms:ubuntu.com) or
[Discourse](https://discourse.charmhub.io/).
```


## Set things up

Install Multipass.

> See more: [Multipass | How to install
> Multipass](https://multipass.run/docs/install-multipass)

Use Multipass to launch an Ubuntu VM with the name `charm-dev` from the 22.04 blueprint:

```bash
multipass launch --cpus 4 --disk 50G --memory 4G --name charm-dev 22.04
```

Once the VM is up, open a shell into it:

```bash
multipass shell charm-dev
```

In order to create the rock, you'll need to install Rockcraft:

```bash
sudo snap install rockcraft --classic
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

```{note}
This tutorial requires version `3.2.0` or later of Charmcraft. Check the version
of Charmcraft using `charmcraft --version` If you have an older version of Charmcraft
installed, use `sudo snap refresh charmcraft --channel latest/edge` to get the latest
edge version of Charmcraft.
```

MicroK8s is required to deploy the Django application on Kubernetes. Install MicroK8s:

```bash
sudo snap install microk8s --channel 1.31-strict/stable
sudo adduser $USER snap_microk8s
newgrp snap_microk8s
```

Wait for MicroK8s to be ready using `sudo microk8s status --wait-ready`. Several
MicroK8s add-ons are required for deployment:

```bash
sudo microk8s enable hostpath-storage
# Required to host the OCI image of the Django application
sudo microk8s enable registry
# Required to expose the Django application
sudo microk8s enable ingress
```

Juju is required to deploy the Django application. Install Juju and bootstrap a
development controller:

```bash
sudo snap install juju --channel 3.5/stable
mkdir -p ~/.local/share
juju bootstrap microk8s dev-controller
```

Finally, create a new directory for this tutorial and go inside it:

```bash
mkdir django-hello-world
cd django-hello-world
```


## Create the Django application

Create a `requirements.txt` file, copy the following text into it and then save it:

```
Django
```

Install `python3-venv` and create a virtual environment:

```bash
sudo apt-get update && sudo apt-get install python3-venv -y
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a new project using `django-admin`:

```bash
django-admin startproject django_hello_world
```


## Run the Django application locally

Change into the `django_hello_world` directory and run the Django application to verify
that it works:

```bash
cd django_hello_world
python3 manage.py runserver
```

Test the Django application by using `curl` to send a request to the root endpoint. You
may need a new terminal for this; if you are using Multipass use `multipass shell
charm-dev` to get another terminal:

```bash
curl localhost:8000
```

The Django application should respond with:

> The install worked successfully! Congratulations!

```{note}
The response from the Django application includes HTML and CSS which makes it
difficult to read on a terminal.
```

The Django application looks good, so you can stop it for now using `Ctrl`+`C`.


## Pack the Django application into a rock

First, we'll need a `rockcraft.yaml` file. Rockcraft will automate its creation and
tailoring for a Django application by using the `django-framework` profile:

```bash
cd ..
rockcraft init --profile django-framework
```

The `rockcraft.yaml` file will automatically be created and set the name based on your
working directory. Open it in a text editor and check that the `name` is
`django-hello-world`. Ensure that `platforms` includes the architecture of your host.
For example, if your host uses the ARM architecture, include `arm64` in `platforms`.

```{note}
For this tutorial, we'll use the name `django-hello-world` and assume you are on
the `amd64` platform. Check the architecture of your system using `dpkg
--print-architecture`. Choosing a different name or running on a different platform will
influence the names of the files generated by Rockcraft.
```

Django applications require a database. Django will use a sqlite database by default.
This won't work on Kubernetes because the database would disappear every time the pod is
restarted (e.g., to perform an upgrade) and this database would not be shared by all
containers as the application is scaled. We'll use Juju later to easily deploy a
database.

We'll need to update the `settings.py` file to prepare for integrating the app with a
database. Open `django_hello_world/django_hello_world/settings.py` and include `import
json`, `import os` and `import secrets` along with the other imports at the top of the
file.

Near the top of the `settings.py` file change the following settings to be production
ready:

```python
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', secrets.token_hex(32))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'false') == 'true'

ALLOWED_HOSTS = json.loads(os.environ.get('DJANGO_ALLOWED_HOSTS', '{ref}`]'))
```

Go further down to the Database section and change the `DATABASES` variable to:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRESQL_DB_NAME'),
        'USER': os.environ.get('POSTGRESQL_DB_USERNAME'),
        'PASSWORD': os.environ.get('POSTGRESQL_DB_PASSWORD'),
        'HOST': os.environ.get('POSTGRESQL_DB_HOSTNAME'),
        'PORT': os.environ.get('POSTGRESQL_DB_PORT'),
    }
}
```

We'll need to update the `requirements.txt` file to include `psycopg2-binary` so that
the Django app can connect to PostgreSQL.

Pack the rock:

```bash
ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true rockcraft pack
```

```{note}
Depending on your network, this step can take a couple of minutes to finish.

`ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS` is required whilst the Django extension is
experimental.
```

Once Rockcraft has finished packing the Django rock, you'll find a new file in your
working directory with the `.rock` extension:

```bash
ls *.rock -l
```

The rock needs to be copied to the MicroK8s registry so that it can be deployed in the
Kubernetes cluster:

```bash
rockcraft.skopeo --insecure-policy copy --dest-tls-verify=false \
    oci-archive:django-hello-world_0.1_amd64.rock \
    docker://localhost:32000/django-hello-world:0.1
```

```{note}
If you changed the `name` or `version` in `rockcraft.yaml` or are not on an
`amd64` platform, the name of the `.rock` file will be different for you.
```


## Create the charm

Create a new directory for the charm and go inside it:

```bash
mkdir charm
cd charm
```

We'll need a `charmcraft.yaml`, `requirements.txt` and source code for the charm. The
source code contains the logic required to operate the Django application. Charmcraft
will automate the creation of these files by using the `django-framework` profile:

```bash
charmcraft init --profile django-framework --name django-hello-world
```

The files will automatically be created in your working directory. We will need to
connect to the PostgreSQL database. Open the `charmcraft.yaml` file and add the
following section to the end of the file:

```yaml
requires:
  postgresql:
    interface: postgresql_client
    optional: false
    limit: 1
```

The charm depends on several libraries. Download the libraries and pack the charm:

```bash
CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true charmcraft fetch-libs
CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true charmcraft pack
```

```{note}
Depending on your network, this step can take a couple of minutes to finish.
```

Once Charmcraft has finished packing the charm, you'll find a new file in your working
directory with the `.charm` extension:

```bash
ls *.charm -l
```

```{note}
If you changed the name in charmcraft.yaml or are not on the amd64 platform, the
name of the `.charm` file will be different for you.
```


## Deploy the Django application

A Juju model is needed to deploy the application. Create a new model:

```bash
juju add-model django-hello-world
```

```{note}
If you are not on a host with the `amd64` architecture, you will need to include
a constraint to the Juju model to specify your architecture.For example, for the `arm64`
architecture, use `juju set-model-constraints -m django-hello-world arch=arm64`. Check
the architecture of your system using `dpkg --print-architecture`.
```

Now deploy the Django application using Juju:

```bash
juju deploy ./django-hello-world_ubuntu-22.04-amd64.charm \
    django-hello-world \
    --resource django-app-image=localhost:32000/django-hello-world:0.1
```

Deploy PostgreSQL, and integrate and PostgreSQL with the Django application:
```bash
juju deploy postgresql-k8s --trust
juju integrate django-hello-world postgresql-k8s
```

```{note}
It will take a few minutes to deploy the Django application. You can monitor the
progress using `juju status --watch 5s`. Once the status of the App has gone to
`active`, you can stop watching using `Ctrl+C`.
```

The Django application should now be running. You can see the status of the deployment
using `juju status` which should be similar to the following output:

```output
django-hello-world  dev-controller  microk8s/localhost  3.5.3    unsupported  16:47:01+10:00

App                 Version  Status  Scale  Charm               Channel    Rev  Address         Exposed  Message
django-hello-world           active      1  django-hello-world               3  10.152.183.126  no
postgresql-k8s      14.11    active      1  postgresql-k8s      14/stable  281  10.152.183.197  no

Unit                   Workload  Agent  Address      Ports  Message
django-hello-world/0*  active    idle   10.1.157.80
postgresql-k8s/0*      active    idle   10.1.157.78         Primary
```

To be able to test the deployment, we need to include the IP address in the allowed
hosts configuration. We'll also enable debug mode for now whilst we are testing. Both
can be done using `juju config django-hello-world django-allowed-hosts=*
django-debug=true`.

```{note}
Setting the Django allowed hosts to `*` and turning on debug mode should not be
done in production where you should set the actual hostname of the application and
disable debug mode. We will do this in the tutorial for now and later demonstrate how we
can set these to production ready values.
```

Test the deployment using `curl` to send a request to the root endpoint. The IP address
is the Address listed in the Unit section of the `juju status` output (e.g.,
`10.1.157.80` in the sample output above):

```bash
curl 10.1.157.80:8000
```

The Django app should again respond with:

> The install worked successfully! Congratulations!


## Add a root endpoint

The generated Django application does not come with a root endpoint, which is why we had
to initially enable debug mode for testing. Let's add a root endpoint that returns a
`Hello, world!` greeting. We will need to go back out to the root directory for the
tutorial and go into the `django_hello_world` directory using `cd
../django_hello_world`. Add a new Django app using:

```bash
django-admin startapp greeting
```

Open the `greeting/views.py` file and replace the content with:

```python
from django.http import HttpResponse

def index(request):
    return HttpResponse("Hello, world!\n")
```

Create the `greeting/urls.py` file with the following contents:

```python
from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
]
```

Open the `django_hello_world/urls.py` file and edit the value of `urlpatterns` to
include `path('', include("greeting.urls")`, for example:

```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("greeting.urls")),
    path("admin/", admin.site.urls),
]
```

Since we're changing the application we should update the version of it. Go back to the
root directory of the tutorial using `cd ..` and change the `version` in
`rockcraft.yaml` to `0.2`. Pack and upload the rock using similar commands as before:

```bash
ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true rockcraft pack
rockcraft.skopeo --insecure-policy copy --dest-tls-verify=false \
    oci-archive:django-hello-world_0.2_amd64.rock \
    docker://localhost:32000/django-hello-world:0.2
```

Now we can deploy the new version of the Django application using:

```bash
cd charm
juju refresh django-hello-world \
    --path=./django-hello-world_ubuntu-22.04-amd64.charm \
    --resource django-app-image=localhost:32000/django-hello-world:0.2
```

Now that we have a valid root endpoint we can disable debug mode:

```bash
juju config django-hello-world django-debug=false
```

Use `juju status --watch 5s` again to wait until the app is active again. The IP address
will have changed so we need to retrieve it again using `juju status`. Now we can call
the root endpoint using `curl 10.1.157.80:8000` and the Django application should
respond with `Hello, world!`.


## Enable a configuration

To demonstrate how to provide configuration to the Django application, we will make the
greeting configurable. Go back out to the tutorial root directory using `cd ..`. Open
the `django_hello_world/greeting/views.py` file and replace the content with:

```python
import os

from django.http import HttpResponse

def index(request):
    return HttpResponse(f"{os.environ.get('DJANGO_GREETING', 'Hello, world!')}\n")
```

Increment the `version` in `rockcraft.yaml` to `0.3` and run the pack and upload
commands for the rock:

```bash
ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true rockcraft pack
rockcraft.skopeo --insecure-policy copy --dest-tls-verify=false \
    oci-archive:django-hello-world_0.3_amd64.rock \
    docker://localhost:32000/django-hello-world:0.3
```

Change back into the charm directory using `cd charm`. The `django-framework` Charmcraft
extension supports adding configurations in `charmcraft.yaml` which will be passed as
environment variables to the Django application. Add the following to the end of the
`charmcraft.yaml` file:

```yaml
config:
  options:
    greeting:
      description: |
        The greeting to be returned by the Django application.
      default: "Hello, world!"
      type: string
```

```{note}
Configuration options are automatically capitalised and `-` are replaced by `_`. A
`DJANGO_` prefix will also be added as a namespace for app configurations.
```

We can now pack and deploy the new version of the Django app:

```bash
CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=true charmcraft pack
juju refresh django-hello-world \
    --path=./django-hello-world_ubuntu-22.04-amd64.charm \
    --resource django-app-image=localhost:32000/django-hello-world:0.3
```

After we wait for a bit monitoring `juju status` the application should go back to
`active` again. Sending a request to the root endpoint using `curl 10.1.157.81:8000`
(after getting the IP address from `juju status`) should result in the Django
application responding with `Hello, world!` again. We can change the greeting using
`juju config django-hello-world greeting='Hi!'`. After we wait for a moment for the app
to be restarted, `curl 10.1.157.81:8000` should now respond with `Hi!`.


## Expose the app using ingress

```{note}
This step of the tutorial only works for hosts with the `amd64` architecture. For
other architectures, skip this step.
```

As a final step, let's expose the application using ingress. Deploy the
`nginx-ingress-integrator` charm and integrate it with the Django app:

```bash
juju deploy nginx-ingress-integrator
juju integrate nginx-ingress-integrator django-hello-world
```

```{note}
RBAC is enabled in the `charm-dev` Multipass blueprint. Run `juju trust
nginx-ingress-integrator --scope cluster` if you're using the `charm-dev` blueprint.
```

The hostname of the app needs to be defined so that it is accessible via the ingress. We will also set the default route to be the root endpoint:

```bash
juju config nginx-ingress-integrator \
    service-hostname=django-hello-world path-routes=/
```

Monitor `juju status` until everything has a status of `active`. Use `curl
http://django-hello-world --resolve django-hello-world:80:127.0.0.1` to send a request
via the ingress. It should still be returning the `Hi!` greeting.

```{note}
The `-H "Host: django-hello-world"` option to the `curl` command is a way of setting the
hostname of the request without setting a DNS record.
```

We can now also change the Django allowed hosts to `django-hello-world` which is a
production ready value (for production, you will need to setup a DNS record):

```bash
juju config django-hello-world django-allowed-hosts=django-hello-world
```

Running `curl 127.0.0.1 -H "Host: django-hello-world"` should still get the Django app
to respond with `Hi!`.


## Tear things down

You've reached the end of this tutorial. You have created a Django application, deployed
it locally, build an OCI image for it and deployed it using Juju. Then we integrated it
with PostgreSQL to be production ready, demonstrated how to add a root endpoint and how
to configure the application and finally we exposed our application using an ingress.

If you'd like to reset your working environment, you can run the following in the root
directory for the tutorial:

```bash
cd ..
deactivate
rm -rf charm .venv django_hello_world
```

Then, delete all the files created during the tutorial:

```bash
rm django-hello-world_0.1_amd64.rock \
    django-hello-world_0.2_amd64.rock \
    django-hello-world_0.3_amd64.rock \
    rockcraft.yaml requirements.txt
```

And remove the juju model:

```bash
juju destroy-model django-hello-world --destroy-storage
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
