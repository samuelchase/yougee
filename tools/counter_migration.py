# for remote shelling
# python -m tools.counter_migration

import datetime
import j_counter

aq = 'nearwoo'
tqs = ['day_305_2013', 'week_44_2013', 'month_11_2013',
       'week_43_2013', 'month_10_2013', 'anytime']
vcs = ['all_campaign_values', 'paid']

cn_old = 'amt'
cn_new = 'amt_plus_recurring'
for tq in tqs:
  for vc in vcs:
    old_counter_name = '_'.join([aq, tq, vc, cn_old])
    new_counter_name = '_'.join([aq, tq, vc, cn_new])
    val = j_counter.f_get_count(old_counter_name)
    print 'setting %s to %f' % (new_counter_name, val)
    j_counter.f_set_count(new_counter_name, val)

# all time
# this week
# last week
# this month
# last month
# today


