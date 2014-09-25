import migrations
from migrations import task_enqueuer, MigrationException
from migrations.model import DBMigration
from test_utils import GAETestCase
from my.models import QueDoidura
from google.appengine.api import taskqueue, namespace_manager
import my.migrations
import my.migrations_empty_namespace
import my.migrations_pau_na_query
import my.migrations_pau_na_migration


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


class TestRunMigrationsOnEmptyNamespace(GAETestCase):
    def setUp(self):
        GAETestCase.setUp(self)
        self._old_ns = namespace_manager.get_namespace()
        namespace_manager.set_namespace('')
        QueDoidura(v1=3).put()
        QueDoidura(v1=4).put()
        QueDoidura(v1=5).put()
        self._old_task_add = taskqueue.add
        taskqueue.add = sync_task_add

    def tearDown(self):
        GAETestCase.tearDown(self)
        taskqueue.add = self._old_task_add
        namespace_manager.set_namespace(self._old_ns)

    def test_run_migrations(self):
        # Roda as migracoes
        first_migration = migrations.run_pending(my.migrations_empty_namespace)
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
        first_migration = migrations.run_pending(my.migrations_empty_namespace)
        self.assertIsNone(first_migration)

        # E os DBMigrations estao ok
        namespace_manager.set_namespace('')
        dbmigrations = []
        for dbmigration in DBMigration.query():
            self.assertTrue(dbmigration.status == 'DONE')
            dbmigrations.append(dbmigration.name)
        self.assertEqual(2, len(dbmigrations))
        self.assertTrue('migration_empty_0001' in dbmigrations)
        self.assertTrue('migration_empty_0002' in dbmigrations)


class TestRunMigrationsWithQueryError(GAETestCase):
    def setUp(self):
        GAETestCase.setUp(self)
        self._old_ns = namespace_manager.get_namespace()
        namespace_manager.set_namespace('ns1')
        QueDoidura(v1=3).put()
        QueDoidura(v1=4).put()
        QueDoidura(v1=5).put()
        self._old_task_add = taskqueue.add
        taskqueue.add = sync_task_add

    def tearDown(self):
        GAETestCase.tearDown(self)
        taskqueue.add = self._old_task_add
        namespace_manager.set_namespace(self._old_ns)

    def test_run_migrations(self):
        # Roda as migracoes
        try:
            migrations.run_pending(my.migrations_pau_na_query)
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
        dbmigrations = {dbm.name: dbm for dbm in DBMigration.query()}
        self.assertEqual(2, len(dbmigrations))
        self.assertTrue('DONE', dbmigrations['migration_paunaquery_0001'].status)
        self.assertTrue('ERROR', dbmigrations['migration_paunaquery_0002'].status)

        # E a migration 1 nao vai rodar de novo
        dones = DBMigration.last_1000_names_done_or_running('my.migrations_pau_na_query')
        self.assertEqual(1, len(dones))
        self.assertEqual('migration_paunaquery_0001', dones[0])


class TestRunMigrationsWithMigrationError(GAETestCase):
    def setUp(self):
        GAETestCase.setUp(self)
        self._old_ns = namespace_manager.get_namespace()
        namespace_manager.set_namespace('ns1')
        QueDoidura(v1=3).put()
        QueDoidura(v1=4).put()
        QueDoidura(v1=5).put()
        self._old_task_add = taskqueue.add
        taskqueue.add = sync_task_add

    def tearDown(self):
        GAETestCase.tearDown(self)
        taskqueue.add = self._old_task_add
        namespace_manager.set_namespace(self._old_ns)

    def test_run_migrations(self):
        # Roda as migracoes
        try:
            migrations.run_pending(my.migrations_pau_na_migration)
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
        dbmigrations = {dbm.name: dbm for dbm in DBMigration.query()}
        self.assertEqual(2, len(dbmigrations))
        self.assertTrue('DONE', dbmigrations['migration_paunamigration_0001'].status)
        self.assertTrue('ERROR', dbmigrations['migration_paunamigration_0002'].status)

        # E a migration 1 nao vai rodar de novo
        dones = DBMigration.last_1000_names_done_or_running('my.migrations_pau_na_migration')
        self.assertEqual(1, len(dones))
        self.assertEqual('migration_paunamigration_0001', dones[0])
