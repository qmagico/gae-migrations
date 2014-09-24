from migrations.model import MigrationException
from migrations import migrations_enqueuer, task_enqueuer
from migrations.model import DBSingleMigration
from test_utils import GAETestCase
import settings
from my.migrations import migration_0001_one
from my.migrations import migration_0002_two
from my.models import QueDoidura
from google.appengine.api import taskqueue, namespace_manager


class TestListMigrations(GAETestCase):
    def setUp(self):
        GAETestCase.setUp(self)
        self._old_MIGRATIONS_MODULE = settings.MIGRATIONS_MODULE
        settings.MIGRATIONS_MODULE = 'my.migrations'

    def tearDown(self):
        GAETestCase.tearDown(self)
        settings.MIGRATIONS_MODULE = self._old_MIGRATIONS_MODULE

    def test_list_migrations(self):
        migrations = migrations_enqueuer.get_all_migrations(settings.MIGRATIONS_MODULE)
        self.assertEqual(2, len(migrations))
        self.assertTrue(isinstance(migrations[0], migration_0001_one.MyTask))
        self.assertTrue(isinstance(migrations[1], migration_0002_two.MyTask))


def sync_task_add(*args, **kwargs):
    task_enqueuer.execute(kwargs['params']['funcpath'], kwargs['params']['kwargs_json'])



class TestRunMigrationsOnEmptyNamespace(GAETestCase):
    def setUp(self):
        GAETestCase.setUp(self)
        self._old_MIGRATIONS_MODULE = settings.MIGRATIONS_MODULE
        settings.MIGRATIONS_MODULE = 'my.migrations_empty_namespace'
        self._old_ns = namespace_manager.get_namespace()
        namespace_manager.set_namespace('')
        QueDoidura(v1=3).put()
        QueDoidura(v1=4).put()
        QueDoidura(v1=5).put()
        self._old_task_add = taskqueue.add
        taskqueue.add = sync_task_add

    def tearDown(self):
        GAETestCase.tearDown(self)
        settings.MIGRATIONS_MODULE = self._old_MIGRATIONS_MODULE
        taskqueue.add = self._old_task_add
        namespace_manager.set_namespace(self._old_ns)

    def test_run_migrations(self):
        # Roda as migracoes
        first_migration = migrations_enqueuer.enqueue_next_single_migration()
        self.assertEqual('migration_empty_0001', first_migration)
        count = 0
        v1sum = 0
        namespace_manager.set_namespace('')
        for qd in QueDoidura.query():
            self.assertEqual(qd.v2, 2 * qd.v1)
            self.assertEqual(qd.v3, 3 * qd.v1)
            count += 1
            v1sum += qd.v1
        self.assertEqual(3, count)
        self.assertEqual(12, v1sum)

        # E depois nao roda mais nada
        first_migration = migrations_enqueuer.enqueue_next_single_migration()
        self.assertIsNone(first_migration)

        # E os DBMigrations estao ok
        namespace_manager.set_namespace('')
        dbmigrations = []
        for dbmigration in DBSingleMigration.query():
            self.assertTrue(dbmigration.status == 'DONE')
            dbmigrations.append(dbmigration.name)
        self.assertEqual(2, len(dbmigrations))
        self.assertTrue('migration_empty_0001' in dbmigrations)
        self.assertTrue('migration_empty_0002' in dbmigrations)


