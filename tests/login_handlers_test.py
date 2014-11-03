from google.appengine.ext import ndb
import webapp2
import time
import requests
import logging
import json
from webapp2_extras.appengine.auth.models import Unique

from models import Advertiser

class TestOwnLogins(webapp2.RequestHandler):
    def get(self):
        email = 'alice@pagewoo.com'
        password = 'password'
        new_password = 'new_password'

        # check for existing advertiser first, delete if necessary
        adv = Advertiser.get_by_auth_id(email)
        logging.error('found advertiser')
        if adv is not None:
            for auth_id in adv.auth_ids:
                uu = ndb.Key(Unique, 'Advertiser.auth_id:'+auth_id)
                uu.delete()
            logging.info('deleted auth ids')
            adv.key.delete()
            logging.info('deleted advertiser')
            time.sleep(3)

        data = {'email': email, 'password': password}
        r = requests.post(self.uri_for('createadvertiser', _full=True),
                                            data=json.dumps(data))
        logging.info('create advertiser')
        logging.info('r.status_code ' + str(r.status_code))
        logging.info('r.content ' + str(r.content))
        time.sleep(2)

        # sign in
        r = requests.post(self.uri_for('advertisersignin', _full=True),
                                            data=json.dumps(data))
        logging.info('sign in advertiser')
        logging.info('r.status_code ' + str(r.status_code))
        logging.info('r.content ' + str(r.content))
        # cookies = r.cookies

        # forget our password
        data = {'email': email}
        r = requests.post(self.uri_for('forgotadvertiserpassword', _full=True),
                                            data=json.dumps(data))
        logging.info('forgot advertiser password')
        logging.info('r.status_code ' + str(r.status_code))
        logging.info('r.content ' + str(r.content))
        response_data = json.loads(r.content)
        token = response_data['data']['token']

        # reset our password
        data = {'password': new_password, 'confirm_password': new_password}
        r = requests.post(self.uri_for('resetadvertiserpassword',
                                                                      email=email,
                                                                      token=token,
                                                                      _full=True),
                                            data=json.dumps(data))
        logging.info('reset advertiser password')
        logging.info('r.status_code ' + str(r.status_code))
        logging.info('r.content ' + str(r.content))
        time.sleep(2)

        # sign in with new password
        data = {'email': email, 'password': new_password}
        r = requests.post(self.uri_for('advertisersignin', _full=True),
                                            data=json.dumps(data))
        logging.info('sign in advertiser with new password')
        logging.info('r.status_code ' + str(r.status_code))
        logging.info('r.content ' + str(r.content))
        # cookies = r.cookies


