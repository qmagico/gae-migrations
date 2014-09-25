import migrations
import run_pending_tests
from test_utils import GAETestCase
from my.models import QueDoidura
from google.appengine.api import taskqueue, namespace_manager
import my.migrations_run_twice


class TestRunAllMigrations(GAETestCase):
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

    def test_run_on_all_namespaces(self):
        # Roda as migracoes
        migrations.run_all(my.migrations_run_twice)

        namespace_manager.set_namespace('ns1')
        self.assertEqual(QueDoidura.query().count(), 3)
        qds = QueDoidura.query().order(QueDoidura.v1).fetch()
        self.assertEqual(18, qds[0].v1)
        self.assertEqual(24, qds[1].v1)
        self.assertEqual(30, qds[2].v1)
        namespace_manager.set_namespace('ns2')
        self.assertEqual(QueDoidura.query().count(), 2)
        qds = QueDoidura.query().order(QueDoidura.v1).fetch()
        self.assertEqual(60, qds[0].v1)
        self.assertEqual(66, qds[1].v1)

        # E agora verificamos que as tasks sao executadas novamente

        migrations.run_all(my.migrations_run_twice)

        namespace_manager.set_namespace('ns1')
        self.assertEqual(QueDoidura.query().count(), 3)
        qds = QueDoidura.query().order(QueDoidura.v1).fetch()
        self.assertEqual(18*6, qds[0].v1)
        self.assertEqual(24*6, qds[1].v1)
        self.assertEqual(30*6, qds[2].v1)
        namespace_manager.set_namespace('ns2')
        self.assertEqual(QueDoidura.query().count(), 2)
        qds = QueDoidura.query().order(QueDoidura.v1).fetch()
        self.assertEqual(60*6, qds[0].v1)
        self.assertEqual(66*6, qds[1].v1)

    def test_run_on_one_namespace(self):
        # Roda as migracoes
        migrations.run_all(my.migrations_run_twice, ns='ns1')

        namespace_manager.set_namespace('ns1')
        self.assertEqual(QueDoidura.query().count(), 3)
        qds = QueDoidura.query().order(QueDoidura.v1).fetch()
        self.assertEqual(18, qds[0].v1)
        self.assertEqual(24, qds[1].v1)
        self.assertEqual(30, qds[2].v1)
        namespace_manager.set_namespace('ns2')
        self.assertEqual(QueDoidura.query().count(), 2)
        qds = QueDoidura.query().order(QueDoidura.v1).fetch()
        self.assertEqual(10, qds[0].v1)
        self.assertEqual(11, qds[1].v1)

        migrations.run_all(my.migrations_run_twice, ns='ns2')

        namespace_manager.set_namespace('ns1')
        self.assertEqual(QueDoidura.query().count(), 3)
        qds = QueDoidura.query().order(QueDoidura.v1).fetch()
        self.assertEqual(18, qds[0].v1)
        self.assertEqual(24, qds[1].v1)
        self.assertEqual(30, qds[2].v1)
        namespace_manager.set_namespace('ns2')
        self.assertEqual(QueDoidura.query().count(), 2)
        qds = QueDoidura.query().order(QueDoidura.v1).fetch()
        self.assertEqual(60, qds[0].v1)
        self.assertEqual(66, qds[1].v1)
