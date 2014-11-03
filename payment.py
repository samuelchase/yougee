from google.appengine.api import urlfetch
from google.appengine.ext import deferred
from google.appengine.ext import ndb
from google.appengine.api import users
import webapp2
import logging
import math
import json
import datetime


from nearwoo_sessions import BaseRequestHandler
from models import StripeDS
from models import Advertiser
from models import Partner
from models import PartnerPromoCategory
from models import Promotional
from models import YelpJsonDS
from models import NearWooCampaignDS
from models import Invoices
from models import PaymentErrors
from models import EmailPlan
from models import EmailTemplate
from models import MarketingContact
from models import MiniHistoricalCampaignData
from models import ScheduledSuperCharge
from models import InternalErrorOnCharge
from models import LanderCustomer
from wootils import iterate
from wootils import save_in_transaction
from wootils import make_status_message
from wootils import func_to_backend
from wootils import get_advertiser_by_yelp
from wootils import get_time_qualifier
from wootils import convert_start_time
from wootils import ordinal
from wootils import add_months
from wootils import add_adamounts_to_yelp
from wootils import PageWooError
from wootils import to_pacific_time
from kpi_data import track_supercharge
from kpi_data import track_recurring
from kpi_data import track_new_campaign
from kpi_data import track_campaign_shuffle
from kpi_data import track_downgrade
from kpi_data import track_upgrade
from kpi_data import checkout_campaign
from transactional_emails import send_tmail
import promo_handlers
import jchernobyl_client
import stripe
import jconfig
import j_emails
import referrals
import wootils
import time


# Test Key
# stripe.api_key = '62Sr2aKd8Dp1KZno8DSHzUwAMEfC4XfW'
#### TODO: REVERT
# Real Key
# stripe.api_key = 'ZEaFndNzcWlDkSOGPeaI2O76ibLEvQ20'


stripe.api_key = jconfig.get_stripe_key()
pagewoo_host = 'http://app.pagewoo.com'
host = jconfig.get_host()

ERROR_EMAIL_WAIT_DAYS = 15

# we want internal failure to evaluate to False in if checks throughout
class FalseyObject(object):
    def __bool__(self):
        return False
    __nonzero__ = __bool__
# sentinel object to mark App Engine/code failure vs. payment failure
INTERNAL_FAILURE = FalseyObject()



#----------------------- DECORATORS begin ---------------------------

# Check Charge Error Decorator
def charge(original_function):
    def wrap(*args, **kwargs):
        success, err, inv = original_function(*args, **kwargs)
        logging.debug('success ' + str(success) + ' err ' + str(err))
        if not success:
            logging.error("Error message from original function %s: %s",
                          original_function, err)
            logging.warning(args)
            logging.warning(kwargs)
            camp_key = kwargs['camp_key']
            logging.info('camp_key ' + str(camp_key))
            camp = NearWooCampaignDS.urlsafe_get(str(camp_key))
            logging.info(camp)
            logging.error('About To Send Error message ')
            j_emails.send_payment_error_email(camp, err)
            logging.info(
                'SEND PAYMENT ERROR EMAIL +++++++++++++++++++++++++++')
            send_tmail(camp_key, 'payment_error')
        return success, err, inv
    return wrap


# Check Stripe Error Decorator
# first argument must be advertiser
def stripepayment(original_function):
    def wrap(*args, **kwargs):
        try:
            return original_function(*args, **kwargs), None
        except stripe.CardError, e:
            # Card Declined
            advertiser = kwargs['advertiser']
            campaign = kwargs['campaign']
            amt = args[0]
            body = e.json_body
            error = body['error']
            logging.error('Card Error: ' + str(error['message']))
            advertiser.payment_error = True
            payment_error(amt, advertiser, campaign, json.dumps(error))
            advertiser.put()
            try:
                return (False, error['message'])
            except Exception:
                logging.exception('could not grab message from error (%r)',
                                  error)
                return (False, str(error))
        except stripe.StripeError, e:
            # Some Problem Happened With Stripe
            advertiser = kwargs['advertiser']
            campaign = kwargs['campaign']
            amt = args[0]
            body = e.json_body
            error = 'no proper error response'
            if body and 'error' in body:
                error = body['error']
            logging.error('There was a problem with stripe')
            advertiser.payment_error = True
            payment_error(amt, advertiser, campaign, json.dumps(error))
            advertiser.put()
            try:
                return (False, error['message'])
            except Exception:
                logging.exception('could not grab message from error (%r)',
                                  error)
                return (False, str(error))
    return wrap

# Check Stripe Customer Decorator


def stripecustomer(original_function):
    def wrap(*args, **kwargs):
        try:
            logging.info('Stripe Customer ARGS ' + str(args))
            return original_function(*args)
        except stripe.CardError, e:
            # Card Declined
            advertiser_key = kwargs['advertiser']
            adv_key = ndb.Key(urlsafe=advertiser_key)
            adv = adv_key.get()
            body = e.json_body
            err = body['error']
            logging.error('Card Error: ' + str(err))
            j_emails.send_card_error_email(adv, err['message'])
            return None, err
        except stripe.StripeError, e:
            try:
                # Some Problem Happened With Stripe
                advertiser_key = kwargs['advertiser']
                adv_key = ndb.Key(urlsafe=advertiser_key)
                adv = adv_key.get()
                body = e.json_body
                err = body.get('error', None)
                logging.error('Card Error: %s', err)
                logging.error('There was a problem with Stripe')
                j_emails.send_card_error_email(adv, err['message'])
            except Exception:
                logging.exception(e)
                logging.critical('could not handle exception')
            return None, err
        except Exception as e:
            logging.error('SAM EXCEPTION %s', e)
        logging.warning('WRAP DEFINED')
    return wrap


# --------------------- Decorators end ---------------------------

# Creates a New Customer for a given stripe token and returns the stripe id
class StripeIdFromToken(webapp2.RequestHandler):

    def get(self, stripe_token):
        customer, status = save_new_stripe_customer(
            stripe_token, 'new customer')
        self.response.write(customer['id'])

# Creates a New Stripe Customer


@stripecustomer
def save_new_stripe_customer(stripe_token, advertiser='customer'):
    logging.warning(stripe_token)
    logging.warning(advertiser)
    customer = stripe.Customer.create(
        description=advertiser,
        card=stripe_token
    )
    return customer, None


class UpdateCustomer(webapp2.RequestHandler):

    def post(self):
        # obj = self.request.body
        #customer_id = obj['customer_id']
        self.response.write('customer account updated')


class DeleteCustomer(webapp2.RequestHandler):
    def post(self):
        obj = self.request.body
        customer_id = obj['customer_id']
        customer = stripe.Customer.retrieve(customer_id)
        customer.delete()
        plan = stripe.Plan.retrieve(customer_id)
        plan.delete()
        self.response.write('Customer and Plan has been deleted')


class AllCustomers(webapp2.RequestHandler):
    def post(self):
        all_customers = stripe.Customer.query()
        self.response.write(json.dumps(all_customers))



class StartCampaign(webapp2.RequestHandler):
    def get(self, campaign_key):
        camp = NearWooCampaignDS.urlsafe_get(campaign_key)
        camp.paused = False
        camp.is_live = True
        camp.put()
        try:
            jchernobyl_client.call_chernobyl(camp, retry=False)
            if self.request.get('charge', False):
                try:
                    charge_the_customer(camp_key=campaign_key)
                    self.response.write(make_status_message(
                        success=True,
                        message='Succesfully Restarted and Charged'))
                except Exception as e:
                    logging.exception(e)
            else:
                self.response.write(make_status_message(success=True, message='Succesfully Restarted'))
        except PageWooError as e:
            self.response.write(make_status_message(success=False,
                                                    message=e.message))
        except Exception:
            logging.exception('Failed to call chernobyl and restart campaign')
            self.response.write(make_status_message(success=False,
                                                    message='Server error'))



class PauseCampaign(webapp2.RequestHandler):
    def get(self, campaign_key):
        camp = NearWooCampaignDS.urlsafe_get(campaign_key)
        # force separate object
        original_camp = camp.key.get()
        camp.paused = True
        camp.is_live = False
        camp.last_paused = datetime.datetime.today()
        camp.put()
        try:
            jchernobyl_client.call_chernobyl(camp, retry=False)
            logging.info('Successfully paused campaign')
            self.response.write(make_status_message(success=True,
                                                    message='Paused campaign'))
        except PageWooError as e:
            if camp.woos_left:
                self.response.write(make_status_message(success=False,
                                                        message='Failed to pause: %s' % e.message))
                original_camp.put()
            else:
                self.response.write(make_status_message(success=True,
                                                        message='already'
                                                        'inactive campaign'
                                                        'marked as paused'))
        except Exception:
            self.response.write(make_status_message(success=False,
                                                    message='server error'))
            original_camp.put()


# We need to charge their account
# Every Day Cron Job charge all recurring campaigns
class ChargeCustomers(webapp2.RequestHandler):
    def get(self):
        day_of_month = self.request.get('day', None)
        if day_of_month:
            logging.debug('day specified ' + str(day_of_month))
            charge_customers(int(day_of_month))
        else:
            charge_customers()
        self.response.write('charges')


class ChargeCustomer(webapp2.RequestHandler):
    def get(self, campaign_key):
        user = users.get_current_user()
        force = self.request.get('force', False)
        force = int(force)
        result = charge_the_customer(camp_key=campaign_key, user=user, force=force)
        self.response.write(result)


def partner_is_wholesale(partner_id):
    p = Partner.gql('where partner_id = :1', partner_id).get()
    if p:
        if p.wholesale:
            return True, p.stripe_id
        else:
            return False, None
    else:
        return False, None


def partner_is_wholesale2(partner_id):
    p = Partner.gql('where partner_id = :1', partner_id).get()
    if p:
        if p.wholesale:
            return True, p.stripe_id, p.wholesale_price
        else:
            return False, None, p.wholesale_price
    else:
        return False, None, None

class BuyBlockPoints(webapp2.RequestHandler):
    def post(self):
        obj = json.loads(self.request.body)
        campaign_key = obj['campaign_key']
        advertiser_key = obj['advertiser_key']
        num_block_points = int(obj['num_block_points'])
        campaign = NearWooCampaignDS.urlsafe_get(campaign_key)
        logging.debug('Num Block Points ' + str(num_block_points))
        logging.debug('Retail Price ' + str(campaign.retail_price))
        amt_to_charge = int(num_block_points * campaign.retail_price) * 100
        adv_key = ndb.Key(urlsafe=advertiser_key)
        adv = adv_key.get()
        charge, err, _ = charge_advertiser(
                    amt_to_charge, adv, campaign,
                    charge_type='blockpoints',
                    camp_key=campaign_key)
        if charge:
            adv.block_points += num_block_points
            adv.put()
            msg = make_status_message(success=True, message ='Succesfully charged ' + str(num_block_points) + ' at ' + str(campaign.retail_price))
        else:
            msg = make_status_message(success=False, message ='Charge Failed, credit card error \n' + str(err))

        self.response.out.write(msg)


