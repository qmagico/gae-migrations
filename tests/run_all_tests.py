import migrations
from migrations.model import DBMigration
import run_pending_tests
from test_utils import GAETestCase
from my.models import QueDoidura
from google.appengine.api import taskqueue, namespace_manager
import my.migrations_data_checker


class TestRunDataCheckMigration(GAETestCase):
    def setUp(self):
        GAETestCase.setUp(self)
        self._old_ns = namespace_manager.get_namespace()

        namespace_manager.set_namespace('ns1')
        QueDoidura(v1=3).put()
        QueDoidura(v1=4).put()
        QueDoidura(v1=5).put()

        namespace_manager.set_namespace('ns2')
        QueDoidura(v1=10).put()
        QueDoidura(v1=11).put()

        self._old_task_add = taskqueue.add
        taskqueue.add = run_pending_tests.sync_task_add

    def tearDown(self):
        GAETestCase.tearDown(self)
        taskqueue.add = self._old_task_add
        namespace_manager.set_namespace(self._old_ns)

    def test_run_migrations(self):
        # Roda as migracoes
        migrations.run_all(my.migrations_data_checker)

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

        migrations.run_all(my.migrations_data_checker)

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
        self.assertEqual(DBMigration.query().count(), 0)
