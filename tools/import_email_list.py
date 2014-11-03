import sys
import csv
from models import *
from email.utils import parseaddr
import json

# cut -f2 -d, marketingcontacts.csv | sort -u | sed "s/^[ \t]*//" | sort -u >> locations.csv

#infile = sys.argv[1]

default_tz = 'America/Los_Angeles'

tzsf = 'timezones.json'
with open(tzsf, 'r') as f:
  tzs = json.loads(f.read())

def normalize_location(loc):
  if 'your area' in loc.lower():
    loc = loc.strip()
    loc = loc.lower()
    return loc
  consts = loc.split()
  newconsts = []
  for c in consts:
    c = c.strip()
    c = c.capitalize()
    newconsts.append(c)
  return ' '.join(newconsts)

def email_exists(email):
  adv1 = Advertiser.gql('where business_email = :1', email).get()
  adv2 = Advertiser.gql('where email = :1', email).get()
  adv3 = Advertiser.get_by_auth_id(email)
  return adv1 is not None or adv2 is not None or adv3 is not None

#inf = 'marketingcontacts.csv'
#inf = 'xaa'
#inf = 'xab'
#inf = 'xac'
inf = 'Purchasedleads1.csv'

with open(inf, 'r') as f:
  reader = csv.DictReader(f.readlines())

# skip if we have advertiser with email or business email
for line in reader:
  _, email = parseaddr(line['EMAIL'].strip())
  if email == '' or email_exists(email):
    continue
  # pn = line['PHONE']
  # phone = pn.strip().encode('utf-8', 'ignore')
  first_name = line['FIRST'].strip().capitalize().encode('utf-8', 'ignore')
  # last_name = line['LAST'].strip().capitalize().encode('utf-8', 'ignore')
  business_name = normalize_location(line['MERCHANT'].strip())
  business_name = business_name.encode('utf-8', 'ignore')
  loc = normalize_location(line['MARKET'].strip()).encode('utf-8', 'ignore')
  source = line['SOURCE']
  zipcode = line['ZIP']
  state = line['STATE']
  # if loc in tzs:
  #   tz = tzs[loc]['timeZoneId']
  # else:
  #   tz = default_tz
  mc = MarketingContact2.get_by_id(email)
  if mc is None:
    mc = MarketingContact2(id=email)
  # mc.phone = phone
  mc.location = loc
  # mc.timezone = tz
  mc.first_name = first_name
  # mc.last_name = last_name
  mc.email = email
  mc.business_name = business_name
  mc.source = source
  mc.zipcode = zipcode
  mc.state = state
  mc.put()

