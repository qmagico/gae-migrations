import importlib
import pkgutil
from migrations import task_enqueuer
from migrations.model import DBMigration
from types import ModuleType
from google.appengine.api import namespace_manager
from google.appengine.api.taskqueue.taskqueue import TaskRetryOptions
from google.appengine.ext.ndb import Cursor
from google.appengine.ext.db.metadata import get_namespaces
from migrations import task_enqueuer
import settings
import logging
import traceback


NO_RETRY = TaskRetryOptions(task_retry_limit=0)


def run_pending(module):
    if isinstance(module, ModuleType):
        module_name = module.__name__
    elif isinstance(module, basestring):
        module_name = module
        module = importlib.import_module(module_name)
    else:
        raise BaseException('Tah de brincation with me, cara?')
    migrated_names = DBMigration.last_1000_names_done_or_running(module=module_name)
    for candidate_migration_name in get_all_migration_names(module):
        if not candidate_migration_name in migrated_names:
            task_enqueuer.enqueue(task_start_migration,
                                  queue=settings.MIGRATIONS_QUEUE,
                                  module_name=module_name,
                                  migration_name=candidate_migration_name,
                                  cursor_state=None,
                                  task_retry_options=NO_RETRY)
            return candidate_migration_name


def get_all_migration_names(module):
    all_migration_names = []
    for subm, subn, is_module in pkgutil.iter_modules(module.__path__):
        all_migration_names.append(subn)
    all_migration_names = sorted(all_migration_names)
    return all_migration_names


def task_start_migration(module_name, migration_name, cursor_state=None):
    module = importlib.import_module(module_name)
    migration_module = importlib.import_module(module_name + '.' + migration_name)
    migrator = Migrator(module, migration_module)
    migrator.start(cursor_state)


class Migrator():
    def __init__(self, module, migration_module):
        self.module = module
        self.migration_module = migration_module
        self.module_name = module.__name__
        self.migration_name = migration_module.__name__.split('.')[-1]
        self.migration_description = getattr(migration_module, 'DESCRIPTION', '')
        self.migrations_per_task = getattr(migration_module, 'MIGRATIONS_PER_TASK', 1000)

    def init_cursor(self):
        cursor_state = {
            'namespaces': [n for n in get_namespaces() if n],
            'namespace_index': 0,
            'cursor_urlsafe': None,
        }
        return cursor_state

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
            query = self.migration_module.get_query()
        except Exception, e:
            error_msg = 'error getting query'
            self.stop_with_error(error_msg, e)

        size = self.migrations_per_task

        result, cursor, more = query.fetch_page(size, start_cursor=cursor)
        more = self.update_cursor_state(cursor_state, cursor, more)
        return result, cursor_state, more

    def start(self, cursor_state):
        self.dbmigration = DBMigration.find_or_create(self.module_name, self.migration_name, self.migration_description)

        entities, cursor_state, more = self.fetch(cursor_state)

        for entity in entities:
            try:
                logging.info('migrating %s...' % entity.key)
                self.migration_module.migrate_one(entity)
            except Exception, e:
                error_msg = 'error migrating on namespace %s: %s' % (namespace_manager.get_namespace(), entity.key)
                self.stop_with_error(error_msg, e)
        logging.info('Total entities migrated: %s' % len(entities))

        if more:
            task_enqueuer.enqueue(task_start_migration,
                                  queue=settings.MIGRATIONS_QUEUE,
                                  module_name=self.module_name,
                                  migration_name=self.migration_name,
                                  cursor_state=cursor_state,
                                  task_retry_options=NO_RETRY)
        else:
            self.finish_migration()
            run_pending(self.module)

    def stop_with_error(self, error_msg, exception):
        stacktrace = traceback.format_exc()
        self.dbmigration.error(error_msg, stacktrace)
        logging.error(error_msg)
        raise MigrationException(exception, self.dbmigration)

    def finish_migration(self):
        self.dbmigration.finish()
        logging.info('end of migration %s on namespace %s' % (self.migration_name, namespace_manager.get_namespace()))


class MigrationException(BaseException):
    def __init__(self, cause, dbmigration):
        BaseException.__init__(self, cause.message)
        self.dbmigration = dbmigration
        self.cause = cause




#
#
# def start_db_checker():
#     DBDataChecker.delete_all()
#     enqueue_next_task(DBDataChecker)
#
#
# def enqueue_next_single_migration():
#     return enqueue_next_task(DBSingleMigration)
