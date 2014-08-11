gae-migrations [![Build Status](https://travis-ci.org/qmagico/gae-migrations.svg?branch=master)](https://travis-ci.org/qmagico/gae-migrations)
==============

This is a "[south like](http://south.readthedocs.org/en/latest)" framemework to do data migrations on Google App Engine platform.

## How to use
There are few rules you'll need to follow, but is not that hard, I promess.

#### Set a url to run tasks
You should already know that Google App Engine's task are like web handlers, so you'll need to set up your app to add the task runner handler in your app.yaml

```
- url: /run_generic_task
  script: migrations.gae_handler.application
```

You can change the `/run_generic_task` to whatever you like

#### Editing settings.py
gae-migrations need need some settings to work, which come from a settings.py file in your root application.
Make sure this settings provides:

* `TASKS_QUEUE = "DEFAULT`
  This is the task queue you appointed to run the migrations.

* `TASKS_RUNNER_URL = '/run_generic_task'`
  Put where the URL from step 1.

* `MIGRATIONS_LIST = []`
  This is a list of all files containing migration, this [code snipet]() may help you.

#### Extend the `AbstractMigrationTask` or `AbstractMigrationTaskOnEmptyNamespace` class to migrate the database.
todo
