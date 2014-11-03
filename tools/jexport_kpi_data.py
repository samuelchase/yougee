from collections import OrderedDict
import webapp2
import datetime
import traceback
import logging

from wootils import dicts_to_csv_str
from wootils import make_status_message
from wootils import month_to_words
from wootils import add_months
from wootils import get_counter_by_time
import jconfig


AGENT = jconfig.get_nearwoo_agent()
START_DATE = datetime.datetime(2013, 7, 1, 0, 0, 0)
TO_EXPORT = OrderedDict()
TO_EXPORT['Free Campaigns'] = ('month', 'ncampaigns', 'free')
TO_EXPORT['Paid Campaigns'] = ('month', 'ncampaigns', 'paid')
TO_EXPORT['Neighborhoods'] = ('month', 'nblockgroups', 'all_campaign_values')
TO_EXPORT['Free to Paid Upgrades'] = ('month', 'paid_ncampaign_upgrades', 'free')
TO_EXPORT['Paid to Paid Upgrades'] = ('month', 'paid_ncampaign_upgrades', 'paid')
TO_EXPORT['Paid to Free Downgrades'] = ('month', 'free_ncampaign_downgrades', 'paid')
TO_EXPORT['Revenue'] = ('month', 'amt', 'all_campaign_values')


class ExportKPIData(webapp2.RequestHandler):
  def get(self):
    try:
      data = export_kpi_data()
      if len(data) > 0:
        fieldnames = data[0].keys()
        csv_str = dicts_to_csv_str(data, fieldnames=fieldnames, write_header=True)
        msg = 'requested kpi data'
        status = make_status_message(success=True, message=msg, data=csv_str)
      else:
        msg = 'no data found'
        status = make_status_message(success=False, message=msg)
    except Exception as e:
      logging.exception(e)
      tb = traceback.format_exc()
      status = make_status_message(success=False, message=tb)
    self.response.write(status)


def export_kpi_data():
  data = []
  dt = datetime.datetime.today()
  while dt.month >= START_DATE.month:
    month_data = OrderedDict()
    month_data['Month'] = month_to_words(dt)
    for fieldname, (tdelta, counter_type, cvc) in TO_EXPORT.items():
      val, _ = get_counter_by_time(AGENT, tdelta, counter_type, cvc, dt)
      print tdelta, counter_type, cvc, dt, val
      month_data[fieldname] = val
    data.append(month_data)
    dt = add_months(dt, -1)
  return data