class TestRunMigrationsWithQueryError(GAETestCase):
    def setUp(self):
        GAETestCase.setUp(self)
        self._old_MIGRATIONS_MODULE = settings.MIGRATIONS_MODULE
        settings.MIGRATIONS_MODULE = 'my.migrations_pau_na_query'
        self._old_ns = namespace_manager.get_namespace()
        namespace_manager.set_namespace('ns1')
        QueDoidura(v1=3).put()
        QueDoidura(v1=4).put()
        QueDoidura(v1=5).put()
        self._old_task_add = taskqueue.add
        taskqueue.add = sync_task_add

    def tearDown(self):
        GAETestCase.tearDown(self)
        settings.MIGRATIONS_MODULE = self._old_MIGRATIONS_MODULE
        taskqueue.add = self._old_task_add
        namespace_manager.set_namespace(self._old_ns)

    def test_run_migrations(self):
        # Roda as migracoes
        try:
            migrations_enqueuer.enqueue_next_single_migration()
        except MigrationException as e:
            deupau = True
            migration_exception = e
        self.assertTrue(deupau)
        self.assertEqual('Deu pau na query', migration_exception.cause.message)
        count = 0
        v1sum = 0
        namespace_manager.set_namespace('ns1')
        for qd in QueDoidura.query():
            self.assertEqual(qd.v2, 2 * qd.v1)
            self.assertIsNone(qd.v3)
            count += 1
            v1sum += qd.v1
        self.assertEqual(3, count)
        self.assertEqual(12, v1sum)

        # E os DBMigrations estao ok
        namespace_manager.set_namespace('')
        dbmigrations = {dbm.name: dbm for dbm in DBSingleMigration.query()}
        self.assertEqual(2, len(dbmigrations))
        self.assertTrue('DONE', dbmigrations['migration_paunaquery_0001'].status)
        self.assertTrue('ERROR', dbmigrations['migration_paunaquery_0002'].status)

        # E a migration 1 nao vai rodar de novo
        dones = DBSingleMigration.last_1000_names_done_or_running()
        self.assertEqual(1, len(dones))
        self.assertEqual('migration_paunaquery_0001', dones[0])


class TestRunMigrationsWithMigrationError(GAETestCase):
    def setUp(self):
        GAETestCase.setUp(self)
        self._old_MIGRATIONS_MODULE = settings.MIGRATIONS_MODULE
        settings.MIGRATIONS_MODULE = 'my.migrations_pau_na_migration'
        self._old_ns = namespace_manager.get_namespace()
        namespace_manager.set_namespace('ns1')
        QueDoidura(v1=3).put()
        QueDoidura(v1=4).put()
        QueDoidura(v1=5).put()
        self._old_task_add = taskqueue.add
        taskqueue.add = sync_task_add

    def tearDown(self):
        GAETestCase.tearDown(self)
        settings.MIGRATIONS_MODULE = self._old_MIGRATIONS_MODULE
        taskqueue.add = self._old_task_add
        namespace_manager.set_namespace(self._old_ns)

    def test_run_migrations(self):
        # Roda as migracoes
        try:
            migrations_enqueuer.enqueue_next_single_migration()
        except MigrationException as e:
            deupau = True
            migration_exception = e
        self.assertTrue(deupau)
        self.assertEqual('Deu pau na migracao', migration_exception.cause.message)
        count = 0
        v1sum = 0
        namespace_manager.set_namespace('ns1')
        for qd in QueDoidura.query():
            self.assertEqual(qd.v2, 2 * qd.v1)
            self.assertIsNone(qd.v3)
            count += 1
            v1sum += qd.v1
        self.assertEqual(3, count)
        self.assertEqual(12, v1sum)

        # E os DBMigrations estao ok
        namespace_manager.set_namespace('')
        dbmigrations = {dbm.name: dbm for dbm in DBSingleMigration.query()}
        self.assertEqual(2, len(dbmigrations))
        self.assertTrue('DONE', dbmigrations['migration_paunamigration_0001'].status)
        self.assertTrue('ERROR', dbmigrations['migration_paunamigration_0002'].status)

        # E a migration 1 nao vai rodar de novo
        dones = DBSingleMigration.last_1000_names_done_or_running()
        self.assertEqual(1, len(dones))
        self.assertEqual('migration_paunamigration_0001', dones[0])


class TestRunDataCheckMigration(GAETestCase):
    def setUp(self):
        GAETestCase.setUp(self)
        self._old_DATA_CHECKER_MODULE = settings.DATA_CHECKER_MODULE
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
        settings.DATA_CHECKER_MODULE = self._old_DATA_CHECKER_MODULE
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