class ScheduleSuperCharge(webapp2.RequestHandler):
    def get(self, camp_key):
        today = datetime.datetime.today()
        supercharges = ScheduledSuperCharge.gql(
            'where campaign_key = :1 and scheduled > :2',
            camp_key, today).fetch(1000)
        result = []
        for s in supercharges:
            result.append({
                'date': s.scheduled.strftime("%m-%d-%Y"),
                'hour':s.scheduled.hour,
                'impressions':s.impressions})
        if result:
            msg = make_status_message(
                success=True, message='Found Schedule', data=result)
        else:
            msg = make_status_message(
                success=False, message='No Supercharges Found', data=[])
        self.response.write(msg)

    def post(self):
        obj = json.loads(self.request.body)
        campaign_key = obj['campaign_key']
        advertiser_key = obj['advertiser_key']
        num_block_points = int(obj['points'])
        day = obj['day'].split('-')
        scheduled = datetime.datetime(
            int(day[0]), int(day[1]), int(day[2]), int(obj['hour']))
        camp = NearWooCampaignDS.urlsafe_get(campaign_key)
        # TODO: associate invoice with this supercharge
        s = ScheduledSuperCharge()
        s.advertiser_key = advertiser_key
        s.impressions = num_block_points * 1000
        logging.debug('Scheduling SuperCharge %s', str(s.impressions))
        s.campaign_key = campaign_key
        s.points = num_block_points
        s.retail_price = camp.retail_price
        s.scheduled = scheduled
        s.put()
        adv_key = ndb.Key(urlsafe=advertiser_key)
        adv = adv_key.get()
        adv.block_points = adv.block_points - num_block_points
        adv.put()


class RunSuperCharges(webapp2.RequestHandler):
    # TODO Currently Not scalable past 1000 for a specific year/month/day/hour
    def get(self):

        hour = self.request.get('hour', None)
        now = datetime.datetime.now()
        delta = datetime.timedelta(hours=1)
        if hour:
            logging.debug('HOUR NOW')
            now = datetime.datetime(now.year, now.month, now.day, int(hour))

        before = datetime.datetime(now.year, now.month, now.day, now.hour)
        before = before - delta
        after = datetime.datetime(now.year, now.month, now.day, now.hour)
        after = after + delta

        logging.debug('Before: %s', before.strftime("%H-%m-%d-%Y"))
        logging.debug('After: %s ', after.strftime("%H-%m-%d-%Y"))

        supercharges = ScheduledSuperCharge.gql(
            'where scheduled > :1 and scheduled < :2',
            before, after).fetch(1000)
        logging.debug('SuperCharges %s', str(supercharges))

        for supercharge in supercharges:
            logging.debug('Running Supercharge: %s', str(supercharge.to_dict()))
            campaign = None
            try:
                campaign = NearWooCampaignDS.urlsafe_get(
                    supercharge.campaign_key)
                impressions = supercharge.impressions
                success = supercharge(campaign, supercharge.key.id(), impressions)
                campaign.put()
                amt_to_charge = impressions*campaign.retail_price

                if success:
                    func_to_backend(track_supercharge, campaign, amt_to_charge,
                                    impressions,
                                    block_points_used=supercharge.points)
                    backend_host = jconfig.get_backend_host()
                    value = float(amt_to_charge)
                    rpc = urlfetch.create_rpc()
                    wootils.make_fetch_call_no_cache(
                        rpc, backend_host +
                        '/kpidata/incrementsuperchargecounters/' +
                        supercharge.campaign_key + '/' + str(impressions) + '/' + str(value))
                    j_emails.send_supercharge_email(campaign, impressions)
                    # send transactional to user
                    send_tmail(campaign.key.urlsafe(), 'supercharge')
                else:
                    supercharge.error = 'error'
                    supercharge.put()
            except Exception as e:
                logging.exception('Failed to supercharge for campaign: %s',
                                  campaign.key.urlsafe() if campaign else None)
                supercharge.error = str(e) # this is wrong?
                supercharge.put()
        self.response.write('success')


class SuperChargeCampaign(webapp2.RequestHandler):
    def post(self):
        user = users.get_current_user()
        data = json.loads(self.request.body)
        advertiser_key = data['advertiser_key']
        campaign_key = data['campaign_key']
        amt_to_charge = data['amt_to_charge']
        impressions = data['impressions']
        points = data['points']
        logging.info("POINTS = " + str(points))
        adv_key = ndb.Key(urlsafe=advertiser_key)
        adv = adv_key.get()
        points = int(points)
        amt_to_charge = float(amt_to_charge)
        point_diff = 0
        block_points_applied = 0
        if points:
            if adv.block_points > points:
                point_diff = adv.block_points - points
                adv.block_points = point_diff
                block_points_applied = points
                amt_to_charge = 0
                adv.put()
            else:
                amt_to_charge = amt_to_charge - (adv.block_points * 10)
                block_points_applied = adv.block_points
                adv.block_points = 0
                adv.put()

        impressions = int(impressions)
        if not impressions:
            m = 'NO IMPRESSIONS TO CHARGE'
            logging.error(m)
            msg = make_status_message(success=False, code=400, message=m)
            self.response.write(msg)
            return
        if not adv:
            m = 'No Advertiser Found'
            logging.error(m)
            msg = make_status_message(success=False, code=400, message=m)
            self.response.write(msg)
            return
        campaign = NearWooCampaignDS.urlsafe_get(campaign_key)
        if not campaign:
            m = 'No Campaign Found'
            logging.error(m)
            msg = make_status_message(success=False, code=400, message=m)
            self.response.write(msg)
            return

        previous_data = MiniHistoricalCampaignData.from_campaign(
                campaign)

        pagewoo_key = campaign.pagewoo_campaign_key

        if not pagewoo_key:
            m = 'No PageWoo Key Found'
            logging.error(m)
            msg = make_status_message(success=False, code=400, message=m)
            self.response.write(msg)
            return

        amt_to_charge = int(amt_to_charge * 100)

        if amt_to_charge:
            logging.info('Charging ' + str(amt_to_charge))
            # COME BACK AND LOOK AT THIS!!!
            supercharge = {'impressions': impressions, 'cost': amt_to_charge}
            is_wholesale, partner_stripe_id, wholesale_price = (
                partner_is_wholesale2(campaign.partner_id))
            if is_wholesale:
                logging.warning('Wholesale Price %s', wholesale_price)
                logging.warning('amt_to_charge before %s'. amt_to_charge)
                amt_to_charge = int((amt_to_charge / 10) * wholesale_price)
                logging.warning('amt_to_charge after %s', amt_to_charge)
                charge, err, inv = charge_partner(
                    amt_to_charge, adv, campaign.partner_id,
                    partner_stripe_id, campaign, 'supercharge',
                    supercharge=supercharge, camp_key=campaign.key.urlsafe(),
                    block_points_applied=block_points_applied)
                if not charge:
                    msg = make_status_message(
                        success=False, code=400, message=m)
                    self.response.write(msg)
                    return
            else:
                charge, err, inv = charge_advertiser(
                    amt_to_charge, adv, campaign,
                    charge_type='supercharge', supercharge=supercharge,
                    camp_key=campaign.key.urlsafe(),
                    block_points_applied=block_points_applied)
                if not charge:
                    msg = make_status_message(
                        success=False, code=400, message=m)
                    self.response.write(msg)
                    return

        success = supercharge(campaign, inv.key.id(), impressions)
        campaign.put()

        if success:
            func_to_backend(track_supercharge, campaign, amt_to_charge / 100.0,
                            impressions, block_points_used=points,
                            previous_data=previous_data, user=user)
            backend_host = jconfig.get_backend_host()
            value = float(amt_to_charge) / 100
            rpc = urlfetch.create_rpc()
            wootils.make_fetch_call_no_cache(
                rpc, backend_host +
                '/kpidata/incrementsuperchargecounters/' +
                campaign_key + '/' + str(impressions) + '/' + str(value))
            j_emails.send_supercharge_email(campaign, impressions)

            # send transactional to user
            send_tmail(campaign.key.urlsafe(), 'supercharge')

            msg = make_status_message(
                success=True, code=200, message='Succesful Supercharge')
            self.response.write(msg)
        else:
            msg = make_status_message(
                success=False, code=400, message='failed set rtb controls')
            self.response.write(msg)


def prorate(charge_day, amount_subscribed):
    today = datetime.datetime.utcnow().day
    if charge_day:
        # If the last charge occurred last month
        if today < charge_day:
            last_month_diff = 30 - charge_day
            total_diff = last_month_diff + today
            left_over = 30 - total_diff
        # If the last charge occurred this month
        else:
            total_diff = today - charge_day
            left_over = 30 - total_diff

        left_over_pct = float(left_over) / 30
        pro_rate = amount_subscribed * left_over_pct
        return pro_rate
    else:
        return 0


def recalculate_charges(amount_subscribed, wholesale_price, charge_day,
                        neighborhood_ct):
    amount_subscribed = (neighborhood_ct-1) * wholesale_price
    pro_rate = prorate(charge_day, amount_subscribed)
    initial_charge = max(amount_subscribed - pro_rate, 0)
    return initial_charge, amount_subscribed


def register_techscout_sale(promo_id, camp, charge):
    rep = Promotional.gql('where promo_id = :1', promo_id).get()
    if rep:
        if rep.partner_id == 'techscouts':
            # call out to techscouts
            post_data = {}
            post_data['scout_number'] = int(promo_id[5:])
            post_data['amount_subscribed'] = camp.amount_subscribed
            post_data['amount_charged'] = float(0)
            post_data['business_name'] = camp.store or camp.name
            post_data['business_category'] = camp.business_category
            logging.error('Calling ' + jconfig.scouts_url() + '/fieldsignup')
            try:
                respo = urlfetch.fetch(jconfig.scouts_url() + '/fieldsignup', method='POST', payload=json.dumps(post_data), deadline=60)
                content = json.loads(respo.content)
                if content['status'] == 'success':
                    logging.info('Field Signup Registered')
                else:
                    logging.error(respo.content)
            except Exception:
                logging.exception('Error Calling techschouts')


class LanderCharge(webapp2.RequestHandler):
    def post(self):
        stripe.api_key = jconfig.get_stripe_key()
        data = json.loads(self.request.body)
        token = data['token']
        charge_amount = float(data['charge_amount'])
        amt = int(charge_amount * 100)

        try:
            customer, error = save_new_stripe_customer(token, advertiser=data['full_name'])
            stripe_id = customer['active_card']['customer']
            logging.info('Stripe ID ' + str(stripe_id))

        except Exception:
            logging.exception('Customer Creation Error')
            self.response.write('Failed to create stripe customer')
            return
        try:
            logging.error('AMT: ' + str(amt))
            if amt > 50: 
                charge = charge_customer(amt, 'usd', stripe_id, description='lander')


                

                if charge:
                    t = LanderCustomer()
                    t.name = data['full_name']
                    t.charge_amount = charge_amount
                    t.url = data['url']
                    t.email = data['email']
                    t.business_type = data['business_type']
                    t.business_name = data['business_name']
                    t.impressions = int(data['impressions'])
                    t.stripe_id = stripe_id
                    t.ad_copy = data['ad_copy']

                    try:
                        t.start_date = datetime.datetime.strptime(data['start_date'], '%m/%d/%Y')
                        t.end_date = datetime.datetime.strptime(data['end_date'], '%m/%d/%Y')
                    except Exception:
                        logging.exception('DateTime Conversion Failed')
                        logging.error(data['start_date'])
                        logging.error(data['end_date'])
                    t.put()

                logging.info(str(charge))
                msg = make_status_message(success=True, data=[], message='Successful charge')
                self.response.write(msg)
                j_emails.send_jake_email(data, charge_amount, stripe_id, ' ')
            else:
                msg = make_status_message(success=False, data=[], message='Nothing to charge')
                j_emails.send_jake_email(data, charge_amount, stripe_id, 'not enough impressions to charge')
                self.response.write(msg)
        except Exception:
            logging.exception('Customer Charge Error')
            msg = make_status_message(success=False, data=[], message='Sorry, but your card had been declined.')
            j_emails.send_jake_email(data, charge_amount, stripe_id, 'card error')
            self.response.write(msg)
            return



