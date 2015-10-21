gae-migrations
==============

DISCONTINUATION NOTICE
----------------------
This project is officialy discontinued and most likely won't be receiving commits anymore.
----------------------


This is a framework for long-running tasks on Google Appengine.
It can be used to run "[south like](http://south.readthedocs.org/en/latest)" migrations, which run once on a lifetime, but one can also use it to run periodic jobs.

Migrations can be ran on all namespaces or on a single namespace.

## How to use

#### 1. Copy the migrations folder into your app

#### 2. Create a settings.py file in your app root with:

```
TASKS_QUEUE = 'DEFAULT'  # Some queue name to run tasks, if you want to use task_enqueuer in your app
MIGRATIONS_QUEUE = 'migrations'  # Queue name to run migrations
TASKS_RUNNER_URL = '/run_generic_task'  # A URL for task_enqueuer
```

#### 3. Register the task handler on your `app.yaml`:

```
- url: /run_generic_task
  script: migrations.gae_handler.application
  login: admin
```

#### 4. Create migrations modules

A migrations module is a python module (folder) which has one or more migrations inside.
A migration is a python module (.py file) that defines functions and properties about the migration.
There are different functions and attributes that a migration can have. Read on

##### 4.1 Migration Attributes

* DESCRIPTION - A description for the migration
* MIGRATIONS_PER_TASK - How many entities should be migrated per single task run (only use this if you define `get_query()`)
* RESTRICT_NAMESPACE - Only run this task on the specified namespace
* MIGRATE_EMPTY - Migrate, even though you have no entities matching the query in that Namespace, default: False

##### 4.2 Migration functions

* get_query() - This is optional. This is supposed to return a ndb query object which will loop through all the objects you want to migrate.
* migrate_one(entity) - Perform migration on a single entity
* migrate_many(entities) - Perform migration on an array of entities
* migrate() - Just run the migration
* update_json_data(migrate_result, actual_json_data) - if your migration requires some previous data from other interactions 
you might return something from either migrate, migrate_one or migrate_many functions that you will have access to it after each interaction to 
update your migration.json_data based on this migrate_result and the actual_json_data.

If you implement `get_query`, you should also implement `migrate_one` or `migrate_many`. Otherwise, you must implement `migrate`.


#### 5. Start migrations

On your app, you trigger migrations by doing:

```python
import migrations
import my.south_like.migrations.module
import my.periodic_tasks.module
import my.tasks.that.only.run.on.red.namespace.module

migrations.run_pending(my.south_like.migrations.module)
migrations.run_all(my.periodic_tasks.module)
migrations.run_all(my.tasks.that.only.run.on.red.namespace.module, ns='red')
```

Take a look at the the test-cases, they should give you a good idea of how all works :-)
