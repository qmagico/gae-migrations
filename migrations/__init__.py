#coding:utf-8

import logging
import traceback
import pickle

from google.appengine.api import taskqueue, namespace_manager
from google.appengine.api.taskqueue.taskqueue import TaskRetryOptions
from google.appengine.ext.ndb import Cursor
from google.appengine.ext.db.metadata import Namespace, get_namespaces

from migrations.model import DBMigrationLog

__author__ = 'tony'

NO_RETRY = TaskRetryOptions(task_retry_limit=1)


def enqueue_next_task(tasks):
    migrated_names = DBMigrationLog.last_1000_names_done_or_running()
    for task in tasks:
        if not task.get_migration_name() in migrated_names:
            task.start()
            break

def enqueue_migration(cursor_state={}):
    migration_path = ''
    migration.start(cursor_state)


# não serializar, pegar o self.name e importar dinamicamente

class AbstractMigrationTask():
    def __init__(self):
        self.migration_query = self.get_query()
        self.name = self.get_name()

    def migration_path():
        return NotImplemented

    def fetch(self, cursor_urlsafe, namespace_index):
        query_ns = get_namespaces(self.namespace_index)

        if query_ns != namespace_manager.get_namespace():
            namespace_manager.set_namespace(query_ns)

        cursor = cursor_urlsafe and Cursor(urlsafe=cursor_urlsafe)
        result, cursor, more = self.migration_query().fetch(1000, cursor=cursor)
        return result, cursor.urlsafe(), more


    def start(self, cursor_state):
        cursor_urlsafe = cursor_state.get('cursor_urlsafe', None)
        namespace_index = cursor_state.get('namespace_index', 0)

        entities, cursor, more = self.fetch(cursor_urlsafe, namespace_index)

        for entity in entities:
            try:
                self.migrate_one(entity)
            except Exception, e:
                error_msg = 'error migrating on namespace %s: %s' % (self.namespace, entity.key)
                self.stop_with_error(error_msg, e)
        
        if more:
            task_params = {
                'migration_pickle_object': pickle.dumps(self),
                'cursor_state': {
                    'cursor_urlsafe': cursor_urlsafe,
                    'namespace_index': self.namespace_index
                }
            }

            tasks.enqueue(enqueue_migration, task_params)

        elif self.namespace_index > len(get_namespaces()):
            task_params = {
                migration_pickle_object: pickle.dumps(self),
                cursor_state: {
                    cursor_urlsafe: cursor_urlsafe,
                    namespace_index: self.namespace_index + 1
                }
            }

            tasks.enqueue(enqueue_migration, task_params)

        else:   
            self.finish_migration()
            self.enqueue_next_migration()


    def enqueue_next_migration(self):
        from migrations import migrations_enqueuer
        migrations_enqueuer.enqueue_next_migration_task()

    def stop_with_error(self, error_msg, exception):
        stacktrace = exception.format_exc()
        DBMigrationLog.error(self.name, error_msg, stacktrace)
        logging.error(err)
        raise MigrationException(exception)

    def finish_migration(self):
        DBMigrationLog.finish_migration(self.name)
        logging.info('end of migration %s on empty namespace' % self.name)
        









# class AbstractMigrationTaskOnEmptyNamespace(QMHandler):
    

#     def enqueue_first_task(self):
#         name = self.get_migration_name()
#         description = self.get_migration_description()
#         DBMigration.new_migration(name, description)
#         logging.info('starting migration %s' % name)
#         taskqueue.add(
#             url=router.to_path(self.__class__.migration_task),
#             queue_name=MIGRATIONS_QUEUE,
#             retry_options=NO_RETRY
#         )

#     def migration_task(self, cursor_urlsafe=None):
#         cursor = cursor_urlsafe and Cursor(urlsafe=cursor_urlsafe)
#         namespace_manager.set_namespace('')
#         try:
#             query = self.get_query()
#         except BaseException as ex:
#             stacktrace = traceback.format_exc()
#             err = 'Error obtaining query on empty namespace: %s' % ex
#             logging.error(err)
#             self.stop_with_error(err, stacktrace)
#             raise MigrationException(ex)
#         result, cursor, more = query.fetch_page(1, start_cursor=cursor)
#         if result:
#             entity = result[0]
#             try:
#                 self.migrate_one(entity)
#             except BaseException as ex:
#                 stacktrace = traceback.format_exc()
#                 err = 'error migrating on empty namespace %s: %s' % (entity.key, ex)
#                 logging.error(err)
#                 self.stop_with_error(err, stacktrace)
#                 raise MigrationException(ex)
#             logging.info('ran migration %s on empty namespace id=%s' % (
#                 self.get_migration_name(),
#                 entity.key))
#             if more:
#                 taskqueue.add(
#                     url=router.to_path(self.__class__.migration_task),
#                     params={'cursor_urlsafe': cursor.urlsafe()},
#                     queue_name=MIGRATIONS_QUEUE,
#                     retry_options=NO_RETRY
#                 )
#             else:
#                 self.finish_migration()
#         else:
#             self.finish_migration()