class NucleusCampaignCreator(webapp2.RequestHandler):
    ''' Called for AdNucleus Campaign Creation'''
    def post(self):
        data = json.loads(self.request.body)
        nadv_key = data['nadv_key']
        nadv = models.NucleusAdvertiser.urlsafe_get(nadv_key)
        
        yelp = YelpJsonDS()
        yelp.name = nadv.name
        yelp.advertiser_key = nadv_key
        yelp.put()
        
        camp = NearWooCampaignDS()
        camp.yelp_key = yelp.key.urlsafe()

        if data['creative_type'] == 'mobile_display':
            camp.creative_type = models.CreativeType.mobile_display
        elif data['creative_type'] == 'web_display':
            camp.creative_type = models.CreativeType.web_display
        elif data['creative_type'] == 'mobile_video':
            camp.creative_type = models.CreativeType.mobile_video
        elif data['creative_type'] == 'web_video':
            camp.creative_type = models.CreativeType.web_video

        camp.nucleus_camp_name = data['nucleus_camp_name']
        camp.name = data['flight_name']
        camp.target_cpm = data['target_cpm']
        camp.budget = data['budget']
        
        camp.start_date = convert_date(data['start_date'])
        camp.end_date = convert_date(data['end_date'])

        # set_time_for_camp Still use fallback time?
        camp.start_time = convert_start_time(data['start_time'])
        camp.end_time = convert_start_time(data['end_time'])
        camp.segments = data['segments']
        camp.advertiser_key = nadv_key

        camp.store = data['flight_name']
        camp.search = create_search_list(yelp_data['flight_name'])
        camp.play = True
        camp.paid = True

        camp.block_groups = data['block_groups']
        camp.neighborhood_ct = int(len(data['block_groups']))

        # How do we calculate
        camp.max_views = int(data['max_views'])
        adamount = camp.max_views/camp.neighborhood_ct

        # Just evenly spread the adamounts based on max_views
        camp.adamounts = []
        for i in range(len(camp.neighborhood_ct)):
            camp.adamounts.append(adamount)

        # charge the customer
        charge, err, _ = charge_nucleus_advertiser(amt, advertiser, campaign, charge_type, camp_key=None)

        if charge:
            camp = save_in_transaction(camp)

            camp.my_key = camp.key.urlsafe()
                # Set pagination dates
            camp.pagination_date_created = str(
                camp.date_created) + '|' + camp.key.urlsafe()
            # set to created as a fallback
            camp.pagination_checked_out_created = str(
                camp.date_created) + '|' + camp.key.urlsafe()
           
            # make campaign key searchable
            camp = wootils.make_camp_search_key_from_camp(camp)

            camp = save_in_transaction(camp)

            yelp.campaign_key = camp.key.urlsafe()
            yelp.rep_build_status = 'live'
            yelp.checked_out = True
            yelp.put()

            func_to_backend(jchernobyl_client.call_chernobyl,
                            camp.key.urlsafe())
           
            self.response.out.write(make_status_message(code=200, message='successful checkout', data=camp.to_dict()))
        else:
            self.response.out.write(make_status_message(code=500, message='Charge Failed', data=[]))



