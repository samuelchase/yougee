from models import *

search_terms = [
    'farhad',
    'flatrate',
    'great green cleaning and maid service',
    'integra physical',
    'jil landis',
    'lear capital',
    'mlb opening',
    'oxi fresh',
    'thn enterprises',
    'tone barre'
    ]

pro_camps = []
for term in search_terms:
  query = NearWooCampaignDS.gql('where search = :1', term)
  for camp in query:
    pro_camps.append(camp)

from wootils import *

def to_dict(camp):
  d = {}
  missing = 'missing'
  d['name'] = getattr(camp, 'name', missing)
  d['first invoice'] = getattr(camp, 'first_invoice_date_created_pacific', missing)
  d['neighborhoods'] = getattr(camp, 'neighborhood_ct', missing)
  d['views'] = getattr(camp, 'views', missing)
  d['partner_id'] = getattr(camp, 'partner_id', missing)
  d['promo_id'] = getattr(camp, 'promo_id', missing)
  d['key'] = str(camp.key())
  return d

fieldnames = ['name', 'first invoice', 'neighborhoods', 'views', 'partner_id',
  'promo_id', 'key']
rows = []
updated = []
for camp in pro_camps:
  rows.append(to_dict(camp))
  camp.pro = True
  camp.put()
  updated.append(camp)

csv_str = dicts_to_csv_str(rows, fieldnames=None, write_header=True)
with open('pro_campaigns.csv', 'w') as f:
  f.write(csv_str)


