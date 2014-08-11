import time
import logging
import sys

from importlib import import_module
from google.appengine.api import namespace_manager
from google.appengine.ext import ndb
from google.appengine.api.taskqueue.taskqueue import TaskRetryOptions
from google.appengine.ext.ndb import Cursor
from google.appengine.ext.db.metadata import get_namespaces
from migrations import task_enqueuer
import settings

RUNNING = 'RUNNING'
DONE = 'DONE'
ERROR = 'ERROR'
NO_RETRY = TaskRetryOptions(task_retry_limit=1)


class MigrationException(BaseException):
    def __init__(self, cause):
        BaseException.__init__(self, cause.message)
        self.cause = cause


class DBMigrationLog(ndb.Model):
    name = ndb.StringProperty(required=True)
    description = ndb.StringProperty(required=True)
    status = ndb.StringProperty(required=True, choices=[RUNNING, DONE, ERROR])
    creation = ndb.DateTimeProperty(auto_now_add=True)
    last_update = ndb.DateTimeProperty(auto_now=True)
    error_msg = ndb.TextProperty()
    stacktrace = ndb.TextProperty()

    @classmethod
    def new_migration(cls, name, description):
        original_ns = namespace_manager.get_namespace()
        namespace_manager.set_namespace('')
        migration = cls.query(cls.name == name).get()
        if not migration:
            migration = cls()
            migration.name = name
        migration.description = description
        migration.status = RUNNING
        migration.put()
        namespace_manager.set_namespace(original_ns)
        return migration

    @classmethod
    def last_1000_names_done_or_running(cls):
        original_ns = namespace_manager.get_namespace()
        namespace_manager.set_namespace('')
        migrations = cls.query(cls.status.IN([DONE, RUNNING])).order(-cls.name).fetch(1000)
        names = []
        for migration in migrations:
            names.append(migration.name)
        namespace_manager.set_namespace(original_ns)
        return names

    @classmethod
    def finish_migration(cls, name):
        original_ns = namespace_manager.get_namespace()
        namespace_manager.set_namespace('')
        migration = cls.query(cls.name == name).get()
        if migration:
            migration.status = DONE
            migration.put()
        time.sleep(1)  # eventually consistent fdp
        namespace_manager.set_namespace(original_ns)

    @classmethod
    def error(cls, name, error_msg, stacktrace):
        original_ns = namespace_manager.get_namespace()
        namespace_manager.set_namespace('')
        migration = cls.query(cls.name == name).get()
        if migration:
            migration.error_msg = error_msg
            migration.stacktrace = stacktrace
            migration.status = ERROR
            migration.put()
        namespace_manager.set_namespace(original_ns)


class AbstractMigrationTask():
    def __init__(self, empty_namespace=False):
        self.empty_namespace = empty_namespace
        self.migration_query = self.get_migration_query()
        self.name = self.get_name()

    @classmethod
    def enqueue_migration(cls, params):
        module = import_module(params['migration_module'])
        migration = getattr(module, 'MyTask')()
        migration.start(params['cursor_state'])

    def get_migration_module(self):
        return sys.modules[self.__module__].__name__

    def get_namespace_by_index(self, namespace_index):
        return get_namespaces()[namespace_index]

    def get_migration_query(self):
        try:
            return self.get_query()
        except Exception, e:
            error_msg = 'error getting query'
            self.stop_with_error(error_msg, e)

    def fetch(self, cursor_urlsafe, namespace, size):
        if namespace != namespace_manager.get_namespace():
            namespace_manager.set_namespace(namespace)

        cursor = cursor_urlsafe and Cursor(urlsafe=cursor_urlsafe)
        result, cursor, more = self.migration_query.fetch_page(size, start_cursor=cursor)
        return result, cursor, more

    def start(self, cursor_state):
        cursor_urlsafe = cursor_state.get('cursor_urlsafe', None)
        namespace_index = cursor_state.get('namespace_index', 0)
        size = cursor_state.get('size', 1000)

        if self.empty_namespace:
            namespace = ''
        else:
            namespace = self.get_namespace_by_index(namespace_index)

        entities, cursor, more = self.fetch(cursor_urlsafe, namespace, size)

        for entity in entities:
            try:
                self.migrate_one(entity)
            except Exception, e:
                error_msg = 'error migrating on namespace %s: %s' % (self.namespace, entity.key)
                self.stop_with_error(error_msg, e)

        task_params = {
            'migration_module': self.get_migration_module(),
            'cursor_state': {},
            'task_url': settings.TASKS_RUNNER_URL,
            'task_queue_name': settings.MIGRATIONS_QUEUE,
            'task_retry_options': NO_RETRY
        }

        if more:
            task_params['cursor_state'] = {
                'cursor_urlsafe': cursor and cursor.urlsafe(),
                'namespace_index': namespace_index
            }

            task_enqueuer.enqueue(AbstractMigrationTask.enqueue_migration, task_params)

        elif namespace_index < len(get_namespaces()) - 1 and not self.empty_namespace:
            task_params['cursor_state'] = {
                'namespace_index': namespace_index + 1
            }

            task_enqueuer.enqueue(AbstractMigrationTask.enqueue_migration, task_params)

        else:
            self.finish_migration()
            self.enqueue_next_migration()

    def enqueue_next_migration(self):
        from migrations import migrations_enqueuer
        migrations_enqueuer.enqueue_next_migration()

    def stop_with_error(self, error_msg, exception):
        stacktrace = exception.format_exc()
        DBMigrationLog.error(self.name, error_msg, stacktrace)
        logging.error(error_msg)
        raise MigrationException(exception)

    def finish_migration(self):
        DBMigrationLog.finish_migration(self.name)
        logging.info('end of migration %s on empty namespace' % self.name)


class AbstractMigrationTaskOnEmptyNamespace(AbstractMigrationTask):
    def __init__(self):
        AbstractMigrationTask.__init__(self, empty_namespace=True)
