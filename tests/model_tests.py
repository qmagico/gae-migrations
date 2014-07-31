import mommy

from google.appengine.api import namespace_manager
from test_utils import GAETestCase
from migrations.model import DBMigrationLog, AbstractMigrationTask, RUNNING, DONE, ERROR


class MigrationsMock(AbstractMigrationTask):
    def __init__(self, name=''):
        self.name = name
        self.executed = False
        self.migrate_entities = 0
        AbstractMigrationTask.__init__(self)

    def start(self, cursor_state={}, testing_method=False):
        self.executed = True
        if testing_method:
            AbstractMigrationTask.start(self, cursor_state)

    def get_name(self):
        return self.name

    def get_query(self):
        return DBMigrationLog.query()

    def migrate_one(self, *args):
        self.migrate_entities += 1


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
    def test_execute_query_on_selected_namespace(self):
        namespace_manager.set_namespace("namespace1")
        for i in range(5):
            mommy.save_one(DBMigrationLog)

        namespace_manager.set_namespace("namespace2")
        for i in range(5):
            mommy.save_one(DBMigrationLog)

        migration = MigrationsMock()
        result, cursor_urlsafe, more = migration.fetch(None, 0, size=3)

        self.assertEqual(3, len(result))
        self.assertEqual(str, type(cursor_urlsafe))
        self.assertTrue(more)

        result, cursor_urlsafe, more = migration.fetch(cursor_urlsafe, 0, size=3)
        self.assertEqual(2, len(result))
        self.assertEqual(str, type(cursor_urlsafe))
        self.assertFalse(more)

        result, cursor_urlsafe, more = migration.fetch(None, 1, size=3)
        self.assertEqual(3, len(result))
        self.assertEqual(str, type(cursor_urlsafe))
        self.assertTrue(more)

        result, cursor_urlsafe, more = migration.fetch(cursor_urlsafe, 0, size=3)
        self.assertEqual(2, len(result))
        self.assertEqual(str, type(cursor_urlsafe))
        self.assertFalse(more)

    def test_start_migration_with_less_than_1000(self):
        migration = MigrationsMock()
        cursor_state = {}

        for i in range(5):
            mommy.save_one(DBMigrationLog)

        migration = MigrationsMock()
        migration.start(cursor_state, testing_method=True)

        self.assertEqual(5, migration.migrate_entities)

    def test_start_migration_with_more_entities(self):
        migration = MigrationsMock()
        cursor_state = {
            'size': 3
        }

        for i in range(5):
            mommy.save_one(DBMigrationLog)

        migration = MigrationsMock()
        migration.start(cursor_state, testing_method=True)

        self.assertEqual(5, migration.migrate_entities)

    def test_start_migration_with_more_namespaces(self):
        namespace_manager.set_namespace("namespace1")
        for i in range(5):
            mommy.save_one(DBMigrationLog)

        namespace_manager.set_namespace("namespace2")
        for i in range(5):
            mommy.save_one(DBMigrationLog)

        migration = MigrationsMock()
        cursor_state = {
            'size': 3,
            'namespace_index': 0
        }

        migration = MigrationsMock()
        migration.start(cursor_state, testing_method=True)

        self.assertEqual(5, migration.migrate_entities)
