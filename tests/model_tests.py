import mommy

from gaetest import GAETestCase
from migrations.model import DBMigrationLog, RUNNING, DONE, ERROR

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

        expected = list(sorted([name, name2]))
        to_run = DBMigrationLog.last_1000_names_done_or_running()
        to_run.sort()

        self.assertListEqual(expected, to_run)
