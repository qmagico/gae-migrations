import migrations
from migrations import task_enqueuer
from migrations.model import DBMigration
from test_utils import GAETestCase
from my.migrations import migration_0001_one
from my.migrations import migration_0002_two
from my.models import QueDoidura
from google.appengine.api import taskqueue, namespace_manager
import my


def sync_task_add(*args, **kwargs):
    task_enqueuer.execute(kwargs['params']['funcpath'], kwargs['params']['kwargs_json'])


class TestRunMigrations(GAETestCase):
    def setUp(self):
        GAETestCase.setUp(self)
        namespace_manager.set_namespace('ns1')
        QueDoidura(v1=3).put()
        QueDoidura(v1=4).put()
        QueDoidura(v1=5).put()
        namespace_manager.set_namespace('ns2')
        QueDoidura(v1=30).put()
        QueDoidura(v1=40).put()
        self._old_task_add = taskqueue.add
        taskqueue.add = sync_task_add
        self._old_ns = namespace_manager.get_namespace()

    def tearDown(self):
        GAETestCase.tearDown(self)
        taskqueue.add = self._old_task_add
        namespace_manager.set_namespace(self._old_ns)

    def test_run_migrations(self):
        # Roda as migracoes
        first_migration = migrations.run_pending(my.migrations)
        self.assertEqual('migration_0001_one', first_migration)
        count = 0
        v1sum = 0
        namespace_manager.set_namespace('ns1')
        for qd in QueDoidura.query():
            self.assertEqual(qd.v2, 2 * qd.v1)
            self.assertEqual(qd.v3, 3 * qd.v1)
            count += 1
            v1sum += qd.v1
        namespace_manager.set_namespace('ns2')
        for qd in QueDoidura.query():
            self.assertEqual(qd.v2, 2 * qd.v1)
            self.assertEqual(qd.v3, 3 * qd.v1)
            count += 1
            v1sum += qd.v1
        self.assertEqual(5, count)
        self.assertEqual(82, v1sum)

        # E depois nao roda mais nada
        first_migration = migrations.run_pending(my.migrations)
        self.assertIsNone(first_migration)

        # E os DBMigrations estao ok
        namespace_manager.set_namespace('')
        dbmigrations = []
        for dbmigration in DBMigration.query(DBMigration.module == 'my.migrations'):
            self.assertTrue(dbmigration.status == 'DONE')
            dbmigrations.append(dbmigration.name)
        self.assertEqual(2, len(dbmigrations))
        self.assertTrue('migration_0001_one' in dbmigrations)
        self.assertTrue('migration_0002_two' in dbmigrations)
