gae-migrations
==============

This is a "[south like](http://south.readthedocs.org/en/latest)" framemework to run data migrations on Google App Engine platform.

## How to use

##### 1. Copy the migrations folder into your app

##### 2. Create a settings.py file in your app root with:

```
TASKS_QUEUE = 'DEFAULT'  # Some queue name to run tasks, if you want to use task_enqueuer in your app
MIGRATIONS_QUEUE = 'migrations'  # Queue name to run migrations
TASKS_RUNNER_URL = '/run_generic_task'  # A URL for task_enqueuer
MIGRATIONS_MODULE = 'module.where.you.keep.your.migrations'  # A python module where you'll keep your migrations
```

##### 3. Create migrations

Basically you need to:

* Create one migration per file, [see examples here](https://github.com/qmagico/gae-migrations/tree/master/tests/my/migrations)
* The migration class must be named "MyTask" and extend `AbstractMigrationTask` or `AbstractMigrationTaskOnEmptyNamespace`
* You must implement `get_name`, `get_description`, `get_query`, and `migrate_one`
* Optionally you can implement `migrations_per_task`, otherwise, gae-migrations will try to migrate 1000 entities per task run.

##### 4. Start migrations

On your app, you trigger migrations by doing:

```python
from migrations import migrations_enqueuer

migrations_enqueuer.enqueue_next_migration()
```
