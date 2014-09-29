import time
from google.appengine.api import namespace_manager
from google.appengine.ext import ndb

RUNNING = 'RUNNING'
DONE = 'DONE'
ERROR = 'ERROR'


class DBMigration(ndb.Model):
    name = ndb.StringProperty(required=True)
    description = ndb.StringProperty(required=True)
    module = ndb.StringProperty(required=True)
    status = ndb.StringProperty(required=True, choices=[RUNNING, DONE, ERROR])
    creation = ndb.DateTimeProperty(auto_now_add=True)
    last_update = ndb.DateTimeProperty(auto_now=True)
    error_msg = ndb.TextProperty()
    stacktrace = ndb.TextProperty()

    @classmethod
    def find_or_create(cls, module, name, description):
        original_ns = namespace_manager.get_namespace()
        namespace_manager.set_namespace('')
        migration = cls.query(cls.module == module, cls.name == name).get()
        if not migration:
            migration = cls()
            migration.module = module
            migration.name = name
        migration.description = description
        migration.status = RUNNING
        migration.put()
        namespace_manager.set_namespace(original_ns)
        return migration

    @classmethod
    def find_by_status(cls, module, status):
        original_ns = namespace_manager.get_namespace()
        namespace_manager.set_namespace('')
        migrations = cls.query(cls.module == module, cls.status == status).fetch()
        namespace_manager.set_namespace(original_ns)
        return migrations

    @classmethod
    def last_1000_names_done_or_running(cls, module):
        original_ns = namespace_manager.get_namespace()
        namespace_manager.set_namespace('')
        migrations = cls.query(cls.module == module, cls.status.IN([DONE, RUNNING])).order(-cls.name).fetch(1000)
        names = []
        for migration in migrations:
            names.append(migration.name)
        namespace_manager.set_namespace(original_ns)
        return names

    @classmethod
    def delete_all(cls, module):
        original_ns = namespace_manager.get_namespace()
        namespace_manager.set_namespace('')
        for db_data_checker in cls.query(DBMigration.module == module):
            db_data_checker.key.delete()
        namespace_manager.set_namespace(original_ns)

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


# class DBDataChecker(BDMigration):
#
#     number_of_inconsistencies = ndb.IntegerProperty()
#
#     @classmethod
#     def get_module(cls):
#         return settings.DATA_CHECKER_MODULE
#
#     @classmethod
#     def delete_all(cls):
#         original_ns = namespace_manager.get_namespace()
#         namespace_manager.set_namespace('')
#         for db_data_checker in cls.query():
#             db_data_checker.key.delete()
#
#         namespace_manager.set_namespace(original_ns)


class DBInconsistency(ndb.Model):

    task_key = ndb.KeyProperty()
    entities = ndb.KeyProperty(repeated=True)

    def __init__(self, task_key, entities):
        super(DBInconsistency, self).__init__(namespace='')
        self.task_key = task_key
        self.entities = entities







# class DataCheckerMigration(AbstractMigrationTask):
#
#     @classmethod
#     def get_db_class(cls):
#         return DBDataChecker
#
#     def inconsistency_found(self, entities):
#         dbmigration = DBDataChecker.find_or_create(self.get_name(), self.get_description())
#         dbmigration.number_of_inconsistencies += 1
#         dbmigration.put()
#
#         inconsistency = DBInconsistency(dbmigration.key, entities)
#         inconsistency.put()
#
#
