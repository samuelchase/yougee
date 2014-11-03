import webapp2
import json
import datetime
from collections import OrderedDict
from google.appengine.ext import ndb


from models import Advertiser
from models import NearWooCampaignDS
from models import YelpJsonDS
from wootils import iterate
from wootils import strip_tz_info
from wootils import to_pacific_time
from wootils import dicts_to_csv_str
from wootils import get_time_qualifier
from yelp import annotate_yelpjsonds


MISSING = 'missing'


class YelpInspector(object):
    def __init__(self, yelp):
        self.yelp = yelp
        if yelp.yelp_data is None or yelp.yelp_data == '':
            yelp_data = {}
        else:
            yelp_data = json.loads(yelp.yelp_data)
        self.data = yelp_data
        self.yelp_key = str(self.yelp.key())
        is_lead = False
        camp = None
        if yelp.campaign_key == '':
            is_lead = True
        else:
            try:
                camp = NearWooCampaignDS.get(yelp.campaign_key)
            except Exception:
                is_lead = True
            else:
                if camp is None or not camp.completed:
                    is_lead = True
        self.is_lead = is_lead
        self.camp = camp
        adv = None
        try:
            adv = ndb.Key(yelp.advertiser_key).get()
        except Exception:
            pass
        self.adv = adv
        # temporary fix, undo later
        if self.yelp.year_tq == '':
            self.yelp = annotate_yelpjsonds(self.yelp)
            self.yelp.put()

    def to_dict(self):
        d = OrderedDict()
        d['Yelp Campaign Name'] = self.yelp_campaign_name
        d['Yelp Contact Person'] = self.yelp_contact_person
        d['Yelp Neighborhoods'] = self.n_block_groups
        d['Yelp Phone'] = self.yelp_phone
        d['Yelp Address'] = self.yelp_address
        d['Yelp Email'] = self.yelp_email
        d['Yelp Rep ID'] = self.yelp_promo_id
        d['Yelp Partner ID'] = self.yelp_partner_id
        d['Campaign Name'] = self.camp_name
        d['Campaign Rep ID'] = self.camp_promo_id
        d['Campaign Partner ID'] = self.camp_partner_id
        d['Advertiser Name'] = self.advertiser_key
        d['Advertiser Email'] = self.advertiser_email
        d['Advertiser Business Email'] = self.advertiser_business_email
        d['Advertiser Business Phone'] = self.advertiser_business_phone
        d['Yelp Created'] = self.yelp_created
        d['Campaign Created'] = self.camp_created
        d['Advertiser Created'] = self.advertiser_created
        d['Yelp Key'] = self.yelp_key
        d['Campaign Key'] = self.camp_key
        d['Advertiser Key'] = self.advertiser_key
        return d

    @property
    def yelp_campaign_name(self):
        return self.data.get('name', MISSING)

    @property
    def yelp_contact_person(self):
        return self.data.get('person', MISSING)

    @property
    def n_block_groups(self):
        yelp = self.yelp
        n_block_groups = -1
        if yelp.geoids is None or yelp.geoids == '':
            yelp.geoids = json.dumps([])
            yelp.put()
        else:
            n_block_groups = len(json.loads(yelp.geoids))
        return n_block_groups

    @property
    def yelp_phone(self):
        return self.data.get('phone', MISSING)

    @property
    def yelp_address(self):
        return self.data.get('address', MISSING)

    @property
    def yelp_email(self):
        return self.data.get('email', MISSING)

    @property
    def yelp_created(self):
        return strip_tz_info(to_pacific_time(self.yelp.date_created))

    @property
    def yelp_promo_id(self):
        return getattr(self.yelp, 'promo_id', MISSING)

    @property
    def yelp_partner_id(self):
        return getattr(self.yelp, 'partner_id', MISSING)

    @property
    def camp_name(self):
        return getattr(self.camp, 'name', MISSING)

    @property
    def camp_promo_id(self):
        return getattr(self.camp, 'promo_id', MISSING)

    @property
    def camp_partner_id(self):
        return getattr(self.camp, 'partner_id', MISSING)

    @property
    def camp_created(self):
        created = getattr(self.camp, 'date_created', MISSING)
        if isinstance(created, datetime.datetime):
            created = strip_tz_info(to_pacific_time(created))
        return created

    @property
    def camp_key(self):
        key = MISSING
        if isinstance(self.camp, NearWooCampaignDS):
            key = str(self.camp.key())
        return key

    @property
    def advertiser_name(self):
        return getattr(self.adv, 'name', MISSING)

    @property
    def advertiser_key(self):
        key = MISSING
        if isinstance(self.adv, Advertiser):
            key = self.adv.key.urlsafe()
        return key

    @property
    def advertiser_email(self):
        return getattr(self.adv, 'email', MISSING)

    @property
    def advertiser_business_phone(self):
        return getattr(self.adv, 'business_phone', MISSING)

    @property
    def advertiser_business_email(self):
        return getattr(self.adv, 'business_email', MISSING)

    @property
    def advertiser_created(self):
        created = getattr(self.adv, 'created', MISSING)
        if isinstance(created, datetime.datetime):
            created = strip_tz_info(to_pacific_time(created))
        return created


class YelpLeadGenerator(object):
    def __init__(self, year=None, month=None):
        self.leads = []
        self.year = year
        self.month = month
        self.month_tq = None
        if self.year is not None and self.month is not None:
            self.month_tq = get_time_qualifier('month',
                                               dt=datetime.datetime(year, month, 1))

    def populate(self):
        query = YelpJsonDS.all()
        if self.month_tq is not None:
            query = YelpJsonDS.gql('where month_tq = :1', self.month_tq)
        for yelp in iterate(query):
            inspector = YelpInspector(yelp)
            if inspector.is_lead:
                self.leads.append(inspector.to_dict())

    def to_csv_str(self):
        csv_str = ''
        if len(self.leads) > 0:
            fieldnames = self.leads[0].keys()
            csv_str = dicts_to_csv_str(self.leads, fieldnames=fieldnames,
                                       write_header=True)
        return csv_str


def all_yelp_leads_to_file():
    lead_generator = YelpLeadGenerator()
    lead_generator.populate()
    csv_str = lead_generator.to_csv_str()
    fn = 'yelp_leads.csv'
    with open(fn, 'w') as f:
        f.write(csv_str)


class YelpLeadGeneratorHandler(webapp2.RequestHandler):
    def get(self):
        month = self.request.get('month', None)
        year = self.request.get('year', None)
        if month is not None:
            month = int(month)
        if year is not None:
            year = int(year)
        lead_generator = YelpLeadGenerator(year=year, month=month)
        lead_generator.populate()
        csv_str = lead_generator.to_csv_str()
        fn = 'yelp_leads.csv'
        self.response.headers["Content-Type"] = 'text/csv'
        self.response.headers[
            'Content-Disposition'] = 'attachment; filename=' + fn
        self.response.write(csv_str)


