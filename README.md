gae-migrations [![Build Status](https://travis-ci.org/qmagico/gae-migrations.svg?branch=master)](https://travis-ci.org/qmagico/gae-migrations)
==============

This is a "[south like](http://south.readthedocs.org/en/latest)" framemework to do data migrations on Google App Engine platform.

## How to use
There are few rules you'll need to follow, but is not that hard, I promess.

#### Set a url to run tasks
You should already know that Google App Engine's task are like web handlers, so you'll need to implement a handler and call our generic enqueuer method [`migrations.task_enqueuer.execute`](https://github.com/qmagico/gae-migrations/blob/master/migrations/task_enqueuer.py#L29), as simple as this:

```
import webapp2
from migrations import task_enqueuer

class GenericTaskRunner(webapp2.RequestHandler):
    def get(self, *args, **kwargs):
      task_enqueuer.execute(*args, **kwargs)
        

application = webapp2.WSGIApplication([
    ('/run_generic_task', GenericTaskRunner),
], debug=True)
```

#### Editing settings.py
gae-migrations need to know some data to work as well, edit the [`migrations.settings.py`](https://github.com/qmagico/gae-migrations/blob/master/migrations/settings.py) to provide this informations

* `TASKS_QUEUE = "DEFAULT`
  This is the task queue you appointed to run the migrations.

* `TASKS_RUNNER_URL = '/run_generic_task'`
  Put where the URL from step 1.

* `MIGRATIONS_LIST = []`
  This is a list of all files containing migration, this [code snipet]() may help you.

#### Extend the `AbstractMigrationTask` or `AbstractMigrationTaskOnEmptyNamespace` class to migrate the database.
todo

