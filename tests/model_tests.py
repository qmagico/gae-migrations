from migrations.model import AbstractDBTask, RUNNING, DONE, ERROR
from test_utils import GAETestCase


class TestDBMigrationLog(GAETestCase):
    def test_log_new_migration(self):
        name = 'migration_0000_test'
        description = 'just a test'
        AbstractDBTask.find_or_create(name, description)

        migration_log = AbstractDBTask.query().get()
        self.assertEqual(name, migration_log.name)
        self.assertEqual(description, migration_log.description)
        self.assertEqual(RUNNING, migration_log.status)

    def test_log_finish_migration_with_success(self):
        name = 'migration_0000_test'
        description = 'just a test'
        migration = AbstractDBTask.find_or_create(name, description)
        migration.finish()

        migration_log = AbstractDBTask.query().get()
        self.assertEqual(name, migration_log.name)
        self.assertEqual(description, migration_log.description)
        self.assertEqual(DONE, migration_log.status)

    def test_log_finish_migration_with_error(self):
        name = 'migration_0000_test'
        description = 'just a test'
        error_msg = '=('
        stacktrace = 'error'

        migration = AbstractDBTask.find_or_create(name, description)
        migration.error(error_msg, stacktrace)

        migration_log = AbstractDBTask.query().get()
        self.assertEqual(name, migration_log.name)
        self.assertEqual(description, migration_log.description)
        self.assertEqual(error_msg, migration_log.error_msg)
        self.assertEqual(stacktrace, migration_log.stacktrace)
        self.assertEqual(ERROR, migration_log.status)

    def test_already_executed_migrations(self):
        name = 'migration_0000_test'
        description = 'just a test'
        migration = AbstractDBTask.find_or_create(name, description)
        migration.finish()

        name2 = 'migration_0001_test'
        description2 = 'just a test'
        AbstractDBTask.find_or_create(name2, description2)

        expected = [name, name2]
        to_run = AbstractDBTask.last_1000_names_done_or_running()

        self.assertItemsEqual(expected, to_run)
