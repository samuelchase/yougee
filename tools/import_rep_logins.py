from webapp2_extras.appengine.auth.models import Unique
from models import *
import csv
from partner_promo_shared import *


lang = Partner.get_by_auth_id('lang')
# make new partners
new_partners = [
  ('dailynews', 'DailyNews'),
  ('inlandvalley', 'InlandValley'),
  ('lanewsgroup', 'LANewsGroup'),
  ('sgvtribune', 'SGVTribute'),
  ('southbay', 'SouthBay'),
  ]
for np, np_name in new_partners:
  p = Partner.get_by_auth_id(np)
  p.set_password('password')
  p.put()

copy_attrs = ['contact_person', 'email', 'neighborhood_multiplier', 'payment_password',
    'phone', 'partner_admin', 'nearwoo_default_promo_category', 'nearwoo_promo_categories',
    'preselected', 'price_multiplier', 'revenue_split', 'revenue_split_first_month',
    'stripe_id', 'stripe_recipient_key', 'stripe_token', 'verified', 'wholesale',
    'wholesale_price', 'neighborhood_multiplier']
for np, np_name in new_partners:
  ok, p = Partner.create_user(np, partner_id=np, email=lang.email)
  if not ok:
    p = Partner.get_by_auth_id(np)
  for attr in copy_attrs:
    setattr(p, attr, getattr(lang, attr))
  p.partner_admin = 'lang'
  p.name = np_name
  p.set_password(np+'password')
  p.put()

"""
for np in new_partners:
  p = Partner.get_by_auth_id(np)
  print np, p


uu = ndb.Key(Unique, 'Partner.auth_id:dailynews')
Unique.get_by_id('Partner.auth_id:dailynews')
""""

inf = 'suntimes3.csv'
with open(inf, 'r') as f:
  reps = csv.DictReader(f.readlines())

for rep in reps:
  name = rep['name']
  phone = rep['phone']
  email = rep['email']
  partner_id = rep['partner_id'].lower()
  partner = Partner.get_by_auth_id(partner_id)
  promo_id = rep['username'].lower()
  password = rep['password']
  ok, promo = Promotional.create_user(promo_id,
                  promo_id=promo_id,
                  partner_id=partner_id,
                  promo_type='representative',
                  name=name,
                  phone=phone,
                  email=email)
  if not promo_id in partner.promotionals:
    partner.promotionals.append(promo_id)
    partner.put()
  if not ok:
    promo = Promotional.get_by_auth_id(promo_id)
  create_promotional_uri_segment(promo, promo_id)
  promo.set_password(password)
  promo.put()



sgv = Partner.get_by_auth_id('sgvtribune')
daily = Partner.get_by_auth_id('dailynews')

walkid = 'f6f89472'
walk = Promotional.get_by_auth_id(walkid)

sgv.promotionals.remove(walkid)
daily.promotionals.append(walkid)

walk.partner_id = 'dailynews'

sgv.put()
daily.put()

