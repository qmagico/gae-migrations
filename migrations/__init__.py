import importlib
import pkgutil
from migrations import task_enqueuer
from migrations.model import DBMigration, RUNNING
from types import ModuleType
from google.appengine.api import namespace_manager
from google.appengine.api.taskqueue.taskqueue import TaskRetryOptions
from google.appengine.ext.ndb import Cursor
from google.appengine.ext.db.metadata import get_namespaces
import settings
import logging
import traceback


NO_RETRY = TaskRetryOptions(task_retry_limit=0)


def run_pending(module):
    return _run_pending(module)


def run_all(module, ns=None):
    module, module_name = _module_and_name(module)
    _throw_if_already_running(module_name)
    DBMigration.delete_all(module_name)
    return _run_pending(module, ns)


def _module_and_name(module):
    if isinstance(module, ModuleType):
        module_name = module.__name__
    elif isinstance(module, basestring):
        module_name = module
        module = importlib.import_module(module_name)
    else:
        raise BaseException('Tah de brincation with me, cara?')
    return module, module_name


def _run_pending(module, ns=None):
    module, module_name = _module_and_name(module)
    _throw_if_already_running(module_name)
    migrated_names = DBMigration.last_1000_names_done_or_running(module=module_name)
    for candidate_migration_name in get_all_migration_names(module):
        if not candidate_migration_name in migrated_names:
            task_enqueuer.enqueue(task_start_migration,
                                  queue=settings.MIGRATIONS_QUEUE,
                                  module_name=module_name,
                                  migration_name=candidate_migration_name,
                                  cursor_state=None,
                                  ns=ns,
                                  task_retry_options=NO_RETRY)
            return candidate_migration_name


def _throw_if_already_running(module_name):
    migrations = DBMigration.find_by_status(module_name, RUNNING)
    if migrations:
        raise BaseException('Cannot start migrations on module %s because [%s] is RUNNING' % (
            module_name, migrations[0].name))


def get_all_migration_names(module):
    if isinstance(module, basestring):
        module = importlib.import_module(module)
    all_migration_names = []
    for subm, subn, is_module in pkgutil.iter_modules(module.__path__):
        all_migration_names.append(subn)
    all_migration_names = sorted(all_migration_names)
    return all_migration_names


def task_start_migration(module_name, migration_name, cursor_state=None, ns=None):
    module = importlib.import_module(module_name)
    migration_module = importlib.import_module(module_name + '.' + migration_name)
    restrict_ns = getattr(migration_module, 'RESTRICT_NAMESPACE', None)
    if ns is not None and restrict_ns is not None and ns != restrict_ns:
        raise Exception('Impossivel executar migracao %s. ns=%s / restrict_ns=%s' % (migration_name, ns, restrict_ns))
    if restrict_ns is None:
        restrict_ns = ns
    if restrict_ns is None:
        migrator = Migrator(module, migration_module)
    else:
        migrator = MigratorOnOneNamespace(module, migration_module, restrict_ns)
    migrator.start(cursor_state)


class MigrationException(BaseException):
    def __init__(self, cause, dbmigration):
        BaseException.__init__(self, cause.message)
        self.dbmigration = dbmigration
        self.cause = cause


class Migrator(object):
    def __init__(self, module, migration_module):
        self.module = module
        self.migration_module = migration_module
        self.module_name = module.__name__
        self.migration_name = migration_module.__name__.split('.')[-1]
        self.migration_description = getattr(migration_module, 'DESCRIPTION', '')
        self.migrations_per_task = getattr(migration_module, 'MIGRATIONS_PER_TASK', 1000)
        self.restrict_ns = None
        self.has_query = hasattr(self.migration_module, 'get_query')
        self.has_migrate = hasattr(self.migration_module, 'migrate')
        self.has_migrate_one = hasattr(self.migration_module, 'migrate_one')
        self.has_migrate_many = hasattr(self.migration_module, 'migrate_many')

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

    def _run(self, cursor_state):
        if not cursor_state:
            cursor_state = self.init_cursor()
        namespace = self.get_namespace(cursor_state)
        if namespace != namespace_manager.get_namespace():
            namespace_manager.set_namespace(namespace)
        more = False
        if self.has_migrate:
            self.migration_module.migrate()
            more = self.update_cursor_state(cursor_state, None, False)
        elif self.has_query:
            entities, cursor_state, more = self.fetch(cursor_state)
            if self.has_migrate_one:
                for entity in entities:
                    logging.info('migrating %s...' % entity.key)
                    self.migration_module.migrate_one(entity)
            elif self.has_migrate_many:
                logging.info('migrating %s entities...' % len(entities))
                self.migration_module.migrate_many(entities)
            else:
                raise BaseException('Migracao nao define os metodos necessarios!')
            logging.info('Total entities migrated: %s' % len(entities))
        else:
            raise BaseException('Migracao nao define os metodos necessarios!')
        return cursor_state, more

    def start(self, cursor_state):
        self.dbmigration = DBMigration.find_or_create(self.module_name, self.migration_name, self.migration_description)

        try:
            cursor_state, more = self._run(cursor_state)
            if more:
                task_enqueuer.enqueue(task_start_migration,
                                      queue=settings.MIGRATIONS_QUEUE,
                                      module_name=self.module_name,
                                      migration_name=self.migration_name,
                                      cursor_state=cursor_state,
                                      ns=self.restrict_ns,
                                      task_retry_options=NO_RETRY)
            else:
                self.finish_migration()
                _run_pending(self.module, self.restrict_ns)
        except Exception, e:
            error_msg = 'error migrating on namespace %s' % namespace_manager.get_namespace()
            self.stop_with_error(error_msg, e)

    def stop_with_error(self, error_msg, exception):
        stacktrace = traceback.format_exc()
        self.dbmigration.error(error_msg, stacktrace)
        logging.error(error_msg)
        raise MigrationException(exception, self.dbmigration)

    def finish_migration(self):
        self.dbmigration.finish()
        logging.info('end of migration %s on namespace %s' % (self.migration_name, namespace_manager.get_namespace()))


class MigratorOnOneNamespace(Migrator):
    def __init__(self, module, migration_module, restrict_ns):
        super(MigratorOnOneNamespace, self).__init__(module, migration_module)
        self.restrict_ns = restrict_ns

    def init_cursor(self):
        cursor_state = {'cursor_urlsafe': None}
        return cursor_state

    def get_namespace(self, cursor_state):
        return self.restrict_ns

    def update_cursor_state(self, cursor_state, querycursor, more):
        if more:
            cursor_state['cursor_urlsafe'] = querycursor.urlsafe()
            return True
        else:
            return False
