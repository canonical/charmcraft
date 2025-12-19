.. _use-db-with-12-factor-charms:

.. _meta::
    :description: Integrate a MySQL database into your charmed 12-factor app written with FastAPI.

Use a database with your 12-factor app charm
============================================

This guide demonstrates how to integrate a MySQL database into your FastAPI
12-factor app. You will learn how to define object-relational mappings (ORM),
handle schema migrations with Alembic, and manage the database integration using Juju.

Prerequisites
-------------

- A working FastAPI application charmed with 12-factor tooling. This guide will be
  following the :ref:`tutorial up until you deploy the app
  <write-your-first-kubernetes-charm-for-a-fastapi-app-deploy-the-fastapi-app>`.
- A Juju model
- Basic familiarity with `SQLAlchemy <https://www.sqlalchemy.org/>`_ and
  `Alembic <https://alembic.sqlalchemy.org/en/latest/>`_.


Prepare the environment
-----------------------

For Python projects, MySQL requires the pymysql driver. Add it to
``requirements.txt``.

.. code-block::
    :caption: requirements.txt

    fastapi
    sqlalchemy
    alembic
    PyMySQL[rsa]

When using pymysql, your connection string (handled later by the charm)
follows the format ``mysql+pymysql://user:pass@host/db``.


Declare models
--------------

First, define the structure of your data. Create a simple ``User``
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


Define migrations
-----------------

Database schemas change over time. To manage these changes without losing data,
let's use Alembic for migrations.

Configure Alembic
~~~~~~~~~~~~~~~~~

In your project root, run:

.. code-block:: bash

    alembic init alembic

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

Generate a migration script
~~~~~~~~~~~~~~~~~~~~~~~~~~~

For migration, you need a revision file that instructs the database how to create the ``users`` table.
This command requires you to connect to the database, but since access isn't available,
use SQLite as an empty database for only this step. Set the environment variable
to a non-existent SQLite instance:

.. code-block:: bash

    export MYSQL_DB_CONNECT_STRING="sqlite:///./test.db"
    alembic revision --autogenerate -m "create users table"

Set up automated updates
~~~~~~~~~~~~~~~~~~~~~~~~

Create  a ``migrate.sh`` script for our migration commands so that 12-Factor
app tooling can automatically run your upgrades. This file will automatically run
when a database integration event happens (such as ``created``, ``changed```, or ``departed``).

.. code-block:: bash
    :caption: migrate.sh

    alembic upgrade head


Write the database connection code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now it's time to set up the database connection. The application should read
the connection string from the ``MYSQL_DB_CONNECT_STRING`` environment variable.

Create ``database.py``:

.. code-block:: python
    :caption: database.py

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import os

    DATABASE_URL = os.getenv("MYSQL_DB_CONNECT_STRING")

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
    :emphasize-lines: 12-23

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

Update ``rockcraft.yaml``
-------------------------

Next, add two parts to ``rockcraft.yaml`` file that copy
the Alembic related files and packages needed to run the database migrations.

.. code-block:: yaml
    :caption: rockcraft.yaml
    :emphasize-lines: 6,24-37

    # See https://documentation.ubuntu.com/rockcraft/1.16.0/reference/extensions/fastapi-framework
    # For questions or help, visit https://matrix.to/#/#12-factor-charms:ubuntu.com

    name: fastapi-hello-world
    base: ubuntu@24.04 # the base environment for this FastAPI application
    version: '0.2' # just for humans. Semantic versioning is recommended
    summary: A summary of your FastAPI application # 79 char long summary
    description: |
        This is fastapi project's description. You have a paragraph or two to tell the
        most important story about it. Keep it under 100 words though,
        we live in tweetspace and your description wants to look good in the
        container registries out there.
    # the platforms this rock should be built on and run on.
    # you can check your architecture with `dpkg --print-architecture`
    platforms:
        amd64:
        # arm64:
        # ppc64el:
        # s390x:

    extensions:
    - FastAPI-framework

    parts:
        alembic:
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


Pack the rock and upload it to the local container registry:

.. tabs::

    .. group-tab:: MicroK8s
        .. code-block:: bash

            rockcraft pack

            rockcraft.skopeo copy \
            --insecure-policy \
            --dest-tls-verify=false \
            oci-archive:fastapi-hello-world_0.2_$(dpkg --print-architecture).rock \
            docker://localhost:32000/fastapi-hello-world:0.2

    .. group-tab:: Canonical K8s
        .. code-block:: bash

            rockcraft pack

            sudo /snap/k8s/current/bin/ctr \
            --address /run/containerd/containerd.sock \
            --namespace k8s.io images import \
            --base-name docker.io/library/fastapi-hello-world \
            ./fastapi-hello-world_0.2_$(dpkg --print-architecture).rock

Update ``charmcraft.yaml``
--------------------------

Add the ``mysql`` integration to the ``charmcraft.yaml`` file:

.. code-block:: yaml
    :caption: charmcraft.yaml

    requires:
      mysql:
        interface: mysql_client
        optional: false
        limit: 1

Deploy the app
--------------

Deploy the app with Juju:

.. tabs::

    .. group-tab:: MicroK8s
        .. code-block:: bash

            juju deploy ./charm/fastapi-hello-world_$(dpkg --print-architecture).charm \
            --resource app-image=localhost:32000/fastapi-hello-world:0.2

    .. group-tab:: Canonical K8s
        .. code-block:: bash

            juju deploy ./charm/fastapi-hello-world_$(dpkg --print-architecture).charm \
            --resource app-image=fastapi-hello-world:0.2


Integrate with MySQL
--------------------

With everything in place, you're ready to deploy a MySQL database and integrate
it with your application.
The 12-factor tooling handles the relation data and injects
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


Verify the database is working
------------------------------

As a final step, verify the relation by creating a user through your API.

First, get the application's IP:

.. code-block:: bash

    juju status

Send a POST request:

.. code-block:: bash

    curl -X POST "http://<APP_IP>:8000/users/?username=juju_admin&email=admin@example.com"

Send a GET request:

.. code-block:: bash

    curl "http://<APP_IP>:8000/users/"

If successful, the API returns the JSON object of the created user,
confirming that the app can write to the persistent MySQL storage.

