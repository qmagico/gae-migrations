from migrations.model import DataCheckerMigration
from my.models import QueDoidura


class MyTask(DataCheckerMigration):

    def get_name(self):
        """ Nome da migracao. Deve ser unico por migracao. Ese sempre a implementacao abaixo"""
        return __name__.split('.')[-1]

    def get_description(self):
        """ Descricao amigavel dessa alteracao no banco """
        return 'conta quantas vezes essa task foi executada'

    def get_query(self):
        """ Retorna um objeto query das coisas que precisam ser migradas """
        return QueDoidura.query()

    def migrate_one(self, entity):
        """ Executa a migracao pra um elemento retornado pela query """
        if entity.v3 is None:
            entity.v3 = 1
        else:
            entity.v3 += 1
        entity.put()
