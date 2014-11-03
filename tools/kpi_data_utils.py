import datetime
from jcounter import *
from kpi_data import *
from models import *
from wootils import *


def migrate_counters(agent, ocn, ncn, t0):
  """ migrates counters by copying from old counter name (ocn) to
  new counter name (ncn), starting from datetime t0 """
  assert ( ocn == 'amt' and ncn == 'amt_plus_recurring' or
           ocn == 'nblockgroups' and ncn == 'nblockgroups_plus_recurring' )
  assert ocn in INT_COUNTERS or ocn in FLOAT_COUNTERS
  assert ncn in INT_COUNTERS or ncn in FLOAT_COUNTERS
  is_int = ocn in INT_COUNTERS
  tN = strip_tz_info(to_pacific_time(datetime.datetime.today()))
  dt = t0
  while dt < tN:
    for tdelta in ALL_TDELTAS:
      for vc in ALL_CAMPAIGN_VALUE_CATEGORIES:
        val = get_counters_by_time(agent, tdelta, ocn, vc, [dt], add_time_labels=False)
        tq = get_time_qualifier(tdelta, dt=dt)
        inc_counters([agent], [tq], [vc], cn=ncn, amount=val)
  return True



