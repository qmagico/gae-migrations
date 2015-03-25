from google.appengine.ext import ndb
from my.models import QueDoidura
import json
from google.appengine.api import namespace_manager


# Opcional. Retorna quantas migracoes devem ser rodadas por task (default = 1000)
MIGRATIONS_PER_TASK = 2

# Descricao amigavel dessa alteracao no banco
DESCRIPTION = 'multiplica por 2'


def update_json_data(migrate_result, old_json_data):
    old_json_data = json.loads(old_json_data) if old_json_data else {}
    migrate_result = json.loads(migrate_result) if migrate_result else {}
    if 'v1_for_namespace' not in old_json_data:
        old_json_data['v1_for_namespace'] = {}
    for ns in migrate_result['v1_for_namespace']:
        if ns in old_json_data['v1_for_namespace']:
            old_json_data['v1_for_namespace'][ns].extend(migrate_result['v1_for_namespace'][ns])
        else:
            old_json_data['v1_for_namespace'][ns] = migrate_result['v1_for_namespace'][ns]
    return json.dumps(old_json_data)


def get_query():
    """ Retorna um objeto query das coisas que precisam ser migradas """
    return QueDoidura.query()


def migrate_many(entities):
    for entity in entities:
        entity.v2 = entity.v1 * 2
    ndb.put_multi(entities)
    ns = namespace_manager.get_namespace()
    return json.dumps({'v1_for_namespace': {ns: [e.v1 for e in entities]}})