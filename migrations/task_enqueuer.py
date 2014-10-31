import json
import logging
import importlib
import time
from google.appengine.api.labs.taskqueue.taskqueue import TransientError, TaskRetryOptions
import settings
from google.appengine.api import taskqueue, app_identity
from google.appengine.api import namespace_manager
import traceback
from google.appengine.api import mail


NO_RETRY = TaskRetryOptions(task_retry_limit=0, task_age_limit=1)
DEFAULT_COUNTDOWN = 1
# See http://stackoverflow.com/questions/26657605/appengine-runs-failed-tasks-twice-even-if-task-retry-limit-0

ERROR_MAIL_BODY_TMPL = """
--------------------------
TASK:
%s(%s)

--------------------------
ERROR
%s

--------------------------
STACK
%s
"""


def enqueue(function, queue=settings.TASKS_QUEUE, **kwargs):
    def _task_add(func_wargs0, path0, queue0, task_args0):
        logging.info('enqueuing task on namespace %s: %s(%s)' % (namespace_manager.get_namespace(), path0, func_wargs0))
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
    if not 'retry_options' in task_args:
        task_args['retry_options'] = NO_RETRY
    if not 'countdown' in task_args:
        task_args['countdown'] = DEFAULT_COUNTDOWN
    try:
        _task_add(func_wargs, path, queue, task_args)
    except TransientError, e:
        logging.warning('Ocorreu um TransientError: %s', e.message)
        time.sleep(0.5)
        _task_add(func_wargs, path, queue, task_args)


def execute(funcpath, kwargs_json):
    logging.info('executing task on namespace %s: %s(%s)' % (namespace_manager.get_namespace(), funcpath, kwargs_json))
    try:
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
    except BaseException as e:
        errmsg = 'Task error: %s' % e
        stacktrace = traceback.format_exc()
        logging.error(errmsg)
        logging.error(stacktrace)
        if hasattr(settings, 'TASKS_ERROR_NOTIFY_MAIL'):
            _notify_error(funcpath, kwargs_json, e, stacktrace)
        raise e


def _notify_error(funcpath, kwargs_json, e, stacktrace):
    appid = app_identity.get_application_id()
    subject = 'Error executing task on namespace: %s/%s: %s' % (appid, namespace_manager.get_namespace(), funcpath)
    body = ERROR_MAIL_BODY_TMPL % (funcpath, kwargs_json, e, stacktrace)
    to = settings.TASKS_ERROR_NOTIFY_MAIL['to']
    if not isinstance(to, list):
        to = [to]
    mail.send_mail(
        sender=settings.TASKS_ERROR_NOTIFY_MAIL['from'],
        to=to,
        subject=subject,
        body=body)
