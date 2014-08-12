from google.appengine.ext import ndb


class QueDoidura(ndb.Model):
    v1 = ndb.IntegerProperty()
    v2 = ndb.IntegerProperty()
    v3 = ndb.IntegerProperty()
