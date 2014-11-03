import json
import csv
import logging
import models
from google.appengine.ext import ndb
from collections import OrderedDict

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)
query = models.NearWooCampaignDS.query()
fetch_limit = 500


outf = 'marketing.csv'
all_camps = []


fieldnames = [
    'status', 'business_name', 'name', 'yelp_contact', 'adv_pers_email',
    'adv_business_email', 'promo_id', 'partner_id', 'camp_key', 'cursor']


def main():
    ctx = ndb.get_context()
    ctx.set_memcache_policy(False)
    ctx.set_cache_policy(False)
    with open(outf, 'a') as f:
        writer = csv.DictWriter(f, fieldnames)
        writer.writeheader()
        count = 0
        still_stuff_to_do = True
        next_cursor = None
        cur_str = ''
        while still_stuff_to_do:
            try:
                entities, next_cursor, still_stuff_to_do = query.fetch_page(
                    fetch_limit, start_cursor=next_cursor)
                logging.info("Fetched %d camps" % len(entities or []))
                # advertiser_keys = [ndb.Key(urlsafe=c.advertiser_key) for c in
                #                    entities if c and c.advertiser_key]
                # yelp_keys = [ndb.Key(urlsafe=c.yelp_key) for c in entities if c
                #              and c.yelp_key]
                # found = ndb.get_multi(advertiser_keys + yelp_keys)
                # found_dict = {e.key.urlsafe(): e for e in found if e}
                if next_cursor:
                    cur_str = next_cursor.urlsafe()
                else:
                    cur_str = ''
                dcts = []
                for camp in entities:
                    try:
                        count += 1
                        # adv = found_dict.get(c.advertiser_key, None)
                        # yelp = found_dict.get(c.yelp_key, None)
                        adv = camp.advertiser
                        yelp = camp.yelp
                        result = camp_to_adv_record(camp, yelp, adv, cur_str)
                        dcts.append(result)
                        logging.info("%d: %s", count, result.get('business_name', None))
                    except Exception as e:
                        logging.exception("Failed while appending: %s", e)
                writer.writerows(dcts)
                # under rate circumstances, still_stuff_to_do is off,
                # in which case
                # we need to check if the returned cursor is None
                if not next_cursor:
                    break
            except Exception:
                # reload from file
                pass


def camp_to_adv_record(camp, yelp, adv, cursor):
    d = OrderedDict()
    d['cursor'] = cursor
    if not camp:
        return d
    try:
        d['promo_id'] = camp.rep_id
        d['partner_id'] = camp.partner_id
        d['business_name'] = camp.store or camp.name or ''
        d['camp_key'] = camp.key.urlsafe()
        logging.info("Name: %s", camp.name)

        if not camp.advertiser_key or not camp.yelp_key:
            logging.error("No advertiser key, not doing anything")

        if yelp:
            yelp_data = json.loads(yelp.yelp_data)
            d['yelp_contact'] = yelp_data.get('person', None)
        else:
            logging.error("No yelp for for %s", camp.key.urlsafe())
        if adv:
            d['name'] = adv.name
            d['adv_pers_email'] = getattr(adv, 'email', None)
            d['adv_business_email'] = getattr(adv, 'business_email', None)
        else:
            logging.error("No advertiser for %s", camp.key.urlsafe())
        if camp.neighborhood_ct > 1 or camp.home_price != 0:
            status = 'paid'
        elif camp.invoices:
            status = 'cancelled'
        else:
            status = 'free'
        d['status'] = status
    except Exception as e:
        logging.exception("Failed for camp: %s (%s)", camp.key.urlsafe(), e)
    return d

if __name__ == "__main__":
    main()
