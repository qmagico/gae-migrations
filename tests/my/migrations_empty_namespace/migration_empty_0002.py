from my.models import QueDoidura

# Descricao amigavel dessa alteracao no banco
DESCRIPTION = 'multiplica por 3'
RESTRICT_NAMESPACE = ''


def get_query():
    """ Retorna um objeto query das coisas que precisam ser migradas """
    return QueDoidura.query()

def migrate_one(entity):
    """ Executa a migracao pra um elemento retornado pela query """
    entity.v3 = entity.v1 * 3
    entity.put()
