from models import *
import datetime

def datetime_to_str(dt):
  if dt:
    return dt.strftime('%Y-%m-%d-%H-%M-%S')
  else:
    return 'none'

results = []

for camp in NearWooCampaignDS.all():
  print camp.name
  adv_key = ndb.Key(urlsafe=camp.advertiser_key)
  adv = adv_key.get()
  if adv:
    row = {}
    row['given_name'] = adv.given_name,
    row['family_name'] = adv.family_name,
    row['name'] = adv.name
    row['business_name'] = adv.business_name
    row['business_email'] = adv.business_email
    row['advertiser_email'] = adv.email
    row['campaign_name'] = camp.name
    row['checked_out'] = datetime_to_str(camp.checked_out)
    row['completed'] = camp.completed
    row['n_neighborhoods'] = camp.neighborhood_ct
    results.append(row)


from google.appengine.api import mail
import json
mail.send_mail(sender="alice@pagewoo.com",
               to="alice@pagewoo.com",
               subject="NearWoo Advertiser list",
               body=json.dumps(results))

### from json to csv

import csv
import json

inf = 'invoices.json'
with open(inf, 'r') as f:
  invs = json.loads(f.read())

fieldnames = set()
for inv in invs:
  card = inv['card']
  for k, v in card.items():
    nk = 'card_' + k
    inv[nk] = v
  del inv['card']
  #fee_details = inv['fee_details']
  #for k, v in fee_details.items():
  #  nk = 'fee_details_' + k
  #  inv[nk] = v
  del inv['fee_details']
  fieldnames = set(inv.keys()).union(fieldnames)


outf = 'nearwoo_invoices.csv'
with open(outf, 'w') as f:
  writer = csv.DictWriter(f, fieldnames)
  for d in invs:
    d2 = {}
    for k, v in d.items():
      if isinstance(v, (str, unicode)):
        d2[k] = v.encode('ascii', 'replace')
      else:
        d2[k] = v
    writer.writerow(d2)



