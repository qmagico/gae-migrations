import migrations
from migrations import task_enqueuer
from test_utils import GAETestCase
import settings
import my.migrations
from my.migrations import migration_0002_two
from my.models import QueDoidura
from google.appengine.api import taskqueue, namespace_manager


class TestListMigrations(GAETestCase):
    def test_list_migrations(self):
        allmigration_names = migrations.get_all_migration_names(my.migrations)
        self.assertEqual(2, len(allmigration_names))
        self.assertEqual('migration_0001_one', allmigration_names[0])
        self.assertEqual('migration_0002_two', allmigration_names[1])




class TestCheckInconsistencyMigration(GAETestCase):
    def setUp(self):
        GAETestCase.setUp(self)
        self._old_DATA_CHECKER_MODULE = settings.MIGRATIONS_MODULE
        settings.DATA_CHECKER_MODULE = 'my.migrations_data_checker'
        self._old_ns = namespace_manager.get_namespace()

        namespace_manager.set_namespace('ns1')
        QueDoidura(v1=3).put()
        QueDoidura(v1=4).put()
        QueDoidura(v1=5).put()

        namespace_manager.set_namespace('ns2')
        QueDoidura(v1=10).put()
        QueDoidura(v1=11).put()

        self._old_task_add = taskqueue.add
        taskqueue.add = sync_task_add

    def tearDown(self):
        GAETestCase.tearDown(self)
        settings.MIGRATIONS_MODULE = self._old_DATA_CHECKER_MODULE
        taskqueue.add = self._old_task_add
        namespace_manager.set_namespace(self._old_ns)

    def test_run_migrations(self):
        # Roda as migracoes
        migrations_enqueuer.start_db_checker()

        namespace_manager.set_namespace('ns1')
        self.assertEqual(QueDoidura.query().count(), 3)
        v1sum = 0
        for qd in QueDoidura.query():
            self.assertEqual(qd.v2, 2 * qd.v1)
            self.assertEqual(qd.v3, 1)
            v1sum += qd.v1
        namespace_manager.set_namespace('ns2')
        self.assertEqual(QueDoidura.query().count(), 2)
        for qd in QueDoidura.query():
            self.assertEqual(qd.v2, 2 * qd.v1)
            self.assertEqual(qd.v3, 1)
            v1sum += qd.v1
        self.assertEqual(33, v1sum)

        # E agora verificamos que as tasks sao executadas novamente

        migrations_enqueuer.start_db_checker()

        namespace_manager.set_namespace('ns1')
        self.assertEqual(QueDoidura.query().count(), 3)
        v1sum = 0
        for qd in QueDoidura.query():
            self.assertEqual(qd.v2, 2 * qd.v1)
            self.assertEqual(qd.v3, 2)
            v1sum += qd.v1
        namespace_manager.set_namespace('ns2')
        self.assertEqual(QueDoidura.query().count(), 2)
        for qd in QueDoidura.query():
            self.assertEqual(qd.v2, 2 * qd.v1)
            self.assertEqual(qd.v3, 2)
            v1sum += qd.v1
        self.assertEqual(33, v1sum)

        # self.assertIsNone(first_migration)

        # E os DBMigrations estao ok
        self.assertEqual(DBSingleMigration.query().count(), 0)
