from migrations.model import AbstractMigrationTask


class MyTask(AbstractMigrationTask):

    def get_name(self):
        """ Nome da migracao. Deve ser unico por migracao. Ese sempre a implementacao abaixo"""
        return __name__.split('.')[-1]

    def get_description(self):
        """ Descricao amigavel dessa alteracao no banco """
        return 'multiplica por 3'

    def get_query(self):
        """ Retorna um objeto query das coisas que precisam ser migradas """
        raise Exception("Deu pau na query")

    def migrate_one(self, entity):
        """ Executa a migracao pra um elemento retornado pela query """
        raise Exception("Deu pau na migracao")
