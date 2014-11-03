import datetime
import logging
import json


import models


year = 2014 
month = 3
days = [12, 13, 14, 15, 16, 17]

# 1. get all campaigns for the dates given
# 2. exclude campaigns that were created on or after the date given
# 3. compare against invoices - ignore campaigns that have been charged on
#    or around the given date with a recurring payment
# 4. if the campaign passed through all of these filters,
#    charge customer for that campaign with payment.charge_the_customer

count = 0
free = []
charged = []
processed = []
for day in days:
    dt = datetime.datetime(year, month, day)
    logging.error('\ncharging for %s', dt)
    camps = models.NearWooCampaignDS.gql('where charge_day = :1', day)
    for camp in camps:
        count += 1
        key = camp.key.urlsafe()
        processed.append(key)
        logging.error('processing %s', key)
        if camp.amount_subscribed == 0.0:
            logging.error(' --> free campaign - reloading')
            free.append(key)
            continue
        if camp.date_created >= dt:
            logging.error(' --> created after charge date')
            continue
        # TODO: fetching only the latest 100 isn't overly failsafe, but should
        # do for most use cases
        invs = models.Invoices.gql('where campaign_key = :1', key).fetch(100)
        has_inv = False
        for inv in invs:
            # if there's a recurring charge within +- 3 days of the supposed
            # charge date - ignore
            if (inv.invoice_type == 'recurring' and 
                abs((inv.date_created-dt).days) < 3):
                logging.error(' --> found invoice "%s" from %s',
                              inv.invoice_type, inv.date_created)
                has_inv = True
                continue
        if not has_inv:
            logging.error(' --> charging customer')
            charged.append(key)


with open('free.json', 'w') as f:
    f.write(json.dumps(free))
with open('charged.json', 'w') as f:
    f.write(json.dumps(charged))


import sys
sys.exit()

with open('free.json') as f:
    free = json.loads(f.readline())
with open('charged.json') as f:
    charged = json.loads(f.readline())

import payment
actually_charged = []
for key in charged:
    try:
        payment.charge_the_customer(key)
        actually_charged.append(key)
    except:
        logging.exception('sth internally went wrong with charge')


