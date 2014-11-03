from models import *
from wootils import *
import json


count = 0
query = Invoices.all()
for inv in db_iterate_cursor(query):
  count += 1
  charge = json.loads(inv.charge)
  created_pacific = strip_tz_info(to_pacific_time(inv.date_created))
  inv.date_created_pacific = created_pacific
  inv.year_tq = get_time_qualifier('year', dt=created_pacific)
  inv.month_tq = get_time_qualifier('month', dt=created_pacific)
  inv.week_tq = get_time_qualifier('week', dt=created_pacific)
  inv.day_tq = get_time_qualifier('day', dt=created_pacific)
  inv.charge_amount = charge['amount'] / 100.0
  if count % 100 == 0:
    print count, ' invoices done'
  if (inv.partner_id is None or inv.partner_id == '' or
      inv.rep_id is None or inv.rep_id == '' or
      inv.promo_id is None or inv.promo_id == ''):
    camp = NearWooCampaignDS.get(inv.campaign_key)
    if (camp is not None and camp.promo_id != '' and
        camp.partner_id != ''):
      inv.promo_id = camp.promo_id
      inv.rep_id = camp.promo_id
      inv.partner_id = camp.partner_id
  inv.put()


count = 0
query = Invoices.all()
for inv in db_iterate_cursor(query):
  count += 1
  if count % 100 == 0:
    print count, ' invoices done'


