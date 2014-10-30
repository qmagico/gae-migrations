import logging

__author__ = 'tony'

import settings
import webapp2
from migrations import task_enqueuer

# Gambiarra [1]
# If we return a 500 code, appengine will retry the task at least once (even if the queue settings tell it not to)
# http://stackoverflow.com/questions/26657605/appengine-runs-failed-tasks-twice-even-if-task-retry-limit-0
# So we need another way to prevent the task from running again, in this case, throwing an exception
# with status_code = 200


class GenericTaskRunner(webapp2.RequestHandler):
    def get(self):
        try:
            logging.info('GenericTaskRunner.get')
            task_enqueuer.execute(self.request.GET['funcpath'], self.request.GET['kwargs_json'])
        except BaseException as e:
            logging.error('GenericTaskRunner.get - error')
            if hasattr(e, 'status_code'):  # See: Workaround [1]
                self.response.status = e.status_code
            else:
                self.response.status = 500

    def post(self):
        try:
            logging.info('GenericTaskRunner.post')
            task_enqueuer.execute(self.request.POST['funcpath'], self.request.POST['kwargs_json'])
        except BaseException as e:
            logging.error('GenericTaskRunner.post - error')
            if hasattr(e, 'status_code'):  # See: Workaround [1]
                self.response.status = e.status_code
            else:
                self.response.status = 500


application = webapp2.WSGIApplication([
    (settings.TASKS_RUNNER_URL, GenericTaskRunner),
], debug=False)
