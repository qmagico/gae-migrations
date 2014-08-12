import mock
from mommygae import mommy

from google.appengine.api import namespace_manager
from google.appengine.ext import ndb
from migrations.model import DBMigration, AbstractMigrationTask, AbstractMigrationTaskOnEmptyNamespace, RUNNING, DONE, ERROR
from test_utils import GAETestCase



class ModelToMigrate(ndb.Model):
    migrated = ndb.BooleanProperty(default=False)

    @classmethod
    def count_migrated(cls):
        return cls.query(cls.migrated == True).count()
 

class EnqueuerMock():
    def __call__(self, method, task_params):
        method(task_params)


class MigrationsMock(AbstractMigrationTask):
    def __init__(self, name=''):
        self.name = name
        self.executed = False

    def start(self, cursor_state={}):
        self.executed = True
        AbstractMigrationTask.start(self, cursor_state)

    def get_name(self):
        return self.name

    def get_description(self):
        return 'migracao mocada'

    def get_query(self):
        return ModelToMigrate.query()

    def migrate_one(self, entity):
        entity.migrated = True
        entity.put()

class MigrationsMockEmptyNamespace(MigrationsMock):
    def __init__(self):
        MigrationsMock.__init__(self)


MyTask = MigrationsMock

class TestDBMigrationLog(GAETestCase):
    def test_log_new_migration(self):
        name = 'migration_0000_test'
        description = 'just a test'
        DBMigration.find_or_create(name, description)

        migration_log = DBMigration.query().get()
        self.assertEqual(name, migration_log.name)
        self.assertEqual(description, migration_log.description)
        self.assertEqual(RUNNING, migration_log.status)

    def test_log_finish_migration_with_success(self):
        name = 'migration_0000_test'
        description = 'just a test'
        migration = DBMigration.find_or_create(name, description)
        migration.finish()

        migration_log = DBMigration.query().get()
        self.assertEqual(name, migration_log.name)
        self.assertEqual(description, migration_log.description)
        self.assertEqual(DONE, migration_log.status)

    def test_log_finish_migration_with_error(self):
        name = 'migration_0000_test'
        description = 'just a test'
        error_msg = '=('
        stacktrace = 'error'

        migration = DBMigration.find_or_create(name, description)
        migration.error(error_msg, stacktrace)

        migration_log = DBMigration.query().get()
        self.assertEqual(name, migration_log.name)
        self.assertEqual(description, migration_log.description)
        self.assertEqual(error_msg, migration_log.error_msg)
        self.assertEqual(stacktrace, migration_log.stacktrace)
        self.assertEqual(ERROR, migration_log.status)

    def test_already_executed_migrations(self):
        name = 'migration_0000_test'
        description = 'just a test'
        migration = DBMigration.find_or_create(name, description)
        migration.finish()

        name2 = 'migration_0001_test'
        description2 = 'just a test'
        DBMigration.find_or_create(name2, description2)

        expected = [name, name2]
        to_run = DBMigration.last_1000_names_done_or_running()

        self.assertItemsEqual(expected, to_run)
