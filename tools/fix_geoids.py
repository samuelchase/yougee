import json
import logging


import models


def fix_camp(camp):
    try:
        data = json.loads(camp.data)
        places = data.get('places', [])
        if not all([isinstance(x, dict) for x in places]):
            if all([isinstance(x, basestring) for x in places]):
                places = [
                    {'geoid': g,
                     'name': 'NearWOO',
                     'bid_type': 'auto',
                     'bid': ''} for g in places]
                data['places'] = places
                camp.data = json.dumps(data)
                camp.put()
    except:
        logging.exception('could not fix camp %s', camp.key.urlsafe())
    return camp
    

def fix_yelpie(yelpie):
    try:
        geoids = json.loads(yelpie.geoids)
        key = yelpie.key.urlsafe()
        if not all([isinstance(x, basestring) for x in geoids]):
            if all([isinstance(x, dict) for x in geoids]):
                try:
                    geoids = [d['geoid'] for d in geoids]
                    yelpie.geoids = json.dumps(geoids)
                    yelpie.put()
                except:
                    pass
    except:
        logging.exception('failed yelpie fix %s', key)
    return yelpie
        


def run(next_cursor=None):
    query = models.NearWooCampaignDS.query()
    fetch_limit = 500
    still_stuff_to_do = True
    while still_stuff_to_do:
        try:
            entities, next_cursor, still_stuff_to_do = query.fetch_page(
                fetch_limit, start_cursor=next_cursor)
            logging.warning('fetched %s entities', fetch_limit)
            if next_cursor:
                cur_str = next_cursor.urlsafe()
            else:
                cur_str = ''
            logging.error('cursor %s', cur_str) 
            for camp in entities:
                try:
                    camp = fix_camp(camp)
                    fix_yelpie(camp.yelp)
                except Exception as e:
                    logging.exception("Failed while appending: %s", e)
            # under rate circumstances, still_stuff_to_do is off,
            # in which case
            # we need to check if the returned cursor is None
            if not next_cursor:
                break
        except Exception:
            # reload from file
            pass


