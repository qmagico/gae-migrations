import migrations
from test_utils import GAETestCase
import my.migrations
from my.migrations import migration_0002_two


class TestListMigrations(GAETestCase):
    def test_list_migrations(self):
        allmigration_names = migrations.get_all_migration_names(my.migrations)
        self.assertEqual(3, len(allmigration_names))
        self.assertEqual('migration_0001_one', allmigration_names[0])
        self.assertEqual('migration_0002_two', allmigration_names[1])
        self.assertEqual('migration_0003_three', allmigration_names[2])
