""" Handles advertisers referring new advertisers. When these
new advertisers create a campaign, the referer gets block points as a
thank-you.  """


import json
import webapp2
import logging
import pprint


from nearwoo_sessions import BaseRequestHandler
import models
import wootils

from social import shorten
from datetime import datetime

from google.appengine.ext import ndb
from google.appengine.ext import deferred


# number of block points for the referring advertiser
N_BLOCK_POINTS = 5


class Catch(BaseRequestHandler):
    """ Called when referred client clicks on link """

    def get(self, tiny):
        logging.info('catching tiny referral %s', tiny)
        ref = models.TinyReferral.find(tiny)
        if (ref and models.Advertiser.validate_auth_token(ref.adv_key, ref.token)):
            deferred.defer(txn, tiny)
            self.session['referral'] = ref.to_dict()
        self.redirect('/')

@ndb.transactional(xg=True, retries=5)
def txn(tiny):
    ref = models.TinyReferral.find(tiny)
    ref.visits.append(datetime.now())
    ref.put()


class Make(webapp2.RequestHandler):
    """ Create a new tiny referral url """
    def get(self, adv_key, bitlyfy=False, created_for=''):
        logging.debug('make referral for %s', adv_key)
        try:
            ref = models.TinyReferral.create(adv_key, N_BLOCK_POINTS, created_for=created_for)
            data = {
                'url': self.uri_for('adv_referral', tiny=ref.tiny, _full=True)}
            success = True
        except Exception as e:
            logging.exception(e)
            data = {}
            success = False
        if bitlyfy == False:
            self.response.write(wootils.make_status_message(
            success=success, data=data))
        else:
            r = shorten(data['url'])
            self.response.write(r)


@ndb.transactional(xg=True, retries=5, propagation=ndb.TransactionOptions.INDEPENDENT)
def redeem(adv_key, tinyid, block_points):
    """ To be called after the referred client/advertiser has actually
    created & paid for a new campaign """

    adv = models.Advertiser.urlsafe_get(adv_key)
    adv.block_points += int(block_points)
    adv.put()
    tiny = models.TinyReferral.find(tinyid)
    tiny.signups.append(datetime.now())
    tiny.put()


def invalidate(ref):
    """ Invalidates a given referral url """

    logging.debug('invalidating ref %s', pprint.pprint(ref))
    if ref:
        tiny = models.TinyReferral.find(ref['tiny'])
        tiny.inactivate()
        tiny.put()


class SessionData(BaseRequestHandler):
    def get(self):
        self.response.write(json.dumps(self.session))


class ReferralReport(webapp2.RequestHandler):
    def get(self, adv_key):
        adv = models.Advertiser.urlsafe_get(adv_key)
        tinyrefs = models.TinyReferral.query(models.TinyReferral.adv_key == str(adv_key)).fetch()
        data = {
            'name': adv.name,
            'tinyrefs': [],
            'email': adv.business_email,
        }
        for i, link in enumerate(tinyrefs):
            data['tinyrefs'].append([])
            data['tinyrefs'][i] = {}
            data['tinyrefs'][i]['block_points'] = link.block_points
            data['tinyrefs'][i]['created_for'] = link.created_for
            data['tinyrefs'][i]['checkouts'] = len(link.signups)
            data['tinyrefs'][i]['tiny'] = link.tiny
            data['tinyrefs'][i]['clicks'] = len(link.visits)
        self.response.write(wootils.make_status_message(success=True, data=data))