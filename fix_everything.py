from google.appengine.ext import ndb
import datetime
import json
import wootils
import models
import logging


def fix_wrong_adamounts_migration(camp, yelp=None, partner=None):
    yelp = yelp or camp.yelp
    if not yelp:
        logging.error("NO YELP KEY FOR %s, skipping.", camp.key.urlsafe())
        return
    partner = partner or camp.partner
    data = yelp.json_data
    if 'adamounts_migration_date' not in data:
        return
    date = datetime.datetime.strptime(data['adamounts_migration_date'], '%B %d, %Y')
    yelp.adamounts_wrong_wholesale_migration_date = date
    # if it didn't get the right migration, then we're not yet done
    if not yelp.adamounts_migration_with_wholesale_date:
        if partner:
            assert camp.partner_id in partner.auth_ids
            adamounts = data.get('adamounts') or []
            # this was the bug (previously had checked for if partner_id rather
            # than if wholesale)
            if all(a == 1000 for a in adamounts) and camp.home_price > 0 and\
                    not partner.wholesale:
                yelp.possibly_no_extra_home_block_adamount = True
    data.pop('adamounts_migration_date', None)
    yelp.yelp_data = json.dumps(data)
    yield yelp
    # return yelp.key.urlsafe(), camp.key.urlsafe()
    if False:
        yield None

# runs everything to fix stuff, success and failed should be lists so you can
# get to what succeeded and failed
def run_camps(camps, succeeded, failed):
    camps = [c for c in camps if c.yelp_key]
    yelps = []
    step = 500
    for i in range(0, len(camps), step):
        this_camps = camps[i:i+step]
        if not this_camps:
            break
        yelps += ndb.get_multi([ndb.Key(urlsafe=camp.yelp_key) for camp in
                                this_camps])
    partner_ids = set([c.partner_id for c in camps if c.partner_id])
    partners = [models.Partner.get_by_auth_id(partner_id) for partner_id in
                partner_ids]
    partner_dict = {partner_id: partner for partner in partners for partner_id
                                in partner.auth_ids}
    for camp, yelp in zip(camps, yelps):
        print "Handling camp %s (%s)" % (camp.name, camp.key.urlsafe())
        partner = partner_dict.get(camp.partner_id)
        if camp.partner_id and not partner:
            print "Didn't get partner id %s (for %s - %s)" % (camp.partner_id,
                    camp.key.urlsafe(), camp.name)
            failed.append(camp)
            continue
        try:
            succeeded.append(fix_wrong_adamounts_migration(yelp=yelp, camp=camp,
                                                         partner=partner))
        except Exception as e:
            logging.exception("camp %s failed (%s)", camp.key.urlsafe(),
                              str(e))
            failed.append(camp)
    return camps, succeeded, failed

def run_it_more():
    camps = list(wootils.iterate(models.NearWooCampaignDS.query()))
    step = 250
    succeeded, failed = [], []
    for i in range(0, len(camps), step):
        logging.info("CALLING STEP %s", step)
        run_camps(camps, succeeded=succeeded, failed=failed)
    logging.warning(succeeded)
    logging.warning([c.key.urlsafe() if hasattr(c, 'key') else None for c in failed if c])
    logging.info("DONE")

def calculate_expected_amount_subscribed(camp):
    if not camp.is_recurring:
        return
    if camp.is_wholesale:
        return
    yelp = camp.yelp
    promo = camp.promo
    try:
        num_views = sum(yelp.json_data['adamounts'])
    except Exception:
        logging.exception("FAILED OH NOES! %s", camp.key.urlsafe())
        return
    cost = (num_views / 1000) * camp.retail_price
    if promo:
        cost = promo.apply_discount(cost, first_charge=False)
    return cost


def fix_amount_subscribed(camp):
    expected = calculate_expected_amount_subscribed(camp)
    if expected is None or camp.amount_subscribed == expected:
        return
    camp.had_wrong_amount_subscribed = True
    camp.put()
    if False:
        yield