class CampaignCreator(BaseRequestHandler):
    """ Called for Campaign Creation and campaign updating
    WARNING: Retrieves Advertiser from yelp_key, advertiser not passed in """
    def create_campaign(
        self, yelp_key, data, amount_subscribed, num_bgs, initial_charge,
        billing_period, promo_cat, promo_id, pro_rate=0,
        downsell=0, use_block_points=0, wholesaler=None):
        """ TODO: Make sure this isn't deferred, otherwise we'll lose the user
        data """
        wholesaler = wholesaler or {}
        user = users.get_current_user()
        yelp = YelpJsonDS.urlsafe_get(yelp_key)
        yelp_data = data['yelp_data']
        if not yelp_data.get('adamounts'):
            logging.error('Must have non-empty adamounts in yelp data (found %s)' % yelp_data.get('adamounts'))
        camp = None
        # If the campaign for this yelp key exists simply update it
        # this campaign object is passed and returned from various functions
        # until it is finally saved and the campaign is created
        camp = None
        if yelp.campaign_key:
            camp = NearWooCampaignDS.urlsafe_get(yelp.campaign_key)
        if not camp:
            camp = NearWooCampaignDS.gql('WHERE yelp_key = :1', yelp_key).get()
            if camp:
                camp._manual_get_hook()
        if not camp:
            camp = NearWooCampaignDS()
            previous_data = None
        else:
            previous_data = MiniHistoricalCampaignData.from_campaign(camp)

        # Set the Name of the Business
        if not camp.name:
            try:
                camp.name = yelp_data.get('campaign_name', None)
                if not camp.name:
                    camp.name = yelp_data['name']
            except KeyError:
                logging.exception("Couldn't get campaign_name for %s",
                                  camp.key)

        adarray = yelp_data['adamounts']
        logging.error('adarray ' + str(adarray))
        max_views = sum(adarray)
        camp.adamounts = adarray
        logging.error('max_views ' + str(max_views))
        geoids = data['geoids']
        nuns = ['none', 'None', 'null', 'Null', 'undefined', '']
        if promo_id in nuns:
            promo_id = None
        if promo_cat in nuns:
            promo_cat = None
        is_new_campaign = False
        # Set Variables in the case this is a Partner Wholesaler
        if wholesaler:
            logging.info("Have wholesale variables")
            wholesale = wholesaler['wholesale']
            wholesale_price = wholesaler['wholesale_price']
            # TODO: fix this
            partner_id = wholesaler['partner_id']
            partner_stripe_id = wholesaler['partner_stripe_id']
        else:
            logging.info("No wholesale variables")
            wholesale = False
            wholesale_price = None   # default is 25$ a neighborhood
            partner_id = None
            partner_stripe_id = None

        # Set Yelp and Advertiser Keys
        camp.yelp_key = yelp_key
        adv = get_advertiser_by_yelp(yelp_key)
        adv_key = adv.key.urlsafe()
        camp.advertiser_key = adv_key

        # Set Business Type
        # yelp_data = json.loads(yelp.yelp_data)
        if 'biz_type' in yelp_data and 'name' in yelp_data['biz_type']:
            camp.business_type = yelp_data['biz_type']['name']
            logging.debug('Business Type: %s', camp.business_type)
        else:
            camp.business_type = 'none'
            logging.debug('No Business Type %s', camp.business_type)

        # Set Store Name and make searchable
        camp.store = yelp_data['name']
        camp.search = create_search_list(yelp_data['name'])
        camp.play = True

        # All Campaigns are now Paid Campaigns
        # Set Paid Flag
        geoids = data['geoids']
        if geoids:
            camp.paid = camp.home_price > 0 if len(geoids) == 1 else True
        else:
            camp.paid = False
        # Set Time for ads to start being delivered
        camp = set_time_for_camp(camp, yelp_data)
        # Get the existing state of the campaign
        (camp, old_amount_subscribed, old_neighborhood_ct, old_max_views, is_new_campaign) = (
            check_existing_camp(camp, yelp))
        # Reset the Neighborhood Count
        camp.neighborhood_ct = int(num_bgs)
        # Charges applied now
        initial_charge = float(initial_charge)
        # Number of months till recurring payment
        if billing_period:
            billing_period = int(billing_period)
            camp.billing_period = billing_period

        # If its a partner campaign set the retail_pice to 10$
        if wholesale_price:
            camp.retail_price = 10.0
            # recalculate initial_charge and amount_subscribed
            initial_charge, amount_subscribed = recalculate_charges(
                    amount_subscribed, wholesale_price,
                    camp.charge_day, int(num_bgs))

        # Set start_date, end_date, and budget
        if ('flight_plan' in yelp_data and
            (yelp_data['flight_plan']['start_camp_date'] and
            yelp_data['flight_plan']['end_camp_date'] and
            yelp_data['flight_plan']['camp_budget'])):
            camp.start_date = wootils.parse_date(
                yelp_data['flight_plan']['start_camp_date'])
            camp.end_date = wootils.parse_date(
                yelp_data['flight_plan']['end_camp_date'])
            camp.budget = float(yelp_data['flight_plan']['camp_budget'])
            # TODO: Soon we're going to switch to allow partners to specify the
            # client CPM they are budgeting, but for the moment 'budget' means
            # 'amount wholesale partner will charge client'
            new_views = int(math.ceil(camp.budget / 10 * 1000))
            logging.info("Forcing max views to %s (previously were %s) - this"
                         " will overwrite existing max views", new_views, camp.max_views)
            camp.max_views = new_views
            data['max_views'] = new_views
            rtb_controls = None
            if camp.pagewoo_campaign_key:
                try:
                    # TODO: ??
                    rtb_controls = {}
                    #rtb_controls = jchernobyl_client.get_rtb_controls(camp, raise_on_error=True)
                except PageWooError as e:
                    if "Couldn't find campaign" in e.message:
                        pass
                    else:
                        raise

            # create campaign data for pagewoo
            data = create_pagewoo_campaign_data(
                geoids, yelp_data, amount_subscribed, new_views, int(num_bgs),
                camp.waiting_for_content, camp.supercharge,
                camp.pagewoo_campaign_key, old_max_views=old_max_views,
                start_date=camp.start_date, end_date=camp.end_date,
                rtb_controls=rtb_controls)
            data['max_views'] = new_views
        else:
            rtb_controls = None
            if camp.pagewoo_campaign_key:
                try:
                    # TODO: ??
                    rtb_controls = {}
                    # rtb_controls = jchernobyl_client.get_rtb_controls(camp, raise_on_error=True)
                except PageWooError as e:
                    if "Couldn't find campaign" in e.message:
                        pass
                    else:
                        raise
            data = create_pagewoo_campaign_data(
                geoids, yelp_data, amount_subscribed, max_views, int(num_bgs),
                camp.waiting_for_content, camp.supercharge,
                camp.pagewoo_campaign_key, old_max_views=old_max_views,
                rtb_controls=rtb_controls)
        camp.data = json.dumps(data)

        # Set Amount Subscribed
        if camp.budget > 0:
            logging.info('Wholesale price: %s, budget: %s', wholesale_price,
                         camp.budget)
            amount_subscribed = round((camp.budget/10)*wholesale_price, 2)
            camp.amount_subscribed = amount_subscribed
            # we don't care about prorate b/c it's a flight plan!
            initial_charge = camp.amount_subscribed
        else:
            camp.amount_subscribed = round(amount_subscribed, 2)
        logging.info('AMOUNT SUBSCRIBED: %s', amount_subscribed)

        # pro_rate here is the amount to SUBTRACT
        # All discounts will be computed on the prorated amount
        amt_for_promo = initial_charge
        # Save initial charge after promo has been applied
        camp.initial_charge = initial_charge
        # this tells PW how many days are left with recurring campaigns. okay
        # to do this with flight plans b/c PW doesn't use this in that case
        camp.next_recharge_date = add_months(datetime.datetime.utcnow(), 1)
        # The Amount to actually charge the card
        amt_to_charge = int(amt_for_promo * 100)

        camp, _ = apply_promo_to_charge(
            camp, amt_to_charge, amt_for_promo, pro_rate,
            amount_subscribed, num_bgs, promo_id, promo_cat)

        # Apply Block Points
        if use_block_points:
            block_points_applied, amt_to_charge = apply_block_points(
                amt_to_charge, adv, camp.retail_price)
        else:
            block_points_applied = 0

        # CALL CHECKOUT
        if amt_to_charge < 0:
            amt_to_charge = 0
        if amount_subscribed < 0:
            amount_subscribed = 0

        # This Logic Doesn't hold with PROMOS
        # if old_amount_subscribed and not downsell:
        #     downsell = old_amount_subscribed > camp.amount_subscribed

        # If its a DOWNSELL charge nothing increment appropriate counters
        if downsell:
            # resave the geoids into a seperate geoids field in the YelpDS
            yelp = save_yelp_geoids(yelp_key, yelp_data, geoids)
            logging.warning('DOWNSELL')
            amt_to_charge = 0
            amount_subtracted = old_amount_subscribed - camp.amount_subscribed

            # If its a full downgrade send an email
            if camp.neighborhood_ct == 0 and old_neighborhood_ct > 1:
                j_emails.send_downgrade_email(adv, camp, old_neighborhood_ct,
                                              amount_subtracted)
            if old_neighborhood_ct == camp.neighborhood_ct:
                func_to_backend(
                    track_campaign_shuffle, camp, promo_id=promo_id,
                    partner_promo_category=promo_cat,
                    previous_data=previous_data, user=user)
            else:
                # Send transactional email for downgrade
                send_tmail(camp.key.urlsafe(), 'downgrade')
                # Increment Counters
                func_to_backend(track_downgrade, camp, old_amount_subscribed,
                                camp.amount_subscribed, old_neighborhood_ct,
                                camp.neighborhood_ct, promo_id=promo_id,
                                partner_promo_category=promo_cat,
                                previous_data=previous_data, user=user)
        charge = None
        err = None
        logging.info('CHARGING %s', amt_to_charge)
        # Make the Charge if this is paid
        if wholesale and amt_to_charge:
            logging.info('CHARGING PARTNER CARD')
            if is_new_campaign:
                charge, err, _ = charge_partner(
                    amt_to_charge, adv, partner_id, partner_stripe_id, camp,
                    'initial', camp_key=camp.key.urlsafe(),
                    block_points_applied=block_points_applied)
            else:
                charge, err, _ = charge_partner(
                    amt_to_charge, adv, partner_id, partner_stripe_id, camp,
                    'upgrade', camp_key=camp.key.urlsafe(),
                    block_points_applied=block_points_applied)
        elif amt_to_charge:
            if is_new_campaign:
                charge, err, _ = charge_advertiser(
                    amt_to_charge, adv, camp, 'initial',
                    camp_key=camp.key.urlsafe(),
                    block_points_applied=block_points_applied)
            else:
                charge, err, _ = charge_advertiser(
                    amt_to_charge, adv, camp, 'upgrade',
                    camp_key=camp.key.urlsafe(),
                    block_points_applied=block_points_applied)
        if err is not None:
            return err

        # Save the Campaign (only after we know the charge worked out)
        camp = save_in_transaction(camp)
        if charge or not amt_to_charge:
            # resave the geoids into a seperate geoids field in the YelpDS
            yelp = save_yelp_geoids(yelp_key, yelp_data, geoids)

            logging.info('Charge Success %s', charge)
            adv.payment_error = False
            adv.put()
            # send corresponding campaigin for pagewoo
            camp.my_key = camp.key.urlsafe()
            # Set pagination dates
            camp.pagination_date_created = str(
                camp.date_created) + '|' + camp.key.urlsafe()
            # set to created as a fallback
            camp.pagination_checked_out_created = str(
                camp.date_created) + '|' + camp.key.urlsafe()
            # make key searchable
            camp = save_in_transaction(camp)
            # make campaign key searchable
            camp = wootils.make_camp_search_key_from_camp(camp)
            # set yelp campaign key
            yelp.campaign_key = camp.key.urlsafe()
            yelp.rep_build_status = 'live'
            yelp.checked_out = True
            yelp.put()

            # Send to PageWoo (Chernobyl)
            # Update Emails
            email_plan_id = self.session.get('email_plan', None)
            if email_plan_id:
                logging.info('email_plan found ' + str(email_plan_id))
                update_email_plan(email_plan_id, amt_to_charge / 100)
            template_id = self.session.get('email_template', None)
            if template_id:
                logging.info('template found ' + str(template_id))
                update_email_template(template_id, amt_to_charge / 100)
            email = self.session.get('email', None)
            if email:
                remove_from_marketing_list(email)

            # If it's a paid checkout
            if charge:
                logging.debug('PAID CAMPAIGN')
                logging.debug("New Campaign? %s", is_new_campaign)
                if is_new_campaign:
                    if not camp.waiting_for_content:
                        send_tmail(camp.key.urlsafe(), 'camp_live')
                        # send email to kyla
                        j_emails.send_lang_email(camp)
                        # fieldsignup on techscouts
                        logging.error('ABOUT TO CALL register_techscout_sale')
                        register_techscout_sale(promo_id, camp, amt_to_charge)
                        # Set Charge Day
                        camp = set_charge_day(camp, old_neighborhood_ct)
                        # If we have content, checkout
                        camp = checkout_campaign(
                            camp, promo_id=promo_id,
                            partner_promo_category=promo_cat)
                        camp = save_in_transaction(camp)
                    else:
                        pass

                    logging.info('Track new camp --------------' + str(camp))
                    try:
                        ref = self.session.get('referral')
                        if ref:
                            deferred.defer(
                                referrals.redeem,
                                ref[u'adv_key'], ref[u'tiny'],
                                ref[u'block_points'])
                            toEmail = Advertiser.urlsafe_get(ref[u'adv_key']).business_email
                            self.sendThankYouMail(ref[u'tiny'], toEmail)
                    except Exception as e:
                        logging.exception(e)
                        # del self.session['referral']
                    func_to_backend(track_new_campaign, camp,
                                    amt_to_charge / 100, camp.neighborhood_ct,
                                    block_points_used=block_points_applied,
                                    promo_id=promo_id,
                                    partner_promo_category=promo_cat,
                                    previous_data=previous_data, user=user)
                    # if the new advertiser
                elif amt_to_charge:
                    logging.info('Paid to Paid Upgrade')

                    # send an email regarding the upgrade
                    send_tmail(camp.key.urlsafe(), 'upgrade')

                    camp = set_charge_day(camp, old_neighborhood_ct)
                    camp = save_in_transaction(camp)
                    # If it's not new its an upgrade
                    func_to_backend(track_upgrade, camp, amt_to_charge / 100.0,
                                    old_amount_subscribed,
                                    camp.amount_subscribed,
                                    old_neighborhood_ct, camp.neighborhood_ct,
                                    block_points_used=block_points_applied,
                                    promo_id=promo_id,
                                    partner_promo_category=promo_cat,
                                    previous_data=previous_data, user=user)
                else:
                    logging.error('NOT A NEW CAMPAIGN AND NO AMT TO CHARGE')
                    msg = ('A Problem Occurred While '
                           'Attempting to Charge the Card')
                    return msg
            # Otherwise its a free campaign
            # TODO: get rid of this??
            else:
                logging.info('No Charge')
                if is_new_campaign:
                    logging.debug('NEW CAMPAIGN')
                    logging.error('ABOUT TO CALL register_techscout_sale')
                    register_techscout_sale(promo_id, camp, amt_to_charge)
                    if not camp.waiting_for_content:
                        send_tmail(camp.key.urlsafe(), 'camp_live')
                        camp = set_charge_day(camp, old_neighborhood_ct)
                        camp = checkout_campaign(
                            camp, promo_id=promo_id,
                            partner_promo_category=promo_cat)
                        camp = save_in_transaction(camp)
                    else:
                        pass

                    logging.info('Track Campaign -----------' + str(camp))
                    func_to_backend(
                        track_new_campaign, camp, amt_to_charge / 100.0,
                        camp.neighborhood_ct,
                        block_points_used=block_points_applied,
                        promo_id=promo_id, partner_promo_category=promo_cat,
                        previous_data=previous_data, user=user)
            logging.debug('Sending to Chernobyl')
            func_to_backend(jchernobyl_client.call_chernobyl,
                            camp.key.urlsafe())
            return "SUCCESS"
        else:
            msg = 'A Problem Occurred While Attempting to Charge the Card'
            return err

    def sendThankYouMail(self, tiny, toEmail):
        '''Sends a Thank You Email, letting toEmail know,
        that their referred user (TODO: with newUserEmail) just created
        a campaign.
        Send the referral url that has been used for the sign-up at the end of that Email, too.'''

        import sendgrid2
        mail_body = "Thank you for referring a friend, who just started a new campaign. You have earned some block points. Here's your referral link to get more block points. {}/refer/{}".format(jconfig.get_host(), tiny)

        s = sendgrid2.SendGridClient('nearwoonews', 'nearwoo17')
        message = sendgrid2.Mail()
        message.add_to(toEmail)
        message.set_from('noreply@nearwoo.com')
        message.set_subject('You earned block points!')
        message.set_html(mail_body)
        s.send(message)


class ProRateCampaign(CampaignCreator):
    def post(self, advertiser_key, campaign_key, num_bgs):
        data = json.loads(self.request.body)
        yelp_data = data.get('yelp_data', None)
        camp = NearWooCampaignDS.urlsafe_get(campaign_key)
        today = datetime.datetime.today().day
        promo_cat = data.get('promo_cat', None)
        promo_id = data.get('promo_id', None)
        use_block_points = data.get('use_block_points', False)

        logging.info("USE BLOCK Points " + str(use_block_points))

        if camp.charge_day:
            # If the last charge occurred last month
            if today < camp.charge_day:
                last_month_diff = 30 - camp.charge_day
                total_diff = last_month_diff + today
                left_over = 30 - total_diff
            # If the last charge occurred this month
            else:
                total_diff = today - camp.charge_day
                left_over = 30 - total_diff
        else:
            left_over = 30

        left_over_pct = float(left_over) / 30
        pro_rate = camp.amount_subscribed * left_over_pct
        logging.info('AMOUNT SUBSCRIBED %s', camp.amount_subscribed)
        logging.info('LEFT OVER %s', left_over_pct)
        final_amt = ((int(num_bgs) - 1) * camp.retail_price)

        content = self.create_campaign(
            camp.yelp_key, yelp_data, final_amt, num_bgs,
            promo_cat, promo_id, pro_rate, use_block_points=use_block_points)

        if content == 'SUCCESS':
            logging.warning('PAYMENT COMPLETE')
            msg = make_status_message(
                success=True, code=200, data=camp.advertiser_key,
                message='Thank you for your payment')
            self.response.write(msg)
        else:
            logging.error('PAYMENT DECLINED')
            msg = make_status_message(
                success=False, code=500, data=None, message=content)
            self.response.write(msg)


