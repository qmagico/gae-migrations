from migrations.model import AbstractMigrationTaskOnEmptyNamespace
from my.models import QueDoidura


class MyTask(AbstractMigrationTaskOnEmptyNamespace):

    def get_name(self):
        """ Nome da migracao. Deve ser unico por migracao. Ese sempre a implementacao abaixo"""
        return __name__.split('.')[-1]

    def get_description(self):
        """ Descricao amigavel dessa alteracao no banco """
        return 'multiplica por 2'

    def get_query(self):
        """ Retorna um objeto query das coisas que precisam ser migradas """
        return QueDoidura.query()

    def migrate_one(self, entity):
        entity.v2 = entity.v1 * 2
        entity.put()
