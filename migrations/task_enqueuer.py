import json
import logging
import importlib
import time
from google.appengine.api.labs.taskqueue.taskqueue import TransientError
import settings
from google.appengine.api import taskqueue
from google.appengine.api import namespace_manager



def enqueue(function, queue=settings.TASKS_QUEUE, **kwargs):
    def _task_add(func_wargs0, path0, queue0, task_args0):
        taskqueue.add(
            url=settings.TASKS_RUNNER_URL,
            queue_name=queue0,
            params={
                'funcpath': path0,
                'kwargs_json': json.dumps(func_wargs0)
            },
            **task_args0)

    path = function.__module__ + '.' + function.__name__
    task_args = {}
    func_wargs = {}
    for key in kwargs:
        if key.startswith('task_'):
            task_args[key[5:]] = kwargs[key]
        else:
            func_wargs[key] = kwargs[key]

    try:
        _task_add(func_wargs, path, queue, task_args)
    except TransientError, e:
        logging.warning('Ocorreu um TransientError: %s', e.message)
        time.sleep(0.5)
        _task_add(func_wargs, path, queue, task_args)


def execute(funcpath, kwargs_json):
    logging.info('executing task on namespace %s: %s(%s)' % (namespace_manager.get_namespace(), funcpath, kwargs_json))
    kwargs = json.loads(kwargs_json)
    module_list = funcpath.split('.')
    module_name = '.'.join(module_list[0:-1])
    function_name = module_list[-1]
    module = importlib.import_module(module_name)
    function = getattr(module, function_name)
    if isinstance(kwargs, dict):
        function(**kwargs)
    elif isinstance(kwargs, list):
        function(*kwargs)
    else:
        function(kwargs)