class GetProRate(webapp2.RequestHandler):
    def get(self, advertiser_key, campaign_key, num_bgs):
        """Calculates the amount remaining to be spent on the campaign (so that
        you can subtract it to get the increment)"""
        camp = NearWooCampaignDS.urlsafe_get(campaign_key)
        if not camp:
            status = make_status_message(success=False,
                                         message="Campaign not found")
            self.response.write(status)
            return

        left_over_pct = calculate_prorate_percentage(camp)
        subtracter = camp.amount_subscribed * left_over_pct

        result = {'status':'error',
                            'description':'could not calculate prorate',
                            'data':[],
                            'code':'500'
                            }
        if subtracter:
            data = {'prorate': subtracter}
            data['discount'] = get_discount_from_promo_id(
                camp.promo_id, camp.promo_category)
            data['retail_price']= camp.retail_price
            result['status'] = 'success'
            result['data'] = data
            result['description'] = 'prorate is the amount to be subtracted'
            result['code'] = '200'

        result['camp'] = camp.to_dict()
        self.response.write(json.dumps(result))


def calculate_prorate_percentage(camp):
    today = datetime.datetime.today()
    logging.warning('Billing Period ' + str(camp.billing_period))
    if camp.last_charge_date:
        time_left = camp.next_charge_date - today
        total_time_in_billing_period = camp.next_charge_date - camp.last_charge_date
        logging.info(total_time_in_billing_period)
        left_over_pct = float(time_left.days) / total_time_in_billing_period.days
        logging.info("Last charge date: %s. Next charge date: %s. Percentage"
                     "remaining: %s", camp.last_charge_date,
                     camp.next_charge_date, left_over_pct)
    else:
        # Assumes they are monthly only
        today = datetime.datetime.today().day
        if camp.charge_day:
            # If the last charge occurred last month
            if today < camp.charge_day:
                last_month_diff = 30 - camp.charge_day
                total_diff = last_month_diff + today
                left_over = 30 - total_diff
            # If the last charge occurred this month
            else:
                total_diff = today - camp.charge_day
                left_over = 30 - total_diff
        else:
            left_over = 30

        left_over_pct = float(left_over) / 30

    return left_over_pct


# ------------------- ProRate helpers begin ---------------------------

def get_discount_from_promo_id(promo_id, promo_cat):
    promo = Promotional.get_by_auth_id(promo_id)
    fails = ['None', 'none', None, 'null', 'undefined', '']
    if promo in fails:
        return None
    partner_id = promo.partner_id
    ppc = None
    if promo_cat not in fails:
        pp_id = promo.partner_id + ':' + promo_cat
        ppc = PartnerPromoCategory.get_by_id(pp_id)
    if not ppc:
        partner = Partner.gql('where partner_id = :1', partner_id).get()
        pp_id = partner_id + ':' + partner.nearwoo_default_promo_category
        ppc = PartnerPromoCategory.get_by_id(pp_id)
    if not ppc:
        return None
    if ppc.discount_type == 'absolute':
        return ppc.absolute_discount
    else:
        return str(ppc.percent_discount) + '%'

# ------------------ Prorate helpers end ------------------------------


class SavePayment(CampaignCreator):
    """Responsible for saving and creating new campaigns from the yelp data.
    Prorates and charge amounts should already be calculated by this point (and
    currently aren't rechecked by the back end).

    * Create the campaign if it doesn't exist
    * Update the campaign's adamounts, neighborhood count, block group
    * Populate other campaign related properties
    * Send it to Pagewoo
    * Track stats related to it.


    Possible Reasons why save payment would fail:
    * Card declined/rejected

    Will not fail when:
    * Pagewoo doesn't exist or is broken"""
    def post(self, key):
        host = self.request.host
        logging.info(host)
        y_dat = self.request.body.decode('utf-8', errors='ignore')
        logging.info("Request Data (y_dat): %s", y_dat)
        self.save_payment(key, y_dat)

    def save_payment(self, y_key, data):
        data = json.loads(data)
        logging.debug(data)
        # check for invariants that we need
        if 'yelp_data' not in data:
            raise ValueError('required "yelp_data" missing from passed data')
        if 'payment' not in data:
            raise ValueError('required "payment" missing from passed data')
        yelp_data = data['yelp_data']
        payment = data['payment']
        required_keys = ('block_groups', 'initial_charge', 'billing_period',
                         'amount_subscribed')
        missing_keys = [k for k in required_keys if k not in payment]
        if missing_keys:
            raise ValueError('Required keys %s missing.' %
                             missing_keys)
        logging.info(payment)
        block_groups = str(payment['block_groups'])
        # TODO: Does this always need to be set? (it's currently not being set
        # by savepayment sometimes in NW 1.0.
        logging.warning("Initial Charge: %s", payment['initial_charge'])
        initial_charge = float(payment['initial_charge'])
        billing_period = int(payment['billing_period'])
        amount_subscribed = float(payment['amount_subscribed'])
        promo_category = payment.get('promo_category', '')
        promo_id = payment.get('promo_id', '')
        stripe_obj = payment.get('stripe', None)
        # 1 block point = 1 neighborhood = 1000 woos
        use_block_points = bool(
            payment.get('use_block_points', False))
        # default is not a downsell
        downsell = int(yelp_data.get('downsell', 0))
        logging.info('DOWNSELL %s', downsell)
        y_key = yelp_data['gae_key']
        yelp = YelpJsonDS.urlsafe_get(y_key)
        advertiser = Advertiser.urlsafe_get(yelp.advertiser_key)
        if not advertiser:
            msg = make_status_message(success=False,
                                      message="Advertiser not found.")
            self.response.write(msg)
            return
        partner_stripe_id = None

        # Special variable to change value of block
        wholesaler = None
        wholesale_price = 25
        partner = None

        # Check for partner stripe_id if there is one,
        # we will charge the partner's card
        promo = Promotional.gql('where promo_id = :1', promo_id).get()
        if promo:
            partner = Partner.gql(
                'where partner_id = :1', promo.partner_id).get()
            if partner:
                partner_stripe_id = partner.stripe_id
                wholesale_price = partner.wholesale_price
                logging.info('Partner WHOLESALE PRICE ' + str(wholesale_price))

        customer = None
        # If We are downselling we don't charge anyone
        if downsell:
            # this does nothing no stripe stuff necessary
            logging.info('DOWN SELL NOT CHARGING ')
        elif partner_stripe_id or (partner and partner.invoiced):
            logging.info('FOUND PARTNER TOKEN')
            wholesaler = {}
            wholesaler['wholesale'] = partner.wholesale
            wholesaler['wholesale_price'] = partner.wholesale_price
            wholesaler['partner_stripe_id'] = partner.stripe_id
            wholesaler['partner_id'] = partner.partner_id

        # IF we get a stripe_obj from the client side
        elif stripe_obj:
            logging.info('Creating New Customer')
            # Create A New Stripe Customer
            if not advertiser.business_email:
                advertiser.business_email = 'unknown customer'
            logging.info('Advertiser Key: ' + advertiser.key.urlsafe())

            customer, error = save_new_stripe_customer(
                stripe_obj['id'], advertiser=advertiser.key.urlsafe())
            if customer:
                customer_id = customer['id']
                # save the id in the advertiser
                advertiser.stripe_id = customer_id
                logging.warning(
                    "Succcesfully created new customer: " + customer_id)
                advertiser.put()

                # Save Stripe Object with customer id
                save_stripe = StripeDS(
                    type_of_action='new customer',
                    stripeID=customer_id,
                    repID='no rep',
                    advID=yelp.advertiser_key,
                    partnerID='no partner',
                    data=str(customer))
                save_stripe.put()
            else:
                logging.info('Stripe Customer Creation Failed')
                logging.error(error)
                msg = make_status_message(
                    success=False, code=400, data=yelp.advertiser_key,
                    message=error['message'])
                self.response.write(msg)
                return
        elif advertiser.stripe_id:
            # We already have payment info so just continue
            logging.info('Payment Info Found')
        # Check to see if we already have a card in the advertiser obj
        else:
            if amount_subscribed > 0:
                logging.error('NO PAYMENT INFO FOUND!')
                msg = make_status_message(
                    success=False, code=400, message='No payment info found')
                self.response.write(msg)
            else:
                logging.debug('%s is free-ish so no payment info', y_key)
        # TODO: Probably need to pass advertiser to create campaign so that we
        # can tell what's going on with pricing
        content = self.create_campaign(
            y_key, data, amount_subscribed,
            block_groups, initial_charge, billing_period, promo_category, promo_id,
            downsell=downsell, use_block_points=use_block_points,
            wholesaler=wholesaler)

        if content == 'SUCCESS':
            logging.info('PAYMENT COMPLETE')
            msg = make_status_message(
                success=True, code=200, data=yelp.advertiser_key,
                message='Thank you for your payment')
            self.response.write(msg)
        else:
            logging.error('PAYMENT DECLINED')
            msg = make_status_message(
                success=False, code=500, data=None, message=content)
            self.response.write(msg)


class AdOpsCampaignLive(SavePayment):

    def get(self, yelp_key, promo_id):
        host = self.request.host
        logging.info(host)

        promo_category = self.request.get('promo_category')

        yelp = YelpJsonDS.urlsafe_get(yelp_key)
        add_adamounts_to_yelp(yelp)
        y_dat = json.loads(yelp.yelp_data)
        data = {}
        data['yelp_data'] = y_dat
        if not 'payment' in y_dat:
            data['payment'] = {}
        logging.warning('geoiids ' + str(yelp.geoids))
        geoids = json.loads(yelp.geoids)
        logging.warning('len ' + str(len(geoids)))
        data['geoids'] = geoids
        data['payment'] = {}
        data['payment']['block_groups'] = len(geoids)
        # NOTE THIS IS FINE IT WILL BE RECALCULATED WITH PARTNER INFO
        data['payment']['initial_charge'] = len(geoids) * 10.0
        data['payment']['amount_subscribed'] = len(geoids) * 10.0
        data['payment']['promo_id'] = promo_id
        data['payment']['promo_category'] = promo_category
        data['payment']['stripe'] = None
        data['payment']['billing_period'] = 1
        logging.info('Current max views in data: %s', data.get('max_views'))
        logging.warning(data)
        data = json.dumps(data)
        self.save_payment(yelp_key, data)


# ------------------- Stripe helper functions begin ----------------------
def charge_customers(day_of_month=None):
    """Runs the charge function on all customers. We set the charge day to the
    day *before* they checked out and we (now) charge them at 18:00 on the
    charge day (so after business hours on both East and West Coast)"""
    if not day_of_month:
        day_of_month = to_pacific_time(datetime.datetime.today()).day
    logging.info("Charging customers for day %s", day_of_month)
    camps = NearWooCampaignDS.gql('where charge_day = :1', day_of_month)

    result = None
    for key in iterate(camps, keys_only=True):
        try:
            result = charge_the_customer(camp_key=key.urlsafe(),
                                        day_of_month=day_of_month)
            if result is INTERNAL_FAILURE:
                logging.warning('Got internal failure for camp %s (%s). Waiting a'
                                ' second before continuing', key, key.urlsafe())
                time.sleep(1)
        except Exception as e:
            logging.exception('Failed to charge camp: %s', key.urlsafe())
            try:
                camp = key.get()
                InternalErrorOnCharge.store(camp, e,
                                            'charge_customers_toplevel')
            except Exception:
                logging.exception('Failed to store error record too!!')

