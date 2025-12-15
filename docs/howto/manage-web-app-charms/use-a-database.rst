# How-to: Use a database

This guide demonstrates how to integrate a MySQL database into your FastAPI
12-factor app. You will learn how to define object-relational mappings (ORM),
handle schema migrations with Alembic, and manage the database integration using Juju.

## Prerequisites

- A working FastAPI application charmed with ``paas-charm``. This guide will be
  following the [tutorial up until you deploy the app]
  (https://documentation.ubuntu.com/charmcraft/latest/tutorial/
  kubernetes-charm-fastapi/#deploy-the-fastapi-app)
- A Juju model
- Basic familiarity with [SQLAlchemy](https://www.sqlalchemy.org/) and
  [Alembic](https://alembic.sqlalchemy.org/en/latest/).


---

## Object Relational Mapper

To follow the 12-factor methodology, your application should treat backing services
(like databases) as attached resources. While you can write raw SQL, using an
**Object Relational Mapper (ORM)** like SQLAlchemy allows you to interact with your
database using Python classes.

This abstraction layer provides two main benefits:

1. **Safety:** It prevents common security issues like SQL injection.

2. **Portability:** It decouples your code from the specific SQL dialect,
  making it easier to switch database backends if necessary.

.. admonition:: Warning

 While this guide uses MySQL, since we are using ORM's you can swap out
 the db provider very easily.


---

## Prepare the environment

MySQL requires a specific Python driver. Ensure your ``requirements.txt`` includes
a MySQL driver compatible with SQLAlchemy, such as ``pymysql``.

.. code-block::
    :caption: :caption:

    fastapi
    sqlalchemy
    alembic
    PyMySQL[rsa]

.. admonition:: Warning

  When using ``pymysql``, your connection string (handled later by the charm)
  generally follows the format ``mysql+pymysql://user:pass@host/db``.

---

## Declare models

First, define the structure of your data. We will create a simple ``User``
model using SQLAlchemy's declarative system.

Create a file named ``models.py``:


.. code-block:: python
    :caption: models.py

    from sqlalchemy import Column, Integer, String
    from sqlalchemy.orm import declarative_base

    Base = declarative_base()

    class User(Base):
        __tablename__ = "users"

        id = Column(Integer, primary_key=True, index=True, autoincrement=True)
        # MySQL VARCHAR requires a length
        username = Column(String(50), unique=True, index=True, nullable=False)
        email = Column(String(100), unique=True, index=True, nullable=False)

---

## Define migrations

Database schemas change over time. To manage these changes without losing data,
we use **Alembic** for migrations.

### Initialize Alembic

In your project root, run:

.. code-block:: bash

    alembic init alembic

### Configure the environment

Edit ``alembic/env.py`` to point to your models so Alembic can detect changes.
You also need to configure it to read the database URL from the environment,
adhering to 12-factor principles.


.. code-block:: python
    :caption: alembic/env.py

    import os
    from logging.config import fileConfig
    from sqlalchemy import engine_from_config, pool
    from alembic import context
    # Import your models specifically
    from models import Base

    config = context.config

    # 12-factor app: Read config from environment variable
    # The Juju integration will provide this variable
    db_url = os.getenv("MYSQL_DB_CONNECT_STRING")

    if db_url:
        # Convert mysql:// to mysql+pymysql:// for compatibility
        if db_url.startswith("mysql://"):
            db_url = db_url.replace("mysql://", "mysql+pymysql://", 1)
        config.set_main_option("sqlalchemy.url", db_url)

    target_metadata = Base.metadata

    # ... rest of the file ...

### Generate a migration

Create the revision file that instructs the database how to create the ``users`` table:

This command requires us to connect to the database, but since we do not have access
to the database, we will use SQlite instead by setting the enviroment variable to
a non-existent SQlite instance:

.. code-block:: bash

    export MYSQL_DB_CONNECT_STRING="sqlite:///./test.db"
    alembic revision --autogenerate -m "create users table"

### Set up automated updates

12-Factor can automatically run your upgrades. Let's create  a ``migrate.sh``
file to put our migration commands. This file will be automatically picked up
by 12-factor tooling and will be run when a database integration event happens
(ex: created, changed, departed).

.. code-block:: bash
    :caption: migrate.sh

    alembic upgrade head

---

## Create engine and run

Now, set up the database connection. The application should read
the connection string from the ``MYSQL_DB_CONNECT_STRING`` environment variable.

Create ``database.py``:

.. code-block:: python
    :caption: database.py

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import os

    DATABASE_URL = os.getenv("MYSQL_DB_CONNECT_STRING")

    # Fallback for local testing if needed, though production should always have this set
    if not DATABASE_URL:
        raise ValueError("MYSQL_DB_CONNECT_STRING environment variable is not set")
    if DATABASE_URL.startswith("mysql://"):
            DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

Create a simple endpoint in ``app.py`` to test the connection:

.. code-block:: python
    :caption: app.py

    from fastapi import FastAPI, Depends, HTTPException
    from sqlalchemy.orm import Session
    import models
    import database

    app = FastAPI()

    @app.get("/")
    async def root():
        return {"message": "Hello World"}

    @app.post("/users/")
    def create_user(username: str, email: str, db: Session = Depends(database.get_db)):
        user = models.User(username=username, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @app.get("/users/")
    def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
        users = db.query(models.User).offset(skip).limit(limit).all()
        return users

## Update the ``rockcraft.yaml`` file to add the Alembic related files

We need to add two new parts into our ``rockcraft.yaml`` file to copy
the Alembic related files and packages needed to run the database migrations.

.. admonition:: Warning

  Do not forget to change the version to ``0.2`` while updating the ``rockcraft.yaml``
  file

.. code-block:: yaml
    :caption: rockcraft.yaml

    parts:
      Alembic:
        plugin: dump
        source: .
        organize:
          alembic: app/alembic
          alembic.ini: app/alembic.ini
          database.py: app/database.py
          models.py: app/models.py
        stage:
        - app/alembic
        - app/alembic.ini
        - app/database.py
        - app/models.py
      fastapi-framework/dependencies:
        build-packages:
          - pkg-config
          - libmysqlclient-dev
          - python3-dev
        stage-packages:
          - libmysqlclient21  # Required at runtime! (Check your Ubuntu base version for the exact package name)

Now we can pack the file and upload it to local registry:

.. code-block:: bash

    rockcraft pack

    rockcraft.skopeo copy \
      --insecure-policy \
      --dest-tls-verify=false \
      oci-archive:fastapi-hello-world_0.2_$(dpkg --print-architecture).rock \
      docker://localhost:32000/fastapi-hello-world:0.2


.. admonition:: Warning

  If you are using Canonical K8s instead of MIcroK8s you need to use this command
  to upload to local registry:
  sudo /snap/k8s/current/bin/ctr --address /run/containerd/containerd.sock
  --namespace k8s.io images import --base-name docker.io/library/fastapi-hello-world
  ./fastapi-hello-world_0.2_amd64.rock

## Update the ``charmcraft.yaml`` file

Add the ``mysql`` integration to the ``charmcraft.yaml`` file:

.. code-block:: yaml
    :caption: charmcraft.yaml

    requires:
      mysql:
        interface: mysql_client
        optional: false
        limit: 1

## Deploy the app

Let's deploy the app into Juju:

.. code-block:: bash

    juju deploy ./charm/fastapi-hello-world_amd64.charm --resource app-image=localhost:32000/fastapi-hello-world:0.2

.. admonition:: Warning

  If you are using Canonical Kubernetes instead of MicroK8s you
  need to use this command to deploy your charm:
  juju deploy ./charm/fastapi-hello-world_amd64.charm
  --resource app-image=fastapi-hello-world:0.2

---

## Integrate with MySQL

Deploy a MySQL database and integrate it with your application.
The ``paas-charm`` library handles the relation data and injects
the connection string into your app container.

Deploy MySQL:

.. code-block:: bash

    juju deploy mysql-k8s --channel 8.0/stable --trust

Integrate the applications:

.. code-block:: bash

    juju integrate fastapi-hello-world mysql-k8s

Once integrated, Juju triggers a configuration update.
Your app will restart, and the ``MYSQL_DB_CONNECT_STRING`` environment
variable will be populated with the credentials to access the MySQL unit.


---

## Verify the database is working

Verify the relation by creating a user through your API.

Find the application IP using ``juju status``.

Send a POST request:

.. code-block:: bash

    curl -X POST "http://<APP_IP>:8000/users/?username=juju_admin&email=admin@example.com"

Send a GET request:

.. code-block:: bash

    curl "http://<APP_IP>:8000/users/"

If successful, the API returns the JSON object of the created user,
confirming that the app can write to the persistent MySQL storage.

