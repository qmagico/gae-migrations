import migrations
from migrations.model import DBMigration
import run_pending_tests
from test_utils import GAETestCase
from my.models import QueDoidura
from google.appengine.api import taskqueue, namespace_manager
import my.migrations_run_twice
import json


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


    def test_update_json_data(self):
        # Roda as migracoes
        migrations.run_all(my.migrations)
        namespace_manager.set_namespace('')
        dbmigration = DBMigration.query(DBMigration.module == 'my.migrations', DBMigration.status == 'DONE',
                          DBMigration.description == 'multiplica por 2').get()
        dbmig_json_data = json.loads(dbmigration.json_data)
        self.assertIn('v1_for_namespace', dbmig_json_data)
        self.assertIn('ns1', dbmig_json_data['v1_for_namespace'])
        self.assertIn(3, dbmig_json_data['v1_for_namespace']['ns1'])
        self.assertIn(4, dbmig_json_data['v1_for_namespace']['ns1'])
        self.assertIn(5, dbmig_json_data['v1_for_namespace']['ns1'])
        self.assertIn('ns2', dbmig_json_data['v1_for_namespace'])
        self.assertIn(10, dbmig_json_data['v1_for_namespace']['ns2'])
        self.assertIn(11, dbmig_json_data['v1_for_namespace']['ns2'])


    def test_cannot_start_if_something_is_running(self):
        namespace_manager.set_namespace('')
        runningmigration = DBMigration(name='bla', description='x', module='my.migrations_run_twice', status='RUNNING')
        runningmigration.put()
        with self.assertRaises(BaseException) as ex:
            migrations.run_all(my.migrations_run_twice, ns='ns1')
        self.assertEqual('Cannot start migrations on module my.migrations_run_twice because [bla] is RUNNING', ex.exception.message)