def charge_the_customer(camp_key=None, previous_data=None, user=None,
                        force=False, day_of_month=None):
    if not day_of_month:
        day_of_month = to_pacific_time(datetime.datetime.today()).day
    camp = NearWooCampaignDS.urlsafe_get(camp_key)
    if not camp:
        logging.warning("No camp found for %s" % camp_key)
        return
    if not previous_data:
        previous_data = MiniHistoricalCampaignData.from_campaign(camp)
    if camp.budget > 0:
        logging.warning('Budget Campaign Not Recharging')
        return
    logging.info(camp.name)
    logging.info(camp.paused)
    if camp.paused:
        logging.warning('Campaign Paused')
        return
    if not camp.is_recurring:
        logging.info("Not charging, not a recurring campaign")
        return
    advertiser_key = ndb.Key(urlsafe=camp.advertiser_key)
    advertiser = advertiser_key.get()
    try:
        should_reallocate = _charge_active_recurring_campaign(camp, advertiser,
                                                            day_of_month, previous_data, user, force)
    except Exception as e:
        logging.exception('_charge_active_recurring failed without handling'
                          'its exception.')
        InternalErrorOnCharge.store(camp, e,
                                    'charge_the_customers_pre_reallocate',
                                    charge_day=day_of_month)
        return INTERNAL_FAILURE

    if should_reallocate is INTERNAL_FAILURE:
        return INTERNAL_FAILURE

    if should_reallocate:
        try:
            if advertiser.pagewoo_keys:
                pagewoo_key = camp.pagewoo_campaign_key
                if pagewoo_key:
                    return reallocate_camp(camp)
                else:
                    logging.error('Could Not Find pw Key for %s', camp.name)
                    return False
        except Exception as e:
            logging.error('reallocate camp failed')
            InternalErrorOnCharge.store(camp, e, 'reallocate_camp',
                                        charge_day=day_of_month)
            return INTERNAL_FAILURE
    else:
        logging.info("Not reallocating, should_reallocate was False")
        return False


def _charge_active_recurring_campaign(camp, advertiser, day_of_month,
                                      previous_data, user, force=False):
    """Charges the campaign if necessary and returns whether the campaign
    should be reallocated. Handles block points and tracking of recurring
    charges."""
    charge = None
    error = None
    try:
        today = datetime.datetime.utcnow().date()
        # don't charge multi-month campaigns
        if camp.next_charge_date and camp.next_charge_date.date() > today and not force:
            logging.debug("Not billing. Camp %s 's next charge date is: %s",
                        camp.key.urlsafe(), camp.next_charge_date)
            if camp.billing_period <= 1:
                logging.error("Have billing period <= 1 but next_charge_date is not"
                            " today")
                return
            # otherwise, we need to recharge, because we're at that time of the
            # month
            return True
        logging.debug("Charging the customer for %s. Last charge date: %s, next"
                    " charge date: %s. Billing period %s",
                    camp.key.urlsafe(), camp.last_charge_date,
                    camp.next_charge_date, camp.billing_period)
        stripe_id = advertiser.stripe_id
        logging.debug('day of month %s', day_of_month)
        logging.info(camp.name)
        logging.info(camp.key.urlsafe())
        logging.warning("STRIPE ID %s", advertiser.stripe_id)
        logging.info("campaign amount_subscribed %s", camp.amount_subscribed)
        charge_amt = int(camp.amount_subscribed) * 100
        # If Spend Points Monthly is Set use all possible block points
        charge_amt, block_points_applied = use_monthly_block_points(
            charge_amt, advertiser, camp)
        if camp.amount_subscribed <= 0.0:
            logging.info("Not charging or renewing free campaign")
            return False
        if charge_amt <= 0:
            if not block_points_applied:
                logging.error("Charge amount is 0, but not block points applied.")
                return False
            camp.last_charge_date = datetime.datetime.today()
            charge = 'free'
            logging.info("Recharging campaign paid by block points")
            func_to_backend(
                track_recurring, camp, charge_amt / 100.0,
                camp.neighborhood_ct, block_points_applied,
                previous_data=previous_data, user=user)
            # should reallocate if it's free
            return True
        is_wholesale, partner_stripe_id = partner_is_wholesale(camp.partner_id)
        if is_wholesale:
            logging.debug("CHARGING PARTNER " + str(charge_amt))
            logging.debug("PARTNER STRIPE ID " + str(partner_stripe_id))
            charge, error, _ = charge_partner(
                charge_amt, advertiser, camp.partner_id,
                partner_stripe_id, camp, 'recurring',
                camp_key=camp.key.urlsafe(),
                block_points_applied=block_points_applied)
        else:
            logging.debug("CHARGING ADVERTISER " + str(charge_amt))
            logging.debug("STRIPE ID " + str(stripe_id))
            charge, error, _ = charge_advertiser(
                charge_amt, advertiser, camp, 'recurring',
                camp_key=camp.key.urlsafe(),
                block_points_applied=block_points_applied)
        # what should we do on error
        if error:
            logging.error("Had error: %s (not recharging)", error)
            return False
        if charge:
            camp.last_charge_date = datetime.datetime.today()
            func_to_backend(
                track_recurring, camp, charge_amt / 100.0,
                camp.neighborhood_ct, block_points_applied,
                previous_data=previous_data, user=user)

            camp.put()
            return True
        else:
            # no idea how you get here
            logging.error("We do not have a charge, this should be an error -"
                        " CHECKME")
            return False
    except Exception as e:
        if camp:
            logging.exception('Failed to charge camp: %s (%s)', camp.key.urlsafe(), camp.name or
                              camp.store)
        else:
            logging.exception('Failed to charge. No camp found either')
        InternalErrorOnCharge.store(camp, e,
                                    '_charge_active_recurring_customer',
                                    stripe_charge=charge,
                                    charge_error=error,
                                    charge_day=day_of_month)
        return INTERNAL_FAILURE


def use_monthly_block_points(to_charge, advertiser, campaign):
    # If we have block points
    to_charge = to_charge / 100
    block_points_applied = 0
    if advertiser.spend_points_monthly:
        block_points_to_apply = int(
            (math.ceil(campaign.amount_subscribed / 10) * 10) / 10)
        # if we are using all our block points charge the difference
        if block_points_to_apply >= advertiser.block_points:
            logging.debug("Using all " + str(advertiser.block_points))
            to_charge = (campaign.amount_subscribed -
                         (advertiser.block_points * 10))
            block_points_applied = advertiser.block_points
            advertiser.block_points = 0
            advertiser.put()
        # otherwise use as many as we can
        else:
            logging.debug('Using only ' + str(block_points_to_apply))
            to_charge = 0
            block_points_applied = block_points_to_apply
            left_over = advertiser.block_points - block_points_to_apply
            logging.debug(str(left_over) + 'block points left over')
            advertiser.block_points = int(left_over)
            advertiser.put()
    return int(to_charge * 100), int(block_points_applied)

# Applies block points to a charge

BASE_PRICE = 25


def apply_block_points(amt_to_charge, adv, wholesale_price=BASE_PRICE):
    block_points_applied = 0
    block_points = adv.block_points
    # Block Points are always onetime use, so apply them only to amt charged
    logging.debug('AMT_TO CHARGE ' + str(amt_to_charge))
    charge_amt = float(amt_to_charge) / 100
    block_points_to_apply = int(
        (math.ceil(charge_amt / 10) * 10) / wholesale_price)
    # If the block points to apply is greater than block_points use them all
    if block_points_to_apply >= block_points:
        logging.debug('charge amt before ' + str(charge_amt))
        logging.debug('reduce charge ' + str(block_points * wholesale_price))
        charge_amt = charge_amt - (block_points * wholesale_price)
        logging.debug('new charge_amt ' + str(charge_amt))
        logging.info('CHARGE AFTER BLOCK Points')
        block_points_applied = adv.block_points
        adv.block_points = 0
        adv.put()
        logging.info('Block Pointes reset')
    # otherwise enter the difference
    else:
        block_points_left_over = block_points - block_points_to_apply
        block_points_applied = block_points_to_apply
        adv.block_points = block_points_left_over
        charge_amt = 0
        logging.info('block points left over' + str(block_points_left_over))
        adv.put()
    logging.info("BLOCK POINTS APPLIED " + str(block_points_applied))
    return block_points_applied, int(charge_amt * 100)


@charge
def charge_advertiser(amt, advertiser, campaign, charge_type,
                      supercharge=None, camp_key=None, block_points_applied=0):
    stripe_id = advertiser.stripe_id
    description = json.dumps({'camp_key': campaign.key.urlsafe(), 'invoice_type':
                              charge_type})
    charge, err = charge_customer(amt, 'usd', stripe_id, description,
                                  advertiser=advertiser, campaign=campaign)
    logging.info('Charge: %s', charge)
    if amt == 0 and block_points_applied >= 1:
        charge = {'amount':0, 'fee':0}
    if not charge:
        # if the charge failed pass on the error
        return charge, err, None
    else:
        inv = save_invoice(
            charge, advertiser, campaign, charge_type,
            supercharge=supercharge, block_points_applied=block_points_applied)
        campaign.amount_spent += amt / 100
        save_in_transaction(campaign)
        return charge, None, inv

@charge
def charge_nucleus_advertiser(amt, advertiser, campaign, charge_type, camp_key=None):
    stripe_id = advertiser.stripe_id
    description = json.dumps({'camp_key': campaign.key.urlsafe(), 'invoice_type':
                              charge_type})
    charge, err = charge_customer(amt, 'usd', stripe_id, description,
                                  advertiser=advertiser, campaign=campaign)
    logging.info('Charge: %s', charge)
    if amt == 0 and block_points_applied >= 1:
        charge = {'amount':0, 'fee':0}
    if not charge:
        # if the charge failed pass on the error
        return charge, err, None
    else:
        inv = save_invoice(charge, advertiser, campaign, charge_type)
        campaign.amount_spent += amt / 100
        save_in_transaction(campaign)
        return charge, None, inv


@charge
def charge_partner(amt, advertiser, partner_id,  partner_stripe_id, campaign,
                   charge_type, supercharge=None, camp_key=None, block_points_applied=0):
    partner = Partner.gql('where partner_id = :1', partner_id).get()
    if partner.invoiced:
        charge = {'amount': amt, 'fee': 0.0, 'partner_invoice': True}
        logging.warning('Invoiced Partner Not Charging')
    else:
        description = json.dumps(
            {'camp_key': campaign.key.urlsafe(), 'invoice_type': charge_type})
        charge, err = charge_customer(
            amt, 'usd', partner_stripe_id, description,
            advertiser=advertiser, campaign=campaign)
    logging.info('Charge ' + str(charge))

    if amt == 0 and block_points_applied >= 1:
        charge = {'amount':0,'fee':0}

    if not charge:
        # if the charge failed pass on the error
        partner.payment_error = True
        partner.put()
        return charge, err, None
    else:
        inv = save_invoice(charge, advertiser, campaign, charge_type,
                     supercharge=supercharge,
                     block_points_applied=block_points_applied)
        campaign.amount_spent += amt / 100
        save_in_transaction(campaign)
        return charge, None, inv


