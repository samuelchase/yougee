# run as
# nosetests --nologcapture test_kpi_data.py

import random
import copy
import datetime
from nose.tools import eq_
from collections import defaultdict

from kpi_data import INT_COUNTERS
from kpi_data import FLOAT_COUNTERS
from kpi_data import ALL_TDELTAS
from kpi_data import ALL_CAMPAIGN_VALUE_CATEGORIES
from kpi_data import get_counters_by_time
from kpi_data import track_new_campaign
from kpi_data import get_campaign_value_categories
from kpi_data import get_agent_qualifiers
from models import PromoCategory
from models import PartnerPromoCategory
from models import Promotional
from models import Partner
from models import NearWooCampaignDS

BG_PRICE = 10.0
TRIGGER_FUNCTIONS = []


def setup_package():
    TRIGGER_FUNCTIONS = [new_campaign_event]


# 1. with promo_id and partner pc
# 2. with promo_id and without partner_promo_category
# 3. without anything
def test_camp_partner_promo():
    default_pc_label = 'default_pc'
    default_pc = PromoCategory(label=default_pc_label,
          is_recurring=True,
          discount_type='percent',
          absolute_discount=25)
    default_pc.put()
    pc_label = 'pc'
    pc = PromoCategory(id=pc_label,
          label=pc_label,
          is_recurring=True,
          discount_type='percent',
          absolute_discount=5)
    pc.put()
    # create partner
    partner_id='test_partner'
    _, partner = Partner.create_user(partner_id,
            name='test_partner_name',
            partner_id=partner_id,
            nearwoo_default_promo_category=default_pc_label,
            email='partner_email')
    partner.put()
    # create partner promo category
    ppc_label = 'partner_pc'
    ppc_id = partner_id + ':' + ppc_label
    ppc = PartnerPromoCategory(id=ppc_id,
          label=ppc_label,
          nearwoo_label=pc_label,
          partner_id=partner_id,
          is_recurring=pc.is_recurring,
          discount_type=pc.discount_type,
          percent_discount=pc.percent_discount)
    ppc.put()
    ppc = ppc
    # create promotional / rep
    promo_id = 'test_promo'
    _, promo = Promotional.create_user(promo_id,
            promo_type='representative',
            promo_categories=[pc_label],
            promo_id=promo_id,
            partner_id=partner_id,
            email='promo_email')
    promo.put()
    promo = promo
    # create rudimentary campaign
    camp = NearWooCampaignDS()
    camp.name = 'test_campaign'
    camp.neighborhood_ct = 100
    camp.amount_subscribed = 900.0
    camp.partner_id = partner_id
    camp.promo_id = promo_id
    camp.put()
    camp = camp
    for f in TRIGGER_FUNCTIONS:
        yield f, camp, partner, promo


def new_campaign_event(camp, promo_id, partner_promo_category):
    agents = get_agent_qualifiers(promo_id=promo_id,
            partner_promo_category=partner_promo_category,
            camp=camp)
    before_counters = counter_snapshot(agents)
    # prepare arguments
    camp_key = str(camp.key())
    n_block_points = random.randrange(0, camp.amount_subscribed/BG_PRICE)
    amount_charged = camp.amount_subscribed-(n_block_points*10.0)
    n_block_groups = camp.neighborhood_ct
    # calculate expected outcome
    vcs = get_campaign_value_categories(camp.amount_subscribed)
    expected_diff = {
            'ncampaigns':  1,
            'amt':  amount_charged,
            'amt_plus_recurring':  amount_charged,
            'nblockgroups':  n_block_groups,
            'nblockgroups_plus_recurring':  n_block_groups,
            'nblockpoints':  n_block_points,
    }
    expected_counters = add_counter_diff(agents, before_counters,
            vcs, expected_diff)
    # make experiment
    track_new_campaign(camp_key,
                amount_charged, n_block_groups,
                n_block_points=n_block_points,
                promo_id=promo_id,
                partner_promo_category=partner_promo_category)
    # record outcome of experiment
    after_counters = counter_snapshot(agents)
    eq_(after_counters, expected_counters)


### utility functions

def counter_snapshot(agents):
    today = datetime.datetime.today()
    snapshot = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    for agent in agents:
        for counter_name in INT_COUNTERS + FLOAT_COUNTERS:
            for tdelta in ALL_TDELTAS:
                for vc in ALL_CAMPAIGN_VALUE_CATEGORIES:
                    val = get_counters_by_time(agent, tdelta,
                            counter_name, vc, [today], add_time_labels=False)[0]
                    snapshot[counter_name][tdelta][vc] = val
    return snapshot


def add_counter_diff(agents, before_counters, vcs, expected_diff):
    counter_sum = copy.deepcopy(before_counters)
    for agent in agents:
        for counter_name, diff in expected_diff.items():
            for tdelta in ALL_TDELTAS:
                for vc in vcs:
                    counter_sum[agent][counter_name][tdelta][vc] += diff
    return counter_sum


