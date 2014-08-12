import time
import logging
import sys
import traceback

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
NO_RETRY = TaskRetryOptions(task_retry_limit=0)


class MigrationException(BaseException):
    def __init__(self, cause):
        BaseException.__init__(self, cause.message)
        self.cause = cause


class DBMigration(ndb.Model):
    name = ndb.StringProperty(required=True)
    description = ndb.StringProperty(required=True)
    status = ndb.StringProperty(required=True, choices=[RUNNING, DONE, ERROR])
    creation = ndb.DateTimeProperty(auto_now_add=True)
    last_update = ndb.DateTimeProperty(auto_now=True)
    error_msg = ndb.TextProperty()
    stacktrace = ndb.TextProperty()

    @classmethod
    def find_or_create(cls, name, description):
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

    def finish(self):
        original_ns = namespace_manager.get_namespace()
        namespace_manager.set_namespace('')
        last_update = self.last_update
        self.status = DONE
        self.put()
        self._wait_for_update_after(last_update)
        namespace_manager.set_namespace(original_ns)

    def error(self, error_msg, stacktrace):
        original_ns = namespace_manager.get_namespace()
        namespace_manager.set_namespace('')
        last_update = self.last_update
        self.error_msg = error_msg
        self.stacktrace = stacktrace
        self.status = ERROR
        self.put()
        self._wait_for_update_after(last_update)
        namespace_manager.set_namespace(original_ns)

    def _wait_for_update_after(self, d):
        while not self.key.get().last_update > d:
            time.sleep(0.1)


def enqueue_migration(module_name, cursor_state=None):
    task_enqueuer.enqueue(task_start_migration,
                          queue=settings.MIGRATIONS_QUEUE,
                          module_name=module_name,
                          cursor_state=cursor_state,
                          task_retry_options=NO_RETRY)


def task_start_migration(module_name, cursor_state=None):
    module = import_module(module_name)
    migration = module.MyTask()
    migration.start(cursor_state)


class AbstractMigrationTask():
    def get_migration_module(self):
        return sys.modules[self.__module__].__name__

    def init_cursor(self):
        cursor_state = {
            'namespaces': [n for n in get_namespaces() if n],
            'namespace_index': 0,
            'cursor_urlsafe': None,
        }
        return cursor_state

    def migrations_per_task(self):
        return 1000

    def get_namespace(self, cursor_state):
        return cursor_state['namespaces'][cursor_state['namespace_index']]

    def update_cursor_state(self, cursor_state, querycursor, more):
        if more:
            cursor_state['cursor_urlsafe'] = querycursor.urlsafe()
            return True
        else:
            namespaces = cursor_state['namespaces']
            namespace_index = cursor_state['namespace_index']
            if namespace_index < len(namespaces) - 1:
                cursor_state['namespace_index'] += 1
                cursor_state['cursor_urlsafe'] = None
                return True
            else:
                return False

    def fetch(self, cursor_state):
        if not cursor_state:
            cursor_state = self.init_cursor()

        namespace = self.get_namespace(cursor_state)
        if namespace != namespace_manager.get_namespace():
            namespace_manager.set_namespace(namespace)

        cursor_urlsafe = cursor_state.get('cursor_urlsafe', None)
        cursor = cursor_urlsafe and Cursor(urlsafe=cursor_urlsafe)

        query = None
        try:
            query = self.get_query()
        except Exception, e:
            error_msg = 'error getting query'
            self.stop_with_error(error_msg, e)

        size = self.migrations_per_task()

        result, cursor, more = query.fetch_page(size, start_cursor=cursor)
        more = self.update_cursor_state(cursor_state, cursor, more)
        return result, cursor_state, more

    def start(self, cursor_state):
        self.dbmigration = DBMigration.find_or_create(self.get_name(), self.get_description())

        entities, cursor_state, more = self.fetch(cursor_state)

        for entity in entities:
            try:
                self.migrate_one(entity)
            except Exception, e:
                error_msg = 'error migrating on namespace %s: %s' % (namespace_manager.get_namespace(), entity.key)
                self.stop_with_error(error_msg, e)

        if more:
            enqueue_migration(self.get_migration_module(), cursor_state=cursor_state)
        else:
            self.finish_migration()
            from migrations import migrations_enqueuer
            migrations_enqueuer.enqueue_next_migration()

    def stop_with_error(self, error_msg, exception):
        stacktrace = traceback.format_exc()
        self.dbmigration.error(error_msg, stacktrace)
        logging.error(error_msg)
        raise MigrationException(exception)

    def finish_migration(self):
        self.dbmigration.finish()
        logging.info('end of migration %s on empty namespace' % self.get_name())


class AbstractMigrationTaskOnEmptyNamespace(AbstractMigrationTask):
    def init_cursor(self):
        cursor_state = {'cursor_urlsafe': None}
        return cursor_state

    def get_namespace(self, cursor_state):
        return ''

    def update_cursor_state(self, cursor_state, querycursor, more):
        if more:
            cursor_state['cursor_urlsafe'] = querycursor.urlsafe()
            return True
        else:
            return False

