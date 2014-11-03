# -*- coding: utf-8 -*-


import webapp2
from datetime import date
from datetime import timedelta

import models

import requests
from urllib import quote
from jconfig import get_host
from cgi import escape

import logging
import sendgrid2


class FBIncrease(webapp2.RequestHandler):
    def get(self, adv_key):
        if models.FacebookFan.get_by_id(adv_key) is None:
            q = models.Advertiser.urlsafe_get(adv_key)
            q.block_points += 2
            q.put()
            ff = models.FacebookFan(id=adv_key)
            ff.adv_key = adv_key
            ff.put()


class FBDecrease(webapp2.RequestHandler):
    def get(self, adv_key):
        ff = models.FacebookFan.get_by_id(adv_key)
        if ff:
            q = models.Advertiser.urlsafe_get(adv_key)
            q.block_points -= 2
            if q.block_points < 0:
                q.block_points = 0
            q.put()
            ff.key.delete()


class TWIncrease(webapp2.RequestHandler):
    def get(self, adv_key):
        q = models.Advertiser.urlsafe_get(adv_key)
        tweeter = models.Tweeter.query(models.Tweeter.adv_key == adv_key).get()
        tnew = False
        if tweeter == None:
            tnew = True
            tweeter = models.Tweeter()
            tweeter.adv_key = adv_key
        if ((tnew == True) or ((date.today() - tweeter.last_bonus_date) >= timedelta(30))):
            q.block_points += 1
            q.put()
            tweeter.last_bonus_date = date.today()
        tweeter.put()


class ShortenUrl(webapp2.RequestHandler):
    def get(self, url, called=True):
        '''Shortens the passed url using the bit.ly API.
        Returns shortened url as a string.
        In case of any exception, return original url.'''
        try:
            ACCESS_TOKEN = "7e2c5fb022ce26035964be79cf76e48d0685d76f"
            bitly = 'https://api-ssl.bitly.com/v3/shorten?access_token=' + ACCESS_TOKEN + '&longUrl=' + url
            r = requests.get(bitly)
            shorturl = r.json()['data']['url']
        except:
            shorturl = url
        if shorturl == url:
            logging.info("could not shorten url " + shorturl)
        else:
            logging.info("shortened url to " + shorturl)
        if called:
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write(shorturl)
        else:
            return shorturl


def shorten(url):
    c = ShortenUrl()
    return c.get(url, called=False)


class SendPromoMail(webapp2.RequestHandler):
    def post(self):
        adv_key = str(self.request.referer.split('/')[-1])
        r = models.TinyReferral.create(adv_key, created_for='email')
        refurl = self.uri_for('adv_referral', tiny=r.tiny, _full=True)

        to_email = escape(self.request.POST['toEmail'])
        from_email = escape(self.request.POST['fromEmail'])
        mail_body = escape(self.request.POST['emailBody'])
        subject = escape(self.request.POST['subject'])
        logging.info("Promo mail sent by adv {} to {}".format(adv_key, to_email))

        s = sendgrid2.SendGridClient('nearwoonews', 'nearwoo17')
        message = sendgrid2.Mail()
        message.add_to(to_email)
        message.set_from(from_email)
        message.set_subject(subject)
        message.set_html("{}<br/><br/>{}".format(mail_body, shorten(refurl)))
        s.send(message)

        self.redirect('/app/settings/earnmore/' + adv_key)