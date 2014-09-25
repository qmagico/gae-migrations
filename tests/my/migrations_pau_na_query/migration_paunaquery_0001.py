from my.models import QueDoidura

# Opcional. Retorna quantas migracoes devem ser rodadas por task (default = 1000)
MIGRATIONS_PER_TASK = 2

# Descricao amigavel dessa alteracao no banco
DESCRIPTION = 'multiplica por 2'


def get_query():
    """ Retorna um objeto query das coisas que precisam ser migradas """
    return QueDoidura.query()


def migrate_one(entity):
    entity.v2 = entity.v1 * 2
    entity.put()