def reallocate_camp(camp):
    if not camp.pagewoo_campaign_key:
        return False
    today = datetime.datetime.utcnow()
    camp.next_recharge_date = add_months(today, 1)
    camp.max_views += camp.total_adamounts
    camp.put()
    # can't raise on error or it will bork the recurring charge the customer
    # script.
    try:
        resp = jchernobyl_client.call_chernobyl(camp.key.urlsafe(), raise_on_error=True)
        if not resp:
            logging.warning("Setting failed")
            return False
    except Exception as e:
        logging.exception("Failed to set rtb controls: %r", e)
        return False
    else:
        return True


def supercharge(camp, sc_id, views):
    # important: don't add sc_views to max_views
    resp = jchernobyl_client.supercharge(
        camp.pagewoo_campaign_key, sc_id, views)
    return False if not resp else True


# saves a payment error with all necessary properties
def payment_error(amt, advertiser, campaign, error):
    advertiser_key = advertiser.key.urlsafe()
    payment_error = PaymentErrors()
    payment_error.advertiser_key = advertiser_key
    payment_error.campaign_key = campaign.key.urlsafe()
    payment_error.charge_day = campaign.charge_day
    payment_error.error = error
    payment_error.put()


# Saves all an Invoice with all necessary properties
def save_invoice(charge, advertiser, campaign, invoice_type,
                 supercharge={}, block_points_applied=0):
    invoice = Invoices()
    charge['neighborhood_ct'] = campaign.neighborhood_ct
    charge['store'] = campaign.store
    partner_invoice = charge.get('partner_invoice', 0)
    if partner_invoice:
        invoice.charge = json.dumps(charge)
    else:
        invoice.charge = json.dumps(json.loads(str(charge)))
    invoice.charge_day = campaign.charge_day
    invoice.charge_amount = charge['amount'] / 100.0
    invoice.neighborhood_ct = campaign.neighborhood_ct
    invoice.partner_id = campaign.partner_id
    invoice.rep_id = campaign.promo_id
    invoice.promo_id = campaign.promo_id
    invoice.partner_promo_category = campaign.partner_promo_category
    invoice.invoice_type = invoice_type
    invoice.campaign_key = campaign.key.urlsafe()
    invoice.campaign_name = campaign.name
    invoice.advertiser_key = advertiser.key.urlsafe()
    invoice.advertiser_email = advertiser.email
    invoice.stripe_fee = float(charge['fee'])
    invoice.stripe_id = advertiser.stripe_id
    invoice.stripe_id_search = advertiser.stripe_id
    try:
        invoice.transaction_id = charge['id']
    except Exception:
        logging.exception("Error setting transaction id")
    invoice.block_points_applied = block_points_applied
    if invoice_type == 'supercharge':
        invoice.supercharge_impresssion = supercharge['impressions']
        invoice.supercharge_cost = supercharge['cost']
    invoice.put()
    created_pacific = invoice.date_created_pacific
    # annotate campaign with date of the first invoice
    if not campaign.has_first_invoice or campaign.has_first_invoice is None:
        campaign.has_first_invoice = True
        campaign.first_invoice_date_created_pacific = created_pacific
        campaign.first_invoice_year_tq = get_time_qualifier(
            'year', dt=created_pacific)
        campaign.first_invoice_month_tq = get_time_qualifier(
            'month', dt=created_pacific)
        campaign.first_invoice_week_tq = get_time_qualifier(
            'week', dt=created_pacific)
        campaign.first_invoice_day_tq = get_time_qualifier(
            'day', dt=created_pacific)
        save_in_transaction(campaign)
    return invoice


# Purely a wrapper for charging Stripe
@stripepayment
def charge_customer(amount, curr, customer, description, advertiser=None,
                    campaign=None):
    charge = stripe.Charge.create(
        amount=amount,
        currency=curr,
        customer=customer,  # obtained with Stripe.js
        description=description)
    return charge


# ------------------- Stripe helper functions end ----------------------


#----------------------- create_campaign helpers begin ----------------
# Creates the 'data' field of its pagewoo equivalent
def create_pagewoo_campaign_data(
    geoids, yelp_data, amount_subscribed, max_views, num_bgs, waiting_for_content,
    supercharge=0, pagewoo_campaign_key=None, old_max_views=0, start_date=None,
    # TODO: Change name to 'extra_home_woos'
    end_date=None, home_neighborhood_woos = 1000, rtb_controls=None):

    data = rtb_controls or {}

    # don't do this when we have a flight plan
    if not (start_date and end_date):
        if 'max_views' in data:
            if old_max_views >= max_views:
                down_views = old_max_views - max_views
                data['max_views'] -= down_views
            else:
                data['max_views'] += max_views
        else:
            data['max_views'] = max_views

    if data.get('max_views', None) is None:
        logging.error("No max views in Pagewoo data!! (passed max_views is"
                      " %s)", max_views)

    # ask Sam - what if preexisting supercharge?
    if supercharge:
        data['supercharge'] = supercharge
    data['places'] = [
        {'geoid': g, 'name': 'NearWOO', 'bid_type': 'auto', 'bid':''}
        for g in geoids]

    # make cron job for setting live on start_day?
    if waiting_for_content:
        data['play'] = False
    else:
        data['play'] = True
    data['name'] = yelp_data['name']
    data['total_budget'] = float(amount_subscribed)
    data['website_url'] = yelp_data.get('biz_url', 'none')
    data['content_category'] = 'IAB3'  # pbvi fake
    data['illicit_content'] = True
    data['camp_duration'] = 20
    return data


def update_email_plan(email_plan_id, amount_subscribed):
    logging.info('Updating Email Plan')
    email_plan = EmailPlan.gql('where email_plan_id = :1', email_plan_id).get()
    if not email_plan:
        if not amount_subscribed:
                email_plan.current_free_campaigns += 1
                email_plan.free_campaigns += 1
        else:
                email_plan.paid_campaigns += 1
                email_plan.current_paid_campaigns += 1
                email_plan.revenue += amount_subscribed
                email_plan.current_revenue += amount_subscribed
        email_plan.put()


def update_email_template(template_id, amount_subscribed):
    logging.info('Updating Email template')
    template = EmailTemplate.gql('where template_id = :1', template_id).get()
    if not amount_subscribed:
        template.free_campaigns += 1
        template.current_free_campaigns += 1
    else:
            template.paid_campaigns += 1
            template.current_paid_campaigns += 1
            template.revenue += amount_subscribed
            template.current_revenue += amount_subscribed
    template.put()


def remove_from_marketing_list(email):
    logging.warning('removing ' + str(email))
    contact = MarketingContact.gql('where email = :1', email).get()
    if contact:
        contact.key.delete()


def create_search_list(name):
    """ Creates a list of consecutive char combinations
    for searching """
    result = []
    addup = ""
    for x in name:
        addup += x
        result.append(addup)
    return result


def geoid_diff(old_geoids, new_geoids):
    """ Finds the geoids removed """
    new_block_groups = set(bg['geoid'] for bg in new_geoids)
    block_groups = set(bg['geoid'] for bg in old_geoids)
    block_groups_removed = block_groups - new_block_groups
    geoids_removed = '-'.join(block_groups_removed)
    return geoids_removed


def save_yelp_geoids(yelp_key, yelp_data, geoids):
    # IF WE HAVE DON't Have Yelp Data We cant make a campaign
    yelp = YelpJsonDS.urlsafe_get(yelp_key)
    if not yelp:
        logging.error('NO YELP Data Found')
        return None
    yelp.yelp_data = json.dumps(yelp_data)
    yelp.geoids = json.dumps(geoids)
    yelp.put()
    return yelp


def check_existing_camp(camp, yelp):
    """ Gets the number of neighborhoods and amount subscribed
     Returns camp, None, None if the campaign has no existing info """
    old_amount_subscribed = None
    old_neighborhood_ct = None
    is_new_campaign = False
    old_max_views = None
    # If there is a campaign and it has a checkout date
    if camp and camp.completed:
            logging.warning('EXISTING CAMPAIGN')
            old_amount_subscribed = camp.amount_subscribed
            old_neighborhood_ct = camp.neighborhood_ct
            old_max_views = camp.max_views
    # if no campaign exists
    elif not camp:
        logging.warning('New Campaign')
        is_new_campaign = True
        camp = NearWooCampaignDS()
    # if a campaign exists and its not been checked out
    else:
        logging.warning('New Campaign')
        is_new_campaign = True
    return camp, old_amount_subscribed, old_neighborhood_ct, old_max_views, is_new_campaign



def set_time_for_camp(camp, yelp_data):
    """ Sets the time the ads will go out """
    if 'schedule' in yelp_data:
        logging.info("Start_time " + str(yelp_data['schedule']))
        camp.start_time = convert_start_time(yelp_data['schedule'])
    else:
        # default to noon (time slice 23)
        camp.start_time = 23
    # fallback time is 1 hour after start time
    fallback_time = camp.start_time + 2
    if fallback_time >= 47:
        fallback_time = fallback_time - 47
    camp.fallback_time = fallback_time
    return camp


def set_charge_day(camp, old_neighborhood_ct=None):
    """ Sets the charge day of the campaign
    The Charge day is the day of each month which /chargecustomers will
    charge the campaign again and refill max views """
    logging.info('set charge day for %s (old bg count %s)',
                 camp.name, old_neighborhood_ct)
    day_of_month = to_pacific_time(datetime.datetime.utcnow()).day
    charge_day = None
    if day_of_month > 30:
        charge_day = 30
    else:
        charge_day = day_of_month - 1
    if charge_day == 0:
        charge_day = 30
    # this logic doesn't hold up?
    # If this is an existing campaign
    if old_neighborhood_ct:
        reset_threshold = camp.neighborhood_ct - old_neighborhood_ct
        if reset_threshold > 0:
            camp.charge_day = charge_day
            camp.last_charge_date = datetime.datetime.utcnow()
    else:
        # otherwise its a new day and
        camp.charge_day = charge_day
        camp.last_charge_date = datetime.datetime.utcnow()
    logging.info('set charge day to %s', camp.charge_day)
    return camp


def apply_promo_to_charge(
    camp, amt_to_charge, amt_for_promo, pro_rate, amount_subscribed, num_bgs,
    promo_id, promo_cat):
    logging.info('PROM_ID %s', promo_id)
    logging.info('promo_cat %s', promo_cat)

    # Apply promo
    promo_applied = json.loads(
        promo_handlers.apply_promo(promo_id, promo_cat, num_bgs, amt_for_promo))
    # If the promo Fails
    if promo_applied['status'] != 'success':
        logging.debug('rep %s', promo_id)
        logging.debug('promo category %s', promo_cat)
        logging.warning(promo_applied['description'])
        logging.info('amount subscribed %s', amount_subscribed)
    else:
        # Set Discounted amount from promo
        promo_data = promo_applied['data']
        if promo_data['is_recurring']:
            promo_applied = json.loads(promo_handlers.apply_promo(promo_id, promo_cat, num_bgs, amount_subscribed))
            logging.info('GOT PROMO')
            promo_data = promo_applied['data']

        camp.promo_id = promo_data['promo_id']
        camp.promo_category = promo_data['promo_category']
        camp.partner_id = promo_data['partner_id']
        camp.partner_promo_category = promo_data['partner_promo_category']
        # add prorate back for charging them next time
        amount_after_promo = promo_data['discounted_amount'] + pro_rate
        logging.info('IS RECURRING %s', promo_data['is_recurring'])
        if promo_data['is_recurring']:
            camp.amount_subscribed = round(amount_after_promo, 2)
        amt_to_charge = int(promo_data['discounted_amount'] * 100)
        logging.info('CAMP PROMO ID: %s', camp.promo_id)
        logging.info('CAMP PROMO CATEGORY: %s', camp.promo_category)
        # amt_to_charge is the stripe chargeable amount which is an integer
        # representing cents
    return camp, amt_to_charge


