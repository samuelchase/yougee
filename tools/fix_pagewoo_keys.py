# from google.appengine.ext import db
from jcampaign_mapreduce import fix_campaign_pagewoo_keys
from wootils import iterate

from models import NearWooCampaignDS
from wootils import strip_tz_info
from wootils import to_pacific_time


q1 = NearWooCampaignDS.gql('where pagewoo_campaign_key = :1', '')
q2 = NearWooCampaignDS.gql('where pagewoo_campaign_key = :1', None)
q3 = NearWooCampaignDS.gql('where checked_out = :1', None)

# todo: also set promo ids for all campaigns where we didn't attribute
# them correctly? (how??)


def looks_like_a_good_key(k):
  return k is not None and k != '' and not 'missing' in k

for i, query in enumerate([q1, q2, q3]):
  print 'starting query', i, type(query)
  count = 0
  for camp in iterate(query):
    camp = fix_campaign_pagewoo_keys(camp)
    modified = False
    if looks_like_a_good_key(camp.pagewoo_campaign_key):
      camp.completed = True 
      modified = True
    if camp.charge_day is not None:
      camp.checked_out = camp.date_created
      camp.checked_out_pacific = strip_tz_info(to_pacific_time(camp.date_created))
      modified = True
    if modified:
      camp.put()
    count += 1
    if count % 100 == 0:
      print 'yay: ', count


