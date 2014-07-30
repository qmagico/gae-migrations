import migrations
from importlib import import_module
from migrations.settings import migrations_list
from migrations.model import DBMigrationLog


def get_instance(module_str):
    module = import_module(module_str)
    return getattr(module, 'MyTask')()


def run_migrations():
    all_tasks = [get_instance(".".join([migrations_list.__package__, m]))
                 for m in migrations_list.all_migrations]

    migrations.enqueue_next_task(all_tasks)


def enqueue_next_migration(migrations):
    migrated_names = DBMigrationLog.last_1000_names_done_or_running()
    for migration in migrations:
        if not migration.name in migrated_names:
            migration.start()
            break
