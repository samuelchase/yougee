from models import *
from wootils import *

query = NearWooCampaignDS.all()

for camp in db_iterate_cursor(query):
  _, dt = get_first_charge(camp)
  if dt is not None:
    created_pacific = strip_tz_info(to_pacific_time(dt))
    camp.has_first_invoice = True
    camp.first_invoice_date_created_pacific = created_pacific
    camp.first_invoice_year_tq = get_time_qualifier('year', dt=created_pacific)
    camp.first_invoice_month_tq = get_time_qualifier('month', dt=created_pacific)
    camp.first_invoice_week_tq = get_time_qualifier('week', dt=created_pacific)
    camp.first_invoice_day_tq = get_time_qualifier('day', dt=created_pacific)
  else:
    camp.has_first_invoice = False
    camp.first_invoice_date_created_pacific = None
    camp.first_invoice_year_tq = ''
    camp.first_invoice_month_tq = ''
    camp.first_invoice_week_tq = ''
    camp.first_invoice_day_tq = ''
  camp.put()

