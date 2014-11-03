from webapp2_extras.auth import InvalidAuthIdError
from webapp2_extras.auth import InvalidPasswordError
from google.appengine.api import mail
from google.appengine.ext import ndb
import datetime
import json
import webapp2
import logging

from partner_promo_shared import create_promotional_uri_segment
from nearwoo_sessions import BaseRequestHandler
from kpi_data import track_promo_uri_views
from models import Partner
from models import PartnerPromoCategory
from models import PartnerMediaLibrary
from models import PromotionalUriSegment
from models import Promotional
from models import PromoCategory
from models import NearWooCampaignDS
from wootils import make_status_message
from wootils import datetime_to_str
from wootils import func_to_backend
import jconfig


VERIFY_REDIRECT_TO = '/g/#/setpassword'
PROMO_CALLBACK_REDIRECT = '/'
WHOLESALE_PARTNER_REDIRECT = '/g/#/rep_signin'
EMAIL_SENDER = "NearWoo Support<jason@nearwoo.com>"
VERIFY_EMAIL_MESSAGE = """
Welcome to NearWoo!

Your Rep ID is {0}.

  Complete your signup here:
{1}


Your NearWoo Team
"""
FORGOT_PASSWORD_EMAIL_MESSAGE = """
Reset your password here:
{0}


Your NearWoo Team
"""
FORGOT_PROMO_ID_EMAIL_MESSAGE = """
No problem! Your Rep ID is {0}.


Your NearWoo Team
"""

HOST = jconfig.get_host()


class RepDash(BaseRequestHandler):

    def get(self):
        if self.logged_in:
            rep = self.current_user
            data = {'rep_name': rep.promo_id, 'url': rep.uri_segment}
            # get default category from pc
            partner = Partner.get_by_auth_id(rep.partner_id)
            pc = PromoCategory.get_by_id(
                partner.nearwoo_default_promo_category)
            if pc.discount_type == 'absolute':
                data['amt_off'] = '$' + str(int(pc.absolute_discount))
            else:
                data['amt_off'] = str(int(pc.percent_discount)) + '%'
            data['promo'] = pc.to_dict()
            status = make_status_message(success=True,
                                         message='promo session found',
                                         data=data)
        else:
            status = make_status_message(success=False,
                                         message='no promo session found')
        self.response.write(status)


class PromotionalLoggedIn(BaseRequestHandler):

    def get(self):
        if self.logged_in:
            promo = self.current_user
            logging.info(promo.email)
            data = {'promo_id': promo.promo_id, 'rep_email':promo.email}
            # transform privileges for js consumption
            all_privs = list(Promotional.privileges._choices)
            js_privs = []
            for priv in all_privs:
                d = {'name': priv}
                if priv in promo.privileges:
                    d['granted'] = True
                else:
                    d['granted'] = False
                js_privs.append(d)
            data['privileges'] = js_privs
            status = make_status_message(success=True,
                                         message='promo session found',
                                         data=data)
        else:
            status = make_status_message(success=False,
                                         message='no promo session found')
        self.response.write(status)


class VerifyPromotional(BaseRequestHandler):

    def get(self, promo_id, token):
        redirect_uri = VERIFY_REDIRECT_TO + '/' + promo_id + '/' + token
        self.redirect(redirect_uri)

    def post(self, promo_id, token):
        promo_data = json.loads(self.request.body)
        password = promo_data['password']
        confirm_password = promo_data['confirm_password']
        token_is_valid = Promotional.validate_auth_token(promo_id, token)
        logging.info('token is valid ' + str(token_is_valid))
        if token_is_valid:
            p = Promotional.get_by_auth_id(promo_id)
            logging.info('got promo')
            Promotional.delete_auth_token(promo_id, token)
            logging.info('deleted auth token')
        else:
            logging.error('Could not validate user with id "%s" token "%s"',
                          promo_id, token)
            self.abort(404)
        if len(password) < 5:
            status = make_status_message(success=False,
                                         message='password too short')
            self.response.write(status)
            return
        elif password != confirm_password:
            status = make_status_message(success=False,
                                         message='passwords do not match')
            self.response.write(status)
            return
        else:
            p.set_password(password)
        if not p.verified:
            p.verified = True
            p.add_auth_id(p.email)
            Promotional.delete_auth_token(promo_id, token)
        p.put()
        # store user data in the session
        self.auth.unset_session()
        self.auth.set_session(self.auth.store.user_to_dict(p),
                              remember=True)
        status = make_status_message(success=True,
                                     message='e-mail verified; password set')
        self.response.write(status)


