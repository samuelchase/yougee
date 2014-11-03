import sys
import csv
#from models import *
from email.utils import parseaddr
import json

# cut -f2 -d, marketingcontacts.csv | sort -u | sed "s/^[ \t]*//" | sort -u >> locations.csv

#infile = sys.argv[1]

default_tz = 'America/Los_Angeles'

tzsf = 'timezones.json'
with open(tzsf, 'r') as f:
  tzs = json.loads(f.read())


def capitalize_each_word(s):
  consts = s.split()
  newconsts = []
  for c in consts:
    c = c.strip()
    c = c.capitalize()
    newconsts.append(c)
  return ' '.join(newconsts)


"""
def email_exists(email):
  adv1 = Advertiser.gql('where business_email = :1', email).get()
  adv2 = Advertiser.gql('where email = :1', email).get()
  adv3 = Advertiser.get_by_auth_id(email)
  return adv1 is not None or adv2 is not None or adv3 is not None
"""


def UnicodeDictReader(utf8_data, **kwargs):
  csv_reader = csv.DictReader(utf8_data, **kwargs)
  for row in csv_reader:
    yield dict([(key, unicode(value, 'utf-8')) for key, value in row.iteritems()])


inf = 'marketingcontacts.csv'

with open(inf, 'r') as f:
  reader = csv.DictReader(f.readlines())

fieldnames = ['email', 'phone', 'first_name', 'last_name', 'timezone',
    'business_name', 'location']

outf = 'marketingcontacts_formatted.csv'
with open(outf, 'w') as f:
  writer = csv.DictWriter(f, fieldnames)
  for line in reader:
    _, email = parseaddr(line['EMAIL'].strip())
    if email == '':
      continue
    d = {}
    d['email'] = email
    d['phone'] = line['PHONE'].strip()
    d['first_name'] = capitalize_each_word(line['FIRST'].strip())
    d['last_name'] = capitalize_each_word(line['LAST'].strip())
    business_name = capitalize_each_word(line['MERCHANT'].strip())
    d['business_name'] = business_name
    loc = capitalize_each_word(line['MARKET'].strip())
    if loc in tzs:
      d['timezone'] = tzs[loc]['timeZoneId']
    else:
      d['timezone'] = default_tz
    d['location'] = loc
    writer.writerow(d)

