#### loop over all yelpjsonds that have a promo id and set rep_build_status
from models import *

c = 0
for p in Partner.query():
  still_stuff_to_do = True
  query = YelpJsonDS.gql('where partner_id = :1', p.partner_id)
  while still_stuff_to_do:
    for yelp in query.fetch(1000):
      c += 1
      if c % 100 == 0:
        print c
      camp = get_campaign_by_yelp(str(yelp.key()))
      if not camp:
        yelp.rep_build_status = 'incomplete'
      elif camp.completed:
        yelp.rep_build_status = 'live'
      elif yelp.waiting_for_content:
        yelp.rep_build_status = 'incomplete'
      else:
        yelp.rep_build_status = 'complete'
      print str(yelp.key()), yelp.promo_id, yelp.partner_id, yelp.rep_build_status
      yelp.put()
    cursor = query.cursor()
    print cursor
    still_stuff_to_do = query.count(limit=1) > 0
    query = query.with_cursor(cursor)
  print c

#### reassign campaign from rep to another rep
from models import *

camp_key = 'aglzfm5lYXJ3b29yGgsSEU5lYXJXb29DYW1wYWlnbkRTGMLgvwMM'
from_rep_id = 'sandyhofacker'
to_rep_id = 'lisazahler'

camp = NearWooCampaignDS.get(camp_key)
from_rep = Promotional.get_by_auth_id(from_rep_id)
to_rep = Promotional.get_by_auth_id(to_rep_id)

camp.promo_id = to_rep.promo_id
camp.partner_id = to_rep.partner_id

from_rep.campaigns.remove(camp_key)
to_rep.campaigns.append(camp_key)

# theoretically also need to update applied and applied_to

from_partner = Partner.get_by_auth_id(from_rep.partner_id)
to_partner = Partner.get_by_auth_id(to_rep.partner_id)

from_partner.campaigns.remove(camp_key)
to_partner.campaigns.append(camp_key)

camp.put()
from_rep.put()
to_rep.put()
from_partner.put()
to_partner.put()

#### db cursor iteration

still_stuff_to_do = True
query = NearWooCampaignDS.gql('where is_live = :1', True)
c = 0

while still_stuff_to_do:
  for camp in query:
    push_charge_day(camp)
    c += 1
    if c % 100 == 0 and c > 0:
      print c
  cursor = query.cursor()
  still_stuff_to_do = query.count(limit=1) > 0
  query = query.with_cursor(cursor)

query = NearWooCampaignDS.gql('where is_live = :1', True)
c = 0
while still_stuff_to_do:
  c += query.count()
  cursor = query.cursor()
  print 'cursor: ' + cursor
  still_stuff_to_do = query.count(limit=1) > 0
  print still_stuff_to_do
  query = query.with_cursor(cursor)
  print 'got query'

### ndb cursor query iteration

#### perhaps write a generator for this one
query = AppsAndSites.query()
still_stuff_to_do = True
fetch_limit = 1000
results = []
count = 0
curs=None
while still_stuff_to_do:
  apps, curs, still_stuff_to_do = query.fetch_page(fetch_limit, start_cursor=curs)
  for a in apps:
    count += 1
    if count > 0 and count % 100 == 0:
      print count
    if any(t in a.name for t in tags):
      results.append(a.name)
      print a.name_unformatted, a.name


### this one is in wootils nowadays:
### see how many paid campaigns where checked out on a given day

from models import *
import datetime
from kpi_data import *

dt_lower = datetime.datetime(2013, 10, 14, 0, 0, 0)
dt_upper = datetime.datetime(2013, 10, 15, 0, 0, 0)
camps = NearWooCampaignDS.gql('where checked_out_pacific >= :1', dt_lower)
i = 1
for camp in camps:
  if camp.amount_subscribed > 0.0 and camp.checked_out_pacific < dt_upper:
    print i, camp.name, camp.checked_out_pacific
    i += 1

agent = 'nearwoo'
tdelta = 'day'
counter_type = 'ncampaigns'
campaign_value_category = 'paid'
count = get_counters_by_time(agent, tdelta, counter_type, campaign_value_category, [dt_lower])

###