class PromotionalLogout(BaseRequestHandler):

    def get(self):
        self.auth.unset_session()
        status = make_status_message(success=True,
                                     message='logged out')
        self.response.write(status)


class PromotionalCreateCampaign(BaseRequestHandler):

    def get(self, promo_id):
        """ log out and redirect to create campaign as advertiser from
        rep dash; apply standard discount """
        # since uri routing is in main, this will log out the rep as advertiser
        self.auth.unset_session()
        promo = Promotional.get_by_auth_id(promo_id)
        host = jconfig.get_host()

        biz = self.request.get('biz', None)
        loc = self.request.get('loc', None)
        if biz and loc:
            self.session['promo_id'] = promo_id
            # self.redirect(host + '/b/#/biz/' + str(biz) + '/' + str(loc))
            self.response.out.write('ok')
        elif not promo or promo.uri_segment is None or promo.uri_segment == '':
            self.redirect(host + '/' + str(promo_id))
        else:
            self.redirect(host + '/' + str(promo.uri_segment)
                          + '?code=standard')


class PromotionalLogin(BaseRequestHandler):

    def post(self):
        logging.info('promo login' + json.dumps(self.request.body))
        promo_data = json.loads(self.request.body)
        promo_id = promo_data['promo_id']
        password = promo_data['password']
        try:
            p = Promotional.get_by_auth_password(promo_id, password)
        except (InvalidAuthIdError, InvalidPasswordError) as e:
            logging.info('Login failed for user %s because of %s',
                         promo_id, type(e))
            status = make_status_message(success=False,
                                         message='invalid username/password')
            self.response.write(status)
            return
        else:
            self.auth.unset_session()
            self.auth.set_session(self.auth.store.user_to_dict(p),
                                  remember=True)
        status = make_status_message(success=True,
                                     message='login successful')
        self.response.write(status)


class EditPromotional(BaseRequestHandler):

    def post(self):
        logging.info("edit promo" + self.request.body)
        promo_data = json.loads(self.request.body)
        promo = self.current_user
        if not promo:
            status = make_status_message(success=False,
                                         message='promo needs to be logged in')
            self.response.write(status)

        if 'phone' in promo_data and promo_data['phone']:
            promo.phone = promo_data['phone']
        if 'email' in promo_data and promo_data['email']:
            promo.email = promo_data['email']
        promo.put()
        if 'uri_segment' in promo_data and promo_data['uri_segment']:
            create_promotional_uri_segment(promo, promo_data['uri_segment'])
        status = make_status_message(success=True,
                                     message='Edited promotional saved')
        logging.info('segment : %s', promo.uri_segment)
        self.response.write(status)


class ForgotPromoID(webapp2.RequestHandler):

    def post(self):
        p = None
        promo_data = json.loads(self.request.body)
        email = promo_data.get('email', None)
        if email:
            p = Promotional.get_by_auth_id(email)
        if not p:
            status = make_status_message(success=False,
                                         message='email not in db',
                                         code=1)
            self.response.write(status)
            return
        if not jconfig.on_dev_server():
            body = FORGOT_PROMO_ID_EMAIL_MESSAGE.format(p.promo_id)
            mail.send_mail(sender=EMAIL_SENDER,
                           to=p.email,
                           subject="Your NearWoo Rep ID",
                           body=body)
        status = make_status_message(success=True,
                                     message=p.promo_id,
                                     code=0)
        self.response.write(status)


