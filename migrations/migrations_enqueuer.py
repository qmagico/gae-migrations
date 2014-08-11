from importlib import import_module
from settings import MIGRATIONS_LIST
from migrations.model import DBMigrationLog


def get_instance(module_str):
    module = import_module(module_str)
    return getattr(module, 'MyTask')()


def get_all_migrations():
    return [get_instance(".".join([MIGRATIONS_LIST.__package__, m]))
            for m in MIGRATIONS_LIST]


def enqueue_next_migration(migrations=get_all_migrations()):
    migrated_names = DBMigrationLog.last_1000_names_done_or_running()
    for migration in migrations:
        if not migration.name in migrated_names:
            migration.start()
            break
