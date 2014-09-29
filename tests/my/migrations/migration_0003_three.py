from my.models import QueDoidura, QuantaLoucura


DESCRIPTION = 'multiplica por 3'


def migrate():
    """ Executa a migracao pra um elemento retornado pela query """
    count = QueDoidura.query().count()
    ql = QuantaLoucura(quanto=count)
    ql.put()