class ForgotPromoPassword(webapp2.RequestHandler):

    def post(self):
        p = None
        promo_data = json.loads(self.request.body)
        promo_id = promo_data.get('promo_id', None)
        if promo_id:
            p = Promotional.get_by_auth_id(promo_id)
        if not p:
            msg = 'promo_id does not exist'
            status = make_status_message(success=False,
                                         message=msg)
            self.response.write(status)
            return
        if not p.verified:
            msg = 'promo has not verified email address'
            status = make_status_message(success=False,
                                         message=msg)
            self.response.write(status)
            return

        token = Promotional.create_auth_token(promo_id)
        verification_url = self.uri_for('verifypromotional',
                                        promo_id=promo_id,
                                        token=token,
                                        _full=True)
        if not jconfig.on_dev_server():
            body = FORGOT_PASSWORD_EMAIL_MESSAGE.format(verification_url)
            mail.send_mail(sender=EMAIL_SENDER,
                           to=p.email,
                           # bcc='sales@pagewoo.com',
                           subject="Reset your NearWoo password",
                           body=body)
        status = make_status_message(success=True,
                                     message=verification_url)
        self.response.write(status)


class PromotionalInfo(BaseRequestHandler):

    def get(self, **kwargs):
        if 'promo_id' in kwargs:
            promo_id = kwargs['promo_id']
            logging.info('promoinfo called with ' + str(promo_id))
            p = Promotional.get_by_auth_id(promo_id)
        else:
            # get user from session
            p = self.current_user
            logging.info('promoinfo session found with ' + str(p.promo_id))
        if not p:
            status = make_status_message(success=False,
                                         message='promo not found')
            self.response.write(status)
            return
        promo_info = p._to_dict()
        for k, v in promo_info.items():
            if k == 'password' or k == 'applied' or k == 'applied_to_campaigns':
                del promo_info[k]
            if isinstance(v, (datetime.date, datetime.datetime)):
                promo_info[k] = datetime_to_str(v)
        status = make_status_message(success=True,
                                     message='promo info',
                                     data=promo_info)
        self.response.write(status)


# list campaigns for the advertiser that is currently logged in

class ListAdvertiserCampaigns(BaseRequestHandler):

    def get(self, advertiser_key):
        q = NearWooCampaignDS.query()
        q = q.filter(NearWooCampaignDS.advertiser_key == advertiser_key)
        camps = []
        for camp in q.fetch(100):
            camps.append(dict(
                campaign_key=camp.key.urlsafe(),
                name=camp.name,
                advertiser_key=advertiser_key,
                date_created=str(camp.date_created),
                neighborhood_ct=camp.neighborhood_ct,
                start_time=camp.start_time,
            ))
        status = make_status_message(success=True,
                                     message='camps',
                                     data=camps)
        self.response.write(status)


# if view privileges

class ListCampaigns(BaseRequestHandler):

    def get(self):
        if self.logged_in:
            promo = self.current_user
        else:
            status = make_status_message(success=False,
                                         message='rep needs to be logged in')
            self.response.write(status)
            return
        q = NearWooCampaignDS.query(NearWooCampaignDS.promo_id ==
                promo.promo_id)
        camps = []
        for camp in q.fetch(100):
            camps.append({'campaign_key': camp.key.urlsafe(),
                          'name': camp.name,
                          'neighborhood_ct': camp.neighborhood_ct,
                          'amount_subscribed': camp.amount_subscribed,
                          'amt_spent': camp.amount_spent,
                          'advertiser_key': camp.advertiser_key})
        logging.info('camps: ' + json.dumps(camps))
        status = make_status_message(success=True,
                                     message='camps',
                                     data=camps)
        self.response.write(status)


# promotional uri general purpose handlers

