import settings
import importlib
import pkgutil
from migrations.model import DBMigration, enqueue_migration


def get_all_migrations():
    migrations = []
    m = importlib.import_module(settings.MIGRATIONS_MODULE)
    for subm, subn, is_module in pkgutil.iter_modules(m.__path__):
        submodule = importlib.import_module(m.__name__ + '.' + subn)
        migrations.append(submodule.MyTask())
    return sorted(migrations, key=lambda m: m.get_name())


def enqueue_next_migration():
    migrated_names = DBMigration.last_1000_names_done_or_running()
    for migration in get_all_migrations():
        if not migration.get_name() in migrated_names:
            enqueue_migration(migration.__module__, None)
            return migration.get_name()