# Welcome email

def welcome_email(yelp_data, adv):
    email = None
    adv_key = adv.key.urlsafe()
    if 'email' in yelp_data:
        email = yelp_data['email']
    if not email:
        email = adv.email
    if email:
        j_emails.send_welcome_email(adv_key, email)


#----------------------- create_campaign helpers end ----------------


# -------------------  Billing begin ----------------------------


class StripeTest(webapp2.RequestHandler):
    def get(self):
        customer = stripe.Customer.retrieve('cus_261fqVnnAm19LM')
        self.response.write(customer)


class UpdateCreditCard(webapp2.RequestHandler):
    def post(self):
        obj = json.loads(self.request.body)
        try:
            if not obj['stripe_id']:
                logging.info('OBJ ' + str(obj))
                new_customer, error = save_new_stripe_customer(
                    obj['stripe_token'], obj['advertiser_key'])
                if new_customer:
                    logging.warning(new_customer)
                    customer_id = new_customer['active_card']['customer']
                    adv_key = ndb.Key(urlsafe=obj['advertiser_key'])
                    adv = adv_key.get()
                    adv.stripe_id = customer_id
                    adv.put()
                    logging.info(customer_id)
                    message = make_status_message(
                        success=True,
                        message='Credit Card saved',
                        data=json.loads(str(new_customer)))
                else:
                    msg = ('Sorry we could not update your card. ' +
                           'Please contact Customer support')
                    message = make_status_message(
                        success=False,
                        message=msg,
                        data=error)
            else:
                customer = stripe.Customer.retrieve(obj['stripe_id'])
                customer.card = obj['stripe_token']
                customer.save()
                data = json.loads(str(customer))
                message = make_status_message(
                    success=True,
                    message='credit card updated',
                    data=data)
        except stripe.CardError, e:
            data = e.json_body
            message = make_status_message(
                success=False,
                message='credit card not updated',
                data=data)
        self.response.write(message)


class GetBillingByAdvertiser(webapp2.RequestHandler):

    def get(self):
        advertiser_key = self.request.get('advertiser_key')
        advertiser_key_obj = ndb.Key(urlsafe=advertiser_key)
        advertiser = advertiser_key_obj.get()
        if (advertiser.stripe_id == 'not a stripe customer' or
                not advertiser.stripe_id):
            post_back = make_status_message(
                success=False,
                message='We did NOT find a credit card for this advertiser',
                data='None')
            self.response.write(post_back)
        else:
            stripe_customer = stripe.Customer.retrieve(advertiser.stripe_id)
            stripe_customer['payment_error'] = advertiser.payment_error
            if advertiser.payment_error:
                payment_error = PaymentErrors.gql(
                    'where advertiser_key = :1', advertiser_key).get()
                if payment_error:
                    the_error = json.loads(payment_error.error)
                    stripe_customer['error_message'] = the_error['message']
            post_back = make_status_message(
                success=True,
                message='Found a credit card for this advertiser',
                data=json.loads(str(stripe_customer)))
            self.response.write(post_back)


class GetBillingByCampaign(webapp2.RequestHandler):

    def post(self):
        request_data = json.loads(self.request.body)
        advertiser_key = ndb.Key(urlsafe=request_data['advertiser_key'])
        adv = advertiser_key.get()
        campaign = NearWooCampaignDS.urlsafe_get(request_data['campaign_key'])
        neighborhood_ct = campaign.neighborhood_ct
        charges = []
        invoices = []
        if adv.stripe_id == 'not a stripe customer' or not adv.stripe_id:
            logging.warning('Not A STRIPE customer')
            invoices = []
            stripe_customer = None
        else:
            stripe_customer = stripe.Customer.retrieve(adv.stripe_id)
            # stripe_invoices = stripe.Invoice.all(
            #   customer=stripe_id,
            #   count=100
            # )
            # invoices= json.loads(str(stripe_invoices))
            stripe_customer = json.loads(str(stripe_customer))
        invoices = Invoices.gql(
            'where campaign_key = :1', campaign.key.urlsafe()).fetch(1000)
        charges = []
        for invoice in invoices:
            charge = json.loads(invoice.charge)
            invoice_type = invoice.invoice_type
            if invoice_type is None:
                invoice_type = 'N/A'
            charge['invoice_type'] = invoice_type
            charge['date'] = invoice.date_created.strftime('%m/%d/%y')
            charges.append(charge)
        self.response.write(json.dumps({
            'partner_key': adv.partner_key,
            'rep_key': adv.rep_key,
            'stripe_id': adv.stripe_id,
            'invoices': charges,
            'bill_day': campaign.charge_day,
            'bill_day_spoken': (ordinal(campaign.charge_day) if campaign.charge_day else None),
            'monthly_amt': campaign.amount_subscribed,
            'neighborhood_ct': neighborhood_ct,
            'stripe_customer': stripe_customer
        }))

# this is the handler for


class AdvUpdateCreditCard(webapp2.RequestHandler):

    def get(self, advertiser_key, stripe_token):
        # try:
        adv_key = ndb.Key(urlsafe=advertiser_key)
        adv = adv_key.get()
        customer = stripe.Customer.retrieve(adv.stripe_id)
        customer.card = stripe_token
        customer.save()
        adv.put()

        payment_errors = PaymentErrors.gql(
            'where advertiser_key = :1', advertiser_key).fetch(1000)
        user = users.get_current_user()
        for payment_error in payment_errors:
            success = charge_the_customer(
                camp_key=payment_error.campaign_key, user=user)
            if not success:
                msg = make_status_message(success=True, data=None)
                self.response.write(msg)
                return
        adv.payment_error = False
        adv.put()
        msg = make_status_message(
            success=True, data=None, message='Credit Card Updated Successfully')
        self.response.write(msg)


class UpdateCustomerPlan(webapp2.RequestHandler):

    def post(self):
        obj = self.request.body
        plan_id = obj['plan_id']
        update_plan = stripe.Plan.retrieve(plan_id)
        # add update arguments here
        update_plan.save()
        self.response.write('cutomer plan updated')


# ------------------ Billing End ------------------------------

############### OLD CODE FOR PAYING RECIPIENTS ###################


class AllPlans(webapp2.RequestHandler):

    def post(self):
        all_plans = stripe.Plan.query()
        self.response.write(json.dumps(all_plans))


class CreateRecipient(webapp2.RequestHandler):

    def post(self):
        obj = json.loads(self.request.body)
        logging.info(obj)
        user_id = obj['user_id']
        bank_token = obj['bank_token']
        fullname = obj['fullname']
        tax_id_type = obj['tax_id_type']
        tax_id = obj['tax_id']
        routing_number = obj['routing_number']
        account_number = obj['account_number']
        recipient_type = obj['recipient']

        if recipient_type == 'partner':
            recipient = partner_recipient(
                fullname, tax_id_type, tax_id, bank_token, recipient_type)
            partner = Partner().gql('where partner_id = :1', user_id).get()
            partner.stripe_recipient_key = recipient.id
            partner.bank_name = recipient.active_account.bank_name
            partner.bank_country_code = recipient.active_account.country
            partner.bank_routing_number = routing_number
            partner.bank_account_number = account_number
            partner.tax_id_type = tax_id_type
            partner.bank_account_name = recipient.name
            partner.tax_id
            partner.put()

        elif recipient_type == 'rep':
            recipient = rep_recipient(
                fullname, tax_id_type, tax_id, bank_token, recipient_type)
            rep = Promotional().gql('where promo_id = :1', user_id).get()
            rep.stripe_recipient_key = recipient.id
            rep.bank_name = recipient.active_account.bank_name
            rep.bank_country_code = recipient.active_account.country
            rep.bank_routing_number = routing_number
            rep.bank_account_number = account_number
            rep.tax_id_type = tax_id_type
            rep.bank_account_name = recipient.name
            rep.tax_id
            rep.put()
        else:
            active_account = 'strip error'

        active_account = recipient
        post_back = dict(status='success', description='Bank account Saved',
                         data=json.loads(str(active_account)))
        self.response.write(json.dumps(post_back))


def transfer_to_recipient(amt, recipient_key):
    transfer = None
    try:
        transfer = stripe.Transfer.create(
            amount=amt,
            currency="usd",
            recipient=recipient_key,
            description="Transfer for test@example.com"
        )
    except:
        logging.error('Transfer Error')
    return transfer


def rep_recipient(fullname, tax_id_type, tax_id, bank_token, recipient_type):
    recipient = stripe.Recipient.create(
        name=fullname,
        type=tax_id_type,
        tax_id=tax_id,
        bank_account=bank_token,
        description='New Recipient: ' + recipient_type
    )
    return recipient


def partner_recipient(fullname, tax_id_type, tax_id, bank_token, recipient_type):
    recipient = stripe.Recipient.create(
        name=fullname,
        type=tax_id_type,
        tax_id=tax_id,
        bank_account=bank_token,
        description='New Recipient: ' + recipient_type
    )
    return recipient


class RepBankingInfo(webapp2.RequestHandler):

    def get(self, promo_id):
        rep = Promotional.gql('where promo_id = :1', promo_id).get()
        if not rep:
            msg = make_status_message(False, 'No Rep', '500', None)
        elif not rep.bank_name:
            msg = make_status_message(False, 'No Banking Info', '500', None)
        else:
            data = {'bank_name': rep.bank_name,
                    'bank_routing_number': rep.bank_routing_number,
                    'bank_account_number': rep.bank_account_number,
                    'tax_id_type': rep.tax_id_type,
                    'tax_id': rep.tax_id,
                    'bank_account_name': rep.bank_account_name,
                    }
            msg = make_status_message(True, 'Rep Banking Info', '200', data)
        self.response.write(msg)


# Pay Partners on Some Schedule to be determined


def calc_pay_from_invoices(e_id, split, entity_type='partner'):
    today = datetime.datetime.today()
    one_month = datetime.timedelta(month=1)
    one_month_back = today - one_month
    if entity_type == 'partner':
        invoices = Invoices.gql(
            'where partner_id = :1 and date_created > :2', e_id, one_month_back).fetch(1000)
    elif entity_type == 'rep':
        invoices = Invoices.gql(
            'where partner_id = :1 and date_created > :2', e_id, one_month_back).fetch(1000)
    else:
        logging.error('WRONG ENTITY_TYPE')
        return False
    amt_to_transfer = 0
    for invoice in invoices:
        inv = json.loads(invoice.invoice)
        amt_to_transfer += inv['amount'] * float(split) / 100
    return amt_to_transfer


def get_partner_from_rep(promo_id):
    p = Promotional.get_by_auth_id(promo_id)
    return p.partner_id


def pay_reps():
    pass


class PayReps(webapp2.RequestHandler):

    def get(self):
        pay_reps()
        # if this is ever a cron job, make sure to put this on the backend
        self.response.write('paid reps')