class CatchPromotionalUri(BaseRequestHandler):

    def head(self, promo_uri_segment):
        self.response.write('cancel robots')

    def get(self, promo_uri_segment):
        try:
            email_template = self.request.get('template', None)
            if email_template:
                logging.info('email_template ' + str(email_template))
            email_plan = self.request.get('email_plan', None)
            if email_plan:
                logging.info('email_plan ' + str(email_plan))
            if email_template:
                self.session['email_template'] = email_template
                self.session['email_plan'] = email_plan
            email = self.request.get('email', None)
            if email:
                self.session['email'] = email
            seg = PromotionalUriSegment.get_by_auth_id(
                promo_uri_segment.strip().lower())
            if not seg:
                self.redirect(PROMO_CALLBACK_REDIRECT)
            else:
                self.session['promo_id'] = seg.promo_id
                partner_promo_category = self.request.get('code', None)
                self.session['promo_category'] = partner_promo_category
                func_to_backend(track_promo_uri_views, promo_uri_segment,
                                partner_promo_category=partner_promo_category)
        except Exception as e:
            logging.exception(e)
        wholesale_partner = False
        if seg and seg.promo_id:
            promo = Promotional.gql('where promo_id = :1', seg.promo_id).get()
            if promo is not None:
                partner = Partner.gql(
                    'where partner_id = :1', promo.partner_id).get()
                if partner and partner.wholesale:
                    wholesale_partner = True
        if wholesale_partner:
            logging.info('redirecting to: ' + WHOLESALE_PARTNER_REDIRECT)
            self.redirect(WHOLESALE_PARTNER_REDIRECT)
        else:
            logging.info('redirecting to: ' + PROMO_CALLBACK_REDIRECT)
            self.redirect(PROMO_CALLBACK_REDIRECT)


class PromoIDFromSession(BaseRequestHandler):

    def get(self):
        logging.debug('promo id from session %s', self.session)
        promo_id = self.session.get('promo_id', None)
        promo_category = self.session.get('promo_category', None)
        email_template = self.session.get('email_template', None)
        email_plan = self.session.get('email_plan', None)
        email = self.session.get('email', None)
        if promo_id is not None:
            msg = 'found promo id'
            data = {'promo_id': promo_id,
                    'promo_category': promo_category,
                    'email_plan': email_plan,
                    'email_template': email_template,
                    'email': email}
            status = make_status_message(success=True, message=msg, data=data)
        else:
            msg = 'did not find promo id'
            status = make_status_message(success=False, message=msg)
        self.response.write(status)


class UpdateCampaignPromotional(webapp2.RequestHandler):

    def get(self, promo_id, partner_promo_category, n_block_groups, camp_key):
        """ update all DS relating to updating a given campaign with a new promo code """
        update_campaign_promotional(
            promo_id, partner_promo_category, n_block_groups, camp_key)
        status = make_status_message(
            success=True, message='updated ds with new promo')
        self.response.write(status)


def update_campaign_promotional(
        promo_id, partner_promo_category, n_block_groups,
        camp_key):
        """ update all DS relating to updating a given campaign with a new promo code """
        promo = Promotional.get_by_auth_id(promo_id)
        n_block_groups = int(n_block_groups)
        partner_id = promo.partner_id
        partner = Partner.get_by_auth_id(partner_id)

        # If we don't get a Partner Promo Category then get the Promo Category
        # (default) from the partner
        if partner_promo_category in ['None', 'none', None, 'null', 'undefined', '']:
            ppc_label = 'none'
            pc_label = partner.nearwoo_default_promo_category
            pc = PromoCategory.get_by_id(pc_label)
        else:
            pc = PartnerPromoCategory.get_by_id(
                promo.partner_id + ':' + partner_promo_category)
            pc_label = pc.nearwoo_label
            ppc_label = pc.label
        partner_key = partner.key.urlsafe()
        promo_key = promo.key.urlsafe()

        # update campaign with new promo information
        camp = NearWooCampaignDS.urlsafe_get(camp_key)
        camp.neighborhood_ct = n_block_groups
        camp.promo_id = promo_id
        camp.partner_id = partner_id
        camp.promo_category = pc_label
        camp.partner_promo_category = ppc_label
        camp.discount_type = pc.discount_type
        if camp.discount_type == 'percent':
            camp.percent_discount = pc.percent_discount
        else:
            camp.absolute_discount = pc.absolute_discount
        camp.min_block_groups = pc.min_block_groups
        camp.min_campaign_value = pc.min_campaign_value
        camp.put()

        # update partner
        if not camp_key in partner.campaigns:
            partner.campaigns.append(camp_key)
        partner.put()

        # update promo
        if not camp_key in promo.campaigns:
            promo.campaigns.append(camp_key)
        today = datetime.datetime.today()
        promo.applied.append(today)
        occ = [camp_key, datetime_to_str(today)]
        promo.applied_to_campaigns.append(occ)
        promo.put()

        # update advertiser
        adv = ndb.Key(urlsafe=camp.advertiser_key).get()
        adv.partner_id = partner_id
        adv.promo_id = promo_id
        adv.partner_key = partner_key
        adv.promo_key = promo_key
        adv.put()


