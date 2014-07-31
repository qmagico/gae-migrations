import json
import logging
import importlib
import settings

from google.appengine.api import taskqueue


def enqueue(function, queue=settings.TASKS_QUEUE, **kwargs):
    path = function.__module__ + '.' + function.__name__
    task_args = {}
    func_wargs = {}
    for key in kwargs:
        if key.startswith('task_'):
            task_args[key[5:]] = kwargs[key]
        else:
            func_wargs[key] = kwargs[key]

    taskqueue.add(
        url=settings.TASKS_RUNNER_URL,
        queue_name=queue,
        params={
            'funcpath': path,
            'kwargs_json': json.dumps(func_wargs)
        },
        **task_args)


def execute(funcpath, kwargs_json):
    logging.info('executing task %s(%s)' % (funcpath, kwargs_json))
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