#     def stop_with_error(self, error_msg, stacktrace):
#         name = self.get_migration_name()
#         DBMigration.error(name, error_msg, stacktrace)

#     def finish_migration(self):
#         name = self.get_migration_name()
#         DBMigration.finish_migration(name)
#         logging.info('end of migration %s on empty namespace' % name)
#         from migrations import migrations_enqueuer

#         migrations_enqueuer.enqueue_next_migration_task()


# class AbstractMigrationTask(QMHandler):
#     def enqueue_first_task(self):
#         name = self.get_migration_name()
#         description = self.get_migration_description()
#         DBMigration.new_migration(name, description)
#         logging.info('starting migration %s' % name)
#         taskqueue.add(
#             url=router.to_path(self.__class__.migration_task),
#             queue_name=MIGRATIONS_QUEUE,
#             retry_options=NO_RETRY
#         )

#     def migration_task(self, ns=None, cursor_urlsafe=None, offset_ns=None):
#         if cursor_urlsafe == 'None':
#             cursor_urlsafe = None
#         offset_ns = int(offset_ns) if offset_ns else 0
#         if ns is None:
#             ns, offset_ns = self.current_namespace(offset_ns)
#         if ns is None:
#             return

#         cursor = cursor_urlsafe and Cursor(urlsafe=cursor_urlsafe)
#         namespace_manager.set_namespace(ns)
#         try:
#             query = self.get_query()
#             if not query:
#                 return
#         except BaseException as ex:
#             stacktrace = traceback.format_exc()
#             err = 'Error obtaining query for namespace %s: %s' % (ns, ex)
#             logging.error(err)
#             self.stop_with_error(err, stacktrace)
#             raise MigrationException(ex)
#         result, cursor, more = query.fetch_page(1, start_cursor=cursor)
#         if result:
#             entity = result[0]
#             try:
#                 self.migrate_one(entity)
#             except BaseException as ex:
#                 stacktrace = traceback.format_exc()
#                 err = 'error migrating %s on namespace %s: %s' % (entity.key, ns, ex)
#                 logging.error(err)
#                 self.stop_with_error(err, stacktrace)
#                 raise MigrationException(ex)
#             logging.info('ran migration %s id=%s ns=%s' % (
#                 self.get_migration_name(),
#                 entity.key,
#                 ns))
#             if more:
#                 taskqueue.add(
#                     url=router.to_path(self.__class__.migration_task),
#                     params={'ns': ns, 'cursor_urlsafe': cursor.urlsafe(), 'offset_ns': offset_ns},
#                     queue_name=MIGRATIONS_QUEUE,
#                     retry_options=NO_RETRY
#                 )
#             else:
#                 self.enqueue_next_namespace_or_finish_migration(offset_ns)
#         else:
#             self.enqueue_next_namespace_or_finish_migration(offset_ns)

#     def stop_with_error(self, error_msg, stacktrace):
#         name = self.get_migration_name()
#         DBMigration.error(name, error_msg, stacktrace)

#     def current_namespace(self, offset_ns):
#         ns = Namespace.all().fetch(1, offset_ns)
#         if len(ns) == 0:
#             return None, offset_ns
#         if ns[0].namespace_name != '':
#             return ns[0].namespace_name, offset_ns
#         offset_ns += 1
#         ns = Namespace.all().fetch(1, offset_ns)
#         if len(ns) == 0:
#             return None, offset_ns
#         return ns[0].namespace_name, offset_ns

#     def enqueue_next_namespace_or_finish_migration(self, offset_ns):
#         offset_ns += 1
#         ns = self.current_namespace(offset_ns)[0]
#         if ns:
#             taskqueue.add(
#                 url=router.to_path(self.__class__.migration_task),
#                 params={'ns': ns, 'cursor_urlsafe': None, 'offset_ns': str(offset_ns)},
#                 queue_name=MIGRATIONS_QUEUE,
#                 retry_options=NO_RETRY
#             )
#         else:
#             name = self.get_migration_name()
#             DBMigration.finish_migration(name)
#             logging.info('end of migration %s' % name)
#             from migrations import migrations_enqueuer

#             migrations_enqueuer.enqueue_next_migration_task()