class ApplyPromotional(webapp2.RequestHandler):
    def get(self, promo_id, n_block_groups, campaign_value):
        pc_label = self.request.get('promo_category', None)
        home_value = float(self.request.get('home_cost', 50))
        status = apply_promo(
            promo_id, pc_label, n_block_groups, campaign_value, home_value)
        self.response.write(status)


# Returns a status message with data about the promotionals
def apply_promo(promo_id, pc_label, n_block_groups, campaign_value,
                home_value=50):
    promo = Promotional.get_by_auth_id(promo_id)

    # Make sure we have all the parameters we need
    if not promo:
        logging.info('PROMO NOT FOUND')
        status = make_status_message(
            success=False, code=1, message='promo not found')
        return status
    try:
        n_block_groups = int(n_block_groups)
        campaign_value = float(campaign_value)
    except ValueError:
        msg = ('n_block_group needs to be int-castable, ' +
               'campaign_value needs to be float-castable', 2)
        return make_status_message(success=False, code=2, message=msg)

    today = datetime.datetime.today()
    logging.info('pc_label: %s', pc_label)

    # if we have no promo category get it from the partner of the promo (rep)
    partner = Partner.get_by_auth_id(promo.partner_id)
    if not partner:
        msg = 'Could not find Partner for rep: ' + str(promo_id)
        status = make_status_message(success=False, code=8, message=msg)
        return status

    pc = partner.get_promo_category(pc_label)

    # check if it's valid
    if pc and ((pc.starts and today < pc.starts) or
              (pc.expires and today > pc.expires)):
        return make_status_message(
            success=False, message='Promo code inactive', code=3)

    if not pc:
        pc_label = partner.nearwoo_default_promo_category
        logging.debug('not in PPC pc_label' + str(pc_label))
        pc = PromoCategory.get_by_id(pc_label)

    if not pc:
        return make_status_message(
            success=False, message='Could not find this promo category', code=7)

    # if n_block_groups < pc.min_block_groups:
    # return make_status_message(success=False, message='too few block groups
    # to apply discount', code=4)

    # set default
    home_discounted_amount = home_value

    if campaign_value < pc.min_campaign_value:
        msg = ('campaign value %s is below minimum campaign value (%s)'
               'to apply discount' % (campaign_value, pc.min_campaign_value))
        logging.debug(msg)
        return make_status_message(success=False, message=msg, code=5)

    logging.debug('PPC DISCOUNTS ')
    logging.debug('Absolute Discount: %s', pc.absolute_discount)
    logging.debug('Home Absolute Discount: %s', pc.home_absolute_discount)
    logging.debug('Percent Discount %s', pc.percent_discount)
    logging.debug('Home Percent Discount %s', pc.home_percent_discount)

    if (campaign_value == 0):
        data = {
            'discounted_amount': 0.0,
            'discount': 0.0,
            'percent_discount': 0.0,
            'absolute_discount': 0.0,
            'the_discount': '0 absolute',
            'discount_type': 'absolute'}
    elif pc.discount_type == 'absolute':
        discounted = max(campaign_value - pc.absolute_discount, 0.0)
        if pc.home_absolute_discount:
            home_discounted_amount = max(
                home_value - pc.home_absolute_discount, 0.0)
        logging.info('discounted ' + str(discounted))
        data = {
            'discounted_amount': discounted,
            'discount': pc.absolute_discount,
            'home_discount': pc.home_absolute_discount or 0.0,
            'home_discounted_amount': home_discounted_amount,
            'percent_discount': 0,
            'absolute_discount': campaign_value - discounted,
            'the_discount': '$' + str(pc.absolute_discount),
            'the_home_discount': str(pc.home_absolute_discount) + ' absolute',
            'discount_type': 'absolute'}
    elif pc.discount_type == 'percent':
        discounted = max(
            round(campaign_value*
                (float(100.0 - pc.percent_discount) / 100.0), 2), 0.0)
        if pc.home_percent_discount:
            home_discounted_amount = max(
                round(home_value*
                    (float(100.0 - pc.home_percent_discount) / 100.0), 2), 0.0)
        data = {
            'discounted_amount': discounted,
            'home_discounted_amount': home_discounted_amount,
            'home_discount': home_value-home_discounted_amount,
            'discount': campaign_value-discounted,
            'percent_discount': campaign_value - discounted,
            'absolute_discount': 0,
            'the_discount': str(pc.percent_discount) + ' percent',
            'discount_type': 'percent'
        }
    # account for legacy codes without "is_recurring" field
    is_recurring = pc.is_recurring if pc.is_recurring is not None else False
    data['is_recurring'] = is_recurring
    data['promo_id'] = promo_id
    data['promo_category'] = pc_label
    data['partner_id'] = promo.partner_id
    data['partner_promo_category'] = pc_label
    status = make_status_message(success=True, message='everything went fine',
                                 code=0, data=data)
    return status

