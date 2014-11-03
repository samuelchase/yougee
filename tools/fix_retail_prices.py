import models
import datetime
import wootils
import logging


# when the switch happened in GMT
# Wed Feb 19 6am PST -> Wed Feb 19 2pm GMT
dt = datetime.datetime(2014, 11, 18, 14, 0, 0)

count = 0
query = models.NearWooCampaignDS.gql(
    'where date_created < :1 order by date_created desc', dt)
for camp in wootils.iterate(query):
    count += 1
    print count, camp.date_created, camp.key.urlsafe()
    try:
        camp.billing_period = 1
        camp.home_price = 0.0
        camp.retail_price = 10.0
        camp.put()
    except Exception as e:
        logging.error('camp key %s', camp.key.urlsafe())
        logging.exception(e)

