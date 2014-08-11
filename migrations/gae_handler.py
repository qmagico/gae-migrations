__author__ = 'tony'

import settings
import webapp2
from migrations import task_enqueuer


class GenericTaskRunner(webapp2.RequestHandler):
    def get(self):
        task_enqueuer.execute(self.request.GET['funcpath'], self.request.GET['kwargs_json'])

    def post(self):
        task_enqueuer.execute(self.request.POST['funcpath'], self.request.POST['kwargs_json'])


application = webapp2.WSGIApplication([
    (settings.TASKS_RUNNER_URL, GenericTaskRunner),
], debug=False)