# Media Lib


class MediaLibrary(BaseRequestHandler):

    def get(self):
        # assumes user is logged in
        if self.logged_in:
            promo = self.current_user
            lib = PartnerMediaLibrary.query()
            lib = lib.filter(
                PartnerMediaLibrary.partner_id == promo.partner_id)
            lib = lib.order(-PartnerMediaLibrary.created)
            data = []
            for img in lib:
                if img.promo_category in promo.promo_categories and img.promo_category_is_valid:
                    d = img._to_dict()
                    d['created'] = datetime_to_str(d['created'])
                    data.append(d)
            msg = 'rep images'
            status = make_status_message(success=True, message=msg, data=data)
        else:
            msg = 'rep needs to be logged in'
            status = make_status_message(success=False, message=msg)
        self.response.write(status)

#
# def _resend_promotional_verification_link(promo_id):
#  p = Promotional.get_by_auth_id(promo_id)
#  if not p:
#    msg = 'User with promo_id %s does not exist' % promo_id
#    return make_status_message(success=False, message=msg)
#  if p.verified:
#    msg = 'User with promo_id %s already verified' % promo_id
#    return make_status_message(success=False, message=msg)
#  token = Promotional.create_auth_token(promo_id)
#  verification_url = self.uri_for('verifypromotional',
#                                  promo_id=promo_id,
#                                  token=token,
#                                  _full=True)
#  if not jconfig.on_dev_server():
#    body = VERIFY_EMAIL_MESSAGE.format(promo_id, verification_url)
#    mail.send_mail(sender=EMAIL_SENDER,
#                   to=promo_data['email'],
# bcc to sales, so that they can re-send the
# verification link
#                   bcc='alice@pagewoo.com',
#                   subject="Your NearWoo account",
#                   body=body)
#  return make_status_message(success=True, message=verification_url)
#
#
# class ResendPromotionalVerificationLink(webapp2.RequestHandler):
#  def post(self, promo_id):
#    status = _resend_verification_link(promo_id)
#    self.response.write(status)
#
