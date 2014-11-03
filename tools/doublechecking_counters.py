import datetime

from wootils import db_iterate
from wootils import strip_tz_info
from wootils import to_pacific_time
from kpi_data import get_counters_by_time
from models import NearWooCampaignDS
from models import Invoices


def get_invoices(camp_key):
  res = []
  query = Invoices.gql('where campaign_key = :1', camp_key)
  for inv in db_iterate(query):
    res.append(inv)
  return res

def show_invoices(invlist):
  for inv in invlist:
    print inv.date_created_pacific, inv.invoice_type


def todays_campaign_count(strip_free=False):
  if strip_free:
    vc = 'paid'
  else:
    vc = 'all_campaign_values'
  #agent = jconfig.get_nearwoo_agent()
  # since we're in the remote shell
  agent = 'nearwoo'
  today = strip_tz_info(to_pacific_time(datetime.datetime.today()))
  val, _ = get_counters_by_time(agent, 'day', 'ncampaigns', vc, today)
  return val


def todays_campaigns(strip_free=False):
  today = strip_tz_info(to_pacific_time(datetime.datetime.today()))
  today_start = datetime.datetime(today.year, today.month, today.day, 0, 0, 0)
  tomorrow_start = today_start + datetime.timedelta(days=1)
  camps = NearWooCampaignDS.gql('where checked_out_pacific >= :1', today_start)
  res = []
  for c in camps:
    if c.checked_out_pacific > tomorrow_start:
      continue
    if strip_free:
      if c.amount_subscribed > 0:
        res.append(c)
    else:
      res.append(c)
  return res

