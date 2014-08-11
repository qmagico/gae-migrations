import mock
from mommygae import mommy

from google.appengine.api import namespace_manager
from google.appengine.ext import ndb
from migrations.model import DBMigrationLog, AbstractMigrationTask, AbstractMigrationTaskOnEmptyNamespace, RUNNING, DONE, ERROR
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
    def __init__(self, name='', *args, **kwargs):
        self.name = name
        self.executed = False
        AbstractMigrationTask.__init__(self, *args, **kwargs)

    def start(self, cursor_state={}):
        self.executed = True
        AbstractMigrationTask.start(self, cursor_state)

    def get_name(self):
        return self.name

    def get_query(self):
        return ModelToMigrate.query()

    def migrate_one(self, entity):
        entity.migrated = True
        entity.put()

class MigrationsMockEmptyNamespace(MigrationsMock):
    def __init__(self):
        MigrationsMock.__init__(self, empty_namespace=True)


MyTask = MigrationsMock

class TestDBMigrationLog(GAETestCase):
    def test_log_new_migration(self):
        name = 'migration_0000_test'
        description = 'just a test'
        DBMigrationLog.new_migration(name, description)

        migration_log = DBMigrationLog.query().get()
        self.assertEqual(name, migration_log.name)
        self.assertEqual(description, migration_log.description)
        self.assertEqual(RUNNING, migration_log.status)

    def test_log_finish_migration_with_success(self):
        name = 'migration_0000_test'
        description = 'just a test'
        DBMigrationLog.new_migration(name, description)
        DBMigrationLog.finish_migration(name)

        migration_log = DBMigrationLog.query().get()
        self.assertEqual(name, migration_log.name)
        self.assertEqual(description, migration_log.description)
        self.assertEqual(DONE, migration_log.status)

    def test_log_finish_migration_with_error(self):
        name = 'migration_0000_test'
        description = 'just a test'
        error_msg = '=('
        stacktrace = 'error'

        DBMigrationLog.new_migration(name, description)
        DBMigrationLog.error(name, error_msg, stacktrace)

        migration_log = DBMigrationLog.query().get()
        self.assertEqual(name, migration_log.name)
        self.assertEqual(description, migration_log.description)
        self.assertEqual(error_msg, migration_log.error_msg)
        self.assertEqual(stacktrace, migration_log.stacktrace)
        self.assertEqual(ERROR, migration_log.status)

    def test_already_executed_migrations(self):
        name = 'migration_0000_test'
        description = 'just a test'
        DBMigrationLog.new_migration(name, description)
        DBMigrationLog.finish_migration(name)

        name2 = 'migration_0001_test'
        description2 = 'just a test'
        DBMigrationLog.new_migration(name2, description2)

        expected = [name, name2]
        to_run = DBMigrationLog.last_1000_names_done_or_running()

        self.assertItemsEqual(expected, to_run)


class TestAbstrackMigration(GAETestCase):
    def test_fetch_query_on_selected_namespace(self):
        namespace_manager.set_namespace("namespace1")
        for i in range(5):
            mommy.save_one(ModelToMigrate)

        namespace_manager.set_namespace("namespace2")
        for i in range(5):
            mommy.save_one(ModelToMigrate)

        migration = MigrationsMock()
        result, cursor, more = migration.fetch(None, "namespace1", size=3)

        self.assertEqual(3, len(result))
        self.assertEqual(ndb.Cursor, type(cursor))
        self.assertTrue(more)

        result, cursor, more = migration.fetch(cursor.urlsafe(), "namespace1", size=3)
        self.assertEqual(2, len(result))
        self.assertEqual(ndb.Cursor, type(cursor))
        self.assertFalse(more)

        result, cursor, more = migration.fetch(None, "namespace2", size=3)
        self.assertEqual(3, len(result))
        self.assertEqual(ndb.Cursor, type(cursor))
        self.assertTrue(more)

        result, cursor, more = migration.fetch(cursor.urlsafe(), "namespace2", size=3)
        self.assertEqual(2, len(result))
        self.assertEqual(ndb.Cursor, type(cursor))
        self.assertFalse(more)

    def test_start_migration_with_less_than_1000(self):
        migration = MigrationsMock()
        cursor_state = {}

        for i in range(5):
            mommy.save_one(ModelToMigrate)

        migration = MigrationsMock()
        migration.start(cursor_state)

        self.assertEqual(5, ModelToMigrate.count_migrated())

    @mock.patch('migrations.task_enqueuer.enqueue', new_callable=EnqueuerMock)
    def test_start_migration_with_more_entities(self, mock_enqueue):
        migration = MigrationsMock()
        cursor_state = {
            'size': 3
        }

        for i in range(5):
            mommy.save_one(ModelToMigrate)

        migration = MigrationsMock()
        migration.start(cursor_state)

        self.assertEqual(5, ModelToMigrate.count_migrated())

    @mock.patch('migrations.task_enqueuer.enqueue', new_callable=EnqueuerMock)
    def test_start_migration_with_more_namespaces(self, mock_enqueue):
        namespace_manager.set_namespace("namespace1")
        for i in range(5):
            mommy.save_one(ModelToMigrate)

        namespace_manager.set_namespace("namespace2")
        for i in range(5):
            mommy.save_one(ModelToMigrate)

        migration = MigrationsMock()
        cursor_state = {
            'size': 3,
            'namespace_index': 0
        }

        migration.start(cursor_state)
        namespace_manager.set_namespace("namespace1")
        self.assertEqual(5, ModelToMigrate.count_migrated())
        
        namespace_manager.set_namespace("namespace2")
        self.assertEqual(5, ModelToMigrate.count_migrated())

    @mock.patch('migrations.migrations_enqueuer.enqueue_next_migration')
    def test_start_next_migration_after_finish(self, enqueue_next_mock):
        for i in range(5):
            mommy.save_one(ModelToMigrate)

        migration = MigrationsMock()

        migration.start({})
        self.assertEqual(5, ModelToMigrate.count_migrated())

        enqueue_next_mock.assert_any_call()

class TestAbstractMigrationTaskOnEmptyNamespace(GAETestCase):
    @mock.patch('migrations.task_enqueuer.enqueue', new_callable=EnqueuerMock)
    def test_run_only_on_empty_namespace(self, mock_enqueue):
        namespace_manager.set_namespace("")
        for i in range(5):
            mommy.save_one(ModelToMigrate)

        namespace_manager.set_namespace("namespace1")
        for i in range(5):
            mommy.save_one(ModelToMigrate)


        migration = MigrationsMockEmptyNamespace()
        migration.start({})

        namespace_manager.set_namespace("")
        self.assertEqual(5, ModelToMigrate.count_migrated())

        namespace_manager.set_namespace("namespace1")
        self.assertEqual(0, ModelToMigrate.count_migrated())
