import importlib
import pkgutil
from migrations.model import enqueue_migration, DBSingleMigration, DBDataChecker
import settings


def get_all_migrations(module):
    migrations = []
    m = importlib.import_module(module)
    for subm, subn, is_module in pkgutil.iter_modules(m.__path__):
        submodule = importlib.import_module(m.__name__ + '.' + subn)
        migrations.append(submodule.MyTask())
    return sorted(migrations, key=lambda m: m.get_name())


def enqueue_next_task(db_class):
    migrated_names = db_class.last_1000_names_done_or_running()
    for task in get_all_migrations(db_class.get_module()):
        if not task.get_name() in migrated_names:
            enqueue_migration(task.__module__, None)
            return task.get_name()

    if db_class == DBDataChecker:
        # settings.FINISHED_DATA_CHECK()
        pass

def start_db_checker():
    DBDataChecker.delete_all()
    enqueue_next_task(DBDataChecker)


def enqueue_next_single_migration():
    return enqueue_next_task(DBSingleMigration)
