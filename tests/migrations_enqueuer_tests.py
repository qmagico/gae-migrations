from migrations import migrations_enqueuer

from test_utils import GAETestCase
from model_tests import MigrationsMock


class TestStartMigrations(GAETestCase):
    def test_enqueue_first_migration(self):
        migrations_list = [MigrationsMock('migration_0000_mocked_migration')]
        migrations_enqueuer.enqueue_next_migration(migrations_list)
        self.assertTrue(migrations_list[0].executed)

    def test_dont_migrate_until_last_was_done(self):
        migrations_list = [MigrationsMock('migration_0000_mocked_migration'),
                           MigrationsMock('migration_0010_mocked_migration')]

        migrations_enqueuer.enqueue_next_migration(migrations_list)
        self.assertTrue(migrations_list[0].executed)
        self.assertFalse(migrations_list[1].executed)
