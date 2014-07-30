import time

from google.appengine.api import namespace_manager
from google.appengine.ext import ndb


RUNNING = 'RUNNING'
DONE = 'DONE'
ERROR = 'ERROR'


class MigrationException(BaseException):
    def __init__(self, cause):
        BaseException.__init__(self, cause.message)
        self.cause = cause


class DBMigrationLog(ndb.Model):
    name = ndb.StringProperty(required=True)
    description = ndb.StringProperty(required=True)
    status = ndb.StringProperty(required=True, choices=[RUNNING, DONE, ERROR])
    creation = ndb.DateTimeProperty(auto_now_add=True)
    last_update = ndb.DateTimeProperty(auto_now=True)
    error_msg = ndb.TextProperty()
    stacktrace = ndb.TextProperty()

    @classmethod
    def new_migration(cls, name, description):
        original_ns = namespace_manager.get_namespace()
        namespace_manager.set_namespace('')
        migration = cls.query(cls.name == name).get()
        if not migration:
            migration = cls()
            migration.name = name
        migration.description = description
        migration.status = RUNNING
        migration.put()
        namespace_manager.set_namespace(original_ns)
        return migration

    @classmethod
    def last_1000_names_done_or_running(cls):
        original_ns = namespace_manager.get_namespace()
        namespace_manager.set_namespace('')
        migrations = cls.query(cls.status.IN([DONE, RUNNING])).order(-cls.name).fetch(1000)
        names = []
        for migration in migrations:
            names.append(migration.name)
        namespace_manager.set_namespace(original_ns)
        return names

    @classmethod
    def finish_migration(cls, name):
        original_ns = namespace_manager.get_namespace()
        namespace_manager.set_namespace('')
        migration = cls.query(cls.name == name).get()
        if migration:
            migration.status = DONE
            migration.put()
        time.sleep(1)  # eventually consistent fdp
        namespace_manager.set_namespace(original_ns)

    @classmethod
    def error(cls, name, error_msg, stacktrace):
        original_ns = namespace_manager.get_namespace()
        namespace_manager.set_namespace('')
        migration = cls.query(cls.name == name).get()
        if migration:
            migration.error_msg = error_msg
            migration.stacktrace = stacktrace
            migration.status = ERROR
            migration.put()
        namespace_manager.set_namespace(original_ns)
