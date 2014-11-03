from google.appengine.ext import ndb
from Crypto.Cipher import AES
from Crypto import Random
import webapp2
import json

from wootils import make_status_message


PRIV_KEY = '\xaf?\xe6\xde\xe8:\xa5\xca\xa7\x98\xbf\xf8\x97\xb7\xa0l'
BLOCK_SIZE = 16


class X(ndb.Model):
    enc = ndb.BlobProperty(required=True)
    iv = ndb.BlobProperty(required=True)
    priv_key = ndb.BlobProperty(required=True)
    namespace = ndb.StringProperty(
        choices=['default'], default='default', required=True)
    version = ndb.StringProperty(
        choices=['v1'], default='v1', required=True)

    @classmethod
    def _pad(self, s):
        return (s + (BLOCK_SIZE-len(s) % BLOCK_SIZE) *
                chr(BLOCK_SIZE-len(s) % BLOCK_SIZE))

    @classmethod
    def _unpad(self, s):
        return s[0:-ord(s[-1])]

    @classmethod
    def gen(cls, val):
        x = cls()
        x.iv = Random.new().read(BLOCK_SIZE)
        x.priv_key = PRIV_KEY
        cipher = AES.new(x.priv_key, AES.MODE_CFB, x.iv)
        val = x._pad(val)
        x.enc = x.iv + cipher.encrypt(val)
        return x

    def dec(self):
        iv = self.enc[:BLOCK_SIZE]
        val = self.enc[BLOCK_SIZE:]
        cipher = AES.new(self.priv_key, AES.MODE_CFB, iv)
        x = cipher.decrypt(val)
        x = self._unpad(x)
        return x


class Handler(webapp2.RequestHandler):
    def get(self):
        """
        curl "http://localhost:8082/x/handler?x-id=6192449487634432"
        {"status": "success", "data": {"val": "1234 1234 5678 5678"}, "description": "found"}%
        """
        val = self.request.get('x-id', None)
        if val is None:
            success = False
            data = {}
            msg = 'no x id given'
            self.post
        else:
            val = int(val)
            try:
                x = X.get_by_id(val)
                if not x:
                    success = False
                    data = {}
                    msg = 'not found'
                else:
                    success = True
                    data = {'val': x.dec()}
                    msg = 'found'
            except:
                success = False
                data = {}
                msg = 'problem retrieving data'
        msg = make_status_message(
            success=success, message=msg, data=data)
        self.response.write(msg)

    def post(self):
        """
        curl -k --data "x-no=1234 1234 5678 5678" http://localhost:8082/x/handler
        {"data": {"id": 6192449487634432}, "description": "all good", "status":
        "success"}
        """
        import json
        val = json.loads(self.request.body)['x']
        if val is None:
            success = False
            data = {}
            msg = 'no x given'
            self.post
        else:
            try:
                x = X.gen(val=val)
                key = x.put()
                data = {'id': key.id()}
                success = True
                msg = 'all good'
            except:
                success = False
                data = {}
                msg = 'problem saving data'
        msg = make_status_message(
            success=success, message=msg, data=data)
        self.response.write(msg)


app = webapp2.WSGIApplication(
    [('/x/handler', Handler)], debug=True)
